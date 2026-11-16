# Development reader contract

One-call development adapter; no autonomous strategy, prices, decisions or schedules. Explicit model ID, Responses API `store:false`, no tools, strict JSON schema. No retries or repair calls.

## APIs

- `source_packet(pair)`: retains `guidance-margin-reader-source/v1`, event_id, current/prior issuer_cik and source {id,url,representation,raw_text,sha256,locator,published_at,received_at}. Validates hashes. Drops all golden metrics, period/basis/perimeter labels and external attestations.
- `build_request(packet, model)`: model sees only issuer CIK, source ID and exact raw text per side. Locators may contain human interpretations, so they are not sent as extraction hints. Requires an explicit model ID.
- `bind_candidates(packet, output, extracted_at)`: exact output keys current/prior; document keys period_start, period_end, period_kind, basis, definition_id, perimeter_id (string/null), revenue, operating_profit, operating_margin (metric/null). Unknown semantic labels remain null. No extra fields.
- Metrics have exactly form, unit, qualifier, point, low, high, center, spread. Form point/range/center_spread; unit USD_MILLIONS/PERCENT/UNSUPPORTED; qualifier exact/approximate/ambiguous. Required slots are point, low+high, or center+spread; all others null. Each slot has exactly quote and token strings. Quote occurs once in retained source; token occurs once in quote and must not be a partial number. Unicode offsets and numerical values are computed locally. All external flags UNKNOWN, latest prior ID null, decision_at null; qualify can never yield FACTS_READY.
- `run_once(packet, out, model, transport=None)`: new private output directory, no overwrite. Injected transport `(request_body, key)` returns `(http_status, raw_response_bytes, request_id_or_null)`. Credential from OPENAI_API_KEY only. Default HTTPSConnection posts to api.openai.com/v1/responses, no redirects, with certificate verification; standard SSL_CERT_FILE is respected and installed certifi is used when available. Exactly one attempt, no retries. Existing directory raises FileExistsError before call.

## Artifacts and outcomes

`source_packet.json` and `request.json` are flushed before network. Request includes model/prompt/request/module hashes and actual start time. No credentials. Crash with only request files is unresolved and is not automatically resent. `response.txt` retains exact first response bytes unless credential redaction or invalid UTF-8 requires sanitization. `response.json` holds the parsed body or unparsed-body wrapper. Original and retained body SHA256 and redaction status are retained. Both literal and JSON-escaped credentials are redacted. Files and their directory are flushed before a call. Never overwrite these files.

`result.json` returns status, out, provider_calls and response metadata: actual receipt, elapsed time, request/response IDs, returned model, usage, body hash/redaction. KEY_MISSING has calls0. TRANSPORT_ERROR has attempted calls1 and exception class only, never exception text. HTTP_ERROR includes redirects. INCOMPLETE and REFUSED preserve the first response. REJECTED means invalid structure or evidence. CANDIDATE creates candidate.json and stores existing qualification. Unknown sources/semantics/clocks remain unknown. Invalid packet input raises ValueError before directory creation.

CLI requires fixtures, fixture-id, model and new out directory. Without `--live`, it only writes prepared input; `--live` makes one API attempt. Safe summary only on stdout. It does not automatically load env files.

Incomplete retained table excerpts are deliberately allowed to yield missing facts. The current RBBN and KTOS snippets omit some headers and must not be supplemented from their golden fixture labels. Complete source packets and independent semantic review are still needed for meaningful live evaluation. Historical fixtures are development data, never an untouched validation set.
