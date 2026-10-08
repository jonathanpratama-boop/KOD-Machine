# Independent source audit — US data repair

## Scope and evidence boundary

Reviewed the supplied snapshot at `/Users/jonathanpratama/Projects/KOD-US-Repair/KOD-Machine-hermes-us-data-repair-v1`, specifically `idx-signals/idxsig/global_panel.py`, `execution.py`, `paper.py`, and the supporting `profiles.py`. Line references below are relative to `idx-signals/idxsig/`.

The supplied GitHub base is `1420ee68ac1da2f063bfaf96a1bd374701f23a05`. The local directory has no Git repository metadata (`git rev-parse` failed), so ancestry and equality to that commit were **not independently verified**.

No panel, raw market payload, ledger, research result, holdout result, or 2024+ outcome data was opened. No downloads, operational scans, trades, source edits, or ledger writes occurred. Detector and strategy were not changed. The only file created by this audit is this report.

**Evidence strength:** findings are source-verified defects or explicit causal-model limitations. Small synthetic formula checks ran successfully with Python's standard library. An attempted in-memory execution of extracted source functions stopped immediately because the tool interpreter lacks NumPy; it did not execute project code. Accordingly, the reproduction procedures below are proposed function-level regressions, not claims of completed integration tests. Missing original raw inputs remain a blocker to historical reconstruction; this source snapshot is not sufficient to rerun or quantify the original experiment.

## 1. High — price-level consumers lack event-time units; paper's single scale cannot restore execution-date costs

**Source:** `global_panel.py:3–5, 79–89, 158–163`; `execution.py:222–236, 271–286`; `profiles.py:32–44, 49–52`; `paper.py:469–486, 506–507`.

### Verified mechanism

The US loader copies Yahoo quote OHLCV and declares the prices source-split-adjusted. It neither retains an explicit corporate-action schedule nor exposes a separate contemporaneous price series. Execution uses those same prices for integer-share sizing and entry/exit cost tiers. `ca_mode="adjusted"` still uses `split_factor`; it does not recover contemporaneous quote units. The profile's price-band function is likewise level-dependent, although this audit did not trace the matching caller.

This confirms the **mechanism of the already-known historical-price-level defect**, not a new estimate of its extent. For example, with notional 5,000, a contemporaneous price of 30 permits 166 whole shares; its later two-for-one-backadjusted price of 15 permits 333 adjusted-unit shares. The configured per-side tier changes from 0.0005 to 0.0015. Whole-share rounding and tier assignment are not invariant to retrospective adjustment. This does not imply that all split-adjusted return ratios are wrong, or that every price-times-volume value is contaminated: those require separate price/volume convention checks against original inputs.

Paper scoring tries to repair units using `scale = current_signal_close / recorded_signal_close`. Multiplying the stored stop/chase by that scale can correctly align plan thresholds with a consistently adjusted price path. However, line 485 treats `entry_price / scale` as the price actually paid. That restores **signal-day units**, not necessarily entry-day units. If a split occurs between the signal and entry, those units differ. Lines 485–486 also use the same entry-derived tier for both entry and exit, unlike `execute()`, which selects each side's tier separately.

### Safe reproduction suggestion

Use an in-memory synthetic US `Market` with seven sessions in 2020, one ticker, positive volume, no locks, and adjusted open/close/previous all 15. Provide a decision recorded at signal close 30, stop 25.5, chase 33, and a five-session horizon. Stipulate a two-for-one split effective at the next opening: actual entry and exit prices are both 15. Call only `paper.score`, never `score_pending` or `append`.

The source formulas yield scale 0.5 and inferred cost price 30, applying tier 0.0005 rather than the actual-price tier 0.0015. With the configured sell fee, the formula checks produce net return `-0.0010272863568214774` versus `-0.0030232651023465174` with actual entry/exit tiers. These are synthetic arithmetic results, not historical outcomes.

