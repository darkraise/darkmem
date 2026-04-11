"""Named binding propagation for re-exported symbols.

Each language module exposes a ``propagate()`` function with the signature::

    def propagate(
        file_path: str,
        language: str,
        import_map: dict[str, str],
        symbol_table: dict[str, list[str]],
    ) -> dict[str, tuple[str, str]]: ...

The top-level :func:`propagate` dispatches to the correct module based on
the ``language`` argument.
"""

from __future__ import annotations

from app.services.named_bindings import python_bindings, typescript_bindings

BindingMap = dict[str, tuple[str, str]]

_LANGUAGE_MAP: dict[str, object] = {
    "python": python_bindings,
    "typescript": typescript_bindings,
    "javascript": typescript_bindings,
}


def propagate(
    file_path: str,
    language: str,
    import_map: dict[str, str],
    symbol_table: dict[str, list[str]],
    source_text: str = "",
) -> BindingMap:
    """Return named bindings for re-exported symbols.

    Dispatches to the appropriate language propagator.  Returns an empty map
    for unrecognised languages.

    Args:
        file_path: Repo-relative path of the file being analysed.
        language: Language identifier (e.g. ``"python"``, ``"typescript"``).
        import_map: ``import_source → resolved_file_path`` for this file.
        symbol_table: ``file_path → list[exported_symbol_name]``.
        source_text: Raw source text of the file; passed through to the
            language propagator for pattern matching.

    Returns:
        ``BindingMap`` — ``local_name → (source_path, exported_name)``.
    """
    mod = _LANGUAGE_MAP.get(language.lower())
    if mod is None:
        return {}
    return mod.propagate(  # type: ignore[attr-defined]
        file_path, language, import_map, symbol_table, source_text
    )


__all__ = ["propagate"]
