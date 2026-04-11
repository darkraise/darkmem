"""Go package import resolution.

Handles Go module path-based package imports. Requires the module path from
``go.mod`` to strip the module prefix and map imports to directories containing
``.go`` source files.
"""


def resolve_package_files(
    import_source: str,
    module_path: str,
    file_paths: list[str],
) -> list[str]:
    """Return all non-test ``.go`` files that belong to the imported package.

    The package directory is found by stripping the module path prefix from the
    import path and matching the resulting relative path as a directory suffix
    against all known ``.go`` files.  Only files *directly* inside that
    directory are included — subdirectories form separate packages in Go.

    Args:
        import_source: The full Go import path (e.g. ``"github.com/org/repo/internal/auth"``).
        module_path: The module path declared in ``go.mod`` (e.g. ``"github.com/org/repo"``).
        file_paths: All repo-relative file paths for existence checks.

    Returns:
        List of repo-relative paths for matching ``.go`` source files (excluding
        ``_test.go`` files).  Empty list if the package is external or has no
        matching files.
    """
    if not import_source.startswith(module_path):
        return []

    after_module = import_source[len(module_path):]
    if not after_module or after_module[0] != "/":
        return []

    relative_pkg = after_module.lstrip("/")
    if not relative_pkg:
        return []

    pkg_suffix = "/" + relative_pkg + "/"
    pkg_prefix = relative_pkg + "/"
    matches: list[str] = []

    for fp in file_paths:
        if not fp.endswith(".go") or fp.endswith("_test.go"):
            continue

        normalized = "/" + fp
        idx = normalized.find(pkg_suffix)
        if idx >= 0:
            after_pkg = normalized[idx + len(pkg_suffix):]
        elif fp.startswith(pkg_prefix):
            after_pkg = fp[len(pkg_prefix):]
        else:
            continue

        # Only direct children — no nested subdirectories.
        if "/" not in after_pkg:
            matches.append(fp)

    return matches


def resolve(
    file_path: str,
    import_source: str,
    language: str,
    repo_root: str,
    file_paths: list[str],
    module_path: str = "",
) -> str | None:
    """Resolve a Go import to the first ``.go`` file in the matching package.

    For a full picture of cross-file dependencies within a Go package, use
    :func:`resolve_package_files` directly — this function returns only the
    first match to satisfy the single-file resolver interface.

    Args:
        file_path: Unused; present for interface conformance.
        import_source: Raw Go import path string.
        language: Unused; present for interface conformance.
        repo_root: Unused; present for interface conformance.
        file_paths: All repo-relative paths for existence checks.
        module_path: Module path from ``go.mod``.  When empty, resolution is
            skipped and ``None`` is returned.

    Returns:
        First matching repo-relative ``.go`` file path, or ``None``.
    """
    if not module_path:
        return None

    pkg_files = resolve_package_files(import_source, module_path, file_paths)
    return pkg_files[0] if pkg_files else None
