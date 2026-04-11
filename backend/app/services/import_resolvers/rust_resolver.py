"""Rust module import resolution.

Handles ``crate::``, ``super::``, ``self::`` prefix paths and ``::`` separators,
mapping them to ``.rs`` source files via the standard Rust module layout
(``name.rs`` or ``name/mod.rs``).
"""

from pathlib import PurePosixPath


def _try_rust_module_path(module_path: str, file_set: frozenset[str]) -> str | None:
    """Try to resolve a slash-separated module path to a Rust source file.

    Tries ``path.rs``, ``path/mod.rs``, and ``path/lib.rs``.  If none match,
    strips the last segment (which may be a symbol name rather than a module)
    and retries.

    Args:
        module_path: Forward-slash separated module path without extension.
        file_set: Set of all repo-relative file paths.

    Returns:
        Matching repo-relative ``.rs`` path, or ``None``.
    """
    if file_set and module_path + ".rs" in file_set:
        return module_path + ".rs"
    if file_set and module_path + "/mod.rs" in file_set:
        return module_path + "/mod.rs"
    if file_set and module_path + "/lib.rs" in file_set:
        return module_path + "/lib.rs"

    last_slash = module_path.rfind("/")
    if last_slash > 0:
        parent = module_path[:last_slash]
        if parent + ".rs" in file_set:
            return parent + ".rs"
        if parent + "/mod.rs" in file_set:
            return parent + "/mod.rs"

    return None


def _resolve_internal(
    file_path: str,
    import_source: str,
    file_set: frozenset[str],
) -> str | None:
    """Core Rust resolution logic (low-level helper).

    Args:
        file_path: Repo-relative path of the importing file.
        import_source: Rust use-path as extracted from source (``::``-separated).
        file_set: Set of all repo-relative file paths.

    Returns:
        Repo-relative ``.rs`` file path, or ``None``.
    """
    if import_source.startswith("crate::"):
        rust_path = import_source[len("crate::"):].replace("::", "/")
        # Standard layout: src/<path>.
        result = _try_rust_module_path("src/" + rust_path, file_set)
        if result:
            return result
        # Non-standard layout: repo root.
        return _try_rust_module_path(rust_path, file_set)

    if import_source.startswith("super::"):
        dir_parts = list(PurePosixPath(file_path).parts[:-1])
        if dir_parts:
            dir_parts.pop()
        rust_path = import_source[len("super::"):].replace("::", "/")
        full_path = "/".join(dir_parts + [rust_path]) if dir_parts else rust_path
        return _try_rust_module_path(full_path, file_set)

    if import_source.startswith("self::"):
        dir_parts = list(PurePosixPath(file_path).parts[:-1])
        rust_path = import_source[len("self::"):].replace("::", "/")
        full_path = "/".join(dir_parts + [rust_path]) if dir_parts else rust_path
        return _try_rust_module_path(full_path, file_set)

    if "::" in import_source:
        rust_path = import_source.replace("::", "/")
        return _try_rust_module_path(rust_path, file_set)

    return None


def resolve(
    file_path: str,
    import_source: str,
    language: str,
    repo_root: str,
    file_paths: list[str],
) -> str | None:
    """Resolve a Rust use-path to a repo-relative source file.

    Handles:

    * ``crate::`` — resolved from ``src/`` (standard layout) with repo-root fallback.
    * ``super::`` — resolved from the parent module directory.
    * ``self::`` — resolved from the current module directory.
    * Grouped imports ``use crate::models::{Foo, Bar}`` — the prefix path is
      resolved; individual symbol names are stripped.
    * Top-level grouped ``use {crate::a, crate::b}`` — first resolvable path wins.

    Args:
        file_path: Repo-relative path of the importing file.
        import_source: Raw Rust use-path string.
        language: Unused; present for interface conformance.
        repo_root: Unused; present for interface conformance.
        file_paths: All repo-relative paths for existence checks.

    Returns:
        Repo-relative ``.rs`` file path, or ``None``.
    """
    file_set = frozenset(file_paths)

    # Top-level grouped: use {crate::a, crate::b}
    if import_source.startswith("{") and import_source.endswith("}"):
        inner = import_source[1:-1]
        for part in (p.strip() for p in inner.split(",") if p.strip()):
            result = _resolve_internal(file_path, part, file_set)
            if result:
                return result
        return None

    # Scoped grouped: use crate::models::{Foo, Bar}
    brace_idx = import_source.find("::{")
    if brace_idx != -1 and import_source.endswith("}"):
        path_prefix = import_source[:brace_idx]
        brace_content = import_source[brace_idx + 3:-1]
        for item in (i.strip() for i in brace_content.split(",") if i.strip()):
            item_name = item.split(" as ")[0].strip() if " as " in item else item
            result = _resolve_internal(file_path, f"{path_prefix}::{item_name}", file_set)
            if result:
                return result
        # Fallback: resolve the prefix path itself.
        return _resolve_internal(file_path, path_prefix, file_set)

    return _resolve_internal(file_path, import_source, file_set)
