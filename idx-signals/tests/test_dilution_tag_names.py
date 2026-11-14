"""ADDENDUM_4: when an EmitenNews slug names an IDX ticker (idxsig.catalysts.names_code and its callers).
Synthetic slugs and universes only; no network, no repository data. Each test names the failure it guards
against."""

from __future__ import annotations

import unittest
from datetime import datetime, timezone
from unittest import mock

from idxsig import catalysts as cr

REAL_FP = "aksi-korporasi-bhuwanatala-indah-bipp-setujui-private-placement"
UNIVERSE = frozenset({"aksi", "bipp", "laba", "bank", "abcd", "efgh"})

# The frozen list of ADDENDUM_4 (common_word_codes.txt), copied verbatim.
FROZEN_COMMON = """
agar aksi area auto ayam baik baja bali bank beef beli best bina bird blue bola buah buka bull bumi cash
chip city coal coin crab cuan data daya deal dewa dewi east edge emas euro fast film fire food gema gold
golf good gula guna hope idea ikan indo jati jawa jaya kayu keju king kopi kota laba labs laju land life
link live main mari mark maya mega meja mutu naik nasi nice nine obat pada palm part pipa pola raja real
reli roda roti runs safe same satu ship sofa star tamu taxi trim true truk uang visi viva wifi wine zinc
""".split()


def names(slug: str, ticker: str, universe=UNIVERSE) -> bool:
    return cr.names_code(slug, ticker, universe)


class FrozenLists(unittest.TestCase):
    def test_common_word_codes_equal_the_frozen_list(self):
        """Guards against: a code added, dropped or mis-cased in COMMON_WORD_CODES, which would silently change
        which tickers need the IDX code list."""
        self.assertEqual(len(FROZEN_COMMON), 105)
        self.assertIsInstance(cr.COMMON_WORD_CODES, frozenset)
        self.assertEqual(cr.COMMON_WORD_CODES, frozenset(FROZEN_COMMON))
        self.assertTrue(all(c == c.lower() and len(c) == 4 for c in cr.COMMON_WORD_CODES))

    def test_not_a_name_holds_aksi_korporasi(self):
        """Guards against: the "aksi korporasi" section label missing from NOT_A_NAME or stored as a string."""
        self.assertIsInstance(cr.NOT_A_NAME, tuple)
        self.assertIn(("aksi", "korporasi"), cr.NOT_A_NAME)
        self.assertTrue(all(isinstance(p, tuple) for p in cr.NOT_A_NAME))


