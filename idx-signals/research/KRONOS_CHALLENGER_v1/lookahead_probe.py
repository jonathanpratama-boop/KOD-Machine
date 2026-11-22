"""Probe the real causal loader; does not run the model or inspect returns.

Schedule is copied from the first three frozen cohort identifiers. The only
decision is the hash of the exact completed-candle input passed to inference.
This checks loader selection, not inherited event inclusion or model training.
"""
import hashlib
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepare import causal_context


SCHEDULE = (
    ('RSRUSDT', '2024-07-11T13:00:00+00:00'),
    ('RADUSDT', '2024-07-28T08:00:00+00:00'),
    ('MAVUSDT', '2024-07-29T11:00:00+00:00'),
)


def decide(data):
    frame = data.copy()
    frame['timestamps'] = pd.to_datetime(frame['timestamps'], utc=True)
    frame['close_time'] = pd.to_datetime(frame['close_time'], utc=True)
    decisions = []
    for symbol, decision_string in SCHEDULE:
        decision = pd.Timestamp(decision_string)
        candidate = frame.loc[frame.symbol == symbol].drop(columns='symbol').set_index('timestamps')
        try:
            context = causal_context(candidate, decision - pd.Timedelta(hours=1), decision)
        except ValueError:
            # A future decision may have too little data after truncation or
            # invalid scrambled future values; earlier decisions remain tested.
            continue
        text = context.to_csv(float_format='%.12g')
        decisions.append({'event_id': symbol + '|' + decision_string,
                          'decision_time': decision_string,
                          'input_sha256': hashlib.sha256(text.encode()).hexdigest()})
    return pd.DataFrame(decisions, columns=['event_id', 'decision_time', 'input_sha256'])
