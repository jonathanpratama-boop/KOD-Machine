"""Join completed, frozen predictions to separate outcomes, then evaluate once."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
from evaluate import evaluate

HERE = Path(__file__).resolve().parent


def read_jsonl(path):
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.run / 'run_manifest.json').read_text())
    prediction_path = args.run / 'predictions.jsonl'
    if 'finished_at' not in manifest:
        raise ValueError('Inference must finish before outcomes are joined')
    if hashlib.sha256(prediction_path.read_bytes()).hexdigest() != manifest['predictions_sha256']:
        raise ValueError('Predictions changed after inference finished')
    if hashlib.sha256((HERE / 'protocol.json').read_bytes()).hexdigest() != manifest['protocol_sha256']:
        raise ValueError('Protocol changed during the run')
    protocol = json.loads((HERE / 'protocol.json').read_text())
    cohort_hash = hashlib.sha256((HERE / 'cohort.csv').read_bytes()).hexdigest()
    if cohort_hash != manifest['cohort_sha256'] or cohort_hash != protocol['cohort']['cohort_sha256']:
        raise ValueError('Cohort differs from the frozen selection')
    if hashlib.sha256((args.data / 'input_manifest.jsonl').read_bytes()).hexdigest() != manifest['input_manifest_sha256']:
        raise ValueError('Input manifest changed during the run')
    check = json.loads((HERE / 'results' / 'LOOKAHEAD_CHECK.json').read_text())
    if check.get('verdict') != 'PASS':
        raise ValueError('Look-ahead check must pass before scoring')
    cohort_ids = [row['event_id'] for row in csv.DictReader((HERE / 'cohort.csv').open())]
    predictions = read_jsonl(prediction_path)
    outcomes = read_jsonl(args.data / 'outcomes.jsonl')
    if [row['event_id'] for row in predictions] != cohort_ids or [row['event_id'] for row in outcomes] != cohort_ids:
        raise ValueError('Predictions/outcomes must retain the entire frozen cohort, once, in order')
    records = []
    for prediction, outcome in zip(predictions, outcomes):
        records.append({**prediction, 'actual_gross_return': outcome['actual_gross_return'],
                        'actual_forecast_target_return': outcome['actual_forecast_target_return'],
                        'outcome_status': outcome['status'], 'outcome_error': outcome.get('error')})
    result = evaluate(records)
    result['protocol_sha256'] = manifest['protocol_sha256']
    result['predictions_sha256'] = manifest['predictions_sha256']
    result['outcomes_sha256'] = hashlib.sha256((args.data / 'outcomes.jsonl').read_bytes()).hexdigest()
    for name in ['records.jsonl', 'RESULT.json']:
        if (args.run / name).exists():
            raise FileExistsError('Scored run already exists; retain it without overwriting')
    (args.run / 'records.jsonl').write_text(''.join(json.dumps(row, allow_nan=False) + '\n' for row in records))
    (args.run / 'RESULT.json').write_text(json.dumps(result, indent=2, allow_nan=False) + '\n')
    print(json.dumps({key: result[key] for key in ['counts', 'baseline', 'combined_on_same_opportunities',
                     'paired_mean_delta', 'paired_delta_95pct_date_cluster_bootstrap', 'combined_beats_cash', 'verdict']}, indent=2))


if __name__ == '__main__':
    main()
