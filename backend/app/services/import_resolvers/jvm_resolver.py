"""JVM import resolution (Java + Kotlin).

Handles wildcard imports, member/static imports, and Kotlin-specific patterns.
Maps dotted JVM package paths to directory structures containing ``.java`` and
``.kt``/``.kts`` files.
"""

_JAVA_EXTENSIONS: tuple[str, ...] = (".java",)
_KOTLIN_EXTENSIONS: tuple[str, ...] = (".kt", ".kts")
_JVM_EXTENSIONS: tuple[str, ...] = (".java", ".kt", ".kts")


def resolve_jvm_wildcard(
    import_path: str,
    file_paths: list[str],
    extensions: tuple[str, ...] = _JVM_EXTENSIONS,
) -> list[str]:
    """Resolve a JVM wildcard import (``com.example.*``) to all matching files.

    Only files *directly* inside the package directory are returned; files in
    sub-packages are excluded because they belong to separate packages.

    Args:
        import_path: Dotted import path ending with ``.*`` (e.g. ``com.example.util.*``).
        file_paths: All repo-relative file paths.
        extensions: File extensions to include.

    Returns:
        List of repo-relative file paths inside the package directory.
    """
    package_path = import_path[:-2].replace(".", "/")
    pkg_suffix = "/" + package_path + "/"
    pkg_prefix = package_path + "/"
    matches: list[str] = []

    for fp in file_paths:
        if not any(fp.endswith(ext) for ext in extensions):
            continue

        normalized = fp.replace("\\", "/")
        idx = normalized.rfind(pkg_suffix)
        if idx >= 0:
            after_pkg = normalized[idx + len(pkg_suffix):]
        elif normalized.startswith(pkg_prefix):
            after_pkg = normalized[len(pkg_prefix):]
        else:
            continue

        if "/" not in after_pkg:
            matches.append(fp)

    return matches


def _resolve_jvm_member(
    import_path: str,
    file_paths: list[str],
    extensions: tuple[str, ...],
) -> str | None:
    """Resolve a member/static import by stripping the member name.

    Handles ``com.example.Constants.VALUE`` → ``com/example/Constants.java``.
    The last segment is considered a member name when it starts with a lowercase
    letter, is ALL_CAPS (constant), or is ``*`` (wildcard member import).

    Args:
        import_path: Dotted import path (no trailing ``.*`` wildcard).
        file_paths: All repo-relative file paths.
        extensions: File extensions to search.

    Returns:
        First matching repo-relative file path, or ``None``.
    """
    segments = import_path.split(".")
    if len(segments) < 3:
        return None

    last_seg = segments[-1]
    is_member = (
        last_seg == "*"
        or (last_seg and last_seg[0].islower())
        or last_seg.isupper()
    )
    if not is_member:
        return None

    class_path = "/".join(segments[:-1])
    class_suffix_lower = "/" + class_path.lower() + "."

    for fp in file_paths:
        for ext in extensions:
            candidate_suffix = "/" + class_path + ext
            normalized = "/" + fp.replace("\\", "/")
            if normalized.endswith(candidate_suffix) or normalized.lower().endswith(
                class_suffix_lower + ext.lstrip(".")
            ):
                return fp

    return None


def _resolve_direct(
    import_path: str,
    file_paths: list[str],
    extensions: tuple[str, ...],
) -> str | None:
    """Resolve a dotted class import directly to a file.

    Converts dots to slashes and searches for an exact suffix match.

    Args:
        import_path: Dotted class import (e.g. ``com.example.User``).
        file_paths: All repo-relative file paths.
        extensions: File extensions to search.

    Returns:
        First matching repo-relative file path, or ``None``.
    """
    class_path = import_path.replace(".", "/")
    for fp in file_paths:
        for ext in extensions:
            if fp.replace("\\", "/").endswith("/" + class_path + ext) or fp.replace(
                "\\", "/"
            ) == class_path + ext:
                return fp
    return None


def resolve(
    file_path: str,
    import_source: str,
    language: str,
    repo_root: str,
    file_paths: list[str],
) -> str | None:
    """Resolve a Java or Kotlin import to a repo-relative file path.

    Resolution order:

    1. Wildcard (``.*``) — returns the first file in the matching package
       directory (use :func:`resolve_jvm_wildcard` for the full list).
    2. Member/static import — strips the member name and resolves the class.
    3. Direct class import — converts dots to slashes and suffix-matches.

    Kotlin additionally searches ``.java`` files to support Java interop.

    Args:
        file_path: Unused; present for interface conformance.
        import_source: Raw JVM import string.
        language: ``"java"`` or ``"kotlin"`` (case-insensitive).
        repo_root: Unused; present for interface conformance.
        file_paths: All repo-relative paths for existence checks.

    Returns:
        Repo-relative file path, or ``None``.
    """
    is_kotlin = language.lower() == "kotlin"
    primary_exts = _KOTLIN_EXTENSIONS if is_kotlin else _JAVA_EXTENSIONS
    fallback_exts = _JAVA_EXTENSIONS if is_kotlin else ()

    if import_source.endswith(".*"):
        result = resolve_jvm_wildcard(import_source, file_paths, primary_exts)
        if not result and fallback_exts:
            result = resolve_jvm_wildcard(import_source, file_paths, fallback_exts)
        return result[0] if result else None

    # Member import.
    member = _resolve_jvm_member(import_source, file_paths, primary_exts)
    if not member and fallback_exts:
        member = _resolve_jvm_member(import_source, file_paths, fallback_exts)
    if member:
        return member

    # Kotlin top-level function imports: 2-segment paths with a lowercase last segment.
    if is_kotlin:
        segments = import_source.split(".")
        if len(segments) >= 2 and segments[-1] and segments[-1][0].islower():
            pkg_wildcard = ".".join(segments[:-1]) + ".*"
            dir_files = resolve_jvm_wildcard(pkg_wildcard, file_paths, primary_exts)
            if not dir_files:
                dir_files = resolve_jvm_wildcard(pkg_wildcard, file_paths, _JAVA_EXTENSIONS)
            if dir_files:
                return dir_files[0]

    # Direct class resolution.
    direct = _resolve_direct(import_source, file_paths, primary_exts)
    if not direct and fallback_exts:
        direct = _resolve_direct(import_source, file_paths, fallback_exts)
    return direct
