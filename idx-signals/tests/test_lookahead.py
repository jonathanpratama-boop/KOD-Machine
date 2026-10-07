"""Lookahead hardening (audit v2, section 7): adversarial rules that try to see the future.

Each test names the leak it guards against. The defences, in order: prefix-first
construction (rules.causal_signals), the full-window diagnostic, the source audit
(rules/audit.py) and the run-time sandbox (rules/sandbox.py)."""

import unittest

import numpy as np

from idxsig.execution import Market
from idxsig.provenance import PKG_ROOT
from idxsig.rules import CausalSource, LookaheadError, causal_signals, signal_array
from idxsig.rules import placebo, user_rule
from idxsig.rules.audit import RuleAuditError, audit_module, audit_source
from tests.rulekit import module_rule
from tests.support import random_walk_panel

PANEL_FILE = str(PKG_ROOT / "data" / "panel")


def market(**kw):
    df, _ = random_walk_panel(n_tickers=12, n_sessions=90, **kw)
    return Market.from_panel(df)


CAUSAL_BREAKOUT = """
def compute(m):
    close = np.where(m.present, m.close, np.nan)
    out = np.full(m.shape, np.nan)
    for d in range(20, m.shape[1]):
        window = close[:, d - 20:d]
        out[:, d] = (close[:, d] > np.nanmax(window, axis=1)).astype(float)
    return np.where(m.tradeable, out, np.nan)
"""


class PrefixFirst(unittest.TestCase):
    def test_recorded_signal_is_what_the_prefix_call_returned(self):
        """Guards against: recording full-window signals and only spot-checking them afterwards."""
        m = market()
        rule = module_rule("BREAKOUT", CAUSAL_BREAKOUT)
        sig, info = causal_signals(rule, m)
        src = CausalSource(m)
        for d in (25, 47, 89):
            part = signal_array(rule, src.view(d))
            k = src.rows_at(d)
            np.testing.assert_array_equal(src.unorder(np.vstack([part, np.full((m.shape[0] - k, d + 1), np.nan)]))[:, d],
                                          sig[:, d])
        self.assertEqual(info["prefix_calls"], m.shape[1])
        self.assertGreater(np.nansum(sig), 0)

    def test_global_normalisation_is_refused(self):
        """Guards against: z-scoring each name with its whole-history mean and std (uses future prices)."""
        rule = module_rule("ZSCORE", """
            def compute(m):
                close = np.where(m.present, m.close, np.nan)
                z = (close - np.nanmean(close, axis=1, keepdims=True)) / np.nanstd(close, axis=1, keepdims=True)
                return np.where(m.tradeable, (z > 1).astype(float), np.nan)
        """)
        with self.assertRaisesRegex(LookaheadError, "reads data from after the close"):
            causal_signals(rule, market())

    def test_truncation_aware_rule_cannot_leak(self):
        """Guards against: a rule that behaves causally whenever it is handed a shortened window
        (as the old check did) and peeks only on the full run."""
        rule = module_rule("SNEAKY", """
            FULL = 90
            def compute(m):
                close = np.where(m.present, m.close, np.nan)
                if m.shape[1] < FULL:
                    return np.where(m.tradeable, 0.0, np.nan)
                tomorrow = np.concatenate([close[:, 1:], close[:, -1:]], axis=1)
                return np.where(m.tradeable, (tomorrow > close).astype(float), np.nan)
        """)
        with self.assertRaises(LookaheadError):
            causal_signals(rule, market())

    def test_names_listed_later_are_invisible(self):
        """Guards against: a rule that depends on how many names will exist (future IPOs), which the old
        check missed because truncation kept every row."""
        rule = module_rule("HEADCOUNT", """
            def compute(m):
                close = np.where(m.present, m.close, np.nan)
                threshold = 100 * m.shape[0]
                return np.where(m.tradeable, (close > threshold).astype(float), np.nan)
        """)
        m = market(ipo={3: 40, 7: 70})
        old = signal_array(rule, m)  # what the old row-preserving truncation compared against
        for d in (10, 50):
            np.testing.assert_array_equal(old[:, : d + 1], signal_array(rule, m.truncate(d)))
        with self.assertRaises(LookaheadError):
            causal_signals(rule, m)


