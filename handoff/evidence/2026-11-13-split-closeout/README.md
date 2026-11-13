# Current split corrections and publication closeout

On 13 November 2026, 164 current provider responses were captured for all 183 sealed US signal sets through 12 November. All response hashes and sizes match the committed manifest. The new assessment ledger records its actual creation time, 07:53:35Z, and every record is explicitly later evidence. All 366 receipts independently verify against the original pinned certificates. Original speculation, legacy tags, paper plans/results and scan ledgers are byte-identical to base b836c8d516275d37b6dee3f6990d206b15868278.

## Result

SMX (10 November) returns to the corrected view. GOVX and SLXN (11 November) are excluded as confirmed artifacts. Across all 183 sets there are seven confirmed artifacts, five probable artifacts, and five unresolved cases (two unassessable, two unexplained extreme moves and one units inconsistency). The 121 planned paper-book spikes include nine artifacts and no unresolved cases.

The published report shows all three views. The frozen ALL book has 11 completed trades averaging -10.37%; the corrected view has seven averaging -15.52%. KOD's selected book has two completed trades averaging -4.02% in every view. These are small descriptive samples, not a new strategy verdict. Original and corrected results remain side by side; the correction is not treated as information available before a historical trade.

The same-input split-assessment dry run proposes zero new records after initialization. The nightly US sealing hook includes the new assessor; its next hosted nightly execution has not yet been observed at this closeout.

## Evidence and operations

- `independent-acceptance.json` contains all record/token hashes, certificate hashes, the independent 12-row report reconstruction and unchanged-ledger checks.
- The raw response files remain outside public Git under the existing raw-data convention. Exact copies exist on the owner's Mac and in a private server repair directory. The public manifest records their URLs, capture times and hashes. The private copy receipt is included in `operational-receipts.json`.
- The local default LibreSSL could not verify Sectigo's otherwise-valid chain. Modern OpenSSL verified the same token locally and independently on Linux. Its FreeTSA untrusted-certificate path also needed a directory without spaces. The operational run used byte-identical copies of the existing pinned certificates; no trust root or receipt requirement changed.
- The reviewed source-refresh and publisher are deployed. The hourly source rebuild runs separately from the cloud backup. Thirty dashboard regressions pass. The visible paper-input warning remains PARTIAL_INPUT; an offline rebuild does not claim the cloud job's SEC configuration was checked.
- The supplementary collector is closed with all 196 scheduled captures verified and published. This is distinct from the ongoing R2 collector, which remained active with its existing PID throughout deployment. No collection quota, protocol or trade rule changed.
- External R2 alert delivery is still unverified. This release does not claim a notification receipt or add a new alert system.

The final post-merge dashboard source revision and publication receipt are recorded in the user-facing handoff after the merge. All required repository checks must pass on this candidate before release.
