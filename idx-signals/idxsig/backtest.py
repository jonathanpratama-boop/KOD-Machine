"""Run a rule over the whole universe and compare it with random entries.

Universe: every ticker in the panel window, including names that later delisted, on
every session where the rule is evaluable. Not a list of past winners.

Two random baselines, each run through the identical execution model and holding period.
For every attempted signal, `random_draws` replacement entries are drawn on the same
session from the names where the rule was evaluable:

  matched       from names in the same price band, liquidity, market-cap, volatility,
                momentum, drawdown and listing-age buckets as the signalled name
                (controls.py, v2), so exposure to illiquid or volatile names is not mistaken
                for a signal. This is the primary comparison.
  same-session  from all of them, uniformly. Controls for market timing only.

Each draw is a portfolio of the rule's size and dates. The rule's average return and hit
rate are placed in each distribution of draws.

No lookahead, by construction (rules.causal_signals): the signal recorded at session d is
column d of a call that received only sessions 0..d and the names listed by d, through a
read-only view without the corporate-action registry, under a source audit and a run-time
sandbox. A full-window call that disagrees with the prefix-built signals fails the run.

Corporate actions: ca_mode="registry" (default) scales shares only through resets the
registry verifies; the registry must have been built from this exact panel.

Data quality: every run reports how many of its sessions are TIER_1/2/3 (quality.py) and
the known limitations of the data, and warns when the window leaves TIER_1.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from . import controls, quality
from . import rules as rule_registry
from .corporate_actions import REGISTRY_VERSION, RegistryMismatch
from .execution import NEVER_ENTERED, SCORED, STATUS, ExecConfig, Market, execute
from .market import Fees
from .rules import LookaheadError
from .profiles import PROFILES
from .sources.idx_mirror import FIRST_SNAPSHOT


@dataclass(frozen=True)
class RunConfig:
    rule_id: str
    start: str | None = None  # default: the mirror's first snapshot (survivorship-complete from there)
    end: str | None = None  # default: last session of the IDX mirror (the best-covered era)
    holding_days: int | None = None  # default: the rule's pre-registered holding period
    entry_lag: int = 1
    notional: float = 10_000_000.0
    max_participation: float = 0.10
    fee_buy: float = 0.0015
    fee_sell: float = 0.0025
    overlap: str = "skip"  # skip a signal while the same name is still held
    random_draws: int = 200
    seed: int = 20261007
    data_end_exit: str = "last_close"
    ca_mode: str = "registry"  # "exclude" / "value_preserving": earlier modes, to reproduce older runs
    lookahead_cuts: int | None = None  # None: prefix-first, causal by construction; N: legacy sampled check
    controls_version: str = "v2"
    market: str = "IDX"  # profiles.PROFILES: IDX, US, CRYPTO
    units: str = "panel"  # "as_traded": price levels in the units traded that session (panel unit_factor)
    fill_model: str = "A"  # "A": original (entry-session final volume); "B": decision-time capacity (open); "C": FILL-C-v1 (close)
    quarantine: str = "none"  # "unit_schedule": leave out names the panel lists as lacking a verified schedule
    # Execution plan (execution.ENTRY_RULES / EXIT_RULES). None: the rule's own frozen plan if it carries
    # one (rules.Rule.plan), else the original model ("fixed" / entry_lag / "fixed").
    entry_rule: str | None = None
    entry_window: int | None = None
    exit_rule: str | None = None
    side: str | None = None  # "long" / "short" (execution.SIDES); None: the rule's plan, else long
    liquidation: float | None = None  # short side: isolated-margin liquidation at this fraction above the entry
    jump_ratio: float | None = None  # trades held across a close/reference ratio beyond this are not scored
    holdout_final: bool = False  # the one pre-registered holdout evaluation (see HOLDOUT)


# The IDX holdout sealed by research/E1/protocol.json. A DETECTOR run whose window touches it is
# refused unless holdout_final is set: that is the single final test, and it is on record as such.
HOLDOUT = ("2024-01-02", "2025-02-21")
# The US and crypto holdout sealed by research/E2/protocol.json (2024 onward), the same rule.
GLOBAL_HOLDOUT = ("2024-01-01", "2099-12-31")


class HoldoutSealed(RuntimeError):
    pass


def resolve_plan(cfg: RunConfig, rule) -> dict:
    """The plan a run executes: explicit config first, then the rule's frozen plan, then the original."""
    frozen = dict(getattr(rule, "plan", None) or {})
    return {"entry_rule": cfg.entry_rule or frozen.get("entry_rule", "fixed"),
            "entry_window": cfg.entry_window or frozen.get("entry_window", 1),
            "exit_rule": cfg.exit_rule or frozen.get("exit_rule", "fixed"),
            "side": cfg.side or frozen.get("side", "long")}


