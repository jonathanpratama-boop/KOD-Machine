#!/usr/bin/env python3
"""Read-only dead-man's switch and daily status line for the KOD observation cohort.

Reads exactly three things on the timing server:
  /etc/kod/observation-plan.json   the frozen plan (observe.py --plan)
  /var/lib/kod/schedule/           observe.py's receipts: slot-NN/begin.json, end.json, HALTED.json
  /opt/kod/audit/DEPLOYMENT.json   the deployment record; its plan_sha256 pins the plan file bytes
and sends one HTTPS POST per run to a monitoring check: the check's ping URL when healthy, or
that URL with "/fail" appended (the healthchecks.io ping convention). The ping URLs come only
from the environment (KOD_WATCH_SLOT_URL, KOD_WATCH_DAILY_URL; systemd loads them from
/etc/kod/watch.env) and are never printed in full.

Health rule. A slot is judged once scheduled_at + late_after_seconds + grace has passed. It is
healthy only if its end.json is a receipt for that slot under this plan with status CAPTURED.
Any other status (PARTIAL, BLOCKED, MISSED, INTERRUPTED, FAILED), a missing or unreadable
end.json, HALTED.json, or a plan whose bytes differ from the deployment record is a failure
with a reason. The plan has two digests and both are checked: DEPLOYMENT.json records sha256
of the file bytes; observe.py writes sha256(json.dumps(plan, sort_keys=True)) into receipts.

Alerting rule. "slot" mode reports the latest judged slot: it pings /fail when that slot or a
standing condition (HALTED.json, plan mismatch, unreadable inputs) fails. Earlier failures are
repeated in the body but do not keep the check failed, so a later outage still raises a new
alert. "daily" mode sends the one-line summary and pings /fail when a slot judged in the last
24 hours failed or a standing condition holds. After the final slot has been reported, slot
mode sends nothing ("QUIET"); the operator then disables the slot timer.

Boundaries. Never creates, writes, renames, locks or deletes anything; it only reads KOD files.
It does not start, retry, repair or backfill an observation and has no dependency on the
observation scheduler, so a monitoring failure cannot reach the schedule. It reads no market
data and makes no other network request.

Not claimed. CAPTURED means observe.py recorded CAPTURED after its own integrity check; this
watcher does not re-verify capture evidence, clocks or backups (kod-status and timing-status
do that). A delivered ping proves only that the monitoring service accepted it.

Standard library only; tested on CPython 3.12 and 3.13.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import json
import os
from pathlib import Path
import ssl
import sys
import time
import traceback
import urllib.error
import urllib.parse
import urllib.request

UTC = timezone.utc
WIB = timezone(timedelta(hours=7), "WIB")  # Indonesia Western Time; no daylight saving
PLAN = Path("/etc/kod/observation-plan.json")
SCHEDULE = Path("/var/lib/kod/schedule")
DEPLOYMENT = Path("/opt/kod/audit/DEPLOYMENT.json")
# kod-watch-slot.timer fires 720 s after each slot; late_after_seconds is 600 in the deployed
# plan, so the grace must stay below 120 s for a run to judge the slot it follows.
GRACE_SECONDS = 60
SLOT_PERIOD = timedelta(hours=4)  # spacing of the plan's slots and of kod-watch-slot.timer
DAILY_PERIOD = timedelta(days=1)  # kod-watch-daily.timer
URL_VARIABLES = {"slot": "KOD_WATCH_SLOT_URL", "daily": "KOD_WATCH_DAILY_URL"}
TIMEOUT_SECONDS = 10
RETRY_DELAYS_SECONDS = (2, 4, 8)  # up to three retries after the first attempt
STATUSES = ("CAPTURED", "PARTIAL", "BLOCKED", "MISSED", "INTERRUPTED", "FAILED")
DETAIL_LIMIT = 160
DISABLE = "disable kod-watch-slot.timer and pause the slot check"
FINISHED = f"slot watch finished: {DISABLE}"


class ConfigError(ValueError):
    """The watcher's own configuration is unusable; nothing is sent."""


@dataclass(frozen=True)
class SlotHealth:
    number: int
    scheduled_at: datetime
    deadline: datetime
    code: str | None  # None until the deadline has passed
    detail: str = ""


@dataclass(frozen=True)
class Assessment:
    slots: tuple[SlotHealth, ...]
    problems: tuple[str, ...]


@dataclass(frozen=True)
class Message:
    result: str  # OK, FAIL or QUIET
    body: str


