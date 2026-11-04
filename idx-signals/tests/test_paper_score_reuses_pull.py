"""paper-score reuses the scan's recent pull instead of pulling the same bars again (the daily routine filled the
disk with two identical ~33 MB pulls). max_age_hours <= 0 keeps the old always-pull behaviour."""
import unittest
from pathlib import Path
from unittest import mock

from idxsig import cli


class ManifestForScore(unittest.TestCase):
    def test_recent_pull_is_reused_not_repeated(self):
        with mock.patch.object(cli, "_recent_manifest", return_value=(Path("m.json"), [])) as recent, \
                mock.patch.object(cli, "_pull_recent") as pull:
            self.assertEqual(cli._manifest_for_score("CRYPTO", 6.0), (Path("m.json"), []))
        recent.assert_called_once_with("CRYPTO", 6.0)
        pull.assert_not_called()

    def test_zero_or_negative_max_age_always_pulls(self):
        for age in (0, 0.0, -1):
            with mock.patch.object(cli, "_recent_manifest") as recent, \
                    mock.patch.object(cli, "_pull_recent", return_value=(Path("new.json"), ["x"])) as pull:
                self.assertEqual(cli._manifest_for_score("US", age), (Path("new.json"), ["x"]))
            pull.assert_called_once_with("US")
            recent.assert_not_called()

    def test_stale_or_missing_pull_falls_back_to_a_fresh_pull(self):
        # _recent_manifest itself pulls when the latest manifest is too old or absent
        with mock.patch.object(cli, "_pull_recent", return_value=(Path("fresh.json"), [])) as pull, \
                mock.patch("idxsig.provenance.latest_manifest", side_effect=FileNotFoundError):
            self.assertEqual(cli._manifest_for_score("CRYPTO", 6.0), (Path("fresh.json"), []))
        pull.assert_called_once_with("CRYPTO")

    def test_paper_score_exposes_max_age_hours(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf), self.assertRaises(SystemExit):
            cli.main(["paper-score", "--help"])
        self.assertIn("--max-age-hours", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