ENTRY_TEXT = {
    "fixed": "buy at the close of session s + {w}",
    "confirm": "buy at the first close in s+1..s+{w} that is above the signal close (reference chain), traded "
               "and not locked at ARA",
    "pullback": "buy at the first close in s+1..s+{w} that is below the signal close (reference chain), traded "
                "and not locked at ARA",
    "unlock": "buy at the first traded close in s+1..s+{w} that is not locked at ARA",
}
EXIT_TEXT = {
    "fixed": "sell at the close of the {h} session after entry",
    "stop_ref": "sell at the first close at or below the signal session's reference price, else at the close of "
                "the {h} session after entry",
    "first_down": "sell at the first close below its own reference price (a down day), else at the close of the "
                  "{h} session after entry",
}
OPEN_ENTRY_TEXT = {  # open-entry markets: the condition is the open the entry happens at
    "long": {"fixed": "buy at the open of session s + {w}",
             "confirm": "buy at the first open in s+1..s+{w} that is above the signal close",
             "pullback": "buy at the first open in s+1..s+{w} that is below the signal close"},
    "short": {"fixed": "sell short at the open of session s + {w}",
              "confirm": "sell short at the first open in s+1..s+{w} that is below the signal close (the fade "
                         "has begun)",
              "pullback": "sell short at the first open in s+1..s+{w} that is above the signal close (into a "
                          "bounce)"},
}
SHORT_EXIT_TEXT = {
    "fixed": "buy back at the close of the {h} session after entry",
    "stop_high": "buy back at the first close at or above the signal session's high, else at the close of the "
                 "{h} session after entry",
    "first_up": "buy back at the first close above its own reference price (an up day), else at the close of "
                "the {h} session after entry",
}


