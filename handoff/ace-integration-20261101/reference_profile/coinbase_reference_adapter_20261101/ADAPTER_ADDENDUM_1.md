# Pre-capture independent-review correction 1 — source chronology

2026-11-01. Saved after mocked tests, before any public API capture. This is a
review correction/addition, not a claim that the earlier spec already implemented
this check. Original ADAPTER_SPEC.md is preserved unchanged.

The independent reviewer reproduced a locally newer, post-intent observation with
a regressed Coinbase source sequence being accepted by the first profile seam.
Local receipt freshness alone was insufficient source-consistency validation.

The reference account now rejects, without journaling/filling, a per-product source
sequence **or source book timestamp lower than the previously accepted value**.
An equal sequence is permitted with a nondecreasing source timestamp: unchanged
books need not be forced to trade/update before a new observation is usable. The
post-intent request/source-time checks still independently apply to every fill.
This is a conservative fail-closed rule; a genuine source sequence reset is not
automatically repaired, retried or treated as a fill. It ends this bounded route.

The public-default function path, not just its CLI, also requires an exact-current-
source independent clearance. Injected mocked clients remain usable offline.

SUPERSEDED BEFORE ANY PUBLIC REQUEST (see managed-routing correction below):
Transport hardening initially proposed in independent pre-capture review: the default
urllib opener now explicitly disables environment proxy handlers. It does not read
proxy credentials or silently choose a different host; TLS verification remains
the standard library default. If direct selected-source access is unavailable,
the route stops. No alternate/proxy transport will be attempted after a refusal.

Clock-validation correction from mocked review: reject HTTP Date values without
explicit GMT timezone. The initial parser converted naive dates using the executor's
local timezone; an invalid naive header could therefore pass the clock tolerance.
The corrected path checks an explicit aware GMT value before UTC conversion, with
no executor-local timezone inference. Receipt wall timestamps remain timezone-aware.


Managed-routing correction (parent review, also before any public API request):
the explicit empty ProxyHandler was reverted because direct-connect overrides can
bypass required managed network routing. The final opener preserves urllib's normal
configured routing and default verified TLS. No environment/OS settings are changed;
no proxy values/credentials are inspected or logged by this application. Its only
custom handlers reject redirects and origin Authorization/Cookie header names.
No HTTP origin authentication handler, cookie processor, netrc integration or endpoint
credentials are installed. Managed proxy behavior is left to the standard transport,
not replaced with an alternative route. If that route rejects access, stop.
Reference: https://docs.python.org/3/library/urllib.request.html#urllib.request.build_opener
