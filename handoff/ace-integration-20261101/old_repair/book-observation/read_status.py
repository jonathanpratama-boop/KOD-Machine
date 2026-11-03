"""Offline status reconciliation; a RUNNING file alone never proves liveness."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def _json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def _journal(path):
    rows, warnings = [], []
    if not path.exists():
        return rows, warnings
    for i, line in enumerate(path.read_text().splitlines(), 1):
        try:
            rows.append(json.loads(line))
        except ValueError:
            warnings.append(f"{path.name}:{i}:unreadable_record")
    return rows, warnings


def read_status(run_dir: Path, *, now: datetime, process_alive: bool | None = None):
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("timezone-aware now required")
    protocol = _json(run_dir / 'protocol.json')
    status = _json(run_dir / 'status.json')
    terminal = _json(run_dir / 'termination.json')
    attempts, warn_a = _journal(run_dir / 'attempts.jsonl')
    observations, warn_o = _journal(run_dir / 'observations.jsonl')
    pairs = protocol.get('pairs', [])
    scheduled = protocol.get('sample_sets', 0) * len(pairs)
    keys = {(r.get('slot'), r.get('symbol')) for r in observations}
    out = {'state': 'UNKNOWN', 'reason': 'NO_VERIFIED_LIVENESS_OR_TERMINATION',
           'process_alive': process_alive, 'recorded_state': status.get('state'),
           'requests_attempted': len(attempts),
           'successful_books': sum(r.get('status') == 'OBSERVED' for r in observations),
           'failed_samples': sum(r.get('status') == 'FAILED' for r in observations),
           'missing_samples': max(0, scheduled - len(keys)), 'scheduled_samples': scheduled,
           'warnings': warn_a + warn_o}
    # Explicit runtime evidence, not a guessed interpretation of a transport error.
    if terminal.get('kind') == 'NETWORK_POLICY_BLOCK' and terminal.get('runtime_error') and terminal.get('observed_at_utc'):
        out.update(state='BLOCKED', reason='EXPLICIT_RUNTIME_NETWORK_POLICY_TERMINATION',
                   termination_evidence=terminal, resume_allowed=False)
        return out
    if terminal.get('kind') == 'PROCESS_EXIT' and terminal.get('observed_at_utc'):
        out.update(state='STOPPED', reason='EXPLICIT_PROCESS_EXIT', termination_evidence=terminal)
        return out
    if status.get('state') in ('COMPLETE', 'STOPPED', 'BLOCKED'):
        out.update(state=status['state'], reason='RECORDED_TERMINAL_STATUS')
        return out
    heartbeat = status.get('last_update_utc')
    try:
        t = datetime.fromisoformat(heartbeat.replace('Z', '+00:00'))
        if t.tzinfo is None or t.utcoffset() is None or t > now:
            raise ValueError('invalid heartbeat')
        age = (now - t).total_seconds()
    except (AttributeError, TypeError, ValueError):
        out['reason'] = 'MISSING_OR_INVALID_HEARTBEAT'
        return out
    threshold = protocol.get('interval_seconds', 120) + len(pairs) * protocol.get('request_timeout_seconds', 20) + 30
    out.update(heartbeat_age_seconds=age, stale_after_seconds=threshold)
    if age > threshold:
        out.update(state='STALE', reason='HEARTBEAT_EXPIRED_NO_TERMINATION_EVIDENCE')
    elif process_alive is False:
        out.update(state='UNKNOWN', reason='PROCESS_NOT_ALIVE_NO_TERMINATION_EVIDENCE')
    elif process_alive is True and not out['warnings']:
        out.update(state='RUNNING', reason='EXPLICIT_PROCESS_LIVENESS_AND_FRESH_HEARTBEAT')
    else:
        out['reason'] = 'FRESH_HEARTBEAT_WITHOUT_VERIFIED_PROCESS_LIVENESS'
    return out


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('run_dir', type=Path)
    parser.add_argument('--process-state', choices=('alive', 'dead', 'unknown'), default='unknown')
    args = parser.parse_args()
    alive = {'alive': True, 'dead': False, 'unknown': None}[args.process_state]
    print(json.dumps(read_status(args.run_dir, now=datetime.now(timezone.utc), process_alive=alive), indent=2))