class SourceAudit(unittest.TestCase):
    def refused(self, body, pattern):
        rule = module_rule("BAD", body)
        with self.assertRaisesRegex(RuleAuditError, pattern):
            causal_signals(rule, market())

    def test_stateful_cache_is_refused(self):
        """Guards against: a module-level cache filled by one call and read by another."""
        self.refused("""
            _CACHE = {}
            def compute(m):
                return np.where(m.tradeable, 0.0, np.nan)
        """, "module-level values must be literals")
        self.refused("""
            def compute(m, seen=[]):
                return np.where(m.tradeable, 0.0, np.nan)
        """, "default arguments must be literals")
        self.refused("""
            def compute(m):
                compute.last = m.close
                return np.where(m.tradeable, 0.0, np.nan)
        """, "attribute assignment")
        self.refused("""
            STATE = 0
            def compute(m):
                global STATE
                return np.where(m.tradeable, 0.0, np.nan)
        """, "global")

    def test_reading_files_is_refused(self):
        """Guards against: a rule that loads the panel itself and reads tomorrow's close."""
        self.refused(f"""
            def compute(m):
                raw = open({PANEL_FILE!r}).read()
                return np.where(m.tradeable, 0.0, np.nan)
        """, "`open` is not allowed")
        self.refused("""
            import pandas as pd
            def compute(m):
                pd.read_csv("x")
                return np.where(m.tradeable, 0.0, np.nan)
        """, "read_csv")
        self.refused("""
            import os
            def compute(m):
                return np.where(m.tradeable, 0.0, np.nan)
        """, "import of os")

    def test_data_held_in_closures_or_import_time_state_is_refused(self):
        """Guards against: data loaded at import time, or a closure built by a factory, carrying the future."""
        self.refused("""
            def make():
                data = np.zeros(3)
                def inner(m):
                    return np.where(m.tradeable, 0.0, np.nan)
                return inner
            compute = make()
        """, "module-level values must be literals")
        self.refused("""
            DATA = np.zeros((1000, 1000))  # stands in for np.load(<panel>) at import time
            def compute(m):
                return np.where(m.tradeable, 0.0, np.nan)
        """, "module-level values must be literals")

    def test_frame_walking_is_refused(self):
        """Guards against: reaching the caller's full arrays through the call stack."""
        self.refused("""
            import sys
            def compute(m):
                full = sys._getframe(2).f_locals
                return np.where(m.tradeable, 0.0, np.nan)
        """, "_getframe")
        self.refused("""
            def compute(m):
                try:
                    raise ValueError
                except ValueError as e:
                    caller = e.__traceback__.tb_frame.f_back
                return np.where(m.tradeable, 0.0, np.nan)
        """, "dunder attribute")
        self.refused("""
            def compute(m):
                return np.where(m.close.base[:, 1:] > 0, 0.0, np.nan)
        """, "base")

    def test_the_audit_is_not_vacuous(self):
        """Guards against: an audit so strict that it rejects real rules (then it would be switched off)."""
        self.assertEqual(audit_module(placebo), [])
        self.assertEqual(audit_module(user_rule), [])
        self.assertEqual(audit_source(CAUSAL_BREAKOUT), [])


class RuntimeSandbox(unittest.TestCase):
    """The source audit is skipped here (audit=False) to show the sandbox stops the same leaks
    when the source hides them."""

    def blocked(self, body, header=None):
        kw = {"header": header} if header else {}
        rule = module_rule("HIDDEN", body, **kw)
        with self.assertRaises(LookaheadError) as ctx:
            causal_signals(rule, market(), audit=False)
        return str(ctx.exception)

    def test_file_reads_are_blocked_even_if_swallowed(self):
        """Guards against: reading data files during compute, including a rule that catches the error."""
        msg = self.blocked(f"""
            def compute(m):
                try:
                    open({str(PKG_ROOT / 'data' / 'manifests')!r} + "/x.json").read()
                except Exception:
                    pass
                return np.where(m.tradeable, 0.0, np.nan)
        """)
        self.assertIn("swallowed", msg)

    def test_frame_and_heap_walks_are_blocked(self):
        """Guards against: sys._getframe, traceback frames and gc.get_objects reaching the full market."""
        header = "import numpy as np\nimport sys\nimport gc\n\n"
        for body in ("    sys._getframe(1)\n", "    gc.get_objects()\n",
                     "    try:\n        raise ValueError\n    except ValueError as e:\n        e.__traceback__.tb_frame\n"):
            self.blocked("def compute(m):\n" + body + "    return np.where(m.tradeable, 0.0, np.nan)\n", header=header)

    def test_view_is_read_only_and_has_no_registry(self):
        """Guards against: a rule writing into the arrays execution uses, reading the corporate-action
        registry (built from later sources), or following .base back to later sessions."""
        src = CausalSource(market())
        view = src.view(30)
        with self.assertRaises(ValueError):
            view.close[0, 0] = 1.0
        for name in ("reg_factor", "share_factor", "split_factor", "ca_ratio", "is_split"):
            with self.assertRaises(AttributeError):
                getattr(view, name)
        self.assertIsNone(view.close.base)
        self.assertEqual(view.close.shape, (12, 31))

    def test_guard_is_inert_outside_rules(self):
        """Guards against: the sandbox breaking the harness's own file access after a rule ran."""
        causal_signals(module_rule("OK", CAUSAL_BREAKOUT), market())
        self.assertTrue((PKG_ROOT / "data" / "corporate_actions" / "manual.csv").read_text())


if __name__ == "__main__":
    unittest.main()