class NamesCode(unittest.TestCase):
    def test_real_false_positive_names_bipp_not_aksi(self):
        """Guards against: the 2026-11-09 tag of AKSI from a headline about Bhuwanatala Indah (BIPP)."""
        self.assertFalse(names(REAL_FP, "AKSI"))
        self.assertTrue(names(REAL_FP, "BIPP"))
        self.assertTrue(cr.names_code(REAL_FP, "BIPP", None))

    def test_common_word_code_alone_in_slug_is_named(self):
        """Guards against: a common-word code never being tagged, even when it is the only code in the slug."""
        self.assertTrue(names("laba-rights-issue-hmetd-rp100-miliar", "LABA"))
        self.assertTrue(names("bank-terbitkan-saham-baru", "BANK"))
        self.assertTrue(
            names("laba-rights-issue-laba", "LABA")
        )  # the code itself twice is not "another" code

    def test_common_word_code_beside_another_code_is_not_named(self):
        """Guards against: "laba" (profit) or "bank" in a headline about another issuer tagging LABA or BANK,
        and against the other issuer losing its tag."""
        slug = "abcd-bukukan-laba-lalu-rights-issue"
        self.assertFalse(names(slug, "LABA"))
        self.assertTrue(names(slug, "ABCD"))
        slug = "bank-abcd-private-placement"
        self.assertFalse(names(slug, "BANK"))
        self.assertTrue(names(slug, "ABCD"))

    def test_only_universe_codes_count_as_other_codes(self):
        """Guards against: an ordinary word that is not an IDX code blocking a common-word code."""
        slug = "laba-xyzw-rights-issue"
        self.assertTrue(names(slug, "LABA", frozenset({"laba"})))
        self.assertFalse(names(slug, "LABA", frozenset({"laba", "xyzw"})))

    def test_normal_code_unchanged_and_needs_no_universe(self):
        """Guards against: an ordinary code changing behaviour, or needing the code list that only common-word
        codes need; two ordinary codes in one slug still both tag."""
        slug = "abcd-dan-efgh-rights-issue"
        for universe in (None, UNIVERSE, frozenset()):
            self.assertTrue(cr.names_code(slug, "ABCD", universe))
            self.assertTrue(cr.names_code(slug, "EFGH", universe))
            self.assertFalse(cr.names_code(slug, "IJKL", universe))
        self.assertTrue(cr.names_code("bank-abcd-private-placement", "ABCD", None))

    def test_whole_word_only(self):
        """Guards against: a code matched inside a longer word ("labarugi", "bippx", "abcdef")."""
        self.assertFalse(names("bippx-private-placement", "BIPP"))
        self.assertFalse(names("abcdef-rights-issue", "ABCD"))
        self.assertFalse(names("xabcd-rights-issue", "ABCD", None))
        self.assertFalse(names("labarugi-naik-rights-issue", "LABA"))
        self.assertTrue(names("pt-bipp-private-placement", "BIPP"))

    def test_phrase_rule_versus_second_occurrence(self):
        """Guards against: "aksi korporasi" counting as a name of AKSI, and against a real second occurrence of
        AKSI in the same slug being thrown away with it."""
        self.assertFalse(names("aksi-korporasi-rights-issue-hmetd", "AKSI"))
        self.assertTrue(names("aksi-korporasi-aksi-rights-issue-hmetd", "AKSI"))
        self.assertTrue(names("aksi-rights-issue-hmetd", "AKSI"))
        # the phrase is contiguous: "aksi" not followed by "korporasi" is an occurrence
        self.assertTrue(names("aksi-terbitkan-saham-baru-korporasi", "AKSI"))
        # a second occurrence still meets rule 1, but rule 3 applies to it: BIPP is another code
        self.assertFalse(names("aksi-korporasi-aksi-dan-bipp-private-placement", "AKSI"))

    def test_case_insensitive(self):
        """Guards against: a ticker or slug in another case missing a match, or the rules being skipped."""
        for t in ("BIPP", "bipp", "Bipp"):
            self.assertTrue(names(REAL_FP, t))
        for t in ("AKSI", "aksi", "Aksi"):
            self.assertFalse(names(REAL_FP, t))
        self.assertFalse(names(REAL_FP.upper(), "aksi"))
        self.assertTrue(names(REAL_FP.upper(), "bipp"))
        self.assertTrue(names("LABA-Rights-Issue", "laba"))
        self.assertFalse(names("ABCD-bukukan-LABA-rights-issue", "Laba"))

    def test_common_word_code_without_universe_raises(self):
        """Guards against: a common-word code being guessed (either way) when the IDX code list is missing."""
        for ticker in ("LABA", "laba"):
            with self.assertRaises(ValueError):
                cr.names_code("laba-rights-issue-hmetd", ticker, None)
        with self.assertRaises(ValueError):
            cr.names_code("abcd-bukukan-laba-rights-issue", "LABA", None)
        self.assertTrue(cr.names_code("abcd-bukukan-laba-rights-issue", "ABCD", None))


def sitemap(*entries: tuple[str, str]) -> bytes:
    body = "".join(
        f"<url><loc>https://www.emitennews.com/news/{slug}</loc><lastmod>{lastmod}</lastmod></url>"
        for slug, lastmod in entries
    )
    return f'<?xml version="1.0"?><urlset>{body}</urlset>'.encode()


UNTIL = "2026-11-09"
RAW = sitemap(
    (REAL_FP, "2026-11-08T09:00:00+07:00"),
    ("bipp-rights-issue-hmetd", "2026-10-01T09:00:00+07:00"),  # 39 days before: outside
    ("bipp-bagikan-dividen", "2026-11-07T09:00:00+07:00"),  # not a dilution headline
    ("laba-rights-issue-hmetd", "2026-10-12T09:00:00+07:00"),  # exactly 28 days before: inside
    ("laba-terbitkan-waran-seri-i", "2026-10-11T09:00:00+07:00"),  # 29 days before: outside
    ("abcd-bukukan-laba-lalu-private-placement", "2026-11-09T08:00:00+07:00"),
    ("efgh-rights-issue", "2026-11-10T08:00:00+07:00"),  # after `until`
)


