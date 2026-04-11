"""Base interface for per-language import resolvers."""

from typing import Protocol


class ImportResolver(Protocol):
    """Protocol for language-specific import resolvers."""

    def resolve(
        self,
        file_path: str,
        import_source: str,
        language: str,
        repo_root: str,
        file_paths: list[str],
    ) -> str | None:
        """Resolve an import source to an actual file path in the repo.

        Args:
            file_path: The file that contains the import statement (repo-relative,
                forward slashes).
            import_source: The raw import string as it appears in source code.
            language: Language identifier (e.g. ``"python"``, ``"typescript"``).
            repo_root: Absolute path to the repository root on disk. Passed for
                context; resolvers operate on repo-relative paths only.
            file_paths: Complete list of repo-relative file paths (forward slashes)
                used for existence checks.

        Returns:
            A repo-relative file path with forward slashes if the import resolves
            to a known file, or ``None`` if no match can be found.
        """
        ...


def resolve(
    file_path: str,
    import_source: str,
    language: str,
    repo_root: str,
    file_paths: list[str],
) -> str | None:
    """Resolve an import source to an actual file path in the repo.

    This is the canonical signature shared by every language resolver module.

    Args:
        file_path: Repo-relative path of the importing file (forward slashes).
        import_source: Raw import string as it appears in source code.
        language: Language identifier string.
        repo_root: Absolute on-disk path to the repository root.
        file_paths: All repo-relative file paths for existence checks.

    Returns:
        Repo-relative resolved file path, or ``None``.
    """
    raise NotImplementedError
