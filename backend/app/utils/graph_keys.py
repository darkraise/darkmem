"""Consistent key composition/decomposition for code_edges source_key/target_key columns.

Format by kind:
  symbol  → "name::file_path" (top-level) or "name::file_path::owner" (a symbol
            nested under an owner — the owner segment disambiguates same-named
            methods of different classes in one file)
  property → "name::file_path::owner", owned like a method, so two classes'
            same-named fields are two nodes and each leaves with its own file
  file    → "file_path"
  module  → "name"
  route, tool, community, process → "name"

Invariant relied on by SQL (heritage split_part, dependent-file lookup): the name
is always segment 1 and the file path always segment 2, so the optional owner
segment is appended LAST and never shifts those two.
"""

_COMPOSITE_KINDS = frozenset({"symbol", "property"})


def compose_key(
    kind: str, name: str, file_path: str | None = None, owner: str | None = None
) -> str:
    if kind in _COMPOSITE_KINDS and file_path:
        if owner:
            return f"{name}::{file_path}::{owner}"
        return f"{name}::{file_path}"
    return name


def split_symbol_key(key: str) -> tuple[str, str | None, str | None]:
    """Decompose a symbol key into (name, file_path, owner).

    Owner is present only for owner-qualified method keys. File paths use '/'
    (never '::'), so splitting on '::' is unambiguous.
    """
    parts = key.split("::")
    name = parts[0]
    file_path = parts[1] if len(parts) > 1 else None
    owner = parts[2] if len(parts) > 2 else None
    return name, file_path, owner


def decompose_key(kind: str, key: str) -> tuple[str, str | None]:
    if kind in _COMPOSITE_KINDS and "::" in key:
        name, file_path, _owner = split_symbol_key(key)
        return name, file_path
    return key, None
