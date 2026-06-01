"""Unit tests for ``_extract_import`` against the real tree-sitter grammars.

These pin the ``ExtractedImport`` contract that ``call_resolver``'s
``build_named_imports`` / ``build_wildcard_imports`` / ``build_import_map``
depend on: ``source`` is always the module path, ``names`` lists the imported
symbols (original pre-alias names), and Python wildcards surface as ``"*"``.
"""

import importlib

import pytest

from app.services.code_parser import (
    TREE_SITTER_AVAILABLE,
    IMPORT_NODE_TYPES,
    _extract_import,
)

pytestmark = pytest.mark.skipif(
    not TREE_SITTER_AVAILABLE, reason="tree-sitter not installed"
)


def _parse_import(module_name: str, language_fn: str, src: str):
    try:
        from tree_sitter import Language, Parser

        mod = importlib.import_module(module_name)
    except ImportError:
        pytest.skip(f"grammar {module_name} not installed")

    lang = Language(getattr(mod, language_fn)())
    tree = Parser(lang).parse(src.encode())

    stack = [tree.root_node]
    node = None
    while stack:
        cur = stack.pop()
        if cur.type in IMPORT_NODE_TYPES:
            node = cur
            break
        stack.extend(reversed(cur.children))
    assert node is not None, f"no import node found in: {src!r}"

    return _extract_import(node, src.encode())


@pytest.mark.parametrize(
    "src, expected_source, expected_names",
    [
        ("from pkg.utils import *", "pkg.utils", ["*"]),
        ("from os import path, getcwd", "os", ["path", "getcwd"]),
        ("from numpy import array as arr", "numpy", ["array"]),
        ("from .mod import thing", ".mod", ["thing"]),
        ("from . import sibling", ".", ["sibling"]),
        ("import x", "x", ["x"]),
        ("import a.b.c", "a.b.c", ["a"]),
        ("import a.b.c as abc", "a.b.c", ["a.b.c"]),
    ],
)
def test_python_imports(src, expected_source, expected_names):
    imp = _parse_import("tree_sitter_python", "language", src)
    assert imp is not None
    assert imp.source == expected_source
    assert imp.names == expected_names


@pytest.mark.parametrize(
    "src, expected_source, expected_names",
    [
        ('import { foo, bar as baz } from "./pkg/utils"', "./pkg/utils", ["foo", "bar"]),
        ('import Default from "./mod"', "./mod", ["Default"]),
        ('import * as ns from "./mod"', "./mod", ["*"]),
        ('import "./side-effect"', "./side-effect", ["./side-effect"]),
    ],
)
def test_typescript_imports(src, expected_source, expected_names):
    imp = _parse_import("tree_sitter_typescript", "language_typescript", src)
    assert imp is not None
    assert imp.source == expected_source
    assert imp.names == expected_names


def test_javascript_named_import():
    imp = _parse_import(
        "tree_sitter_javascript", "language", 'import { foo, bar as baz } from "./x"'
    )
    assert imp is not None
    assert imp.source == "./x"
    assert imp.names == ["foo", "bar"]
