# Future risks and the concrete response

This register distinguishes implemented safeguards from work that still needs a
new source, decision or engineering pass. It is not a monitoring subscription.

| Risk | Existing hook or response | Remaining boundary / trigger |
| --- | --- | --- |
| Broker fees or account tier changes | Named cost profile with source, applicability and effective dates; immutable original account profile | Verify the actual product/ticket and account currency before economic claims; add a new profile version instead of editing an old assumption |
| FX, settlement and withdrawal friction | FX remains separate from quote-currency return arithmetic | AUD account implications remain unknown until the relevant conversion path, fees and settlement constraints are evidenced |
| Proxy venue divergence | Shadow output labels proxy-only observations; rejects a cost/quote venue or explicit currency mismatch | A Binance quote does not establish eToro or Stockbit execution; add a source-specific adapter only when access and evidence are available |
| Missing depth or fading liquidity | Top-of-book scope explicit; requested size checked; zero or insufficient ask liquidity rejected | Full-depth/queue models need retained venue data and a separate tested fill contract; displayed liquidity never guarantees execution |
| Delistings, renamed assets and scaled futures contracts | As-of membership and explicit identity mappings; unknown mappings fail closed | Never reconstruct old membership from today's surviving coins or strip prefixes indiscriminately; alias validity must be dated |
| Binance timestamp/format changes | Explicit ms/us normalization with mixed-unit and causal regression tests | A new undocumented unit/schema is a data conflict; add a new adapter rather than infer a convenient time |
| Provider rate limits or access blocks | Bounded request receipts, HTTP failures and incomplete coverage remain visible | Respect 403/451/captcha refusal; no proxy rotation or bot-check circumvention. Retry only transient cases under the declared bounded policy |
| Vendor becomes paid or removes an endpoint | Optional inputs remain capability/coverage gaps | Report the unavailable capability and block only dependent claims. Do not silently fill it with invented data or suppress independent discovery families |
| Scheduler starts late or misses a slot | Separate declared schedule, actual start and explicit missed-slot receipt | A cron definition is not proof of timely execution. Use observed timing; do not backdate actual start or claim a completed scan from a query alone |
| Host clock is not synchronized | Monotonic durations and explicit chrony observation status | Unknown NTP offset is not zero. Record source/local conflicts without silently correcting stored timestamps |
| External timestamp service fails or responds late | Original batch bytes, token bytes, attempt receipts and offline verification kept separate | A retry keeps its actual later authority time. Missing or unverifiable tokens never become verified evidence |
| Prepared event is postponed/cancelled | Calendar versions explicitly supersede prior versions; exact/window/date-only precision | Old preparation stays attached to the old event version. Reassess against the revised schedule and expiry |
| Regime changes | Optional regime label must have as-of evidence; UNKNOWN supported | Labels derived from future outcomes cannot enter a decision. A regime label alone does not validate strategy adaptation |
| Many correlated samples inflate confidence | Separate detector/evidence cohorts and explicit observation denominators | Coin/request counts are not independent market episodes. Any economic test needs a frozen dependence-aware analysis and net endpoint |
| More models create selection bias | Historical nulls and exposure status preserved; new version/protocol required | Do not search a threshold grid and promote the best historical winner. The early-entry close rule still applies |
| Dependencies drift | Existing runtime/research requirements and constraint files, release checks | Review pinned packages manually on a maintenance cadence. No monthly upgrade job or automatic dependency update is installed by this pass |
| Several agents edit overlapping code | Isolated branch ownership, scoped file responsibilities and append-only checks | Reconcile against current remote head before publication; never force-push another agent's branch or overwrite concurrent work |
| Overlapping operations observe one paper intent out of order | Economic journal locks and monotonic observation validation fail closed; original decision evidence can be recovered without replacing a later fill | A backwards recording-clock revision is rejected. Do not assume overlapping runtime invocations are a supported scheduling mode; serialize them before introducing a concurrent scheduler |
| Evidence remains only on another computer | Remote branch/path/blob availability is reported in `BRANCH_GAPS.md` | This pass did not access Hermes's Mac. Local-only artifacts cannot be treated as inspected evidence; publish hashes and original files through the owner's normal workflow, without background sync |
| Backup or restart mixes incompatible states | Checksummed backup, new-directory restore, immutable economic profile, sidecar IDs | The current publication helper requires Linux `renameat2`; validate a platform-specific no-replace primitive before claiming macOS restore support |
| Timing store grows or readers become slow | Bounded collection and derived board separate from immutable evidence | Measure journal size/read cost before adding indexes or compaction. Any future index must be reconstructible; raw evidence and original records remain preserved |
| User later requests live trading | Entry eligibility remains disabled; no broker credentials or routing added | A separate approved live-execution design, validated policy and explicit per-trade owner decision are required; see `PROPOSALS.md` |

The unresolved INFO_MAGNET result is material to research scope, not a reason to
fake a result or rerun closed price/volume ideas. Current branch evidence and its
limitations are recorded in `PATCHES_RESEARCH.md` and `BRANCH_GAPS.md`. Any later
result must be checked against the originally locked plan and close rule before
changing the lane's status.

No source outage, clock failure, missing optional data or strategy null should
erase unrelated retained candidates. Conversely, an optional-source workaround
must not turn essential missing execution or risk evidence into permission.
