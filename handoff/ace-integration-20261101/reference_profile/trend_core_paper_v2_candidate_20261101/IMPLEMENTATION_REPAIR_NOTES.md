# Synthetic acceptance repair record — 2026-11-01

Both independent review and author review found that pending BUY fills were not
blocked when another held asset's mark became stale. Independent real-Ledger fixture
reproduced it. Fixed with a fail-closed BUY gate; original protocol preserved and
addendum 1 records the clarified requirement. Risk-reducing sells remain possible.

Independent review found that sorting intent processing within one quote event did
not enforce the protocol's global sells-before-buys requirement. ETH could consume a
small cash residue before a pending BTC sale, prematurely complete its IOC intent,
and then leave sale proceeds idle. Fixed by retaining BUY intents while ANY SELL is
pending; a fresh later BUY observation is still required after sells resolve. This
repairs the implementation to the already-written contract, not a new outcome rule.

Input-hash consistency is explicitly rechecked during replay in addition to record
chain, provenance, deterministic result and state hashes. No historical outcome was
used to choose any repair. Final status is in the independent audit report and test
receipt; ordinary CI green alone does not establish this semantic acceptance.

Independent fault injection found that a complete append followed by an fsync error
could be found on retry, deduplicated, and returned without a successful durability
barrier. Fixed: identical retries fsync the already-verified journal and its parent
directory; new appends also sync the parent directory. Failure remains failure until
the barrier succeeds, without appending a duplicate. This is bounded POSIX behavior,
not a guarantee against every filesystem/hardware failure. Provision the account's
directory durably before operational use; nested-directory creation and distributed
filesystems are outside this offline acceptance. Torn tails still fail closed.
