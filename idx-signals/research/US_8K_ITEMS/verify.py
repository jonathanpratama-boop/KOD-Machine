"""Independent check of results_stage<N>/ (no import of idxsig, run.py or k_lib; the trade recomputation is US_INSIDER_BUY/verify.py's, itself independent): input hashes, the event table rebuilt
from filings8k.csv.gz with own code, every EXITED trade of every item and hold recomputed from the panel, the per-item mean excess / analytic t / winsorised mean, and the gates.
Usage (from idx-signals/): python3 research/US_8K_ITEMS/verify.py --stage 1"""
import argparse, hashlib, importlib.util, json, sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
spec = importlib.util.spec_from_file_location("uib_verify", HERE.parent / "US_INSIDER_BUY" / "verify.py")
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)
ITEMS = ["1.01", "1.02", "2.02", "2.03", "3.02", "5.02", "5.07", "7.01", "8.01"]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()  # noqa: E731


def rebuild(f):
    last, rows = {}, []
    f = f[f.filing_date >= "2020-07-01"].sort_values(["filing_date", "cik", "accession"])
    for cik, tk, acc, d, items in zip(f.cik, f.ticker, f.accession, f.filing_date, f["items"].fillna("")):
        for it in sorted({s.strip() for s in str(items).split(",")} & set(ITEMS)):
            dd = pd.Timestamp(d)
            if (cik, it) in last and (dd - last[(cik, it)]).days < 30:
                continue
            last[(cik, it)] = dd
            stage = 1 if "2021-01-04" <= d <= "2022-12-30" else 2 if "2023-01-03" <= d <= "2023-09-29" else 0
            if stage:
                rows.append((it, acc, tk, d, stage))
    return pd.DataFrame(rows, columns=["item", "accession", "ticker", "public_date", "stage"])


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--stage", type=int, required=True, choices=(1, 2))
    stage = ap.parse_args().stage
    bad, d = [], HERE / f"results_stage{stage}"
    res = json.loads((d / "RESULT.json").read_text()); pins = json.loads((HERE / "PINS.json").read_text())
    for k, p in (("events_csv", "events.csv"), ("filings8k", "filings8k.csv.gz")):
        if sha(HERE / p) != pins[k] or res["inputs"][k] != pins[k]:
            bad.append(f"{p} hash")
    pm = json.loads((ROOT / "data/manifests/panel_us_repair-20261008T114805Z.json").read_text()); pfile = ROOT / pm["panel"]
    if sha(pfile) != pm["sha256"] or pm["sha256"] != res["inputs"]["panel"]:
        bad.append("panel hash")
    mine = rebuild(pd.read_csv(HERE / "filings8k.csv.gz", dtype={"accession": str, "items": str}, keep_default_na=False, na_values=[""]))
    inp = pd.read_csv(HERE / "events.csv", dtype={"accession": str, "item": str})
    k = ["item", "accession"]
    a, b = mine.sort_values(k).reset_index(drop=True), inp.sort_values(k).reset_index(drop=True)
    if len(a) != len(b) or (a[k + ["ticker", "public_date", "stage"]].values != b[k + ["ticker", "public_date", "stage"]].values).any():
        bad.append(f"events differ {len(a)} vs {len(b)}")
    report = {}
    for it, rec in res["items"].items():
        means = {}
        for h in rec["holds"]:
            p = d / f"events_{it}_hold{h}.csv"
            ev = pd.read_csv(p, dtype={"accession": str})
            n, w, tb = V.check_trades(ev, pfile, int(h))
            bad += [f"{it} hold {h}: {m}" for m in tb]
            f = ev[ev.net_return.notna() & ev.control_mean.notna()]
            if (abs(f.excess - (f.net_return - f.control_mean)) > 1e-12).any():
                bad.append(f"{it} hold {h}: excess")
            if len(f) != rec["holds"][h]["scored"] or (len(f) > 9 and abs(f.excess.mean() - rec["holds"][h]["mean"]) > 1e-9):
                bad.append(f"{it} hold {h}: stats")
            means[h] = f
        f = means["20"]
        if len(f) > 9:
            x = f.excess.to_numpy(); t_an = V.analytic_t(x, V.week(f.entry_date)); t_b = rec["holds"]["20"]["t"]
            if abs(t_an - t_b) > 0.2 * abs(t_b) + 0.15:
                bad.append(f"{it}: t {t_b:.2f} vs analytic {t_an:.2f}")
            if stage == 1 and rec.get("testable"):
                lo, hi = np.percentile(x, [1, 99]); wins = float(np.clip(x, lo, hi).mean()); yr = {y: g.excess for y, g in f.groupby(f.entry_date.str[:4])}
                g = {"G1_t_ge_3.6": bool(x.mean() > 0 and t_b >= 3.6), "G2_excess_ge_1pct_and_winsorised_ge_0.5pct": bool(x.mean() >= 0.01 and wins >= 0.005),
                     "G3_positive_2021_and_2022": bool(all(y in yr and len(yr[y]) >= 100 and yr[y].mean() > 0 for y in ("2021", "2022"))),
                     "G4_positive_at_holds_5_and_60": bool(means["5"].excess.mean() > 0 and means["60"].excess.mean() > 0)}
                if list(g.values()) != list(rec["gates"].values()):
                    bad.append(f"{it}: gates {g} vs {rec['gates']}")
            report[it] = {"scored": len(f), "mean": float(x.mean()), "analytic_t": t_an, "bootstrap_t": t_b}
    print(json.dumps({"stage": stage, "events_rebuilt": len(a), "items": report, "mismatches": bad, "verdict": res["verdict"]}, indent=1))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
