"""Regressions for source-date boundaries and explicit access blocks."""

import io
import unittest
import urllib.error
from unittest import mock

from idxsig import microstructure, sensors


def sitemap(*entries):
    rows = [
        "<url><loc>https://www.emitennews.com/news/"
        f"{slug}</loc>\n<lastmod>{lastmod}</lastmod></url>"
        for slug, lastmod in entries
    ]
    return ("<urlset>" + "".join(rows) + "</urlset>").encode()


class SourceDateBoundaryTest(unittest.TestCase):
    def test_future_sitemap_modification_is_not_a_current_alert(self):
        raw = sitemap(
            ("ptro-rights-issue-current", "2026-11-04"),
            ("bipp-private-placement-future", "2026-11-05"),
            ("impc-rights-issue-old", "2026-10-01"),
        )
        alerts, retained = sensors.emitennews_dilution(
            {"PTRO", "BIPP", "IMPC"}, fetcher=lambda _: raw, today="2026-11-04"
        )
        self.assertEqual(retained, raw)
        self.assertEqual([a["symbols"] for a in alerts], [["PTRO"]])

    def test_modification_time_is_retained_without_inventing_publication(self):
        modified = "2026-11-03T17:00:00+07:00"
        raw = sitemap(("ptro-rights-issue-current", modified))
        alerts, _ = sensors.emitennews_dilution({"PTRO"}, fetcher=lambda _: raw, today="2026-11-04")
        self.assertIsNone(alerts[0]["posted_at"])
        self.assertEqual(alerts[0]["extra"]["source_modified_at"], modified)
        self.assertEqual(alerts[0]["extra"]["source_time_role"], "SITEMAP_LASTMOD")
        self.assertEqual(alerts[0]["extra"]["publication_time_status"], "UNKNOWN")

    def test_inclusive_day_window_keeps_both_bounds(self):
        raw = sitemap(
            ("ptro-rights-issue-start", "2026-10-28"), ("bipp-private-placement-end", "2026-11-04")
        )
        alerts, _ = sensors.emitennews_dilution(
            {"PTRO", "BIPP"}, fetcher=lambda _: raw, today="2026-11-04", days=7
        )
        self.assertEqual(len(alerts), 2)


class AccessBlockTest(unittest.TestCase):
    def test_access_blocks_and_rate_limits_stop_without_retry(self):
        for code in (403, 451, 418, 429):
            error = urllib.error.HTTPError(
                "https://example.invalid/data", code, "blocked", {}, io.BytesIO(b"blocked")
            )
            with (
                self.subTest(code=code),
                mock.patch.object(
                    microstructure.urllib.request, "urlopen", side_effect=error
                ) as request,
                mock.patch.object(microstructure.time, "sleep") as sleep,
            ):
                with self.assertRaisesRegex(RuntimeError, str(code)):
                    microstructure._get("https://example.invalid/data", retries=3)
                self.assertEqual(request.call_count, 1)
                sleep.assert_not_called()

    def test_transient_server_error_can_retry(self):
        error = urllib.error.HTTPError(
            "https://example.invalid/data", 503, "unavailable", {}, io.BytesIO(b"unavailable")
        )
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"ok":true}'
        with (
            mock.patch.object(
                microstructure.urllib.request, "urlopen", side_effect=[error, response]
            ) as request,
            mock.patch.object(microstructure.time, "sleep") as sleep,
        ):
            self.assertEqual(microstructure._get("https://example.invalid/data"), {"ok": True})
            self.assertEqual(request.call_count, 2)
            sleep.assert_called_once()


if __name__ == "__main__":
    unittest.main()
