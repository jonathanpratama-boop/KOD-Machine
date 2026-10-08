"""Version-aware reproduction of Hermes's three source findings against the merged code.

Hermes's audit/reproduce_source_findings.py (kept unchanged under hermes_handoff_v1/) calls
global_panel._finish and expects the legacy deletion; after the repair _finish is causal, so
that script now fails by design. This one names each version explicitly and shows the defect
in the legacy path and its absence in the repaired path. Synthetic 2020 fixtures only: no
market file, ledger or network is touched.

    python3 research/E2/repair/reproduce_source_findings_v2.py
"""

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from idxsig import global_panel, paper  # noqa: E402
from idxsig.execution import STATUS, ExecConfig, Market, execute  # noqa: E402
from idxsig.market import Fees  # noqa: E402
from idxsig.profiles import US  # noqa: E402


def finding_1_preprocessing():
    rows = []
    for i in range(51):
        for j, day in enumerate(pd.date_range("2020-01-01", periods=3)):
            price = 40.0 if i == 0 and j == 1 else 10.0
            rows.append(dict(ticker=f"T{i:03d}", date=day, source="synthetic", open=price, high=price, low=price,
                             close=price, volume=100000.0))
    f = pd.DataFrame(rows)
    cut = pd.Timestamp("2020-01-02")
    out = {}
    for name, fn in (("legacy_v1", global_panel._finish_legacy_v1), ("causal_v2", global_panel._finish)):
        prefix, _ = fn(f[f.date <= cut].copy())
        full, _ = fn(f.copy())
        at_cut = lambda d: bool(((d.ticker == "T000") & (d.date == cut)).any())  # noqa: E731
        out[name] = {"row_present_at_cutoff": at_cut(prefix), "row_present_after_next_bar": at_cut(full),
                     "prefix_invariant": at_cut(prefix) == at_cut(full)}
    return out


def finding_2_paper_units():
    rows = [dict(ticker="SYNTH", date=d, source="synthetic", previous=15.0, open=15.0, high=15.0, low=15.0, close=15.0,
                 volume=1e6, value=1.5e7, frequency=np.nan, listed_shares=np.nan, tradable_shares=np.nan)
            for d in pd.date_range("2020-01-01", periods=8)]
    m = paper._market(pd.DataFrame(rows), "US")
    decision = {"market": "US", "instrument": {"ticker": "SYNTH"}, "signal_session": "2020-01-01",
                "plan": {"invalidation": 25.5, "max_chase_price": 33}, "verified_price": {"close": 30},
                "decision": "PASS", "decision_id": "SYNTHETIC-NOT-A-CALL"}
    tier = float(US.per_side_cost(np.array([15.0]))[0])
    expected = (1 - US.fee_sell - tier) / (1 + US.fee_buy + tier) - 1
    legacy = paper.score(decision, m)["execution"]["paper_trade"]["net_return"]
    units = {"convention": "SPLIT_ONLY", "coverage_complete": True, "adjustment_reference": "2020-01-08",
             "actions": [{"effective_session": "2020-01-02", "new_shares": 2, "old_shares": 1}]}
    repaired = paper.score(decision, m, price_units=units)["execution"]["paper_trade"]["net_return"]
    return {"split_2_for_1_between_signal_and_entry": True, "net_with_entry_session_units": expected,
            "legacy_signal_scale_v1": legacy, "legacy_matches": bool(np.isclose(legacy, expected)),
            "verified_units": repaired, "verified_matches": bool(np.isclose(repaired, expected))}


def finding_3_opening_volume():
    def status(entry_volume, model):
        df = pd.DataFrame(dict(date=pd.date_range("2020-01-01", periods=30, freq="B"), ticker="SYN", source="synthetic",
                               previous=10.0, open=10.0, high=10.0, low=10.0, close=10.0, volume=100000.0, value=1e6))
        df.loc[21, ["volume", "value"]] = [entry_volume, entry_volume * 10]
        m = Market.from_panel(df, price_limits=False).with_units(np.ones((1, 30)))
        cfg = ExecConfig(holding_days=2, notional=5000.0, entry_price="open", lot_size=1, ca_mode="adjusted",
                         fees=Fees(0.0, 0.0), units="as_traded", fill_model=model)
        return STATUS[int(execute(m, np.array([0]), np.array([20]), cfg)["status"][0])]
    return {model: {"entry_day_final_volume_1000": status(1000.0, model),
                    "entry_day_final_volume_100000": status(100000.0, model)} for model in ("A", "B")}


if __name__ == "__main__":
    out = {"synthetic_only": True, "preprocessing": finding_1_preprocessing(), "paper_units": finding_2_paper_units(),
           "opening_volume": finding_3_opening_volume()}
    assert not out["preprocessing"]["legacy_v1"]["prefix_invariant"] and out["preprocessing"]["causal_v2"]["prefix_invariant"]
    assert not out["paper_units"]["legacy_matches"] and out["paper_units"]["verified_matches"]
    a, b = out["opening_volume"]["A"], out["opening_volume"]["B"]
    assert a["entry_day_final_volume_1000"] != a["entry_day_final_volume_100000"]
    assert b["entry_day_final_volume_1000"] == b["entry_day_final_volume_100000"]
    print(json.dumps(out, indent=2))
