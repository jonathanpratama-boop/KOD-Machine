"""A failed forecast run must not report a quiet market."""
from contextlib import redirect_stdout
from io import StringIO
from unittest import TestCase
from unittest.mock import patch

from idxsig.cli import main


class ForecastRunHealthTests(TestCase):
    def test_all_skipped_inputs_report_failure_without_append(self):
        reason = "SPEC-US-example: features could not be read (EDGAR needs a declared contact); skipped"
        output = StringIO()
        with patch("idxsig.learner3.forecast_records", return_value=([], [reason])), \
             patch("idxsig.learner3.append") as append, redirect_stdout(output):
            result = main(["learner3-forecast"])
        self.assertEqual(result, 2)
        self.assertIn("forecast blocked", output.getvalue())
        self.assertIn(reason, output.getvalue())
        self.assertNotIn("no US speculation set awaiting", output.getvalue())
        append.assert_not_called()

    def test_no_pending_sets_remains_successful_no_op(self):
        output = StringIO()
        with patch("idxsig.learner3.forecast_records", return_value=([], [])), \
             patch("idxsig.learner3.append") as append, redirect_stdout(output):
            result = main(["learner3-forecast"])
        self.assertEqual(result, 0)
        self.assertIn("no US speculation set awaiting", output.getvalue())
        self.assertNotIn("forecast blocked", output.getvalue())
        append.assert_not_called()
