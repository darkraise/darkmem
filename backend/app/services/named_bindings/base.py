"""Base interface for named binding propagation."""

from typing import Protocol


BindingMap = dict[str, tuple[str, str]]
"""Mapping of ``local_name → (source_path, exported_name)``."""


class NamedBindingsPropagator(Protocol):
    """Protocol for language-specific named-binding propagators."""

    def propagate(
        self,
        file_path: str,
        language: str,
        import_map: dict[str, str],
        symbol_table: dict[str, list[str]],
    ) -> BindingMap:
        """Return named bindings for re-exported symbols.

        Args:
            file_path: Repo-relative path of the file being analysed.
            language: Language identifier string.
            import_map: Mapping of ``import_source → resolved_file_path`` for
                imports already resolved for this file.
            symbol_table: Mapping of ``file_path → list[exported_symbol_name]``
                for all files whose exports are known.

        Returns:
            Mapping of ``local_name → (source_path, exported_name)`` for every
            binding that can be traced back to a source file.
        """
        ...


def propagate(
    file_path: str,
    language: str,
    import_map: dict[str, str],
    symbol_table: dict[str, list[str]],
) -> BindingMap:
    """Return mapping of local_name → (source_path, exported_name) for re-exported bindings.

    This is the canonical signature shared by every language bindings module.

    Args:
        file_path: Repo-relative path of the file being analysed.
        language: Language identifier string.
        import_map: Mapping of ``import_source → resolved_file_path``.
        symbol_table: Mapping of ``file_path → list[exported_symbol_name]``.

    Returns:
        ``BindingMap`` — may be empty if no re-exports can be traced.
    """
    raise NotImplementedError
