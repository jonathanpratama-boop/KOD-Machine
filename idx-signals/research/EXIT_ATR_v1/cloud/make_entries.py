"""EXIT-ATR-v1 step 3a: ONE shared list of eligible entries and matched-control entries.

Runs E2's own harness code (commit 21345b1, the code of the recorded E2 CRYPTO run, passed as KOD_CODE_ROOT)
under the recorded run configuration (results/runs/20261008T005732Z_MOONSHOT_E2_CRYPTO_D1_v1/summary.json),
with only the window changed to E2 discovery (2020-07-01..2022-12-31). It mirrors backtest.run() step by step:
causal signals -> execute -> overlap skip (decided by the ORIGINAL 5-session exit, so an earlier ATR exit can
never create extra entries) -> matched draws (controls v2, rng seed+1, 200 draws per attempted signal) ->
execution of every control entry.

It saves timing and entry fields ONLY: no exit price, gross or net return is written or printed.
Usage (from idx-signals/ of this branch):
  KOD_CODE_ROOT=<21345b1 worktree>/idx-signals python3 research/EXIT_ATR_v1/cloud/make_entries.py <panel manifest>
Cloud copy of Hermes's make_entries.py: only HERE (one folder deeper), OUT and this usage line differ.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[3]  # cloud copy: file sits one folder deeper than Hermes's
ROOT = Path(os.environ["KOD_CODE_ROOT"]).resolve()
sys.path.insert(0, str(ROOT))
from idxsig import backtest, global_panel  # noqa: E402

OUT = HERE / "research" / "EXIT_ATR_v1" / "cloud" / "entries"  # cloud copy: output folder
CFG = dict(rule_id="MOONSHOT_E2_CRYPTO_D1", start="2020-07-01", end="2022-12-31", holding_days=5, entry_lag=1,
           notional=5000.0, max_participation=0.1, fee_buy=0.001, fee_sell=0.001, overlap="skip", random_draws=200,
           seed=20261007, data_end_exit="last_close", ca_mode="adjusted", lookahead_cuts=None, controls_version="v2",
           market="CRYPTO")
HIDDEN = ("exit_price", "gross_return", "net_return", "mfe", "mae")  # never saved before the protocol freeze


def frame(m, out, ticks, sigs, extra=None):
    st = np.asarray(backtest.STATUS)[out["status"]]
    d = m.dates.astype("datetime64[D]").astype(str)
    e, x = out["entry_idx"], out["exit_idx"]
    df = pd.DataFrame({"ticker": np.asarray(m.tickers)[ticks], "signal_date": d[sigs], "status": st,
                       "entry_date": np.where(e >= 0, d[np.maximum(e, 0)], ""),
                       "exit_date_original": np.where(x >= 0, d[np.maximum(x, 0)], ""),
                       "entry_price": out["entry_price"], "shares": out["shares"]})
    return df if extra is None else pd.concat([pd.DataFrame(extra), df], axis=1)


def main(manifest: Path) -> int:
    cfg = backtest.RunConfig(**CFG)
    panel_df, meta = global_panel.load(manifest)
    rule = backtest.rule_registry.get(cfg.rule_id)
    profile = backtest.PROFILES[cfg.market]
    exec_cfg = backtest.ExecConfig(lot_size=profile.lot_size, entry_price=profile.entry, cost_tiers=profile.cost_tiers,
                                   holding_days=cfg.holding_days or rule.holding_days, entry_lag=cfg.entry_lag,
                                   notional=cfg.notional, max_participation=cfg.max_participation,
                                   fees=backtest.Fees(cfg.fee_buy, cfg.fee_sell), data_end_exit=cfg.data_end_exit,
                                   ca_mode=cfg.ca_mode)
    full = backtest.Market.from_panel(panel_df, price_limits=profile.price_limits)
    lo, hi = full.bounds(cfg.start, cfg.end)
    m = full.slice(lo, hi)
    sig, lookahead = backtest.signals(rule, m, cfg.lookahead_cuts)
    evaluable = np.isfinite(sig)
    tick_idx, sig_idx = np.nonzero(sig == 1)
    trades = backtest.execute(m, tick_idx, sig_idx, exec_cfg)
    skipped = np.zeros(len(tick_idx), dtype=bool)
    held_until = {}
    for i, (n, s) in enumerate(zip(tick_idx, sig_idx)):  # identical to backtest.run()
        if s + cfg.entry_lag <= held_until.get(n, -1):
            skipped[i] = True
            continue
        if trades["exit_idx"][i] >= 0:
            held_until[n] = trades["exit_idx"][i]
        elif trades["status"][i] == backtest.STATUS.index("INCOMPLETE"):
            held_until[n] = np.iinfo(np.int64).max
    attempt = ~skipped
    a_tick, a_sig = tick_idx[attempt], sig_idx[attempt]
    feats = {k: v[:, lo:hi] for k, v in backtest.controls.features(full, cfg.controls_version, profile.band_edges).items()}
    matched_tick, level_used = backtest.controls.matched_draws(evaluable, feats, a_tick, a_sig, cfg.random_draws,
                                                               np.random.default_rng(cfg.seed + 1), cfg.controls_version)
    r_sig = np.broadcast_to(a_sig, matched_tick.shape)
    ctrl = backtest.execute(m, matched_tick.ravel(), r_sig.ravel(), exec_cfg)

    OUT.mkdir(parents=True, exist_ok=True)
    sig_df = frame(m, trades, tick_idx, sig_idx, {"raw_index": np.arange(len(tick_idx)), "overlap_skipped": skipped})
    j = np.full(len(tick_idx), -1)
    j[attempt] = np.arange(attempt.sum())
    sig_df.insert(1, "j", j)
    draws = matched_tick.shape[0]
    names = backtest.controls.level_names(cfg.controls_version)
    ctrl_df = frame(m, ctrl, matched_tick.ravel(), r_sig.ravel(),
                    {"draw": np.repeat(np.arange(draws), len(a_sig)), "j": np.tile(np.arange(len(a_sig)), draws),
                     "match_level": np.asarray(names, dtype=object)[np.broadcast_to(level_used, matched_tick.shape).ravel()]})
    sig_df.to_csv(OUT / "signals.csv", index=False, float_format="%.10g")
    ctrl_df.to_csv(OUT / "controls.csv.gz", index=False, float_format="%.10g", compression={"method": "gzip", "mtime": 0})
    commit = subprocess.run(["git", "-C", str(ROOT), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
    info = {"code_root": str(ROOT), "code_commit": commit, "config": CFG, "panel_manifest": manifest.name,
            "panel_sha256": meta["sha256"], "window_sessions": [str(m.dates[0])[:10], str(m.dates[-1])[:10]],
            "lookahead": lookahead if isinstance(lookahead, (dict, list, str)) else str(lookahead),
            "execute_keys": sorted(trades.keys()), "hidden_until_freeze": list(HIDDEN),
            "counts": {"raw_signals": int(len(tick_idx)), "overlap_skipped": int(skipped.sum()),
                       "attempted": int(attempt.sum()),
                       "attempted_by_status": sig_df[sig_df.j >= 0].status.value_counts().to_dict(),
                       "control_entries": int(len(ctrl_df)),
                       "control_by_status": ctrl_df.status.value_counts().to_dict(),
                       "match_level_used": pd.Series(level_used).map(dict(enumerate(names))).value_counts().to_dict(),
                       "distinct_signal_coins": int(sig_df[sig_df.j >= 0].ticker.nunique()),
                       "distinct_control_coins": int(ctrl_df.ticker.nunique())}}
    (OUT / "entries_meta.json").write_text(json.dumps(info, indent=1, default=str))
    print(json.dumps(info["counts"], indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
