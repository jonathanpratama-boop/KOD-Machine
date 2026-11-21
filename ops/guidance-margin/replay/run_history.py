"""Run a sealed historical guidance pilot using KOD's shared model credit ledger."""

import argparse
import fcntl
import json
import os
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from idxsig import guidance_margin_feed as feed
from idxsig import guidance_margin_reader as reader
from idxsig.guidance_margin_facts import qualify
from idxsig.provenance import publish_bytes

PREFIX = "replay-low-panw-2025:"
SUBBUDGET = 10
MODEL = feed.DEFAULT_MODEL


def read(path):
    return json.loads(path.read_text())


def seal(path, value):
    raw = (json.dumps(value, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    if path.exists():
        if path.read_bytes() != raw:
            raise ValueError("Sealed file differs: " + path.name)
    else:
        publish_bytes(path, raw)
    return feed.sha(raw)


def call(live, label, size, out, function):
    lock = live / ".feed.lock"
    with lock.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        shared = read(live / "feed_state.json")
        if shared["model"] != MODEL:
            raise ValueError("Previously specified reader unavailable")
        ledger = shared.get("api_reservations", {})
        receipt = out / "result.json"
        if label in ledger:
            if not receipt.exists():
                raise RuntimeError("Indeterminate paid intent; inspect before retry")
            result = read(receipt)
            if ledger[label]["status"] == "UNSETTLED":
                feed.settle_call(live, shared, label, result)
            return result
        if out.exists():
            raise ValueError("Unrecorded output directory")
        used = sum(row["usd"] for key, row in ledger.items() if key.startswith(PREFIX))
        if used + feed.reservation_cost(shared, size) > SUBBUDGET:
            raise RuntimeError("Historical subbudget reached")
        error = feed.reserve_call(live, shared, size, label)
        if error:
            raise RuntimeError(error)
    result = function()
    with lock.open("a") as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
        shared = read(live / "feed_state.json")
        if shared["api_reservations"][label]["status"] == "UNSETTLED":
            feed.settle_call(live, shared, label, result)
    return result


def getdoc(root, url):
    identifier = feed.sha(url.encode())[:24]
    paths = list((root / "sources" / identifier).glob("*.json"))
    if len(paths) > 1:
        raise ValueError("Ambiguous retained version")
    return read(paths[0]) if paths else feed.retain_source(root, url)


def prepare(root, item, issuer, require_matching_intermediates=True):
    current = getdoc(root, item["url"])
    events = issuer["links"][item["index"] + 1 :]
    intervening = []
    remaining = feed.moment(current["published_at"]) - timedelta(days=200)
    after = feed.moment(current["published_at"])
    if not current.get("wire_account"):
        raise ValueError("Missing publisher")
    for row in events:
        doc = getdoc(root, row["url"])
        at = feed.moment(doc["published_at"])
        if at > after:
            raise ValueError("Archive order unverified")
        if at < remaining:
            break
        if at == feed.moment(current["published_at"]):
            continue
        after = at
        same_account = doc["wire_account"] == current["wire_account"]
        if require_matching_intermediates and not same_account:
            raise ValueError("Intervening issuer mismatch")
        if same_account and feed.screen(doc["text"]):
            packet = {"schema_version": reader.PACKET_SCHEMA, "event_id": current["id"]}
            for side, source in [("current", current), ("prior", doc)]:
                packet[side] = {
                    "issuer_cik": item["cik"],
                    "source": feed.as_packet_source(source),
                }
            inv = {
                "complete": True,
                "scope": "Current issuer wire archive back to first screened prior in 200 days. SEC submissions listing access unavailable; no all-market completeness claim.",
                "prior_source_id": doc["id"],
                "intervening_source_texts": intervening,
            }
            return packet, inv
        intervening.append({k: doc[k] for k in ("url", "published_at", "text")})
    raise ValueError("No matching earlier guidance in retained issuer feed")


def review(root, live, item, issuer, require_matching_intermediates=True):
    base = dict(
        event_id=item["id"],
        ticker=item["ticker"],
        release_published_at=item["at"],
        decision_at=item["at"],
        release_url=item["url"],
        source_sha256=item["hash"],
        eligible=False,
        revenue_buy=False,
        margin_buy=False,
    )
    folder = root / "cases" / item["id"]
    folder.mkdir(parents=True, exist_ok=True)
    try:
        packet, inv = prepare(root, item, issuer, require_matching_intermediates)
    except (ValueError, KeyError, OSError) as error:
        return dict(base, reason="Missing source evidence: " + str(error))
    seal(folder / "packet.json", packet)
    seal(folder / "inventory.json", inv)
    label = PREFIX + item["id"]
    extract = folder / "extract"
    size = len(json.dumps(reader.build_request(packet, MODEL)).encode())
    output = call(
        live,
        label + ":extract",
        size,
        extract,
        lambda: reader.run_once(packet, extract, MODEL),
    )
    base.update(
        prior_url=packet["prior"]["source"]["url"], extraction_status=output["status"]
    )
    if not (extract / "candidate.json").exists():
        return dict(base, reason="Extraction " + output["status"])
    candidate = read(extract / "candidate.json")
    path = folder / "review"
    size = len(json.dumps(feed.review_request(packet, candidate, inv, MODEL)).encode())
    response = call(
        live,
        label + ":review",
        size,
        path,
        lambda: feed.run_review(packet, candidate, inv, path, MODEL),
    )
    audit = response.get("review") or {}
    base["review_fields"] = {key: audit.get(key) for key in feed.REVIEW_FIELDS}
    unsupported = [key for key in feed.REVIEW_FIELDS if audit.get(key) != "SUPPORTED"]
    if unsupported:
        return dict(
            base,
            reason="Source review unresolved: " + ", ".join(unsupported),
            evidence_notes=audit.get("evidence_notes"),
        )
    candidate["external"].update(
        attestor="retrospective two-pass source review",
        latest_prior_source_id=packet["prior"]["source"]["id"],
        evidence_notes=audit["evidence_notes"],
    )
    for key in (
        "source_authenticity",
        "metric_binding",
        "prior_completeness",
        "basis_comparable",
        "perimeter_comparable",
    ):
        candidate["external"][key] = "VERIFIED"
    candidate["clocks"]["decision_at"] = response.get("received_at") or feed.now()
    result = qualify(candidate)
    if result["status"] != "FACTS_READY":
        return dict(
            base, reason="Qualification " + result["status"], issues=result["reasons"]
        )
    numbers = result["derived"]
    buy = Decimal(str(numbers["revenue_revision_pct"])) >= 1
    margin = buy and Decimal(str(numbers["margin_revision_pp"])) > 0
    return dict(
        base,
        eligible=True,
        revenue_buy=buy,
        margin_buy=margin,
        derived=numbers,
        reason="Revenue raise >=1%" if buy else "Revenue change below 1%",
    )


def main(root, live):
    if (root / "seal.json").exists():
        seal_record = read(root / "seal.json")
        if (
            feed.sha((root / "decisions.json").read_bytes())
            != seal_record["decisions_sha256"]
        ):
            raise RuntimeError("Decision seal mismatch")
        return
    archive = read(root / "inventory.json")
    cohort = sorted(
        [
            i
            for issuer in archive.values()
            for i in issuer["earnings"]
            if i["at"].startswith("2025-")
        ],
        key=lambda i: (i["ticker"], i["at"]),
    )
    if [i["ticker"] for i in cohort] != ["LOW"] * 4 + ["PANW"] * 4:
        raise ValueError("Unexpected cohort; no model calls")
    seal(root / "cohort.json", cohort)
    decisions = []
    for item in cohort:
        path = root / "decisions" / (item["id"] + ".json")
        if path.exists():
            row = read(path)
        else:
            row = review(root, live, item, archive[item["ticker"]])
            seal(path, row)
        print(row["ticker"], row["release_published_at"], row["reason"], flush=True)
        decisions.append(row)
    sha = seal(root / "decisions.json", decisions)
    seal(
        root / "seal.json",
        dict(
            decisions_sha256=sha,
            protocol_sha256=feed.sha((root / "PROTOCOL.md").read_bytes()),
            cohort_sha256=feed.sha((root / "cohort.json").read_bytes()),
            sealed_at=feed.now(),
        ),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("root", type=Path)
    parser.add_argument("live", type=Path)
    args = parser.parse_args()
    os.umask(0o077)
    main(args.root, args.live)
