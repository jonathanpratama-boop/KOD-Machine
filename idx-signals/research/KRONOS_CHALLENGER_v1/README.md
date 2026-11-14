# Kronos continuation-filter pilot

One optional, offline model adapter evaluates whether pretrained Kronos-small helps reject unhelpful **existing**
KOD legacy ignition signals. `protocol.json` fixes the cohort, model revisions, inputs, threshold, costs, execution
delay and scoring. There is no fitting, parameter search, service, broker connection or scheduled worker.

The 128 identifiers are sampled from already-exposed history after the authors' reported June 2024 training cutoff.
This is exploratory; the original cohort required future 72-hour data availability. See `FEASIBILITY.md` and
`RUN_NOTES.md` for limitations and the specific owner authorization. It does not amend the live 30-day study.

Completed pilot: unfiltered signals averaged **−4.94%**, the filter **−0.34%**, and cash **0%** per opportunity.
Only four trades were accepted; all lost after costs. **Do not promote this configuration.**
See [the full readout](results/REPORT.md) and [all metrics](results/RESULT.json).

## Files and boundaries

| File | Purpose |
|---|---|
| `prepare.py` | Verify public archive checksums; select exactly 168 completed hourly candles; store inputs and outcomes separately. |
| `infer.py` | Load pinned upstream code/weights; validate causal inputs; retain every forecast or failure. Never reads outcomes. |
| `score.py` | After inference finishes and the look-ahead check passes, join every frozen prediction to its outcome. |
| `evaluate.py` | Compare unchanged baseline with accept/cash filter on the same opportunity denominator, including failures. |
| `lookahead_probe.py` | Check that changing/removing future rows does not change causal input selection. |
| `results/` | Verification, per-event results, runtime, preserved inputs/forecasts, hashes and readout. |

Kronos forecasts 25 hours from the last observed close. Entry is one hour after the decision, with exit 24 hours
after entry. The filter accepts only a predicted terminal return above 2%. Rejections hold cash; failed forecasts
retain the baseline position and its losses. Net return subtracts the fixed 2% round-trip assumption. This is an
equal-opportunity event comparison, not a portfolio backtest. Overlapping positions, capital limits, broker
availability and actual fills are not modeled.

## Reproduce

Use an isolated machine; the live collection server is not required. Commands below start at the KOD repository root.
The model weights and code are external downloads; their upstream MIT licenses apply.

```bash
python -m venv /tmp/kod-kronos-venv
/tmp/kod-kronos-venv/bin/pip install --index-url https://download.pytorch.org/whl/cpu torch==2.5.1
/tmp/kod-kronos-venv/bin/pip install -r idx-signals/research/KRONOS_CHALLENGER_v1/requirements.txt
git clone https://github.com/shiyu-coder/Kronos.git /tmp/kod-kronos-upstream
git -C /tmp/kod-kronos-upstream checkout 67b630e67f6a18c9e9be918d9b4337c960db1e9a
/tmp/kod-kronos-venv/bin/python idx-signals/research/KRONOS_CHALLENGER_v1/setup_models.py --models /tmp/kod-kronos-models
/tmp/kod-kronos-venv/bin/python -m unittest discover -s idx-signals/research/KRONOS_CHALLENGER_v1 -p 'test_*.py'
/tmp/kod-kronos-venv/bin/python idx-signals/research/KRONOS_CHALLENGER_v1/prepare.py --data-dir /tmp/kod-kronos-data
/tmp/kod-kronos-venv/bin/python idx-signals/research/KRONOS_CHALLENGER_v1/infer.py --upstream /tmp/kod-kronos-upstream --models /tmp/kod-kronos-models --data /tmp/kod-kronos-data --output /tmp/kod-kronos-reproduction
/tmp/kod-kronos-venv/bin/python idx-signals/research/KRONOS_CHALLENGER_v1/score.py --data /tmp/kod-kronos-data --run /tmp/kod-kronos-reproduction
```

The exact original inputs and separate outcomes are also preserved in `results/inputs.tar.gz`; extracting it into
a fresh data directory avoids downloading the archives again. All 127 successful forecast paths are in
`results/forecasts.tar.gz`.

Use a fresh output directory: completed predictions and results refuse overwriting. A reproduction is an integrity
check, not another strategy trial or an independent observation. CPU numerical results can differ across software
or hardware; the original run manifest records installed versions, seeds, code/weight hashes and process memory.

`results/LOOKAHEAD_CHECK.json` records the actual KOD checker invocation, source sample hashes and its limited scope.
The tests include a separately authored contract suite and a real 2025 microsecond-timestamp archive fixture.
