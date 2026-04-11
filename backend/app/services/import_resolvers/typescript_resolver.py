"""TypeScript/JavaScript import resolution.

Implements the Node.js module resolution algorithm with TypeScript extensions.
"""

from pathlib import PurePosixPath

_TS_EXTENSIONS: tuple[str, ...] = (".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs")
_INDEX_NAMES: tuple[str, ...] = (
    "index.ts",
    "index.tsx",
    "index.js",
    "index.jsx",
    "index.mjs",
)

DEFAULT_PATH_ALIAS_PREFIX: str = "@/"
DEFAULT_PATH_ALIAS_TARGET: str = "src/"


def _try_extensions(base: str, file_set: frozenset[str]) -> str | None:
    """Try each TypeScript/JS extension for a base path lacking an extension."""
    for ext in _TS_EXTENSIONS:
        candidate = base + ext
        if candidate in file_set:
            return candidate
    return None


def _try_as_file_or_directory(path: str, file_set: frozenset[str]) -> str | None:
    """Resolve a path as a file (with extension probing) or directory index."""
    # Direct hit — path already carries an extension.
    if path in file_set:
        return path

    # Probe extensions.
    result = _try_extensions(path, file_set)
    if result:
        return result

    # Directory index.
    for index_name in _INDEX_NAMES:
        candidate = f"{path}/{index_name}"
        if candidate in file_set:
            return candidate

    return None


def resolve(
    file_path: str,
    import_source: str,
    language: str,
    repo_root: str,
    file_paths: list[str],
    path_alias_prefix: str = DEFAULT_PATH_ALIAS_PREFIX,
    path_alias_target: str = DEFAULT_PATH_ALIAS_TARGET,
) -> str | None:
    """Resolve a TypeScript or JavaScript import to a repo-relative file path.

    Resolution order:
    1. ``@/`` (or custom) path alias — rewritten to ``src/`` (or custom target).
    2. Relative imports (``./`` / ``../``) — resolved against the importing file's
       directory with extension probing and index-file fallback.
    3. Bare specifiers — treated as repo-relative paths with the same probing.

    Args:
        file_path: Repo-relative path of the importing file.
        import_source: Raw import specifier string.
        language: Unused; present for interface conformance.
        repo_root: Unused; present for interface conformance.
        file_paths: All repo-relative paths for existence checks.
        path_alias_prefix: Import prefix to rewrite (default ``"@/"``).
        path_alias_target: Repo-relative directory to rewrite to (default ``"src/"``).

    Returns:
        Repo-relative resolved path, or ``None``.
    """
    file_set = frozenset(file_paths)

    # 1. Path alias rewrite (e.g. @/components/Foo → src/components/Foo).
    if import_source.startswith(path_alias_prefix):
        remainder = import_source[len(path_alias_prefix):]
        rewritten = path_alias_target + remainder
        result = _try_as_file_or_directory(rewritten, file_set)
        if result:
            return result

    # 2. Relative imports.
    if import_source.startswith("."):
        importer_dir = str(PurePosixPath(file_path).parent)
        if importer_dir == ".":
            importer_dir = ""
        joined = (
            f"{importer_dir}/{import_source}" if importer_dir else import_source
        )
        # Normalize . and .. segments without touching the filesystem.
        normalized = str(PurePosixPath(joined))
        return _try_as_file_or_directory(normalized, file_set)

    # 3. Bare specifiers — treat as repo-relative.
    return _try_as_file_or_directory(import_source, file_set)