class Slugs(unittest.TestCase):
    def test_idx_dilution_slugs_end_to_end(self):
        """Guards against: idx_dilution_slugs bypassing names_code, or the 28-day window and output format
        changing along with the fix."""
        got = {t: cr.idx_dilution_slugs(RAW, t, UNTIL, universe=UNIVERSE) for t in UNIVERSE}
        self.assertEqual(got["aksi"], [])
        self.assertEqual(got["bank"], [])
        self.assertEqual(got["bipp"], [f"{REAL_FP}|2026-11-08|private_placement"])
        self.assertEqual(got["laba"], ["laba-rights-issue-hmetd|2026-10-12|rights_issue"])
        self.assertEqual(
            got["abcd"], ["abcd-bukukan-laba-lalu-private-placement|2026-11-09|private_placement"]
        )
        self.assertEqual(got["efgh"], [])
        self.assertEqual(
            cr.idx_dilution_slugs(RAW, "EFGH", "2026-11-10", universe=UNIVERSE),
            ["efgh-rights-issue|2026-11-10|rights_issue"],
        )
        self.assertEqual(
            cr.idx_dilution_slugs(RAW, "LABA", UNTIL, days=29, universe=UNIVERSE),
            [
                "laba-rights-issue-hmetd|2026-10-12|rights_issue",
                "laba-terbitkan-waran-seri-i|2026-10-11|convertible_or_warrant",
            ],
        )

    def test_idx_dilution_slugs_normal_code_without_universe(self):
        """Guards against: old callers (no universe) breaking for an ordinary code."""
        self.assertEqual(
            cr.idx_dilution_slugs(RAW, "BIPP", UNTIL),
            [f"{REAL_FP}|2026-11-08|private_placement"],
        )


NOW = datetime(2026, 11, 9, 1, 0, tzinfo=timezone.utc)


def idx_set(ticker: str) -> dict:
    return {
        "type": "SPECULATION_SET",
        "market": "IDX",
        "set_id": f"SPEC-{ticker}",
        "ticker": ticker,
        "signal_session": "2026-11-07",
        "sealed_at": "2026-11-07T10:30:00Z",
        "entry_cutoff": "2026-11-09T01:45:00Z",
        "record_hash": f"h-{ticker}",
    }


class Tags(unittest.TestCase):
    def run_tags(self, universe):
        sets = [idx_set(t) for t in ("AKSI", "LABA", "BIPP", "BANK")]
        with (
            mock.patch.object(cr, "protocol", return_value=({"protocol_id": "P"}, "0" * 64)),
            mock.patch.object(cr, "idx_universe", return_value=universe),
        ):
            tags = cr.dilution_tags(NOW, sets, None, en_fetch=lambda url: RAW, clock=lambda: NOW)
        return {t["ticker"]: t for t in tags}

    def test_common_word_code_unknown_when_code_list_unavailable(self):
        """Guards against: a common-word ticker tagged true or false when the IDX code list cannot be read, and
        against ordinary tickers losing their tags because of it."""
        tags = self.run_tags(None)
        for t in ("AKSI", "LABA", "BANK"):
            self.assertEqual(
                (tags[t]["value"], tags[t]["evidence"], tags[t]["source"]),
                (None, [], "IDX code list unavailable (ADDENDUM_4)"),
            )
        self.assertIs(tags["BIPP"]["value"], True)
        self.assertEqual(tags["BIPP"]["evidence"], [f"{REAL_FP}|2026-11-08|private_placement"])
        self.assertTrue(tags["BIPP"]["source"].startswith("EmitenNews sitemap"))

    def test_tags_true_and_false_with_code_list(self):
        """Guards against: the real false positive (AKSI true from a BIPP headline) recurring in a written tag,
        or a common-word code that is the only code in its headline being tagged false."""
        tags = self.run_tags(UNIVERSE)
        self.assertIs(tags["AKSI"]["value"], False)
        self.assertEqual(tags["AKSI"]["evidence"], [])
        self.assertIs(tags["BANK"]["value"], False)
        self.assertIs(tags["LABA"]["value"], True)
        self.assertEqual(
            tags["LABA"]["evidence"], ["laba-rights-issue-hmetd|2026-10-12|rights_issue"]
        )
        self.assertIs(tags["BIPP"]["value"], True)
        for t in tags.values():
            self.assertEqual(t["tag"], "DILUTION_RECENT")
            self.assertEqual(t["sealed_at"], "2026-11-09T01:00:00Z")


if __name__ == "__main__":
    unittest.main()
