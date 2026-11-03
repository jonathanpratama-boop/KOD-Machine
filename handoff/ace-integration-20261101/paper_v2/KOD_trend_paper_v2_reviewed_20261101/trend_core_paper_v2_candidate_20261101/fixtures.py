"""Synthetic tapes only. No market history or outcome optimization."""
from datetime import date, datetime, timedelta, timezone
import math
from paper_candidate import evidence, sha, stamp, utc

SCENARIO = {"id":"SYNTHETIC_COST_SCENARIO_1", "fee":".001", "slippage":".0005", "precision":8,
            "quote_max_age_seconds":120, "intent_life_seconds":3600, "daily_grace_seconds":300}


def init(cash="10000", at="2026-02-10T00:00:00Z", scenario=None):
    return {"op":"init", "account_id":"SYNTHETIC_TREND_V2", "at":at,
            "initial_cash":cash, "mode":"synthetic_spot_only", "scenario":scenario or SCENARIO}


def quote(symbol, at, bid="100", ask="100.1", size="1000000", *, received_at=None):
    p={"symbol":symbol, "venue":"SYNTHETIC_SPOT", "product":"spot", "observed_at":at,
       "bid":str(bid), "ask":str(ask), "bid_qty":size, "ask_qty":size}
    return {"op":"observe", "at":received_at or at,
            "evidence":evidence(p, received_at or at)}


def decision(signal_date="2026-02-09", at="2026-02-10T00:01:00Z", directions=(1,1)):
    p={}
    for symbol,direction in zip(("BTCUSDT","ETHUSDT"),directions):
        bars=[]
        for i in range(40):
            day=date.fromisoformat(signal_date)-timedelta(days=39-i)
            close=str(100+direction*i*.2+.05*math.sin(i))
            pub=stamp(datetime.combine(day+timedelta(days=1),datetime.min.time(),timezone.utc)+timedelta(seconds=1))
            base={"day":day.isoformat(),"close":close}
            bars.append({**base,"published_at":pub,"received_at":pub,"source_sha256":sha(base)})
        p[symbol]=bars
    return {"op":"decision", "signal_date":signal_date, "at":at,
            "evidence":evidence(p,stamp(utc(at)-timedelta(seconds=1)))}


def seed_quotes(ledger, at="2026-02-10T00:00:50Z", bid="100", ask="100.1"):
    for symbol in ("BTCUSDT","ETHUSDT"):
        ledger.transact(quote(symbol,at,bid,ask))


def buy_both(ledger, cash="10000"):
    ledger.transact(init(cash))
    seed_quotes(ledger)
    d=ledger.transact(decision())
    for symbol in ("BTCUSDT","ETHUSDT"):
        ledger.transact(quote(symbol,"2026-02-10T00:01:05Z"))
    return d
