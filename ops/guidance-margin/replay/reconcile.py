"""Correct the implementation of archive-account matching before any price reads."""

import concurrent.futures
import os
from pathlib import Path
import sys
import run_history as replay


def run(root, live):
    replay.PREFIX = "replay-remaining-seven-2025:"
    replay.SUBBUDGET = 12
    canonical = root / "canonical"
    canonical.mkdir(exist_ok=True)
    if (canonical / "seal.json").exists():
        return
    initial = replay.read(root / "decisions.json")
    first_seal = replay.read(root / "seal.json")
    if (
        replay.feed.sha((root / "decisions.json").read_bytes())
        != first_seal["decisions_sha256"]
    ):
        raise ValueError("Initial seal mismatch")
    archive = replay.read(root / "inventory.json")
    cohort = replay.read(root / "cohort.json")
    by_id = {row["event_id"]: row for row in initial}

    def for_issuer(t):
        result = []
        for item in (x for x in cohort if x["ticker"] == t):
            original = by_id[item["id"]]
            path = canonical / "rows" / (item["id"] + ".json")
            if (
                original.get("reason")
                != "Missing source evidence: Intervening issuer mismatch"
            ):
                result.append(original)
                continue
            if path.exists():
                row = replay.read(path)
            else:
                try:
                    row = replay.review(
                        root,
                        live,
                        item,
                        archive[t],
                        require_matching_intermediates=False,
                    )
                except RuntimeError as e:
                    if str(e) not in (
                        "Historical subbudget reached",
                        "API_CREDIT_BUDGET_REACHED",
                        "API_CREDIT_EXPIRED",
                    ):
                        raise
                    row = dict(original, reason=str(e))
                replay.seal(path, row)
            result.append(row)
            print(t, item["at"], row["reason"], flush=True)
        return result

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows = [row for group in pool.map(for_issuer, sorted(archive)) for row in group]
    sha = replay.seal(canonical / "decisions.json", rows)
    protocol = replay.feed.sha((root / "EXPANSION_CORRECTION.md").read_bytes())
    replay.seal(canonical / "cohort.json", cohort)
    replay.seal(
        canonical / "seal.json",
        dict(
            original_seal=first_seal,
            cohort_sha256=first_seal["cohort_sha256"],
            decisions_sha256=sha,
            correction_sha256=protocol,
            protocol_sha256=first_seal["protocol_sha256"],
            sealed_at=replay.feed.now(),
        ),
    )


if __name__ == "__main__":
    os.umask(0o077)
    run(Path(sys.argv[1]), Path(sys.argv[2]))
