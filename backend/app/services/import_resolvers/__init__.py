"""Per-language import resolvers.

Each resolver module exposes a ``resolve()`` function with the signature::

    def resolve(
        file_path: str,
        import_source: str,
        language: str,
        repo_root: str,
        file_paths: list[str],
    ) -> str | None: ...

The top-level :func:`resolve_import` dispatches to the correct module based on
the ``language`` argument.
"""

from __future__ import annotations

from app.services.import_resolvers import (
    go_resolver,
    jvm_resolver,
    python_resolver,
    rust_resolver,
    typescript_resolver,
)

_LANGUAGE_MAP: dict[str, object] = {
    "python": python_resolver,
    "typescript": typescript_resolver,
    "javascript": typescript_resolver,
    "go": go_resolver,
    "rust": rust_resolver,
    "java": jvm_resolver,
    "kotlin": jvm_resolver,
}


def resolve_import(
    file_path: str,
    import_source: str,
    language: str,
    repo_root: str,
    file_paths: list[str],
) -> str | None:
    """Resolve an import string to a repo-relative file path.

    Dispatches to the appropriate language resolver.  Returns ``None`` for
    unrecognised languages or when no file can be matched.

    Args:
        file_path: Repo-relative path of the importing file (forward slashes).
        import_source: Raw import string as it appears in source code.
        language: Language identifier (e.g. ``"python"``, ``"typescript"``).
        repo_root: Absolute on-disk path to the repository root.
        file_paths: All repo-relative file paths for existence checks.

    Returns:
        Repo-relative resolved file path, or ``None``.
    """
    resolver_module = _LANGUAGE_MAP.get(language.lower())
    if resolver_module is None:
        return None
    return resolver_module.resolve(  # type: ignore[attr-defined]
        file_path, import_source, language, repo_root, file_paths
    )


__all__ = ["resolve_import"]
