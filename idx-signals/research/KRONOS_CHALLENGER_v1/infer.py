"""Frozen, offline Kronos adapter. Reads causal inputs only; never reads outcomes."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import resource
import subprocess
import sys
import time


HERE = Path(__file__).resolve().parent


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def event_seed(event_id):
    return int(hashlib.sha256(f"{event_id}|20261108".encode()).hexdigest()[:8], 16)


def validate_input(frame, row):
    import numpy as np
    import pandas as pd
    times = pd.to_datetime(frame.timestamps, utc=True)
    decision = pd.Timestamp(row['decision_time'])
    expected = pd.date_range(end=decision - pd.Timedelta(hours=1), periods=168, freq='h')
    if len(frame) != 168 or not np.array_equal(times.to_numpy(), expected.to_numpy()):
        raise ValueError('Input must contain exactly 168 contiguous completed hourly candles')
    if (pd.to_datetime(frame.close_time, utc=True) >= decision).any():
        raise ValueError('Future or unfinished candle in input')
    values = frame[['open', 'high', 'low', 'close', 'volume', 'amount']].to_numpy()
    if not np.isfinite(values).all() or (values[:, :4] <= 0).any() or (values[:, 4:] < 0).any():
        raise ValueError('Invalid OHLCVA input')
    if not math.isclose(float(frame.close.iloc[-1]), float(row['last_observed_close']), rel_tol=1e-12):
        raise ValueError('Manifest last close mismatch')
    return times


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--upstream', type=Path, required=True)
    parser.add_argument('--models', type=Path, required=True)
    parser.add_argument('--data', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    protocol = json.loads((HERE / 'protocol.json').read_text())
    commit = subprocess.check_output(['git', '-C', str(args.upstream), 'rev-parse', 'HEAD'], text=True).strip()
    if commit != protocol['upstream_commit']:
        raise ValueError('Upstream revision does not match frozen protocol')
    if subprocess.check_output(['git', '-C', str(args.upstream), 'diff', 'HEAD'], text=True):
        raise ValueError('Upstream tracked code was modified')
    sys.path.insert(0, str(args.upstream.resolve()))
    import numpy as np
    import pandas as pd
    import torch
    from model import Kronos, KronosPredictor, KronosTokenizer

    rows = [json.loads(line) for line in (args.data / 'input_manifest.jsonl').read_text().splitlines()]
    cohort = pd.read_csv(HERE / 'cohort.csv')
    if [r['event_id'] for r in rows] != cohort.event_id.tolist():
        raise ValueError('Input manifest must retain the entire frozen cohort in order')
    args.output.mkdir(parents=True, exist_ok=True)
    output = args.output / 'predictions.jsonl'
    if output.exists():
        raise FileExistsError('Predictions already exist; use a new output directory and retain the old run')
    manifest = {
        'protocol_sha256': sha256(HERE / 'protocol.json'),
        'cohort_sha256': sha256(HERE / 'cohort.csv'),
        'input_manifest_sha256': sha256(args.data / 'input_manifest.jsonl'),
        'adapter_sha256': sha256(__file__), 'upstream_commit': commit,
        'torch': torch.__version__, 'numpy': np.__version__, 'pandas': pd.__version__,
        'device': 'cpu', 'threads': 4, 'models': {}, 'events': len(rows),
        'started_at': pd.Timestamp.now(tz='UTC').isoformat(),
    }
    for name, expected in protocol['models'].items():
        model_dir = args.models / name
        if json.loads((model_dir / 'revision.json').read_text()) != expected:
            raise ValueError('Model revision does not match frozen protocol')
        manifest['models'][name] = {**expected, 'weights_sha256': sha256(model_dir / 'model.safetensors'),
                                    'config_sha256': sha256(model_dir / 'config.json')}
    (args.output / 'run_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    torch.set_num_threads(4)
    torch.set_num_interop_threads(1)
    torch.use_deterministic_algorithms(True)
    model = Kronos.from_pretrained(str(args.models / 'Kronos-small')).eval()
    tokenizer = KronosTokenizer.from_pretrained(str(args.models / 'Kronos-Tokenizer-base')).eval()
    predictor = KronosPredictor(model, tokenizer, device='cpu', max_context=512, clip=5)
    started = time.perf_counter()
    with output.open('x') as journal:
        for index, row in enumerate(rows):
            seed = event_seed(row['event_id'])
            record = {key: row[key] for key in ['event_id', 'symbol', 'decision_time', 'entry_time', 'exit_time']}
            record.update(seed=seed, input_sha256=row.get('input_sha256'), status='failed',
                          predicted_return=None, inference_seconds=0.0)
            event_start = time.perf_counter()
            try:
                if row['status'] != 'ready':
                    raise ValueError('Input unavailable: ' + row.get('error', 'unknown'))
                input_path = Path(row['input_path'])
                if not input_path.is_absolute():
                    input_path = args.data / input_path
                if sha256(input_path) != row['input_sha256']:
                    raise ValueError('Input hash mismatch')
                frame = pd.read_csv(input_path)
                times = validate_input(frame, row)
                future = pd.Series(pd.date_range(start=pd.Timestamp(row['decision_time']), periods=25, freq='h'))
                torch.manual_seed(seed)
                np.random.seed(seed)
                with torch.inference_mode():
                    forecast = predictor.predict(frame, pd.Series(times), future, pred_len=25,
                                                 T=1.0, top_k=0, top_p=0.9, sample_count=8, verbose=False)
                terminal = float(forecast.close.iloc[-1])
                if not math.isfinite(terminal) or terminal <= 0:
                    raise ValueError('Invalid forecast terminal close')
                elapsed = time.perf_counter() - event_start
                if elapsed >= 3600:
                    raise ValueError('Inference missed the one-hour entry budget')
                forecast_name = hashlib.sha256(row['event_id'].encode()).hexdigest() + '.csv'
                forecast.to_csv(args.output / forecast_name)
                record.update(status='ok', predicted_return=terminal / float(frame.close.iloc[-1]) - 1,
                              forecast_file=forecast_name, forecast_sha256=sha256(args.output / forecast_name))
            except Exception as exc:
                record['error'] = f'{type(exc).__name__}: {exc}'
            record['inference_seconds'] = time.perf_counter() - event_start
            journal.write(json.dumps(record, allow_nan=False) + '\n')
            journal.flush()
            print(f"{index + 1}/{len(rows)} {record['status']} {row['event_id']} {record['inference_seconds']:.2f}s", flush=True)
    manifest.update(finished_at=pd.Timestamp.now(tz='UTC').isoformat(),
                    inference_total_seconds=time.perf_counter() - started,
                    peak_rss_mib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024,
                    predictions_sha256=sha256(output))
    (args.output / 'run_manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')


if __name__ == '__main__':
    main()
