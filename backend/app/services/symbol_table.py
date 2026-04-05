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


CALLABLE_KINDS = {"function", "method", "constructor"}


class SymbolTable:
    def __init__(self):
        self._file_index: dict[str, dict[str, list[SymbolEntry]]] = {}
        self._global_index: dict[str, list[SymbolEntry]] = {}

    def add(self, entry: SymbolEntry) -> None:
        file_map = self._file_index.setdefault(entry.file_path, {})
        file_map.setdefault(entry.name, []).append(entry)
        self._global_index.setdefault(entry.name, []).append(entry)

    def lookup_local(self, file_path: str, name: str) -> list[SymbolEntry]:
        return self._file_index.get(file_path, {}).get(name, [])

    def lookup_global(self, name: str) -> list[SymbolEntry]:
        return self._global_index.get(name, [])

    def lookup_callable(self, name: str) -> list[SymbolEntry]:
        return [e for e in self.lookup_global(name) if e.kind in CALLABLE_KINDS]
