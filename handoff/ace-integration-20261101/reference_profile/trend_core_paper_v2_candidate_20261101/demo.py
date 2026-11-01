"""Run only synthetic receipt fixtures; never accesses a venue or real account."""
import argparse
import hashlib
import json
from pathlib import Path

from paper_candidate import Ledger, account_view, bundle_pins, wire
from fixtures import init, buy_both, quote


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir",required=True,help="local folder for two synthetic journals and receipt")
    args=parser.parse_args()
    folder=Path(args.output_dir);folder.mkdir(parents=True,exist_ok=True)
    report={"classification":"SYNTHETIC_ACCOUNTING_ACCEPTANCE_NOT_MARKET_PERFORMANCE",
            "network_used":False,"real_orders":False,"bundle_pins":bundle_pins(),"fixtures":[]}
    for cash in ("1000","10000"):
        path=folder/("synthetic_"+cash+".jsonl")
        l=Ledger(path)
        l.transact(init(cash))
        metadata_path=Path(__file__).parent/"v1/DUPLICATE_AUDIT_METADATA.json"
        metadata_raw=metadata_path.read_bytes()
        l.transact({"op":"audit","at":"2026-02-10T00:00:00Z",
                    "reference_sha256":hashlib.sha256(metadata_raw).hexdigest(),
                    "details":{"v1_signals_are_not_fills":True,"separate_audit_metadata":json.loads(metadata_raw)}})
        decision=buy_both(l,cash)
        l.transact(quote("BTCUSDT","2026-02-10T00:04:00Z","50","50.1"))
        l.transact(quote("ETHUSDT","2026-02-10T00:04:00Z","50","50.1"))
        l.transact(quote("BTCUSDT","2026-02-10T00:04:01Z","40","40.1",size=".1"))
        st=Ledger(path).state()
        report["fixtures"].append({"initial_cash":cash,"normalized_targets":decision["normalized_targets"],
            "account":wire(account_view(st,st["clock"])),"kill":st["kill"],
            "fill_count":len(st["fills"]),"journal_sha256":hashlib.sha256(path.read_bytes()).hexdigest(),
            "note":"Deliberate synthetic loss/partial-liquidation fixture; not a historical trade or expected return."})
    target=folder/"synthetic_receipt.json"
    target.write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps(report,indent=2))

if __name__=="__main__": main()
