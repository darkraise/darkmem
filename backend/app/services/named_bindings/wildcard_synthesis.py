"""Wildcard import expansion (synthetic per-symbol binding generation).

For languages that import entire modules without explicit symbol selection
(Go, Ruby, C/C++, Swift), or for Python ``import module`` namespace aliases,
this module expands the import into individual ``local_name → (source_path,
exported_name)`` entries using the symbol table.

A hard cap of :data:`MAX_SYNTHETIC_BINDINGS_PER_FILE` prevents runaway
expansion for files with very large dependency surfaces.
"""

from __future__ import annotations

MAX_SYNTHETIC_BINDINGS_PER_FILE: int = 1000

BindingMap = dict[str, tuple[str, str]]


def expand_wildcard_import(
    local_alias: str,
    source_path: str,
    symbol_table: dict[str, list[str]],
    existing_bindings: BindingMap,
) -> BindingMap:
    """Expand a single whole-module import into per-symbol bindings.

    Symbols already present in ``existing_bindings`` are skipped to preserve
    explicit bindings that take precedence.

    Args:
        local_alias: The name the module is imported under (e.g. ``"models"``
            for ``import models``).  When non-empty, symbols are recorded as
            ``local_alias.SymbolName → (source_path, SymbolName)`` to reflect
            the qualified access pattern.  When empty, symbols are recorded
            without a prefix (bare wildcard expansion).
        source_path: Repo-relative path of the imported file/module.
        symbol_table: ``file_path → list[exported_symbol_name]``.
        existing_bindings: Already-recorded bindings for this file; used to
            avoid exceeding the cap calculation and to skip conflicts.

    Returns:
        New ``BindingMap`` entries (does not mutate ``existing_bindings``).
    """
    exported_symbols = symbol_table.get(source_path, [])
    new_bindings: BindingMap = {}
    remaining_cap = MAX_SYNTHETIC_BINDINGS_PER_FILE - len(existing_bindings)

    for sym in exported_symbols:
        if remaining_cap <= 0:
            break
        local_name = f"{local_alias}.{sym}" if local_alias else sym
        if local_name not in existing_bindings:
            new_bindings[local_name] = (source_path, sym)
            remaining_cap -= 1

    return new_bindings


def synthesize(
    file_path: str,
    language: str,
    import_map: dict[str, str],
    symbol_table: dict[str, list[str]],
    module_alias_map: dict[str, str] | None = None,
) -> BindingMap:
    """Generate synthetic per-symbol bindings for whole-module imports.

    Handles two scenarios:

    1. **Module alias imports** (via ``module_alias_map``): ``import models as m``
       produces ``m.User → (models.py, User)`` for each symbol exported by
       ``models.py``.  This applies to Python namespace imports and equivalent
       patterns in other languages.

    2. **Wildcard imports without alias** (languages where all module symbols
       enter the local namespace unqualified): each resolved import source in
       ``import_map`` is expanded if its symbols are known in ``symbol_table``.
       Applicable to Go (``import .``), Ruby (``include``), C/C++ (``using namespace``),
       and Swift (``import``).

    Args:
        file_path: Repo-relative path of the file being analysed (unused
            directly; present for interface conformance and future filtering).
        language: Language identifier (e.g. ``"go"``, ``"python"``).
        import_map: ``import_source → resolved_file_path`` for this file.
        symbol_table: ``file_path → list[exported_symbol_name]``.
        module_alias_map: Optional ``alias → resolved_file_path`` for imports
            of the form ``import X as alias`` or ``import X`` (bare module
            imports where the module name itself is the alias).

    Returns:
        ``BindingMap`` with all synthetic entries.  Total entries are capped at
        :data:`MAX_SYNTHETIC_BINDINGS_PER_FILE`.
    """
    bindings: BindingMap = {}

    if module_alias_map:
        for alias, source_path in module_alias_map.items():
            if len(bindings) >= MAX_SYNTHETIC_BINDINGS_PER_FILE:
                break
            new_entries = expand_wildcard_import(alias, source_path, symbol_table, bindings)
            bindings.update(new_entries)

    for _import_source, source_path in import_map.items():
        if len(bindings) >= MAX_SYNTHETIC_BINDINGS_PER_FILE:
            break
        if source_path not in symbol_table:
            continue
        new_entries = expand_wildcard_import("", source_path, symbol_table, bindings)
        bindings.update(new_entries)

    return bindings
