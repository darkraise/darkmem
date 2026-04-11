from __future__ import annotations

from dataclasses import dataclass


@dataclass
class SymbolEntry:
    node_id: str
    file_path: str
    name: str
    kind: str
    param_count: int | None = None
    owner_id: str | None = None
    owner_name: str | None = None
    return_type: str | None = None
    param_types: list[str] | None = None
    declared_type: str | None = None
    is_static: bool = False


CALLABLE_KINDS = {"function", "method", "constructor"}


class SymbolTable:
    def __init__(self):
        self._file_index: dict[str, dict[str, list[SymbolEntry]]] = {}
        self._global_index: dict[str, list[SymbolEntry]] = {}
        self._owner_index: dict[str, dict[str, list[SymbolEntry]]] = {}

    def add(self, entry: SymbolEntry) -> None:
        file_map = self._file_index.setdefault(entry.file_path, {})
        file_map.setdefault(entry.name, []).append(entry)
        self._global_index.setdefault(entry.name, []).append(entry)
        if entry.owner_name:
            owner_map = self._owner_index.setdefault(entry.owner_name, {})
            owner_map.setdefault(entry.name, []).append(entry)

    def lookup_local(self, file_path: str, name: str) -> list[SymbolEntry]:
        return self._file_index.get(file_path, {}).get(name, [])

    def lookup_global(self, name: str) -> list[SymbolEntry]:
        return self._global_index.get(name, [])

    def lookup_callable(self, name: str) -> list[SymbolEntry]:
        return [e for e in self.lookup_global(name) if e.kind in CALLABLE_KINDS]

    def lookup_by_owner(self, owner_name: str, member_name: str) -> list[SymbolEntry]:
        """Find a method/property belonging to a specific class."""
        indexed = self._owner_index.get(owner_name, {}).get(member_name, [])
        if indexed:
            return [e for e in indexed if e.kind in ("method", "function")]

        # Fallback: match by file co-location with the owner class
        owner_files = {
            e.file_path for e in self.lookup_global(owner_name)
            if e.kind in ("class", "struct", "interface", "trait")
        }
        if not owner_files:
            return []
        return [
            e for e in self.lookup_global(member_name)
            if e.kind in ("method", "function") and e.file_path in owner_files
        ]
