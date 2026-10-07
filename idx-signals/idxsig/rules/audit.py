"""Static audit of a rule module: refuse code that could see data from after a session.

The prefix-first computation (rules.causal_signals) makes every recorded signal what the
rule returned when handed only data through that session. It cannot stop a rule from
fetching the future some other way: reading the panel file, holding data loaded at import
time, walking the call stack to the caller's full arrays, or keeping state between calls.
This audit refuses those patterns in the rule's source before it runs; sandbox.py blocks
the same operations at run time in case the source hides them.

Allowed: imports of numpy, pandas, math and a few pure stdlib modules, idxsig.market (tick
and limit helpers), `from . import Rule`, and `import sys` used only as
`sys.modules[__name__]`. Refused: every other import; open/eval/exec/compile/getattr and
friends; dunder attributes and frame attributes; numpy/pandas file I/O; `global` and
`nonlocal`; classes; attribute assignment; module-level values that are not literals;
mutable default arguments.
"""

from __future__ import annotations

import ast
import inspect

ALLOWED_MODULES = frozenset({
    "__future__", "numpy", "pandas", "math", "zlib", "hashlib", "typing", "dataclasses", "itertools",
    "operator", "statistics", "enum", "idxsig.market",
})
ALLOWED_RELATIVE = frozenset({"Rule", "RuleNotProvided"})  # from . import Rule (idxsig.rules)
FORBIDDEN_NAMES = frozenset({
    "open", "eval", "exec", "compile", "__import__", "globals", "locals", "vars", "getattr", "setattr", "delattr",
    "input", "breakpoint", "memoryview", "__builtins__", "help", "exit", "quit",
})
FRAME_ATTRS = frozenset({"f_back", "f_locals", "f_globals", "f_builtins", "f_code", "tb_frame", "tb_next",
                         "gi_frame", "cr_frame", "ag_frame", "gi_code"})
IO_ATTRS = frozenset({"load", "loads", "loadtxt", "genfromtxt", "fromfile", "memmap", "save", "savez",
                      "savez_compressed", "savetxt", "tofile", "DataSource", "fromregex", "lib", "testing",
                      "ctypeslib", "f2py", "distutils", "show_config", "HDFStore", "ExcelFile", "ExcelWriter"})
IO_PREFIXES = ("read_", "to_csv", "to_pickle", "to_parquet", "to_json", "to_excel", "to_hdf", "to_sql",
               "to_feather", "to_clipboard", "to_stata", "to_orc", "to_html", "to_latex", "to_markdown", "to_xml")
MUTABLE_CALLS = frozenset({"dict", "list", "set", "bytearray", "defaultdict", "OrderedDict", "deque", "Counter"})


class RuleAuditError(RuntimeError):
    pass


def _literal(node: ast.AST) -> bool:
    if isinstance(node, (ast.Constant, ast.Name)):
        return True
    if isinstance(node, ast.Tuple):
        return all(_literal(e) for e in node.elts)
    if isinstance(node, ast.UnaryOp):
        return _literal(node.operand)
    if isinstance(node, ast.BinOp):
        return _literal(node.left) and _literal(node.right)
    return False


def _sys_modules_name(node: ast.Attribute, parents: dict) -> bool:
    parent = parents.get(node)
    return (node.attr == "modules" and isinstance(parent, ast.Subscript) and parent.value is node
            and isinstance(parent.slice, ast.Name) and parent.slice.id == "__name__")


def audit_source(source: str, where: str = "rule") -> list[str]:
    tree = ast.parse(source)
    parents = {child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)}
    problems = []

    def bad(node, msg):
        problems.append(f"{where}:{getattr(node, 'lineno', '?')}: {msg}")

    sys_aliases = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "sys":
                    sys_aliases.add(alias.asname or "sys")
                elif alias.name not in ALLOWED_MODULES:
                    bad(node, f"import of {alias.name} is not allowed in a rule")
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                if node.level != 1 or node.module or any(a.name not in ALLOWED_RELATIVE for a in node.names):
                    bad(node, "relative imports other than `from . import Rule` are not allowed")
            elif node.module not in ALLOWED_MODULES:
                bad(node, f"import from {node.module} is not allowed in a rule")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            bad(node, f"`{type(node).__name__.lower()}` keeps state between calls")
        elif isinstance(node, ast.ClassDef):
            bad(node, "class definitions are not allowed in a rule (class attributes can carry state)")
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            bad(node, f"`{node.id}` is not allowed in a rule")
        elif isinstance(node, ast.Attribute):
            if node.attr.startswith("__") and node.attr.endswith("__"):
                bad(node, f"dunder attribute .{node.attr} is not allowed in a rule")
            elif node.attr.startswith("_"):
                bad(node, f"private attribute .{node.attr} is not allowed in a rule")
            elif node.attr in FRAME_ATTRS or node.attr in ("base", "ctypes", "data", "__array_interface__"):
                bad(node, f"frame attribute .{node.attr} is not allowed in a rule")
            elif node.attr in IO_ATTRS or node.attr.startswith(IO_PREFIXES):
                bad(node, f".{node.attr} is file or foreign-code access, not allowed in a rule")
            elif isinstance(node.value, ast.Name) and node.value.id in sys_aliases and not _sys_modules_name(node, parents):
                bad(node, f"sys.{node.attr}: only sys.modules[__name__] is allowed in a rule")
            if isinstance(node.ctx, (ast.Store, ast.Del)):
                bad(node, "attribute assignment is not allowed in a rule (it can carry state between calls)")
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            for default in node.args.defaults + [d for d in node.args.kw_defaults if d is not None]:
                if not _literal(default):
                    bad(default, "default arguments must be literals (a mutable default keeps state between calls)")
            for deco in getattr(node, "decorator_list", []):
                bad(deco, "decorators are not allowed in a rule (caches keep state between calls)")
    for node in tree.body:
        if isinstance(node, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
            value = node.value
            if value is not None and not _literal(value):
                bad(node, "module-level values must be literals (strings, numbers, tuples): anything else can hold "
                          "data loaded at import time or state between calls")
        elif isinstance(node, (ast.Expr,)) and not (isinstance(node.value, ast.Constant)):
            bad(node, "module-level code other than definitions and literal constants is not allowed")
        elif isinstance(node, (ast.For, ast.While, ast.With, ast.Try, ast.If)):
            bad(node, "module-level control flow is not allowed in a rule")
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in MUTABLE_CALLS:
            parent = parents.get(node)
            if isinstance(parent, (ast.Assign, ast.AnnAssign)) and parent in tree.body:
                bad(node, "module-level mutable container")
    return problems


def audit_module(module) -> list[str]:
    return audit_source(inspect.getsource(module), where=module.__name__)


def require_clean(rule) -> None:
    problems = audit_module(rule.module)
    if problems:
        raise RuleAuditError(f"{rule.rule_id} fails the causal-source audit:\n  " + "\n  ".join(problems))
