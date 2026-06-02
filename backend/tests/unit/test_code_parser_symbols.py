"""Class methods and body-nested symbols must be extracted.

tree-sitter nests methods under a class body node (`block`/`class_body`/…), so
scanning only a node's direct children for nested symbols dropped every method —
leaving the symbol table (and thus the call graph, heritage/MRO, blast-radius,
rename, and code_symbol/code_context tools) empty of methods for OO code.
"""
from __future__ import annotations

from app.services.code_parser import parse_file


def _names(syms) -> set[str]:
    out: set[str] = set()
    for s in syms:
        out.add(s.name)
        out |= _names(s.children)
    return out


def test_python_class_methods_are_extracted():
    pr = parse_file(
        "t.py",
        "class Foo:\n    def bar(self):\n        return 1\n    def baz(self):\n        return 2\n",
    )
    assert pr.language == "python"
    foo = next(s for s in pr.symbols if s.name == "Foo")
    method_names = {c.name for c in foo.children}
    assert {"bar", "baz"} <= method_names
    # tree-sitter-python emits function_definition for methods (no method node),
    # so the kind is "function"; the point is they are extracted as child symbols.
    assert all(c.kind in ("method", "function") for c in foo.children)


def test_python_nested_function_is_extracted():
    pr = parse_file(
        "t.py",
        "def outer():\n    def inner():\n        return 0\n    return inner\n",
    )
    outer = next(s for s in pr.symbols if s.name == "outer")
    assert "inner" in {c.name for c in outer.children}


def test_top_level_symbols_still_extracted():
    pr = parse_file(
        "t.py",
        "class Foo:\n    def bar(self):\n        pass\n\ndef top():\n    return 0\n",
    )
    top_level = {s.name for s in pr.symbols}
    assert {"Foo", "top"} <= top_level
    assert "bar" in _names(pr.symbols)


def test_typescript_class_methods_are_extracted():
    pr = parse_file(
        "t.ts",
        "class Svc {\n  start(): void {}\n  stop(): void {}\n}\n",
    )
    if pr.language != "typescript":
        import pytest

        pytest.skip("typescript grammar not installed")
    assert "start" in _names(pr.symbols)
    assert "stop" in _names(pr.symbols)