def stamp(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _minute(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%MZ")


def _wib(value: datetime) -> str:
    local = value.astimezone(WIB)
    if local.date() == value.astimezone(UTC).date():
        return local.strftime("%H:%M WIB")
    return local.strftime("%Y-%m-%d %H:%M WIB")


def _parse_time(text) -> datetime:
    if not isinstance(text, str):
        raise ValueError(f"slot {text!r} is not a timestamp string")
    value = datetime.fromisoformat(text.replace("Z", "+00:00"))
    if value.utcoffset() is None:
        raise ValueError(f"slot {text} has no UTC offset")
    if value.second or value.microsecond:
        raise ValueError(f"slot {text} is not on a whole minute")
    return value.astimezone(UTC)


def _clip(text) -> str:
    flat = " ".join(str(text).split())
    return flat if len(flat) <= DETAIL_LIMIT else flat[: DETAIL_LIMIT - 3] + "..."


def _os_error(path: Path, exc: OSError) -> str:
    return f"{path}: {exc.strerror or type(exc).__name__}"


def receipt_plan_digest(plan: dict) -> str:
    """The plan digest observe.py writes into every receipt."""
    return hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()


def _plan_slots(plan) -> tuple[list[str], list[datetime], int]:
    if not isinstance(plan, dict):
        raise ValueError("plan is not a JSON object")
    texts, late = plan.get("slots"), plan.get("late_after_seconds")
    if not isinstance(texts, list) or not texts:
        raise ValueError("slots must be a non-empty list")
    if not isinstance(late, int) or isinstance(late, bool) or late < 0:
        raise ValueError("late_after_seconds must be a non-negative integer")
    times = [_parse_time(text) for text in texts]
    for number, (earlier, later) in enumerate(zip(times, times[1:]), start=1):
        if later - earlier != SLOT_PERIOD:
            raise ValueError(f"slots {number} and {number + 1} are not four hours apart")
    return texts, times, late


def _deployment_problem(path: Path, plan_bytes: bytes) -> str | None:
    try:
        record = json.loads(path.read_bytes())
    except OSError as exc:
        return f"deployment record unreadable: {_os_error(path, exc)}"
    except ValueError:
        return f"deployment record invalid: {path} is not JSON"
    recorded = record.get("plan_sha256") if isinstance(record, dict) else None
    if not isinstance(recorded, str) or len(recorded) != 64:
        return f"deployment record invalid: {path} has no plan_sha256"
    observed = hashlib.sha256(plan_bytes).hexdigest()
    if observed != recorded:
        return f"plan sha256 {observed[:12]} differs from deployment record {recorded[:12]}"
    return None


def _halt_problem(schedule: Path) -> str | None:
    path = schedule / "HALTED.json"
    if not path.exists():
        return None
    try:
        receipt = json.loads(path.read_bytes())
    except OSError as exc:
        return f"HALTED.json present (unreadable: {exc.strerror or type(exc).__name__})"
    except ValueError:
        return "HALTED.json present (not JSON)"
    if not isinstance(receipt, dict):
        return "HALTED.json present (not a receipt)"
    cause = f"slot {receipt.get('slot')} {receipt.get('status')}"
    if receipt.get("error"):
        cause += f": {_clip(receipt['error'])}"
    return f"HALTED.json present ({cause})"


def _slot_health(folder: Path, number: int, scheduled: str, digest: str) -> tuple[str, str]:
    end = folder / "end.json"
    try:
        raw = end.read_bytes()
    except FileNotFoundError:
        if (folder / "begin.json").exists():
            return "UNFINISHED", "begin.json without end.json (interrupted or still running)"
        return "NOT_STARTED", "no begin.json or end.json"
    except OSError as exc:
        return "INVALID_RECEIPT", f"end.json unreadable: {exc.strerror or type(exc).__name__}"
    try:
        receipt = json.loads(raw)
    except ValueError:
        return "INVALID_RECEIPT", "end.json is not JSON"
    if not isinstance(receipt, dict):
        return "INVALID_RECEIPT", "end.json is not a receipt object"
    if receipt.get("slot") != number or receipt.get("scheduled_at") != scheduled:
        found = f"slot {receipt.get('slot')} scheduled {receipt.get('scheduled_at')}"
        return "INVALID_RECEIPT", _clip(f"end.json is for {found}")
    if receipt.get("plan_sha256") != digest:
        return "INVALID_RECEIPT", "end.json plan_sha256 differs from the plan"
    status = receipt.get("status")
    if status not in STATUSES:
        return "INVALID_RECEIPT", _clip(f"end.json status {status!r} is not a known status")
    if status == "CAPTURED":
        return status, ""
    return status, _clip(receipt.get("reason") or receipt.get("error") or "")


def assess(
    plan_path: Path, schedule: Path, deployment_path: Path, now: datetime, grace_seconds: int
) -> Assessment:
    """Judge every slot whose deadline has passed; read-only on all three inputs."""
    problems = []
    slots = []
    try:
        plan_bytes = Path(plan_path).read_bytes()
    except OSError as exc:
        plan_bytes = None
        problems.append(f"plan unreadable: {_os_error(Path(plan_path), exc)}")
    if plan_bytes is not None:
        mismatch = _deployment_problem(Path(deployment_path), plan_bytes)
        if mismatch:
            problems.append(mismatch)
        try:
            plan = json.loads(plan_bytes)
            texts, times, late = _plan_slots(plan)
        except ValueError as exc:
            problems.append(f"plan invalid: {exc}")
        else:
            digest = receipt_plan_digest(plan)
            margin = timedelta(seconds=late + grace_seconds)
            for number, (text, scheduled) in enumerate(zip(texts, times), start=1):
                deadline = scheduled + margin
                if now > deadline:
                    folder = Path(schedule) / f"slot-{number:02d}"
                    code, detail = _slot_health(folder, number, text, digest)
                    slots.append(SlotHealth(number, scheduled, deadline, code, detail))
                else:
                    slots.append(SlotHealth(number, scheduled, deadline, None))
    halted = _halt_problem(Path(schedule))
    if halted:
        problems.append(halted)
    return Assessment(tuple(slots), tuple(problems))


def _ranges(numbers: list[int]) -> str:
    spans = []
    for number in numbers:
        if spans and number == spans[-1][1] + 1:
            spans[-1][1] = number
        else:
            spans.append([number, number])
    return ",".join(str(a) if a == b else f"{a}-{b}" for a, b in spans)


def _tally(judged: list[SlotHealth]) -> str:
    captured = [s.number for s in judged if s.code == "CAPTURED"]
    failed = [s for s in judged if s.code != "CAPTURED"]
    if captured:
        label = "slot" if len(captured) == 1 else "slots"
        text = f"{label} {_ranges(captured)} CAPTURED"
    else:
        text = "no slot CAPTURED"
    text += f", {len(failed)} failed"
    if failed:
        text += " (" + ", ".join(f"{s.number} {s.code}" for s in failed) + ")"
    return text


def _next(assessment: Assessment) -> str | None:
    for slot in assessment.slots:
        if slot.code is None:
            return f"next {_minute(slot.scheduled_at)} ({_wib(slot.scheduled_at)})"
    return None


def slot_message(assessment: Assessment, now: datetime) -> Message:
    """Report the latest judged slot; QUIET once the final slot was reported a period ago."""
    if not assessment.slots:
        return Message("FAIL", "KOD FAIL: " + "; ".join(assessment.problems))
    judged = [s for s in assessment.slots if s.code is not None]
    latest = judged[-1] if judged else None
    final = latest is assessment.slots[-1]
    if final and now - latest.deadline >= SLOT_PERIOD:
        return Message("QUIET", f"nothing sent: cohort complete and already reported; {DISABLE}")
    clauses = list(assessment.problems)
    if latest is None:
        clauses.append("no slot due yet")
    else:
        subject = f"slot {latest.number} {_minute(latest.scheduled_at)} {latest.code}"
        clauses += [f"{subject}: {latest.detail}" if latest.detail else subject, _tally(judged)]
    clauses.append(FINISHED if final else _next(assessment))
    failed = bool(assessment.problems) or (latest is not None and latest.code != "CAPTURED")
    result = "FAIL" if failed else "OK"
    head = f"KOD {result} COHORT COMPLETE" if final else f"KOD {result}"
    return Message(result, f"{head}: " + "; ".join(clauses))


def daily_message(assessment: Assessment, now: datetime) -> Message:
    """One line for the UTC day; FAIL if a slot judged in the last 24 hours failed."""
    judged = [s for s in assessment.slots if s.code is not None]
    recent = [s for s in judged if s.deadline > now - DAILY_PERIOD]
    failed = bool(assessment.problems) or any(s.code != "CAPTURED" for s in recent)
    clauses = list(assessment.problems)
    if assessment.slots:
        summary = _tally(judged) if judged else "no slot due yet"
        clauses.append(f"{summary}, {_next(assessment) or 'cohort complete'}")
    line = "; ".join(clauses)
    return Message("FAIL" if failed else "OK", f"KOD {now.astimezone(UTC).date()}: {line}")


def ping_url(environ, mode: str) -> str:
    name = URL_VARIABLES[mode]
    value = environ.get(name, "")
    if not value:
        raise ConfigError(f"{name} is not set; add it to /etc/kod/watch.env (see INSTALL.md)")
    parts = urllib.parse.urlsplit(value)
    if parts.scheme != "https" or any(character.isspace() for character in value):
        raise ConfigError(f"{name} must be an https:// URL without spaces")
    # Test the raw text: a bare trailing "?" or "#" parses as an empty query or fragment, yet
    # url + "/fail" would then become a query or fragment of the success URL.
    if "?" in value or "#" in value or parts.username or parts.password or not parts.hostname:
        raise ConfigError(
            f"{name} must be https://host/path without credentials, query or fragment"
        )
    path = parts.path.rstrip("/")
    if not path:
        raise ConfigError(f"{name} must include the check path, not only the host")
    if path.endswith(("/fail", "/start", "/log")):
        raise ConfigError(f"{name} must be the check's base ping URL, not its /fail or /start URL")
    return value.rstrip("/")


def redact(url: str, fail: bool) -> str:
    return f"https://{urllib.parse.urlsplit(url).netloc}/..." + ("/fail" if fail else "")


class _RefuseRedirect(urllib.request.HTTPRedirectHandler):
    """A ping reaches the configured HTTPS URL or fails; it is never redirected."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def open_https(request: urllib.request.Request, timeout: float):
    context = ssl.create_default_context()
    handlers = (_RefuseRedirect(), urllib.request.HTTPSHandler(context=context))
    return urllib.request.build_opener(*handlers).open(request, timeout=timeout)


def _describe(exc: Exception) -> str:
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}"
    if isinstance(exc, urllib.error.URLError):
        return f"URLError: {exc.reason}"
    return f"{type(exc).__name__}: {exc}"


def deliver(url: str, body: str, *, fail: bool, open_url, sleep) -> tuple[bool, int, list[str]]:
    """POST to the ping (or /fail) URL with up to three retries; network errors are returned."""
    target = url + "/fail" if fail else url
    headers = {"Content-Type": "text/plain; charset=utf-8", "User-Agent": "kod-watch/1"}
    errors = []
    for attempt, delay in enumerate((0, *RETRY_DELAYS_SECONDS), start=1):
        if delay:
            sleep(delay)
        request = urllib.request.Request(target, body.encode("utf-8"), headers, method="POST")
        try:
            with open_url(request, TIMEOUT_SECONDS) as response:
                status = response.status
        except (OSError, http.client.HTTPException) as exc:
            errors.append(f"attempt {attempt}: {_describe(exc)}")
            continue
        if 200 <= status < 300:
            return True, attempt, errors
        errors.append(f"attempt {attempt}: HTTP {status}")
    return False, attempt, errors


def _grace(text: str) -> int:
    try:
        value = int(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"grace must be whole seconds, not {text!r}") from None
    if value < 0:
        raise argparse.ArgumentTypeError("grace must be zero or more seconds")
    return value


def main(
    argv=None,
    *,
    environ=os.environ,
    clock=lambda: datetime.now(UTC),
    open_url=open_https,
    sleep=time.sleep,
    stdout=sys.stdout,
    stderr=sys.stderr,
) -> int:
    parser = argparse.ArgumentParser(description="Read-only KOD cohort watch.")
    parser.add_argument("mode", choices=sorted(URL_VARIABLES))
    parser.add_argument("--plan", type=Path, default=PLAN, help="frozen plan (read only)")
    parser.add_argument("--schedule", type=Path, default=SCHEDULE, help="receipts (read only)")
    parser.add_argument("--deployment", type=Path, default=DEPLOYMENT, help="deployment record")
    parser.add_argument(
        "--grace-seconds", type=_grace, default=GRACE_SECONDS, help="added to late_after_seconds"
    )
    parser.add_argument("--dry-run", action="store_true", help="print the ping; send nothing")
    args = parser.parse_args(argv)
    try:
        url = ping_url(environ, args.mode)
    except ConfigError as exc:
        print(f"kod-watch: {exc}", file=stderr)
        return 2
    now = clock()
    compose = slot_message if args.mode == "slot" else daily_message
    try:
        message = compose(
            assess(args.plan, args.schedule, args.deployment, now, args.grace_seconds), now
        )
    except Exception as exc:  # an unexpected watcher defect is reported, never swallowed
        traceback.print_exc(file=stderr)
        problem = f"watcher error: {type(exc).__name__}: {_clip(exc)}"
        message = compose(Assessment((), (problem,)), now)
    record = {
        "mode": args.mode,
        "as_of": stamp(now),
        "result": message.result,
        "body": message.body,
        "dry_run": args.dry_run,
        "target": None,
        "delivered": None,
        "attempts": 0,
        "errors": [],
    }
    if message.result != "QUIET":
        fail = message.result == "FAIL"
        record["target"] = redact(url, fail)
        if not args.dry_run:
            delivered, attempts, errors = deliver(
                url, message.body, fail=fail, open_url=open_url, sleep=sleep
            )
            record.update(delivered=delivered, attempts=attempts, errors=errors)
    print(json.dumps(record, sort_keys=True), file=stdout)
    if record["delivered"] is False:
        detail = "; ".join(record["errors"])
        print(
            f"kod-watch: ping not delivered after {record['attempts']} attempts: {detail}",
            file=stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
