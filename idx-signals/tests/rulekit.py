"""Test rules as real modules built from source text, so the source audit sees exactly the
rule's own code (a rule defined inside a test module would be audited with the test's imports)."""

from __future__ import annotations

import importlib.util
import itertools
import sys
import tempfile
import textwrap
from pathlib import Path
from unittest import mock

from idxsig import rules

HEADER = "from __future__ import annotations\n\nimport numpy as np\n\n"
_DIR = Path(tempfile.mkdtemp(prefix="idxsig-test-rules-"))
_COUNTER = itertools.count()


def module_rule(rule_id: str, body: str, holding: int = 5, header: str = HEADER) -> rules.Rule:
    name = f"_idxsig_test_rule_{rule_id.lower()}_{next(_COUNTER)}"
    path = _DIR / f"{name}.py"
    path.write_text(header + textwrap.dedent(body))
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return rules.Rule(rule_id, "test", f"test rule {rule_id}", holding, module.compute, module)


def with_rule(rule: rules.Rule):
    real = rules.registry

    def patched():
        out = real()
        out[rule.rule_id] = rule
        return out

    return mock.patch.object(rules, "registry", patched)
