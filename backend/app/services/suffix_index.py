"""Suffix-keyed index for O(1) import path resolution."""

from __future__ import annotations

import logging
from pathlib import PurePosixPath

logger = logging.getLogger(__name__)


class SuffixIndex:
    """Maps every suffix of every file path to enable O(1) import lookups.

    For `src/utils/helpers.py`, indexes:
      helpers.py, utils/helpers.py, src/utils/helpers.py,
      helpers, utils.helpers, utils/helpers
    """

    _EXTENSIONS = (
        "", ".py", ".ts", ".js", ".tsx", ".jsx",
        "/index.ts", "/index.js", "/index.tsx", "/index.jsx",
        "/__init__.py",
    )

    def __init__(self, file_paths: list[str]) -> None:
        self._exact: dict[str, list[str]] = {}
        self._lower: dict[str, list[str]] = {}
        self._dir: dict[str, list[str]] = {}
        self._build(file_paths)

    def _build(self, file_paths: list[str]) -> None:
        for fp in file_paths:
            normalized = fp.replace("\\", "/")
            parts = normalized.split("/")

            # Index every path suffix: helpers.py, utils/helpers.py, src/utils/helpers.py
            for i in range(len(parts)):
                suffix = "/".join(parts[i:])
                self._exact.setdefault(suffix, []).append(normalized)
                lower = suffix.lower()
                self._lower.setdefault(lower, []).append(normalized)

            # Strip extension and index dotted module paths
            stem = PurePosixPath(normalized)
            no_ext = str(stem.with_suffix("")) if stem.suffix else normalized
            no_ext_parts = no_ext.split("/")
            for i in range(len(no_ext_parts)):
                # Slash-separated: utils/helpers
                slash_suffix = "/".join(no_ext_parts[i:])
                self._exact.setdefault(slash_suffix, []).append(normalized)
                # Dot-separated: utils.helpers
                dot_suffix = ".".join(no_ext_parts[i:])
                self._exact.setdefault(dot_suffix, []).append(normalized)

            # Directory index
            dir_path = str(PurePosixPath(normalized).parent)
            dir_parts = dir_path.split("/")
            for i in range(len(dir_parts)):
                dir_suffix = "/".join(dir_parts[i:])
                self._dir.setdefault(dir_suffix, []).append(normalized)

    def _resolve_list(self, candidates: list[str]) -> str | None:
        unique = list(dict.fromkeys(candidates))
        if len(unique) == 1:
            return unique[0]
        logger.debug("Ambiguous suffix matches: %s", unique)
        return None

    def lookup(self, import_source: str) -> str | None:
        """Resolve an import source to a file path.

        Returns None if not found or if the suffix is ambiguous (multiple files
        share the same suffix — callers should fall back to full-path resolution).
        """
        source = import_source.replace("\\", "/")

        # Try exact match first
        if source in self._exact:
            return self._resolve_list(self._exact[source])

        # Try with extensions
        for ext in self._EXTENSIONS:
            candidate = source + ext
            if candidate in self._exact:
                return self._resolve_list(self._exact[candidate])

        # Case-insensitive fallback
        lower = source.lower()
        if lower in self._lower:
            return self._resolve_list(self._lower[lower])
        for ext in self._EXTENSIONS:
            candidate = lower + ext
            if candidate in self._lower:
                return self._resolve_list(self._lower[candidate])

        return None

    def list_dir(self, dir_source: str) -> list[str]:
        """List files in a directory matching the suffix."""
        return self._dir.get(dir_source.replace("\\", "/"), [])
