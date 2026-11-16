"""Regression checks for the contradictory live development response.

Written alongside the repair; these are not independently authored tests.
"""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from idxsig.guidance_margin_reader import (
    OUTPUT_SCHEMA, _request_bytes, _transport, bind_candidates, build_request,
    run_once, source_packet,
)
from tests.test_guidance_margin_facts_independent import synthetic_pair
from tests.test_guidance_margin_reader_independent import model_output


class MetricSchemaRegressionTests(unittest.TestCase):
    def setUp(self):
        self.doc = OUTPUT_SCHEMA["properties"]["current"]
        self.metric = self.doc["properties"]["revenue"]

    def test_forms_are_disjoint_and_have_only_their_required_evidence(self):
        expected = {"point": {"point"}, "range": {"low", "high"},
                    "center_spread": {"center", "spread"}}
        variants = self.metric["anyOf"]
        self.assertEqual(len(variants), 4)
        self.assertEqual(variants[-1], {"type": "null"})
        seen = set()
        for branch in variants[:-1]:
            props = branch["properties"]
            self.assertEqual(len(props["form"]["enum"]), 1)
            form = props["form"]["enum"][0]
            self.assertNotIn(form, seen)
            seen.add(form)
            self.assertEqual(set(branch["required"]), set(props))
            self.assertIs(branch["additionalProperties"], False)
            for slot in ("point", "low", "high", "center", "spread"):
                if slot in expected[form]:
                    self.assertEqual(props[slot]["type"], "object")
                    self.assertEqual(set(props[slot]["required"]), {"quote", "token"})
                    self.assertIs(props[slot]["additionalProperties"], False)
                else:
                    self.assertEqual(props[slot], {"type": "null"})
        self.assertEqual(seen, set(expected))

    def test_every_document_metric_uses_the_same_contract(self):
        for side in ("current", "prior"):
            for name in ("revenue", "operating_profit", "operating_margin"):
                self.assertEqual(OUTPUT_SCHEMA["properties"][side]["properties"][name], self.metric)

    def test_original_point_with_center_contradiction_still_rejected_locally(self):
        pair = synthetic_pair()
        output = model_output(pair)
        metric = output["current"]["operating_profit"]
        metric["form"] = "point"
        metric["point"] = metric["low"]
        metric["low"] = metric["high"] = None
        metric["center"] = deepcopy(metric["point"])
        with self.assertRaisesRegex(ValueError, "unused metric slot"):
            bind_candidates(source_packet(pair), output, "2026-11-01T12:00:10Z")

    def test_missing_required_numeric_evidence_is_rejected_locally(self):
        pair = synthetic_pair()
        output = model_output(pair)
        output["current"]["operating_profit"]["low"] = None
        with self.assertRaises(ValueError):
            bind_candidates(source_packet(pair), output, "2026-11-01T12:00:10Z")

    def test_one_source_number_cannot_supply_both_center_and_spread(self):
        pair = synthetic_pair()
        output = model_output(pair)
        metric = output["current"]["operating_profit"]
        metric["form"] = "center_spread"
        metric["center"] = metric["spread"] = deepcopy(metric["low"])
        metric["low"] = metric["high"] = None
        with self.assertRaisesRegex(ValueError, "distinct source numbers"):
            bind_candidates(source_packet(pair), output, "2026-11-01T12:00:10Z")

    def test_wire_preserves_form_before_numeric_evidence(self):
        packet = source_packet(synthetic_pair())
        request = build_request(packet, "explicit-model")
        sent = []

        class Connection:
            def __init__(self, *args, **kwargs):
                pass

            def request(self, method, path, body, headers):
                sent.append(body)

            def getresponse(self):
                return self

            status = 200

            def read(self):
                return b"{}"

            def getheader(self, key):
                return None

            def close(self):
                pass

        with patch("idxsig.guidance_margin_reader.http.client.HTTPSConnection", Connection):
            _transport(request, "fake-development-credential")
        self.assertEqual(sent, [_request_bytes(request)])
        wire = json.loads(sent[0])
        branches = wire["text"]["format"]["schema"]["properties"]["current"]["properties"]["revenue"]["anyOf"]
        for variant in branches[:-1]:
            self.assertEqual(next(iter(variant["properties"])), "form")

    def test_exact_wire_request_is_retained_before_the_call(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(os.environ, {"OPENAI_API_KEY": "fake-key"}):
            out = Path(tmp) / "one-call"

            def transport(body, key):
                retained = (out / "request_body.json").read_bytes()
                self.assertEqual(retained, _request_bytes(body))
                meta = json.loads((out / "request.json").read_text())
                self.assertEqual(meta["request_body_sha256"], hashlib.sha256(retained).hexdigest())
                return 200, b'{"status":"completed","output":[]}', None

            self.assertEqual(run_once(source_packet(synthetic_pair()), out, "explicit-model", transport)["status"], "REJECTED")


if __name__ == "__main__":
    unittest.main()
