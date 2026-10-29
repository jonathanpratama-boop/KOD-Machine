"""A scan refuses a session whose bar is not final (paper.session_closed). Each test names the failure it guards against."""
from __future__ import annotations

import unittest
from datetime import datetime, timezone

from idxsig import paper


def utc(s):
    return datetime.fromisoformat(s).replace(tzinfo=timezone.utc)


class SessionGuard(unittest.TestCase):
    def test_a_session_still_trading_is_refused(self):
        """Guards against: an early run recording half an Indonesian, US or crypto day as a closed decision."""
        self.assertFalse(paper.session_closed("IDX", "2026-10-29", utc("2026-10-29T07:53:00")))  # 14:53 Jakarta
        self.assertFalse(paper.session_closed("IDX", "2026-10-29", utc("2026-10-29T09:29:00")))  # 16:29, inside the margin
        self.assertFalse(paper.session_closed("US", "2026-10-29", utc("2026-10-29T20:15:00")))   # 16:15 New York
        self.assertFalse(paper.session_closed("CRYPTO", "2026-10-29", utc("2026-10-29T23:59:00")))

    def test_the_routines_scheduled_times_pass(self):
        """Guards against: the guard blocking the scheduled routines (IDX 10:17, US 22:47, crypto 00:23 UTC)."""
        self.assertTrue(paper.session_closed("IDX", "2026-10-29", utc("2026-10-29T10:17:00")))
        self.assertTrue(paper.session_closed("US", "2026-10-28", utc("2026-10-28T22:47:00")))
        self.assertTrue(paper.session_closed("CRYPTO", "2026-10-28", utc("2026-10-29T00:23:00")))

    def test_new_york_daylight_saving_is_respected(self):
        """Guards against: a fixed UTC offset letting a winter US session through an hour early."""
        self.assertFalse(paper.session_closed("US", "2026-11-02", utc("2026-11-02T21:15:00")))  # 16:15 EST
        self.assertTrue(paper.session_closed("US", "2026-11-02", utc("2026-11-02T21:31:00")))


if __name__ == "__main__":
    unittest.main()
