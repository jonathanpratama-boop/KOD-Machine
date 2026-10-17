"""E10 step 2: counts-only feasibility (FEASIBILITY_SPEC.md). Reads the saved EX-99 texts, never a price.

Writes research/E10/feasibility/{FEASIBILITY.json, releases.csv.gz, events.csv.gz, audit_sample.csv}.
Usage (from idx-signals/): python3 research/E10/feasibility.py --stamp <collector stamp>
"""
import argparse
import gzip
import json
import sys
from datetime import datetime
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from idxsig import guidance  # noqa: E402

E10 = ROOT / "research" / "E10"
OUT = E10 / "feasibility"
EVENT_SPAN = ("2020-07-01", "2022-11-30")
SEED = 20261017


def etoro_us() -> set[str]:
    raw = ROOT / "data" / "raw" / "etoro" / "20261016T190421Z" / "instruments.json"
    data = json.loads(raw.read_bytes())["InstrumentDisplayDatas"]
    return {str(x["SymbolFull"]).upper().replace(".", "-") for x in data
            if x["InstrumentTypeID"] == 5 and x["ExchangeID"] in (4, 5) and not x.get("IsInternalInstrument")}


def acceptance_ny(blob: dict) -> str | None:
    h = blob.get("acceptance_header")
    if h:
        return datetime.strptime(h, "%Y%m%d%H%M%S").strftime("%Y-%m-%dT%H:%M:%S")
    return None


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
        acc = acceptance_ny(blob)
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
                if prev is not None and (row.t - prev.t).days <= guidance.MAX_GAP_DAYS and \
                        (row.t - prev.t).days >= 5:
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
    # one event per release: a release revising several fiscal years or kinds keeps the dollar figure for the
    # latest fiscal year it guides (the year being forecast), else the growth figure
    if len(ev):
        ev["kind_rank"] = (ev.kind != "dollar").astype(int)
        ev = ev.sort_values(["accession", "fiscal_year", "kind_rank"], ascending=[True, False, True])
        ev = ev.drop_duplicates("accession").drop(columns="kind_rank")
        ev = ev[(ev.acceptance_ny >= EVENT_SPAN[0]) & (ev.acceptance_ny <= EVENT_SPAN[1] + "T23:59:59")]
    ev.to_csv(OUT / "events.csv.gz", index=False)

    etoro = etoro_us()
    ok = releases[releases.status == "OK"]
    in_span = ok[(ok.acceptance_ny >= EVENT_SPAN[0]) & (ok.acceptance_ny <= EVENT_SPAN[1] + "T23:59:59")]
    counts = {
        "filings_listed": int(len(releases)),
        "filings_fetched": int(len(ok)),
        "acceptance_found_share": float(ok.acceptance_ny.notna().mean()) if len(ok) else 0.0,
        "releases_in_event_span": int(len(in_span)),
        "releases_in_span_with_guidance": int((in_span.guidance_keys > 0).sum()),
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
    (OUT / "FEASIBILITY.json").write_text(json.dumps({"stage": "counts only, no prices", "stamp": args.stamp,
                                                      "counts": counts}, indent=2, default=str) + "\n")
    print(json.dumps(counts, indent=2, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
