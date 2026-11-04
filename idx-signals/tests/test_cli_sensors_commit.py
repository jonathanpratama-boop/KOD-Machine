"""`idxsig sensors pull --commit` hands IDXSIG_COMMIT_TRAILER to paper.commit_and_push and returns 0.

cli.py reads the trailer with os.environ.get in the sensors branch but never imported os at module level, so
that path raised NameError after a successful pull. The pull, the RFC 3161 timestamper and the git commit are
all replaced here: nothing touches the network, the sensors log or the repository.
"""

import io
import os
import sys
import types
import unittest
from contextlib import redirect_stdout
from unittest import mock

# Loaded before sys.modules is patched below, so restoring sys.modules never drops them.
from idxsig import cli, paper, sensors

STAMP = "2026-11-04T12:00:00Z"
PULL_SUMMARY = {
    "stamp": STAMP,
    "records": 3,
    "alerts_new": 2,
    "counts": {"stocktwits_trending": {"items": 2, "new": 2}},
    "errors": {},
    "head": "0" * 64,
}
TRAILER = "Co-Authored-By: Sensor Test <sensor-test@example.invalid>"


def _fake_kod_timestamp():
    """Stand-in for kod.timestamp (kod-machine is not on idx-signals' path, and the real one calls out)."""
    stamper_cls = mock.MagicMock(name="RFC3161Timestamper")
    kod_pkg = types.ModuleType("kod")
    ts_mod = types.ModuleType("kod.timestamp")
    ts_mod.RFC3161Timestamper = stamper_cls
    kod_pkg.timestamp = ts_mod
    return stamper_cls, {"kod": kod_pkg, "kod.timestamp": ts_mod}


class SensorsPullCommit(unittest.TestCase):
    def _run(self, argv, env):
        stamper_cls, fake_modules = _fake_kod_timestamp()
        out = io.StringIO()
        with mock.patch.dict(sys.modules, fake_modules), \
                mock.patch.dict(os.environ, env), \
                mock.patch.object(sensors, "pull", return_value=dict(PULL_SUMMARY)) as pull, \
                mock.patch.object(paper, "commit_and_push", autospec=True,
                                  return_value="abc123def") as commit, \
                redirect_stdout(out):
            code = cli.main(argv)
        return code, out.getvalue(), pull, commit, stamper_cls

    def _expected_files(self):
        return [sensors.LOG, sensors.RAW / "20261104T120000Z", paper.TOKENS]

    def test_commit_passes_the_trailer_from_the_environment_and_returns_zero(self):
        code, printed, pull, commit, stamper_cls = self._run(
            ["sensors", "pull", "--sources", "stocktwits_trending", "--commit"],
            {"IDXSIG_COMMIT_TRAILER": TRAILER},
        )
        self.assertEqual(code, 0)
        stamper_cls.assert_called_once_with()
        pull.assert_called_once()
        self.assertEqual(set(pull.call_args.args[0]), {"stocktwits_trending"})
        self.assertIs(pull.call_args.kwargs["timestamper"], stamper_cls.return_value)
        commit.assert_called_once_with(
            self._expected_files(), f"sensors pull {STAMP}: 2 new alert(s)", TRAILER
        )
        self.assertIn("abc123def", printed)

    def test_commit_without_a_trailer_in_the_environment_passes_an_empty_trailer(self):
        env = {k: v for k, v in os.environ.items() if k != "IDXSIG_COMMIT_TRAILER"}
        with mock.patch.dict(os.environ, env, clear=True):
            code, _, _, commit, _ = self._run(
                ["sensors", "pull", "--sources", "stocktwits_trending", "--commit"], {}
            )
        self.assertEqual(code, 0)
        commit.assert_called_once_with(
            self._expected_files(), f"sensors pull {STAMP}: 2 new alert(s)", ""
        )

    def test_pull_without_commit_neither_stamps_nor_commits(self):
        code, _, pull, commit, stamper_cls = self._run(
            ["sensors", "pull", "--sources", "stocktwits_trending"],
            {"IDXSIG_COMMIT_TRAILER": TRAILER},
        )
        self.assertEqual(code, 0)
        stamper_cls.assert_not_called()
        self.assertIsNone(pull.call_args.kwargs["timestamper"])
        commit.assert_not_called()


if __name__ == "__main__":
    unittest.main()