def _ordinal(n: int) -> str:
    n = int(n)
    suffix = "th" if 10 <= n % 100 <= 20 else {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def plan_text(plan: dict, entry_price: str = "close") -> str:
    """One sentence a decision record can carry: the plan as executed, in exchange terms."""
    side = plan.get("side", "long")
    h = _ordinal(plan["holding_days"])
    if side == "short":
        return (OPEN_ENTRY_TEXT["short"][plan["entry_rule"]].format(w=plan["entry_window"]) + "; "
                + SHORT_EXIT_TEXT[plan["exit_rule"]].format(h=h) + "; carry charged per session held")
    if entry_price == "open":
        entry = OPEN_ENTRY_TEXT["long"][plan["entry_rule"]].format(w=plan["entry_window"])
        return entry + "; " + EXIT_TEXT[plan["exit_rule"]].format(h=h)
    return (ENTRY_TEXT[plan["entry_rule"]].format(w=plan["entry_window"]) + "; "
            + EXIT_TEXT[plan["exit_rule"]].format(h=h)
            + "; a sale rolls to the next session where it is possible while locked at ARB or untraded")


def _equal_with_nan(a: np.ndarray, b: np.ndarray) -> bool:
    return bool(np.array_equal(np.isnan(a), np.isnan(b)) and np.array_equal(np.nan_to_num(a), np.nan_to_num(b)))


def signals(rule, m: Market, cuts: int | None) -> tuple[np.ndarray, dict]:
    """Prefix-first causal signals, or (cuts=N, legacy) a full-window call checked at N prefixes."""
    if cuts is None:
        return rule_registry.causal_signals(rule, m)
    from .rules.audit import require_clean

    require_clean(rule)
    src = rule_registry.CausalSource(m)
    n_sessions = m.shape[1]
    full = np.full(m.shape, np.nan)
    k_end = src.rows_at(n_sessions - 1)
    full[:k_end] = rule_registry._call(rule, src.view(n_sessions - 1))
    checked = []
    for frac in np.linspace(0.3, 0.9, cuts) if cuts else []:
        cut = int(frac * (n_sessions - 1))
        k = src.rows_at(cut)
        if not _equal_with_nan(full[:k, : cut + 1], rule_registry._call(rule, src.view(cut))):
            raise LookaheadError(f"{rule.rule_id} changes past signals when sessions after {m.dates[cut]} are "
                                 f"removed: it reads ahead")
        checked.append(str(m.dates[cut]))
    return src.unorder(full), {"mode": "sampled", "truncated_after": checked, "mismatches": 0,
                               "source_audit": "passed"}


def _summary_stats(net: np.ndarray, status: np.ndarray) -> dict:
    scored = np.isin(status, SCORED)
    vals = net[scored]
    entered = ~np.isin(status, NEVER_ENTERED)
    return {
        "attempts": int(len(status)),
        "filled": int(entered.sum()),
        "fill_rate": float(entered.mean()) if len(status) else None,
        "scored": int(scored.sum()),
        "hit_rate": float((vals > 0).mean()) if len(vals) else None,
        "avg_net_return": float(vals.mean()) if len(vals) else None,
        "median_net_return": float(np.median(vals)) if len(vals) else None,
        "std_net_return": float(vals.std(ddof=1)) if len(vals) > 1 else None,
        "status_counts": {STATUS[i]: int((status == i).sum()) for i in range(len(STATUS)) if (status == i).any()},
    }


def _baseline(m: Market, r_tick: np.ndarray, a_sig: np.ndarray, exec_cfg: ExecConfig, rule_stats: dict,
              method: str) -> tuple[dict, pd.DataFrame, dict]:
    draws = r_tick.shape[0]
    r_sig = np.broadcast_to(a_sig, r_tick.shape)
    out = execute(m, r_tick.ravel(), r_sig.ravel(), exec_cfg)
    net = out["net_return"].reshape(draws, -1)
    status = out["status"].reshape(draws, -1)
    rows = []
    for d in range(draws):
        st = _summary_stats(net[d], status[d])
        rows.append({"draw": d, "scored": st["scored"], "fill_rate": st["fill_rate"], "hit_rate": st["hit_rate"],
                     "avg_net_return": st["avg_net_return"], "median_net_return": st["median_net_return"]})
    frame = pd.DataFrame(rows)

    def dist(col: str, observed):
        v = frame[col].dropna().to_numpy() if not frame.empty else np.array([])
        if observed is None or not len(v):
            return None
        return {
            "observed": observed,
            "random_mean": float(v.mean()),
            "random_p2_5": float(np.percentile(v, 2.5)),
            "random_p50": float(np.percentile(v, 50)),
            "random_p97_5": float(np.percentile(v, 97.5)),
            "difference": float(observed - v.mean()),
            "percentile_of_observed": float((v < observed).mean() * 100),
            "p_value_one_sided": float((1 + (v >= observed).sum()) / (1 + len(v))),
        }

    summary = {
        "draws": draws,
        "method": method,
        "pooled": _summary_stats(out["net_return"], out["status"]),
        "avg_net_return": dist("avg_net_return", rule_stats["avg_net_return"]),
        "hit_rate": dist("hit_rate", rule_stats["hit_rate"]),
    }
    return summary, frame, out


def _dense(m: Market, df: pd.DataFrame, col: str, fill) -> np.ndarray:
    out = np.full(m.shape, fill, dtype=np.asarray(fill).dtype if not isinstance(fill, float) else float)
    ti = pd.Index(m.tickers).get_indexer(df["ticker"])
    di = pd.Index(m.dates).get_indexer(df["date"].to_numpy().astype("datetime64[D]"))
    ok = (ti >= 0) & (di >= 0)
    out[ti[ok], di[ok]] = df[col].to_numpy()[ok]
    return out


def _qa_sensitivity(flag: np.ndarray, out: dict, keep: np.ndarray | None = None) -> dict:
    """Stats without trades whose entry or exit session is flagged by retrospective QA."""
    entry, exit_, tick = out["entry_idx"], out["exit_idx"], out["ticker_idx"]
    hit = np.zeros(len(tick), dtype=bool)
    for idx_arr in (entry, exit_):
        ok = idx_arr >= 0
        hit[ok] |= flag[tick[ok], idx_arr[ok]]
    sel = np.ones(len(tick), dtype=bool) if keep is None else keep
    return {"trades_touching_flag": int((hit & sel & np.isin(out["status"], SCORED)).sum()),
            **{k: v for k, v in _summary_stats(out["net_return"][sel & ~hit], out["status"][sel & ~hit]).items()
               if k in ("scored", "avg_net_return", "hit_rate")}}


def run(cfg: RunConfig, panel_df: pd.DataFrame, panel_meta: dict, ca_registry: tuple | None = None,
        signal_cache: dict | None = None) -> dict:
    """ca_registry: (registry DataFrame, registry manifest) from corporate_actions.load, required
    when cfg.ca_mode == "registry". signal_cache: a dict a caller keeps across runs of the same rule
    on the same window and panel (research/E3 runs one detector under many plans); the causal
    signals are computed once per (rule hash, window, panel hash) and reused unchanged."""
    rule = rule_registry.get(cfg.rule_id)
    holding = cfg.holding_days or rule.holding_days
    profile = PROFILES[cfg.market]
    idx = profile.market == "IDX"
    plan = resolve_plan(cfg, rule)
    if plan["side"] == "short":
        if profile.short_carry_per_session is None:
            raise ValueError(f"no short side is modelled for the {profile.market} profile")
        plan = {**plan, "carry_per_session": profile.short_carry_per_session}
    exec_cfg = ExecConfig(
        lot_size=profile.lot_size,
        entry_price=profile.entry,
        cost_tiers=profile.cost_tiers,
        holding_days=holding,
        entry_lag=cfg.entry_lag,
        notional=cfg.notional,
        max_participation=cfg.max_participation,
        fees=Fees(cfg.fee_buy, cfg.fee_sell),
        data_end_exit=cfg.data_end_exit,
        ca_mode=cfg.ca_mode,
        units=cfg.units,
        fill_model=cfg.fill_model,
        liquidation=cfg.liquidation,
        jump_ratio=cfg.jump_ratio,
        **plan,
    )
    start = cfg.start or (FIRST_SNAPSHOT if idx else panel_meta["default_start"])
    end = cfg.end or panel_meta["source_boundary"]
    sealed = HOLDOUT if idx else GLOBAL_HOLDOUT
    if rule.kind == "DETECTOR" and not cfg.holdout_final and end >= sealed[0] and start <= sealed[1]:
        raise HoldoutSealed(f"window {start}..{end} touches the sealed {profile.market} holdout {sealed[0]}.."
                            f"{sealed[1]} (research/{'E1' if idx else 'E2'}/protocol.json); a detector runs there "
                            "once, as the pre-registered final test, with holdout_final=True (--holdout-final)")
    full_market = Market.from_panel(panel_df, price_limits=profile.price_limits)
    if "unit_factor" in panel_df:
        full_market = full_market.with_units(_dense(full_market, panel_df, "unit_factor", 1.0))
    elif cfg.units == "as_traded":
        raise ValueError("units='as_traded' needs a panel with a unit_factor column (build-us-repair-panel)")
    qa_flag = (_dense(full_market, panel_df, "qa_reverting_spike", False).astype(bool)
               if "qa_reverting_spike" in panel_df else None)
    lo, hi = full_market.bounds(start, end)
    ca_info = {"mode": cfg.ca_mode}
    if cfg.ca_mode == "registry":
        if ca_registry is None:
            raise RegistryMismatch("ca_mode='registry' needs a corporate-action registry built from this panel "
                                   "(python -m idxsig build-ca-registry)")
        reg_df, reg_meta = ca_registry
        if reg_meta["inputs"]["panel_sha256"] != panel_meta["sha256"]:
            raise RegistryMismatch(f"registry {reg_meta.get('_manifest')} was built for panel "
                                   f"{reg_meta['inputs']['panel_sha256'][:12]}, not {panel_meta['sha256'][:12]}")
        full_market = full_market.with_registry(reg_df)
        ca_info.update({"registry_version": reg_meta.get("registry_version", REGISTRY_VERSION),
                        "registry_manifest": reg_meta.get("_manifest"),
                        "registry_manifest_sha256": reg_meta.get("_manifest_sha256"),
                        "registry_sha256": reg_meta["sha256"], "registry_by_status": reg_meta.get("by_status")})
    m = full_market.slice(lo, hi)
    if cfg.ca_mode == "registry":
        ca_info["resets_in_window"] = m.with_registry(reg_df).registry_counts
    cache_key = (rule.sha256, start, end, panel_meta["sha256"], cfg.lookahead_cuts)
    if signal_cache is not None and cache_key in signal_cache:
        sig, lookahead = signal_cache[cache_key]
        sig = sig.copy()
    else:
        sig, lookahead = signals(rule, m, cfg.lookahead_cuts)
        if signal_cache is not None:
            signal_cache[cache_key] = (sig.copy(), lookahead)
    quarantined = []
    if cfg.quarantine == "unit_schedule":
        quarantined = sorted(panel_meta.get("unit_quarantine", {}).get("tickers", {}))
        if "unit_quarantine" not in panel_meta:
            raise ValueError("quarantine='unit_schedule' needs a panel built with a split schedule")
        sig[np.isin(m.tickers, quarantined), :] = np.nan  # no signals, not a control: both sides alike
    elif cfg.quarantine != "none":
        raise ValueError(f"unknown quarantine {cfg.quarantine!r}")
    evaluable = np.isfinite(sig)
    tick_idx, sig_idx = np.nonzero(sig == 1)  # row-major: by ticker, then session

    trades = execute(m, tick_idx, sig_idx, exec_cfg)
    overlap_skipped = np.zeros(len(tick_idx), dtype=bool)
    if cfg.overlap == "skip":
        held_until = {}
        for i, (n, s) in enumerate(zip(tick_idx, sig_idx)):
            if s + cfg.entry_lag <= held_until.get(n, -1):
                overlap_skipped[i] = True
                continue
            st = trades["status"][i]
            if trades["exit_idx"][i] >= 0:  # exited, exited at data end, or held across a corporate action
                held_until[n] = trades["exit_idx"][i]
            elif st == STATUS.index("INCOMPLETE"):
                held_until[n] = np.iinfo(np.int64).max
    attempt = ~overlap_skipped
    a_tick, a_sig = tick_idx[attempt], sig_idx[attempt]
    rule_stats = _summary_stats(trades["net_return"][attempt], trades["status"][attempt])
    if exec_cfg.side == "short" and exec_cfg.liquidation is not None:
        rule_stats["liquidated"] = int(trades["liquidated"][attempt].sum())

    draws = cfg.random_draws
    rng = np.random.default_rng(cfg.seed)
    same_tick = np.empty((draws, len(a_sig)), dtype=np.int64)
    for s in np.unique(a_sig):
        cols = np.flatnonzero(a_sig == s)
        same_tick[:, cols] = rng.choice(np.flatnonzero(evaluable[:, s]), size=(draws, len(cols)), replace=True)
    # Features from the whole panel, then windowed: each uses only data at or before its session,
    # and rolling windows are warm at the window's first session.
    feats = {k: v[:, lo:hi] for k, v in controls.features(full_market, cfg.controls_version,
                                                          profile.band_edges,
                                                          as_traded=cfg.units == "as_traded").items()}
    matched_tick, level_used = controls.matched_draws(
        evaluable, feats, a_tick, a_sig, draws, np.random.default_rng(cfg.seed + 1), cfg.controls_version
    )
    baselines, frames, raw = {}, [], {}
    for key, ticks, method in (
        ("random_matched", matched_tick, "same session, same " + " / ".join(controls.VERSIONS[cfg.controls_version])
                                         + " buckets as the signalled name (relaxed from the last feature when "
                                         f"fewer than {controls.MIN_POOL} names match), same execution"),
        ("random", same_tick, "same session, uniform over names where the rule was evaluable, same execution"),
    ):
        if len(a_sig):
            baselines[key], frame, raw[key] = _baseline(m, ticks, a_sig, exec_cfg, rule_stats, method)
            frames.append(frame.assign(baseline=key))
        else:
            baselines[key] = {"draws": draws, "method": method, "pooled": _summary_stats(np.array([]), np.array([], dtype=np.int64)),
                              "avg_net_return": None, "hit_rate": None}
    names = controls.level_names(cfg.controls_version)
    baselines["random_matched"]["match_level_used"] = {
        names[i]: int((level_used == i).sum()) for i in range(len(names)) if (level_used == i).any()
    }
    baselines["random_matched"]["controls"] = controls.coverage(feats, a_tick, a_sig, level_used, cfg.controls_version,
                                                                 None if idx else profile.band_names)
    draws_df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame()

    by_year = []
    years = m.dates.astype("datetime64[Y]").astype(int) + 1970
    sig_year = years[a_sig]
    for y in sorted(set(sig_year.tolist())):
        sel = sig_year == y
        rs = _summary_stats(trades["net_return"][attempt][sel], trades["status"][attempt][sel])
        row = {"year": int(y), "attempts": rs["attempts"], "scored": rs["scored"], "hit_rate": rs["hit_rate"],
               "avg_net_return": rs["avg_net_return"]}
        for key, out in raw.items():
            rsel = np.broadcast_to(sel, (draws, len(a_sig))).ravel()
            rr = _summary_stats(out["net_return"][rsel], out["status"][rsel])
            row[f"{key}_hit_rate"] = rr["hit_rate"]
            row[f"{key}_avg_net_return"] = rr["avg_net_return"]
        by_year.append(row)

    warnings = []
    if idx and np.datetime64(start, "D") < np.datetime64(FIRST_SNAPSHOT, "D"):
        warnings.append(
            f"window starts before {FIRST_SNAPSHOT}, the mirror's first snapshot: names that delisted before "
            f"then are missing, so the universe before {FIRST_SNAPSHOT} is survivor-biased"
        )
    if not idx:
        warnings.append(f"{profile.market}: {panel_meta.get('survivorship', 'survivorship not stated')}")
        if profile.assumption_note:
            warnings.append(profile.assumption_note)
    if idx and np.datetime64(end, "D") > np.datetime64(panel_meta["source_boundary"], "D"):
        warnings.append(
            f"window runs past {panel_meta['source_boundary']}: after that date the panel is survivor-only "
            f"(names delisted later stop at {panel_meta['source_boundary']} and exit as EXIT_DATA_END)"
        )
    if rule_stats["scored"] < 30:
        warnings.append(f"only {rule_stats['scored']} scored trades; any difference from random is mostly noise")
    data_end = rule_stats["status_counts"].get("EXIT_DATA_END", 0)
    if data_end:
        warnings.append(f"{data_end} trades exited at a last traded close because the name stopped trading "
                        f"(data_end_exit={cfg.data_end_exit})")
    excluded = sum(rule_stats["status_counts"].get(k, 0) for k in
                   ("EXCLUDED_CORP_ACTION", "CORP_ACTION_UNRESOLVED", "CORP_ACTION_RIGHTS_ISSUE"))
    if excluded:
        warnings.append(f"{excluded} trades were held across a corporate action the model does not share-scale "
                        f"and are not scored (ca_mode={cfg.ca_mode}); the baselines apply the same rule")
    if idx and cfg.ca_mode != "registry":
        warnings.append(f"ca_mode={cfg.ca_mode} is an earlier corporate-action model, kept to reproduce older runs: "
                        f"it treats every integer reset as a split")
    if lookahead["mode"] != rule_registry.CAUSAL_MODE:
        warnings.append("lookahead check was sampled, not prefix-first: the signals are not causal by construction")
    tiers = (quality.window_composition(m.dates, panel_meta["source_boundary"]) if idx
             else quality.composition_from(m.dates, panel_meta["quality_tiers"]))
    for tier, n in tiers["sessions_by_tier"].items():
        if idx and tier != "TIER_1":
            warnings.append(f"{n} sessions are {tier} data (see data_quality); results there are weaker than TIER_1")
    if rule.kind == "PLACEBO":
        warnings.append("PLACEBO rule: harness self-check, not a trading rule; any lift here is a harness bias")

    tickers = m.tickers
    trades_df = pd.DataFrame({
        "ticker": tickers[tick_idx],
        "signal_date": m.dates[sig_idx].astype(str),
        "status": np.where(overlap_skipped, "SKIP_OVERLAP", np.array(STATUS)[trades["status"]]),
        "entry_date": np.where(trades["entry_idx"] >= 0, m.dates[np.maximum(trades["entry_idx"], 0)].astype(str), ""),
        "exit_date": np.where(trades["exit_idx"] >= 0, m.dates[np.maximum(trades["exit_idx"], 0)].astype(str), ""),
        "entry_price": trades["entry_price"],
        "shares": trades["shares"],
        "exit_price": trades["exit_price"],
        "share_factor": trades["share_factor"],
        "rolled_sessions": trades["rolled_sessions"],
        **({"liquidated": trades["liquidated"]} if exec_cfg.side == "short" else {}),
        "gross_return": trades["gross_return"],
        "net_return": trades["net_return"],
        **({k: trades[k] for k in ("entry_price_as_traded", "exit_price_as_traded", "shares_as_traded")}
           if "entry_price_as_traded" in trades else {}),
    })
    repair = {}
    if cfg.units != "panel" or cfg.fill_model != "A" or cfg.quarantine != "none" or qa_flag is not None:
        repair = {"repair": {
            "units": {"mode": cfg.units, "schedule": panel_meta.get("unit_schedule"),
                      "note": "returns from split-adjusted prices; sizing, cost tiers (entry and exit, each at "
                              "its own session) and the price band at the price as traded that session"
                      if cfg.units == "as_traded" else "original: price levels as rescaled by later splits"},
            "fill_model": {"model": cfg.fill_model,
                           "note": ("A (original): entry needs the entry session to have traded and shares <= "
                                    f"{cfg.max_participation:.0%} of that session's FINAL volume, both known only "
                                    "after the close: an ex-post capacity filter, not proof of an opening fill")
                           if cfg.fill_model == "A" else
                           ("C (FILL-C-v1): closing-auction entry; shares <= "
                            f"{cfg.max_participation:.0%} of the median volume of the 20 sessions up to the signal "
                            "session, in entry-session shares through registry-verified splits (known at the "
                            "decision); an unverified reset in the window -> SKIP_CAPACITY_UNKNOWN; the entry "
                            "session must still trade and not lock at ARA")
                           if cfg.fill_model == "C" else
                           ("B (FILL-B-v1): shares <= "
                            f"{cfg.max_participation:.0%} of the median as-traded volume of the 20 sessions up to "
                            "the signal session (known at the decision); entry needs an opening price and a bar "
                            "with volume on the entry session (daily bars cannot prove the print was at 09:30)")},
            "quarantine": {"mode": cfg.quarantine, "tickers_excluded": len(quarantined),
                           "reasons": panel_meta.get("unit_quarantine", {}).get("reason_counts")},
            "preprocessing": panel_meta.get("preprocessing"),
        }}
        if qa_flag is not None:
            flag = qa_flag[:, lo:hi]
            repair["repair"]["qa_sensitivity"] = {
                "flag": "qa_reverting_spike (a close > 3x the prior close reverting below a third the next "
                        "session, or the mirror; known one session later, never a decision input)",
                "flagged_cells_in_window": int(flag.sum()),
                "rule": _qa_sensitivity(flag, {k: trades[k] for k in ("entry_idx", "exit_idx", "ticker_idx",
                                                                      "status", "net_return")}, attempt),
                **{key: _qa_sensitivity(flag, out) for key, out in raw.items()},
            }
    summary = {
        "rule": {"rule_id": rule.rule_id, "version": rule.version, "kind": rule.kind, "text": rule.text,
                 "sha256": rule.sha256, "holding_days": holding},
        "config": {**asdict(cfg), "start": start, "end": end, "holding_days": holding, **plan},
        "execution": {
            "price": ("official close; signal at close of s, entry at close of s + entry_lag" if profile.entry == "close"
                      else "signal at close of s, entry at the open of s + entry_lag, exit at a close"),
            "plan": exec_cfg.plan,
            "plan_text": plan_text(exec_cfg.plan, profile.entry),
            **({"short_side": {"carry_per_session": exec_cfg.carry_per_session, "note": profile.short_note,
                               "liquidation": exec_cfg.liquidation,
                               "liquidation_note": ("isolated margin: liquidated at the first session whose high "
                                                    f"is {exec_cfg.liquidation:.0%} above the entry, losing that "
                                                    "fraction of the sold notional plus fees and carry"
                                                    if exec_cfg.liquidation is not None else
                                                    "none: losses are unbounded")}}
               if exec_cfg.side == "short" else {}),
            **({"jump_ratio": {"ratio": exec_cfg.jump_ratio,
                               "note": "a session whose close/reference ratio is beyond this inside (entry, exit] "
                                       "is a redenomination or a bad print, not a trade; such trades are "
                                       "EXCLUDED_DATA_JUMP for the rule and the baselines alike"}}
               if exec_cfg.jump_ratio is not None else {}),
            "lot_size": profile.lot_size,
            "cost_tiers": [list(t) for t in profile.cost_tiers],
            "fees": {"buy": cfg.fee_buy, "sell": cfg.fee_sell},
            "auto_rejection": ("entry refused when the entry close is locked at ARA; exit rolls while locked at ARB "
                               "or untraded; regular-board schedule by date, plus 10% special-board limits on "
                               "one-price or sub-Rp50 bars") if profile.price_limits else "none (no daily price limits)",
            "corporate_actions": {
                "registry": "shares scaled only through registry-verified splits, reverse splits and stock "
                            "dividends; trades held across a verified rights issue or any unverified reset are "
                            "not scored (CORP_ACTION_RIGHTS_ISSUE / CORP_ACTION_UNRESOLVED)",
                "exclude": "legacy: every integer reset scaled as a split; other resets excluded",
                "value_preserving": "legacy: shares scaled by every reset (rights valued as reinvested)",
                "adjusted": "source prices are split-adjusted; no reference resets are expected or scaled",
            }[cfg.ca_mode],
        },
        "corporate_action_model": ca_info,
        "harness": {"signals": lookahead["mode"], "rule_view_fields": list(rule_registry.RULE_FIELDS),
                    "controls": cfg.controls_version, "ca_mode": cfg.ca_mode},
        "data_quality": {**tiers, "tiers": quality.tiers(panel_meta.get("first_session", str(m.dates[0])),
                                                         panel_meta["source_boundary"],
                                                         panel_meta.get("last_session", str(m.dates[-1])))
                         if idx else panel_meta["quality_tiers"],
                         "panel_format": panel_meta.get("format", "panel-v1"),
                         "known_limitations": list(quality.KNOWN_LIMITATIONS if idx else panel_meta["known_limitations"])},
        "market": {"profile": profile.market, "currency": profile.currency, "lot_size": profile.lot_size,
                   "entry": profile.entry, "price_limits": profile.price_limits, "venue": profile.venue,
                   "cost_assumption": profile.assumption_note},
        "panel": {"manifest_sha256": panel_meta.get("_manifest_sha256"), "panel_sha256": panel_meta["sha256"],
                  "panel": panel_meta["panel"], "source_boundary": panel_meta["source_boundary"]},
        "universe": {
            "first_session": str(m.dates[0]),
            "last_session": str(m.dates[-1]),
            "sessions": int(m.shape[1]),
            "tickers_in_window": int(m.present.any(axis=1).sum()),
            "tickers_ending_inside_window": int((m.present.any(axis=1) & ~m.present[:, -1]).sum()),
            "evaluable_ticker_sessions": int(evaluable.sum()),
            "tickers_ever_evaluable": int(evaluable.any(axis=1).sum()),
        },
        "signals": {
            "total": int(len(tick_idx)),
            "signal_rate": float(len(tick_idx) / evaluable.sum()) if evaluable.sum() else None,
            "tickers_with_signals": int(len(np.unique(tick_idx))),
            "skipped_overlap": int(overlap_skipped.sum()),
            "attempted": int(attempt.sum()),
        },
        "rule_trades": rule_stats,
        **baselines,
        **repair,
        "by_year": by_year,
        "lookahead_check": lookahead,
        "warnings": warnings,
    }
    return {"summary": summary, "trades": trades_df, "draws": draws_df}