Also test an ordinary no-split crossing of a cost-tier boundary to isolate the separate reuse-of-entry-tier issue.

**Repair acceptance:** distinguish adjusted return coordinates from contemporaneous execution prices and share units; prove event-date conversion at signal, entry, and exit separately. Retain the frozen tier schedule and detector. Do not apply one global signal-date scale to every execution-date monetary calculation.

## 2. High — spike QA uses the next observation to rewrite earlier signal inputs

**Source:** `global_panel.py:39–54, 142`; reused by paper through `paper.py:190–194`.

### Verified mechanism

`_spikes` explicitly calls `shift(-1)`. `_finish` deletes the identified row and recomputes `previous` after deletion. Consequently, appending a future observation can delete a row that was present at a prior decision cutoff and change later lagged returns/history. A downstream causal view cannot undo preprocessing that has already used future observations.

The reversion test is a heuristic, not independent proof of a bad print. Even if some affected rows truly are erroneous, silently cleaning them using future prices is not point-in-time preprocessing. This is distinct from using future prices as outcome labels.

### Safe reproduction suggestion

Build an in-memory frame with 50 synthetic tickers over three 2020 sessions, all positive volume. Keep 49 tickers at 10; set the test ticker's closes to 10, 40, 10. Fifty tickers avoid accidental interference from the minimum-session-coverage rule even after the test row is removed.

Compare `_finish(prefix_through_second_session)` with `_finish(full_frame)` restricted to that same prefix. The middle test row survives the prefix calculation because no next close exists; the full calculation drops it because both strict inequalities hold. The standard-library formula check confirmed this predicate difference. Assert exact row/value equality across prefixes as the desired causal regression; the current implementation violates it.

**Repair acceptance:** use contemporaneously available validity checks for decision inputs. If future-informed corrections are retained for data-quality research, preserve the original observation and correction availability time, and explicitly separate corrected hindsight data from decision-time replay. Do not hide the change inside a downstream causality test.

## 3. High causal-model limitation — a next-open fill is accepted or rejected using that session's final volume

**Source:** `profiles.py:49–50`; `execution.py:134, 216–236`.

### Verified mechanism

The US profile specifies entry at the next open. `execute()` selects that opening price, sizes shares, then rejects entry when the shares exceed `max_participation * m.volume[ticker, entry_session]`. That is the completed entry day's volume, unavailable at its opening. `tradeable` also depends on the completed bar's close and volume.

Thus identical histories and opening prints can receive different opening-fill classifications solely because subsequent session volume differs. This is verified future dependence in execution selection, not evidence that the detector itself reads ahead. A full-day volume fraction can be disclosed as an ex-post capacity approximation; it cannot establish causal executability at the opening print. It can change which returns enter scored samples. The historical direction and magnitude of any bias are unmeasured here.

### Safe reproduction suggestion

Construct two otherwise-identical three-session synthetic markets in 2020, open/close 10, positive volume, no locks, no corporate actions. Execute a signal at index 0 with next-open entry, one-session holding, notional 1,000, lot size 1, participation 0.10, zero fees, and `ca_mode="adjusted"`.

Only change the entry day's final volume: 999 versus 1,000. The source sizes 100 shares in both cases. The verified arithmetic makes the first case `SKIP_LIQUIDITY` and the second eligible to exit normally, although both opening information sets are identical. Call only the pure `execute()` function; do not invoke a harness or ledger writer.

**Repair acceptance:** explicitly separate the ex-post capacity diagnostic from a causal next-open eligibility claim. Any replacement participation rule or execution model is a separately authorized model change, not an unannounced data-repair adjustment; the frozen strategy must remain frozen.

## Disposition

The three mechanisms above are concrete and reproducible with synthetic inputs. They do **not** establish which historical trades were affected, reconstruct missing raw originals, validate a repaired dataset, or authorize a detector/strategy change. Historical impact assessment remains blocked pending provenance-complete authorized inputs. No holdout access is needed to implement the suggested synthetic regressions.
