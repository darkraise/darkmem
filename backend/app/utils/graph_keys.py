"""Consistent key composition/decomposition for code_edges source_key/target_key columns.

Format by kind:
  symbol  → "name::file_path"
  file    → "file_path"
  module  → "name"
  property, route, tool, community, process → "name"
"""

_COMPOSITE_KINDS = frozenset({"symbol"})


def compose_key(kind: str, name: str, file_path: str | None = None) -> str:
    if kind in _COMPOSITE_KINDS and file_path:
        return f"{name}::{file_path}"
    return name


def decompose_key(kind: str, key: str) -> tuple[str, str | None]:
    if kind in _COMPOSITE_KINDS and "::" in key:
        name, file_path = key.split("::", 1)
        return name, file_path
    return key, None
