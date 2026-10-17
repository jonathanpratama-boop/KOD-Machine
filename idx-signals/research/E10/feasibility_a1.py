"""E10 step 2, amendment 1 (FEASIBILITY_AMENDMENT_1.md): counts-only feasibility with the v2 extraction
(idxsig/guidance_v2.py) and the +-50% mismatch guard. Reads the saved EX-99 texts, never a price.

Writes research/E10/feasibility_a1/{FEASIBILITY.json, releases.csv.gz, events.csv.gz, audit_sample.csv}.
Usage (from idx-signals/): python3 research/E10/feasibility_a1.py --stamp <collector stamp>
"""
import argparse
import gzip
import importlib.util
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import guidance_v2 as guidance  # noqa: E402

E10 = ROOT / "research" / "E10"
OUT = E10 / "feasibility_a1"
EVENT_SPAN = ("2020-07-01", "2022-11-30")
SEED = 20261018                       # a fresh audit draw; the first audit used 20261017
_v1 = importlib.util.spec_from_file_location("e10_feas_v1", E10 / "feasibility.py")     # acceptance_ny, etoro_us
v1 = importlib.util.module_from_spec(_v1)
_v1.loader.exec_module(v1)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stamp", required=True)
    args = ap.parse_args()
    src = ROOT / "data" / "raw" / "sec_e10" / args.stamp
    OUT.mkdir(exist_ok=True)
    filings = pd.read_csv(E10 / "filings.csv", dtype={"ticker": str, "accession": str})
    rel_rows, guide_rows = [], []
    for r in filings.itertuples():
        path = src / f"{r.accession}.json.gz"
        if not path.exists():
            rel_rows.append({"accession": r.accession, "cik": r.cik, "ticker": r.ticker, "form": r.form,
                             "status": "MISSING"})
            continue
        blob = json.loads(gzip.decompress(path.read_bytes()))
        found = guidance.release_guidance(blob["texts"])
        acc = v1.acceptance_ny(blob)
        rel_rows.append({"accession": r.accession, "cik": r.cik, "ticker": r.ticker, "form": r.form,
                         "status": "OK", "acceptance_ny": acc, "exhibits": len(blob["texts"]),
                         "guidance_keys": len(found)})
        for (fy, kind), gd in found.items():
            guide_rows.append({"accession": r.accession, "cik": r.cik, "ticker": r.ticker, "form": r.form,
                               "acceptance_ny": acc, "fiscal_year": fy, "kind": kind, "low": gd.low,
                               "high": gd.high, "mid": gd.mid, "sentence": gd.sentence})
    releases = pd.DataFrame(rel_rows)
    guides = pd.DataFrame(guide_rows)
    releases.to_csv(OUT / "releases.csv.gz", index=False)

    events = []
    if len(guides):
        guides = guides.dropna(subset=["acceptance_ny"]).sort_values(["cik", "acceptance_ny"])
        guides["t"] = pd.to_datetime(guides.acceptance_ny)
        for (cik, fy, kind), grp in guides.groupby(["cik", "fiscal_year", "kind"], sort=False):
            grp = grp.sort_values("t")
            prev = None
            for row in grp.itertuples():
                if prev is not None and 5 <= (row.t - prev.t).days <= guidance.v1.MAX_GAP_DAYS:
                    new = guidance.Guidance(fy, kind, row.low, row.high, row.sentence)
                    old = guidance.Guidance(fy, kind, prev.low, prev.high, prev.sentence)
                    ch = guidance.level_change(new, old)
                    if ch is not None:
                        events.append({"accession": row.accession, "cik": cik, "ticker": row.ticker,
                                       "acceptance_ny": row.acceptance_ny, "fiscal_year": fy, "kind": kind,
                                       "prior_accession": prev.accession, "prior_acceptance_ny": prev.acceptance_ny,
                                       "old_mid": prev.mid, "new_mid": row.mid, "level_change": ch,
                                       "class": guidance.label(ch), "old_sentence": prev.sentence,
                                       "new_sentence": row.sentence})
                prev = row
    ev = pd.DataFrame(events)
    mismatched = {}
    if len(ev):
        ev["kind_rank"] = (ev.kind != "dollar").astype(int)
        ev = ev.sort_values(["accession", "fiscal_year", "kind_rank"], ascending=[True, False, True])
        ev = ev.drop_duplicates("accession").drop(columns="kind_rank")
        ev = ev[(ev.acceptance_ny >= EVENT_SPAN[0]) & (ev.acceptance_ny <= EVENT_SPAN[1] + "T23:59:59")]
        far = ev.level_change.abs() > guidance.MAX_CHANGE
        mismatched = ev[far]["class"].value_counts().to_dict()
        ev = ev[~far]
    ev.to_csv(OUT / "events.csv.gz", index=False)

    etoro = v1.etoro_us()
    ok = releases[releases.status == "OK"]
    in_span = ok[(ok.acceptance_ny >= EVENT_SPAN[0]) & (ok.acceptance_ny <= EVENT_SPAN[1] + "T23:59:59")]
    counts = {
        "filings_listed": int(len(releases)),
        "filings_fetched": int(len(ok)),
        "acceptance_found_share": float(ok.acceptance_ny.notna().mean()) if len(ok) else 0.0,
        "releases_in_event_span": int(len(in_span)),
        "releases_in_span_with_guidance": int((in_span.guidance_keys > 0).sum()),
        "dropped_as_mismatch_beyond_50pct": mismatched,
        "events_by_class": ev["class"].value_counts().to_dict() if len(ev) else {},
        "events_by_class_and_year": (ev.assign(year=ev.acceptance_ny.str[:4]).groupby(["year", "class"]).size()
                                     .unstack(fill_value=0).to_dict(orient="index")) if len(ev) else {},
        "events_by_kind": ev["kind"].value_counts().to_dict() if len(ev) else {},
        "issuers_with_events": int(ev.cik.nunique()) if len(ev) else 0,
        "events_on_etoro_listed": (ev[ev.ticker.str.upper().str.replace(".", "-", regex=False).isin(etoro)]
                                   ["class"].value_counts().to_dict()) if len(ev) else {},
        "level_change_quantiles_raise": (ev[ev["class"] == "RAISE"].level_change.quantile([.1, .5, .9])
                                         .round(4).to_dict()) if len(ev) else {},
    }
    sample = pd.concat([ev[ev["class"] == "RAISE"].sample(n=min(40, (ev["class"] == "RAISE").sum()),
                                                          random_state=SEED),
                        ev[ev["class"] == "CUT"].sample(n=min(20, (ev["class"] == "CUT").sum()),
                                                        random_state=SEED)]) if len(ev) else ev
    sample[["accession", "ticker", "class", "fiscal_year", "kind", "old_mid", "new_mid", "level_change",
            "old_sentence", "new_sentence"]].to_csv(OUT / "audit_sample.csv", index=False)
    (OUT / "FEASIBILITY.json").write_text(json.dumps({"stage": "counts only, no prices (amendment 1)",
                                                      "stamp": args.stamp, "counts": counts},
                                                     indent=2, default=str) + "\n")
    print(json.dumps(counts, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
