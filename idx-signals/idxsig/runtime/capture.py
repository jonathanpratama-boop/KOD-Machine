"""Two bounded public observations for an explicit forward paper cycle."""
import fcntl
from pathlib import Path
from uuid import uuid4

from .collect import collect_binance_spot, PublicDataUnavailable
from .coordinator import run_once, now, META_KEYS
from .storage import read_json, immutable_json, atomic_json, locked


def capture(root, *, initial_cash="1000", fee_rate="0.001", slippage="0.001", symbols=None, scheduled_at=None,
            timestamp_decisions=True):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    symbols = symbols or ["BTCUSDT", "ETHUSDT"]
    if not {"BTCUSDT", "ETHUSDT"} <= set(symbols):
        raise ValueError("capture requires BTCUSDT and ETHUSDT; additional radar symbols are optional")
    from .timing import Attempt
    trace = Attempt(root, detector="KOD_PUBLIC_CAPTURE_V1", source="BINANCE_SPOT_PUBLIC",
                    kind="prospective", members=symbols, scheduled_at=scheduled_at)
    with (root / ".capture.lock").open("a+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        if (root / "pending.json").exists():
            # Preserve the actual original cutoff and input; never reinterpret it as a new run.
            pending = read_json(root / "pending.json")
            run_once(root, root / "inputs" / (pending["input_sha256"] + ".json"), root / "profile.json",
                     pending["as_of"], root / "evidence", _captured=True)
        prior_fills = set()
        decision_batch = None
        for index in range(2):
            source = root / "captures" / (uuid4().hex + ".json")
            try:
                snapshot = collect_binance_spot(source, root / "evidence", symbols, days=120)
                if index == 0:
                    trace.mark("received_at")
                else:
                    execution_observed = trace.clock()
                cutoff = now()
                profile_path = root / "profile.json"
                if not profile_path.exists():
                    profile = {"id": "KOD_BINANCE_FORWARD_PAPER_V1", "execution_mode": "FORWARD_PAPER_CAPTURE",
                               "evidence_type": "public_market", "venue": "BINANCE_SPOT", "quote_currency": "USDT",
                               "initial_cash": initial_cash, "fee_rate": fee_rate, "slippage": slippage,
                               "cost_basis": "explicit simulation assumptions; not authenticated account fees",
                               "max_quote_age": 120, "expiry": 3600, "instruments": {}}
                    for item in snapshot["instruments"]:
                        if item["symbol"] in ("BTCUSDT", "ETHUSDT"):
                            profile["instruments"][item["symbol"]] = {k: item[k] for k in (*META_KEYS, "metadata_received_at", "evidence_id") if item.get(k) is not None}
                    with locked(root):
                        immutable_json(profile_path, profile)
                else:
                    profile = read_json(profile_path)
                    if profile.get("execution_mode") != "FORWARD_PAPER_CAPTURE":
                        raise ValueError("capture needs a separate forward paper runtime root")
                    # Existing economic assumptions cannot be revised by CLI defaults or flags.
                    for key, supplied in (("initial_cash", initial_cash), ("fee_rate", fee_rate), ("slippage", slippage)):
                        from decimal import Decimal
                        if Decimal(str(profile[key])) != Decimal(str(supplied)):
                            raise ValueError("capture argument differs from frozen profile: " + key)
                result = run_once(root, source, profile_path, cutoff, root / "evidence", _captured=True)
                payload = result["payload"]
                if index == 0:
                    trace.mark("features_ready_at")
                    if payload["candidates"]:
                        trace.mark("detected_at")
                    if payload["run"]["decision_status"] not in {"ORIGINAL_DECISION_RETAINED", "BLOCKED"}:
                        trace.mark("decision_at")
                        decision_batch = {"decision_at": trace.record["decision_at"],
                            "attempt_id": trace.record["id"], "run_id": payload["run"]["id"],
                            "snapshot_sha256": result["sha256"], "paper_only": True}
                        # The second observation produces a different run/fill receipt.
                        # Keep the signed first decision and final run identities separate.
                        trace.record["links"]["decision_run_id"] = payload["run"]["id"]
                    prior_fills = {row["id"] for row in payload["account"]["fills"]}
                else:
                    new_fills = [row for row in payload["account"]["fills"] if row["id"] not in prior_fills]
                    if new_fills:
                        trace.mark("executable_at", at=execution_observed)
                        trace.mark("fill_at")
            except (ValueError, OSError, KeyError, PublicDataUnavailable) as exc:
                trace.finish("FAILED", reason=type(exc).__name__)
                with locked(root):
                    atomic_json(root / "last_attempt.json", {"status": "FAILED", "recorded_at": now(), "error": str(exc), "phase": "PUBLIC_CAPTURE"})
                raise
        if decision_batch is not None:
            from .time_anchor import anchor_batch
            anchor = anchor_batch(root, decision_batch, enabled=timestamp_decisions)
            if anchor.get("status") != "DISABLED":
                trace.record["links"]["anchor_id"] = anchor.get("anchor_id")
            trace.record["links"]["anchor_status"] = anchor.get("status")
            trace.record["external_timestamp"] = {"status": "UNAVAILABLE",
                "reason": "Batch anchor is separate and may follow quotes/fills; it does not establish earlier decision availability."}
        trace.finish("FILLED" if trace.record["fill_at"] else "COMPLETED",
            links={"run_id": result["payload"]["run"]["id"]},
            reason="Finite public capture; stage times bound observed processing completion, not exchange execution.")
        return result
