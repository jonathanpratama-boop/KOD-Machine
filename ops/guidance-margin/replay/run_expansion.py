"""Run the seven-issuer companion cohort using its separate pre-outcome seal."""

import argparse
import concurrent.futures
import os
from pathlib import Path

import run_history as replay
from expansion_inventory import ISSUERS


def run(root, live):
    replay.PREFIX = "replay-remaining-seven-2025:"
    replay.SUBBUDGET = 12
    if (root / "seal.json").exists():
        if (
            replay.feed.sha((root / "decisions.json").read_bytes())
            != replay.read(root / "seal.json")["decisions_sha256"]
        ):
            raise RuntimeError("Decision seal mismatch")
        return
    archive = replay.read(root / "inventory.json")
    if set(archive) != set(ISSUERS):
        raise ValueError("Incomplete issuer inventory")
    cohort = sorted(
        [e for i in archive.values() for e in i["earnings"]],
        key=lambda e: (e["ticker"], e["at"]),
    )
    if len({e["id"] for e in cohort}) != len(cohort):
        raise ValueError("Duplicate release in manifest")
    replay.seal(root / "cohort.json", cohort)

    def issuer_rows(ticker):
        rows = []
        for item in (e for e in cohort if e["ticker"] == ticker):
            path = root / "decisions" / (item["id"] + ".json")
            if path.exists():
                row = replay.read(path)
            else:
                try:
                    row = replay.review(root, live, item, archive[ticker])
                except RuntimeError as exc:
                    if str(exc) not in (
                        "Historical subbudget reached",
                        "API_CREDIT_BUDGET_REACHED",
                        "API_CREDIT_EXPIRED",
                    ):
                        raise
                    row = dict(
                        event_id=item["id"],
                        ticker=ticker,
                        release_published_at=item["at"],
                        decision_at=item["at"],
                        release_url=item["url"],
                        source_sha256=item["hash"],
                        eligible=False,
                        revenue_buy=False,
                        margin_buy=False,
                        reason=str(exc),
                    )
                replay.seal(path, row)
            rows.append(row)
            print(ticker, item["at"], row["reason"], flush=True)
        return rows

    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        allrows = [
            row for results in pool.map(issuer_rows, sorted(ISSUERS)) for row in results
        ]
    sha = replay.seal(root / "decisions.json", allrows)
    replay.seal(
        root / "seal.json",
        dict(
            decisions_sha256=sha,
            protocol_sha256=replay.feed.sha((root / "PROTOCOL.md").read_bytes()),
            cohort_sha256=replay.feed.sha((root / "cohort.json").read_bytes()),
            sealed_at=replay.feed.now(),
        ),
    )


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("root", type=Path)
    p.add_argument("live", type=Path)
    args = p.parse_args()
    os.umask(0o077)
    run(args.root, args.live)
