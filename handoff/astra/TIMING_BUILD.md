# Timing build: implemented paths and operating boundaries

Engineering specification: [TIMING_CAPTURE_v1](protocols/TIMING_CAPTURE_v1/PROTOCOL.md).
This pass adds paper-only instrumentation and bounded observation capability. It
does not establish a profitable strategy, start a prospective trial, or install
another schedule. Test commands and release evidence belong in `PATCHES.md` and
`TIDY_REPORT.md`; the presence of a command below is not a claim that a public
capture succeeded.

## How the layers connect

| Layer | Implemented code | Connection and retained boundary |
| --- | --- | --- |
| Timing records | `idxsig/timing_capture.py` | Versioned attempts, additive revisions, local hash chain, immutable record bytes and explicit missing stages |
| Operating instrumentation | `idxsig/runtime/timing.py`, `coordinator.py`, `capture.py` | Requested membership and actual invocation clocks surround existing operations; logical economic cutoffs remain unchanged |
| Paper intent/fill linkage | `idxsig/runtime/timing_paper.py` | Per-intent records link original profile, intent, fill, quote evidence and run IDs; replay timestamps are references, not newly measured historical executions |
| Intraday observations | `idxsig/runtime/intraday.py`, `idxsig/market_time.py` | Finite selected-universe 1m/5m/15m capture with complete bars, raw evidence, metadata, quotes/depth and request-level failures; no early detector added |
| Clock integrity | `runtime/timing.clock_observation`, `runtime/time_anchor.py` | Monotonic durations; existing chrony measurement if present; optional external batch timestamps with offline verification and truthful failures |
| Prepared context | `idxsig/timing_context.py` | Versioned calendar, pre-event research branches, named costs, PREMOVE availability adapter, shadow quote checks and observational avoid flags |
| Read-only display | `kod/workstation/operations.py`, `/timing` route and timing template | Reads the separate timing board; a timing-only run can be displayed without a trading-account snapshot |
| Recovery | Existing runtime backup and restore plus timing verification | Timing artifacts live below the runtime root and are included in checksummed archives; restore targets a new directory |

An attempt ID identifies a process invocation. Its linked run/intent/forecast ID
identifies the original economic or research record. Retrying an operation does
not rename that original record or transform it into a new signal. Source-request
records form separate cohorts; their count must not be presented as the number of
independent investment decisions.

## CLI commands

Run from the repository root using the environment in `docs/RUNTIME.md`.
`python tools/kod.py runtime --help` exposes the commands below. Root paths are
examples; use separate runtime directories for synthetic, replay and prospective
work. A demonstration directory must not become a prospective account directory.

Offline synthetic integration, including the existing paper demonstration:

```bash
python tools/kod.py runtime --root runtime/timing-demo timing-demo
python tools/kod.py runtime --root runtime/timing-demo timing-status
python tools/kod.py runtime --root runtime/timing-demo verify
```

`timing-demo` uses an injected synthetic fetcher, synthetic calendar/quote context
and fixed fixture times. It cannot contact a market-data provider or create a real
order. Its saved result is retained on repeat invocation. Durations and local
processing receipts describe the current invocation, not historical availability.

One explicitly scheduled public observation, after the protocol is committed:

```bash
python tools/kod.py runtime --root runtime/timing-forward timing-capture \
  --scheduled-at "$KOD_SCHEDULED_AT" \
  --symbols BTCUSDT ETHUSDT --interval 1m --bars 60
```

`KOD_SCHEDULED_AT` must contain the actual declared UTC observation slot, such as
an ISO timestamp ending in `Z`. It cannot be in the future when execution starts.
It must not be replaced with the actual start to hide scheduler delay. This
command performs one bounded collection and returns; it installs no daemon,
notification or recurring task. A provider refusal remains a blocked observation.
The example selects two instruments for infrastructure diagnosis, not an exclusive
long-term KOD investment universe.

Read the retained observations at the present or an explicit historical cutoff:

```bash
python tools/kod.py runtime --root runtime/timing-forward timing-status
python tools/kod.py runtime --root runtime/timing-forward timing-status --as-of "$KOD_CUTOFF"
```

Retain a prepared context pack, using `schemas/timing_context_v1.schema.json` and
the examples described in `docs/TIMING_CONTEXT.md`:

```bash
python tools/kod.py runtime --root runtime/timing-forward timing-context \
  --input context.json --as-of "$KOD_CUTOFF"
```

The command retains input and normalized output by hash, with the actual local
recording time. An imported earlier cutoff cannot self-certify a prospective
forecast. Missing timestamps, account access, costs or quotes remain explicit.

Record a scheduled slot that did not collect data:

```bash
python tools/kod.py runtime --root runtime/timing-forward timing-missed \
  --scheduled-at "$KOD_SCHEDULED_AT" --symbols BTCUSDT ETHUSDT \
  --reason "Provider unavailable; no completed scan"
```

The existing `once` and `capture` commands also accept `--scheduled-at`. Omission
means schedule latency is unknown. `capture` retains the existing finite two-
observation paper-account operation and named simulation costs. Its public
decision batches request external anchors unless `--no-external-timestamp` is
explicitly supplied. An authority's later response proves existence by that later
time; it does not prove an earlier local decision timestamp. No external anchor
is requested by the offline demo or recorded-input replay.

The workstation's `/timing` page reads `timing/report.json` through a separate
validated adapter. Loading a page does not collect data, run a strategy, submit an
order or write a timing record. Use the existing workstation launch instructions
with `KOD_RUNTIME_ROOT` set to the intended directory.

## Files and clocks

Under a runtime root, the timing layer retains `timing/attempts.jsonl`, immutable
`timing/records/`, requested `timing/memberships/`, supplied `timing/contexts/`,
bounded `timing/captures/`, any `timing/clocks/` evidence and external
`timing/anchors/`. `timing/report.json` is a replaceable derived view. Raw response
objects remain in the runtime evidence store. No frozen repository artifact is
renamed or updated by these commands.

The clock fields distinguish publication, local receipt, process start, feature
readiness, detection, decision, indicative executable observation and simulated
fill. Process completion timestamps are conservative observation bounds, not
exchange timestamps. Without an evidenced threshold crossing, threshold delay
stays unknown. Negative source/local lag is a clock conflict, not predictive lead.

## What remains deliberately unknown

- A successful public capture from the intended operating host and access route
  must be evidenced; a synthetic demonstration does not establish connectivity.
- A chrony installation and successful synchronization are not assumed. Missing
  clock measurement is UNKNOWN; a server timestamp is not an NTP offset.
- No eToro/Stockbit quote, depth, product-access or fill integration is claimed.
  Public exchange observations are proxies where the intended venue differs.
- New intraday data does not create an earlier trigger. The research close rule
  still controls whether a new early-entry experiment may be conducted.
- The five-item avoid checklist has not become a combined validated strategy.
  The suggested 60-decision experiment has not been launched.
- Thirty scheduled attempts diagnose operations. Neither thirty attempts nor
  any elapsed duration automatically qualifies a strategy for live money.

The next operational result is a retained declared-slot observation on a permitted
host, with coverage and source failures visible. Only then accumulate the bounded
diagnostic cohort and attribute the measured delay before proposing another model.
