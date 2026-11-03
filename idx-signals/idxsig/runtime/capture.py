"""Two bounded public observations for an explicit forward paper cycle."""
import fcntl
from pathlib import Path
from uuid import uuid4

from .collect import collect_binance_spot, PublicDataUnavailable
from .coordinator import run_once, now, META_KEYS
from .storage import read_json, immutable_json, atomic_json, locked


def capture(root, *, initial_cash="1000", fee_rate="0.001", slippage="0.001", symbols=None):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    symbols = symbols or ["BTCUSDT", "ETHUSDT"]
    if not {"BTCUSDT", "ETHUSDT"} <= set(symbols):
        raise ValueError("capture requires BTCUSDT and ETHUSDT; additional radar symbols are optional")
    with (root / ".capture.lock").open("a+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        if (root / "pending.json").exists():
            # Preserve the actual original cutoff and input; never reinterpret it as a new run.
            pending = read_json(root / "pending.json")
            run_once(root, root / "inputs" / (pending["input_sha256"] + ".json"), root / "profile.json",
                     pending["as_of"], root / "evidence", _captured=True)
        for _ in range(2):
            source = root / "captures" / (uuid4().hex + ".json")
            try:
                snapshot = collect_binance_spot(source, root / "evidence", symbols, days=120)
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
            except (ValueError, OSError, KeyError, PublicDataUnavailable) as exc:
                with locked(root):
                    atomic_json(root / "last_attempt.json", {"status": "FAILED", "recorded_at": now(), "error": str(exc), "phase": "PUBLIC_CAPTURE"})
                raise
        return result
