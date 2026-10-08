"""Rebuild the panel with share-count corroboration (sec-shares-v1) and repeat the frozen R1/R2 configs
(copied from Codex's v2 runs, which copied the v1 R1/R2 configs).

Run from idx-signals after recheck_archived.py. Original artifacts remain unchanged.
"""
import gc
import json
import platform
import sys
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT))
from idxsig import global_panel
from idxsig.backtest import RunConfig, run
from idxsig.provenance import sha256_file
from idxsig.results import write_run

HERE = Path(__file__).parent
SCHEDULE = 'data/corporate_actions/us_splits-shares-20261008T114309Z.json'
COVERAGE = 'data/corporate_actions/us_splits-coverage-reaudit-20261008T112522Z.json'
PREVIOUS = ('20261008T113137Z_MOONSHOT_E2_US_D1_v1', '20261008T113335Z_MOONSHOT_E2_US_D1_v1')  # Codex v2 runs: fill A, fill B


def main():
    panel = global_panel.build_us_repair(
        ROOT/'data/manifests/yahoo_us-20261008T001812Z.jsonl',
        ROOT/SCHEDULE, '2023-12-29', ROOT/COVERAGE)
    frame, meta = global_panel.load(panel)
    out = {'panel_manifest': str(panel.relative_to(ROOT)), 'panel_manifest_sha256': sha256_file(panel),
           'environment': {'python': platform.python_version(), 'pandas': pd.__version__, 'numpy': np.__version__},
           'quarantine_tickers': len(meta['unit_quarantine']['tickers']), 'runs': []}
    old_meta = json.loads((ROOT/'data/manifests/panel_us_repair-20261008T112818Z.json').read_text())
    old_quarantine = set(old_meta['unit_quarantine']['tickers'])
    new_quarantine = set(meta['unit_quarantine']['tickers'])
    out['newly_quarantined'] = sorted(new_quarantine-old_quarantine)
    out['released_from_quarantine'] = sorted(old_quarantine-new_quarantine)
    for previous in PREVIOUS:
        old = ROOT/'results/runs'/previous
        old_summary = json.loads((old/'summary.json').read_text())
        cfg = RunConfig(**old_summary['config'])
        print(f'Running fill model {cfg.fill_model}', flush=True)
        result = run(cfg, frame, meta)
        new = write_run(result, commit=False)
        s = result['summary']
        before = pd.read_csv(old/'trades.csv.gz', keep_default_na=False).set_index(['ticker','signal_date'])
        after = result['trades'].set_index(['ticker','signal_date'])
        lost = before.index.difference(after.index)
        gained = after.index.difference(before.index)
        both = before.index.intersection(after.index)
        transitions = pd.DataFrame({'old': before.loc[both,'status'], 'new': after.loc[both,'status']}).value_counts()
        record = {'previous_run': previous, 'run': new.name, 'fill_model': cfg.fill_model,
                  'signals': s['signals']['total'], 'scored': s['rule_trades']['scored'],
                  'rule_avg_net_return': s['rule_trades']['avg_net_return'],
                  'matched_random': s['random_matched']['avg_net_return'],
                  'signals_removed': len(lost), 'signals_added': len(gained), 'signals_in_both': len(both),
                  'removed_without_new_quarantine': [(t,d) for t,d in lost if t not in new_quarantine-old_quarantine],
                  'added_without_released_quarantine': [(t,d) for t,d in gained if t not in old_quarantine-new_quarantine],
                  'status_transitions': {f'{a} -> {b}': int(n) for (a,b),n in transitions.items() if a != b}}
        out['runs'].append(record)
        print(json.dumps(record, indent=2), flush=True)
        del result
        gc.collect()
    ledger = list(map(json.loads, (ROOT/'paper/ledger.jsonl').read_text().splitlines()))
    out['paper_outcomes_needing_revision'] = sum(r['type']=='OUTCOME' for r in ledger)
    out['paper_ledger_sha256'] = sha256_file(ROOT/'paper/ledger.jsonl')
    with (HERE/'results.json').open('x') as f:
        f.write(json.dumps(out, indent=2, sort_keys=True)+'\n')


if __name__ == '__main__':
    main()
