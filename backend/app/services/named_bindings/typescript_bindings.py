"""TypeScript/JavaScript named binding propagation.

Tracks re-export chains including ``export { Foo } from './foo'``,
``export * from './module'`` (wildcard), and barrel file (``index.ts``)
aggregation.
"""

from __future__ import annotations

BindingMap = dict[str, tuple[str, str]]

_REEXPORT_PATTERN_NAMED = r"export\s*\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"]"
_REEXPORT_PATTERN_WILDCARD = r"export\s*\*\s*(?:as\s+(\w+)\s+)?from\s*['\"]([^'\"]+)['\"]"
_IMPORT_PATTERN = r"(?:import|export)\s*\{([^}]+)\}\s*from\s*['\"]([^'\"]+)['\"]"

import re as _re


def _parse_specifier_list(raw: str) -> list[tuple[str, str]]:
    """Parse a brace-delimited specifier list into ``(exported, local)`` pairs.

    Handles both ``Foo`` and ``Foo as Bar`` forms.

    Args:
        raw: Content between braces, e.g. ``" Foo, Bar as Baz "``.

    Returns:
        List of ``(exported_name, local_name)`` tuples.
    """
    result: list[tuple[str, str]] = []
    for spec in raw.split(","):
        parts = spec.strip().split()
        if len(parts) == 1 and parts[0]:
            result.append((parts[0], parts[0]))
        elif len(parts) == 3 and parts[1].lower() == "as" and parts[0] and parts[2]:
            result.append((parts[0], parts[2]))
    return result


def propagate(
    file_path: str,
    language: str,
    import_map: dict[str, str],
    symbol_table: dict[str, list[str]],
    source_text: str = "",
) -> BindingMap:
    """Return named bindings for TypeScript/JavaScript re-exports.

    Processes three re-export forms:

    * ``export { Foo } from './foo'`` — explicit named re-export.
    * ``export { Foo as Bar } from './foo'`` — aliased re-export.
    * ``export * from './module'`` — wildcard re-export; expands using
      ``symbol_table`` when the source file's exports are known.
    * ``export * as ns from './module'`` — namespace re-export recorded as
      ``ns → (source_path, "*")``.

    Barrel file detection is implicit: any ``index.ts``/``index.js`` that
    contains only re-exports will be fully expanded via the same logic.

    Args:
        file_path: Repo-relative path of the file being analysed.
        language: Unused; present for interface conformance.
        import_map: ``import_source → resolved_file_path`` for this file.
        symbol_table: ``file_path → list[exported_symbol_name]``.
        source_text: Raw source text of the file (used for pattern matching).
            When empty, propagation relies solely on ``import_map`` keys.

    Returns:
        ``BindingMap`` — ``local_name → (source_path, exported_name)``.
    """
    bindings: BindingMap = {}

    if not source_text:
        return bindings

    # Named re-exports: export { Foo, Bar as Baz } from './source'
    for match in _re.finditer(_REEXPORT_PATTERN_NAMED, source_text):
        specifiers_raw, import_specifier = match.group(1), match.group(2)
        source_path = import_map.get(import_specifier)
        if not source_path:
            continue
        for exported_name, local_name in _parse_specifier_list(specifiers_raw):
            bindings[local_name] = (source_path, exported_name)

    # Wildcard re-exports: export * from './source' or export * as ns from './source'
    for match in _re.finditer(_REEXPORT_PATTERN_WILDCARD, source_text):
        namespace, import_specifier = match.group(1), match.group(2)
        source_path = import_map.get(import_specifier)
        if not source_path:
            continue

        if namespace:
            # export * as ns from './source' — namespace object re-export.
            bindings[namespace] = (source_path, "*")
        else:
            # export * from './source' — expand via symbol table if available.
            exported_symbols = symbol_table.get(source_path, [])
            for sym in exported_symbols:
                if sym not in bindings:
                    bindings[sym] = (source_path, sym)

    return bindings
