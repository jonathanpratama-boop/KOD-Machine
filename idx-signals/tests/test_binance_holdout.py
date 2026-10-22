import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

HOLD = Path(__file__).resolve().parents[1] / "research" / "BINANCE_ANN_1S_HOLDOUT"


def load(name):
    if str(HOLD) not in sys.path:
        sys.path.insert(0, str(HOLD))
    spec = importlib.util.spec_from_file_location(f"holdout_{name}", HOLD / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class DecisionTests(unittest.TestCase):
    def setUp(self):
        self.run = load("run")
        self.react = {"R_60": 0.03, "share_done_by_1s": 0.4}
        self.g1 = {"mean_net": 0.01, "t_net": 2.0, "winsorised_net": 0.008}
        self.g2 = {"mean_net": 0.006}

    def decide(self, g1=None, g2=None, t_pl=-1.0, react=None, clock=False, hurdle=1.65):
        return self.run.decide(g1 or self.g1, g2 or self.g2, t_pl, react or self.react, clock, hurdle)

    def test_pass_needs_all_four_gates(self):
        gates, verdict, reading = self.decide()
        self.assertEqual(verdict, "PASS")
        self.assertTrue(all(gates.values()))
        _, verdict, reading = self.decide(g2={"mean_net": -0.001})
        self.assertEqual((verdict, reading), ("FAIL", "G1_HOLDS_ANOTHER_GATE_FAILS"))
        _, verdict, reading = self.decide(t_pl=2.6)
        self.assertEqual((verdict, reading), ("FAIL", "G1_HOLDS_ANOTHER_GATE_FAILS"))

    def test_g1_is_the_one_sided_five_percent_line(self):
        self.assertFalse(self.decide(g1={**self.g1, "t_net": 1.649})[0][self.run.G1])
        self.assertTrue(self.decide(g1={**self.g1, "t_net": 1.65})[0][self.run.G1])
        self.assertFalse(self.decide(g1={**self.g1, "t_net": 5.0, "mean_net": -0.001})[0][self.run.G1])

    def test_a_miss_is_read_in_the_protocols_order(self):
        miss = {"mean_net": 0.004, "t_net": 1.2, "winsorised_net": 0.003}
        self.assertEqual(self.decide(g1=miss)[2], "LEAN_WITHOUT_POWER")
        none = {"mean_net": -0.002, "t_net": -0.5, "winsorised_net": -0.002}
        self.assertEqual(self.decide(g1=none, clock=True)[2], "NO_SIGN_IT_PERSISTED: THE_MOVE_STARTS_BEFORE_THE_PUBLISHED_TIME")
        self.assertEqual(self.decide(g1=none, react={"R_60": 0.03, "share_done_by_1s": 0.85})[2], "NO_SIGN_IT_PERSISTED: THE_WINDOW_HAS_CLOSED_THE_MARKET_GOT_FASTER")
        self.assertEqual(self.decide(g1=none, react={"R_60": 0.005, "share_done_by_1s": 0.4})[2], "NO_SIGN_IT_PERSISTED: THE_REACTION_ITSELF_SHRANK")
        self.assertEqual(self.decide(g1=none, react={"R_60": 0.03, "share_done_by_1s": 0.6})[2], "NO_SIGN_IT_PERSISTED: NO_CLEAR_WINDOW")


class GuardTests(unittest.TestCase):
    def test_the_holdout_opens_only_with_the_recorded_selection(self):
        hc = load("hold_common")
        with tempfile.TemporaryDirectory() as d, mock.patch.object(hc, "HERE", Path(d)):
            with self.assertRaises(SystemExit):
                hc.require_authorization()
            (Path(d) / "AUTHORIZATION.md").write_text("nothing relevant")
            with self.assertRaises(SystemExit):
                hc.require_authorization()
            (Path(d) / "AUTHORIZATION.md").write_text(f"The owner selected: {hc.AUTH_PHRASE} (Recommended)")
            self.assertIsNone(hc.require_authorization())

    def test_pinned_code_and_input_match_the_protocol(self):
        hc = load("hold_common")
        self.assertIsNone(hc.require_pinned_code())
        with tempfile.TemporaryDirectory() as d, mock.patch.object(hc, "HERE", Path(d)):
            (Path(d) / "PROTOCOL.md").write_text("no hashes here")
            with self.assertRaises(SystemExit):
                hc.require_pinned_code()


class TokenParsingTests(unittest.TestCase):
    def setUp(self):
        self.ev = load("events_v2")
        self.fm = self.ev.load(self.ev.M1 / "feasibility.py", "ann1m_feasibility_test")

    def parse(self, title):
        return self.ev.fixed_tokens(self.fm, title)

    def test_contract_symbols_become_base_tokens(self):
        self.assertEqual(self.parse("Binance Futures Will Launch USDⓈ-Margined NIGHTUSDT Perpetual Contract (2025-12-10)"), ["NIGHT"])
        self.assertEqual(self.parse("Binance Futures Will Launch USDⓈ-Margined SLERFUSDT and SCRTUSDT Perpetual Contracts With up to 75x Leverage"), ["SLERF", "SCRT"])
        self.assertEqual(self.parse("Binance Futures Will Launch USDⓈ-Margined PAXGUSDT Perpetual Contract"), ["PAXG"])

    def test_base_tokens_and_unrecoverable_titles_are_unchanged(self):
        self.assertEqual(self.parse("Binance Futures Will Launch USDⓈ-M GLM Perpetual Contract With Up to 50x Leverage"), ["GLM"])
        self.assertEqual(self.parse("Binance Futures Will Launch Multiple USDⓈ-Margined Equity Perpetual Contracts (2026-02-09)"), [])
        self.assertEqual(self.ev.base_token("USDT"), "USDT")
        self.assertEqual(self.ev.base_token("BTCUSD1"), "BTCUSD1")
        self.assertEqual(self.ev.base_token("ABUSDT"), "AB")               # a two-character base is kept as a base
        self.assertEqual(self.ev.base_token("AUSDT"), "AUSDT")             # a one-character base is not stripped


if __name__ == "__main__":
    unittest.main()
