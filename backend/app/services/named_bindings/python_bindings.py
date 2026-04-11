"""Python named binding propagation.

Tracks:

* ``from pkg import Cls as Alias`` — explicit aliased imports.
* ``from pkg import name`` — direct imports (local name == exported name).
* ``from . import submodule`` — relative intra-package re-exports.
* ``__all__`` list — controls what ``from module import *`` exposes.
"""

from __future__ import annotations

import re as _re

BindingMap = dict[str, tuple[str, str]]

_FROM_IMPORT_RE = _re.compile(
    r"^\s*from\s+(\.+\S*|\S+)\s+import\s+(.+)$",
    _re.MULTILINE,
)
_ALL_RE = _re.compile(
    r"^__all__\s*=\s*\[([^\]]*)\]",
    _re.MULTILINE | _re.DOTALL,
)
_STRING_TOKEN_RE = _re.compile(r"['\"](\w+)['\"]")


def _parse_import_names(raw: str) -> list[tuple[str, str]]:
    """Parse the names portion of a ``from ... import`` statement.

    Handles both parenthesised and plain forms.

    Args:
        raw: Text after the ``import`` keyword, e.g. ``"Foo, Bar as B"``.

    Returns:
        List of ``(exported_name, local_name)`` tuples.
    """
    cleaned = raw.strip().lstrip("(").rstrip(")")
    result: list[tuple[str, str]] = []
    for token in cleaned.split(","):
        parts = token.strip().split()
        if len(parts) == 1 and parts[0] and _re.match(r"^\w+$", parts[0]):
            result.append((parts[0], parts[0]))
        elif len(parts) == 3 and parts[1] == "as" and parts[0] and parts[2]:
            result.append((parts[0], parts[2]))
    return result


def _parse_all_list(source_text: str) -> list[str] | None:
    """Extract the ``__all__`` export list from module source text.

    Args:
        source_text: Raw Python source.

    Returns:
        List of exported symbol names, or ``None`` if ``__all__`` is not found
        or uses a non-literal form.
    """
    match = _ALL_RE.search(source_text)
    if not match:
        return None
    return _STRING_TOKEN_RE.findall(match.group(1))


def propagate(
    file_path: str,
    language: str,
    import_map: dict[str, str],
    symbol_table: dict[str, list[str]],
    source_text: str = "",
) -> BindingMap:
    """Return named bindings for Python re-exported symbols.

    For each ``from X import Y [as Z]`` statement, records the binding
    ``Z → (resolved_path_of_X, Y)`` when the import source resolves to a known
    file.  Wildcard ``from X import *`` is expanded using ``symbol_table`` when
    available, and further filtered by the current file's ``__all__`` if present.

    Args:
        file_path: Repo-relative path of the file being analysed.
        language: Unused; present for interface conformance.
        import_map: ``import_source → resolved_file_path`` for this file.
        symbol_table: ``file_path → list[exported_symbol_name]``.
        source_text: Raw Python source of the file.  When empty, propagation
            returns an empty map.

    Returns:
        ``BindingMap`` — ``local_name → (source_path, exported_name)``.
    """
    if not source_text:
        return {}

    bindings: BindingMap = {}
    all_list = _parse_all_list(source_text)

    for match in _FROM_IMPORT_RE.finditer(source_text):
        import_source, names_raw = match.group(1), match.group(2).strip()
        source_path = import_map.get(import_source)
        if not source_path:
            continue

        if names_raw == "*":
            exported_symbols = symbol_table.get(source_path, [])
            for sym in exported_symbols:
                if all_list is None or sym in all_list:
                    if sym not in bindings:
                        bindings[sym] = (source_path, sym)
        else:
            for exported_name, local_name in _parse_import_names(names_raw):
                if all_list is None or local_name in all_list:
                    bindings[local_name] = (source_path, exported_name)

    return bindings
