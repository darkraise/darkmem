"""Python import resolution — PEP 328 relative imports and proximity-based bare imports.

Import system spec: PEP 302 (original), PEP 451 (current).
"""

from pathlib import PurePosixPath


def _try_python_paths(base: str, file_set: frozenset[str]) -> str | None:
    """Try package (__init__.py) then module (.py) for a base path."""
    pkg = base + "/__init__.py"
    if pkg in file_set:
        return pkg
    mod = base + ".py"
    if mod in file_set:
        return mod
    return None


def resolve(
    file_path: str,
    import_source: str,
    language: str,
    repo_root: str,
    file_paths: list[str],
) -> str | None:
    """Resolve a Python import to a repo-relative file path.

    Resolution order:
    1. Relative imports (PEP 328): leading dots determine package ancestry level.
    2. Proximity bare imports: checks the importer's own directory, then walks
       ancestor directories toward the repo root (approximating sys.path order).

    Namespace packages (PEP 420, directories without ``__init__.py``) are not
    resolved — they cannot be distinguished from arbitrary directories without
    running the interpreter.

    Args:
        file_path: Repo-relative path of the file containing the import.
        import_source: Raw import string (e.g. ``".utils"``, ``"os.path"``).
        language: Unused; present for interface conformance.
        repo_root: Unused; present for interface conformance.
        file_paths: All repo-relative paths for existence checks.

    Returns:
        Repo-relative resolved path, or ``None``.
    """
    file_set = frozenset(file_paths)
    parts = PurePosixPath(file_path).parts
    importer_dir_parts = list(parts[:-1])

    if import_source.startswith("."):
        return _resolve_relative(import_source, importer_dir_parts, file_set)

    return _resolve_bare(import_source, importer_dir_parts, file_set)


def _resolve_relative(
    import_source: str,
    importer_dir_parts: list[str],
    file_set: frozenset[str],
) -> str | None:
    """Resolve a PEP 328 relative import."""
    dot_match_count = 0
    for ch in import_source:
        if ch == ".":
            dot_match_count += 1
        else:
            break

    module_part = import_source[dot_match_count:]

    # More dots than ancestry levels → beyond top-level package → invalid.
    if dot_match_count - 1 > len(importer_dir_parts):
        return None

    dir_parts = importer_dir_parts[:]
    for _ in range(dot_match_count - 1):
        if dir_parts:
            dir_parts.pop()

    if module_part:
        dir_parts.extend(module_part.replace(".", "/").split("/"))

    base = "/".join(dir_parts) if dir_parts else ""
    if not base:
        return None

    return _try_python_paths(base, file_set)


def _resolve_bare(
    import_source: str,
    importer_dir_parts: list[str],
    file_set: frozenset[str],
) -> str | None:
    """Resolve a bare (non-relative) import with proximity heuristic.

    Converts dots to slashes and checks the importer's own directory first,
    then walks ancestor directories toward the repo root.  Single-segment
    imports benefit most; multi-segment ones (``os.path``) follow the same
    path but are unlikely to match unless the package is vendored in the repo.
    """
    path_like = import_source.replace(".", "/")

    # Proximity: check importer's own directory first.
    if importer_dir_parts:
        importer_dir = "/".join(importer_dir_parts)
        result = _try_python_paths(f"{importer_dir}/{path_like}", file_set)
        if result:
            return result

    # Ancestor walk: check each ancestor directory up to repo root.
    for i in range(len(importer_dir_parts) - 1, -1, -1):
        ancestor_parts = importer_dir_parts[:i]
        prefix = "/".join(ancestor_parts) + "/" if ancestor_parts else ""
        result = _try_python_paths(f"{prefix}{path_like}", file_set)
        if result:
            return result

    return None
