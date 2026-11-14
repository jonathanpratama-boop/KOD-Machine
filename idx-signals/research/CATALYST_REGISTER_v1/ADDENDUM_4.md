# Addendum 4: when an EmitenNews headline "names" an IDX ticker (frozen 2026-11-09)

The protocol's IDX `DILUTION_RECENT` rule counts an EmitenNews headline about new shares "that names the set's ticker".
The code tested only whether the ticker was a word of the headline's slug. Several IDX codes are also ordinary words
(`laba` profit, `naik` up, `bank`, `emas` gold, `aksi` action, `cuan` profit, `beli` buy and others). On 2026-11-09 the
set `SPEC-SCAN-2026-11-09-F1_ARA-AKSI` was tagged `true` from the headline
`aksi-korporasi-bhuwanatala-indah-bipp-setujui-private-placement`, which is about Bhuwanatala Indah (BIPP), not AKSI.
Of the 20 IDX tags written up to then, that is the only one the rule below changes. The row stays as written; this
addendum governs tags written from the commit that adds it.

## The rule (normative)

A slug names an IDX code when all of these hold:

1. The code, in lower case, is a whole word of the slug (words are the slug split on `-`).
2. That word is not the start of a fixed phrase in `NOT_A_NAME` (now only `aksi korporasi`, "corporate action", a
   section label). If the code also appears elsewhere in the slug as a word, rule 1 is met by that occurrence.
3. If the code is in `COMMON_WORD_CODES` (frozen in `idxsig/catalysts.py`), the slug names no other IDX code. The IDX
   codes are those of the latest Yahoo pull manifest. When that list cannot be read, a tag for a code in
   `COMMON_WORD_CODES` is recorded as unknown (`null`, source "IDX code list unavailable"), never guessed.

Codes outside `COMMON_WORD_CODES` behave exactly as before. A headline that names two ordinary codes (for example a
standby buyer and the issuer) still tags both: that ambiguity is left as it was.

`COMMON_WORD_CODES` was chosen from the most frequent code-shaped words of the 2026 sitemap. A real company whose code
is on the list and whose own headline also names another company is missed; that is the price of the rule and is
accepted because the tag is metadata only (protocol: "it changes no cone, plan, twin, decision or policy").

Nothing else in the protocol changes.
