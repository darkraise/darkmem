from __future__ import annotations

import logging
from pathlib import Path

from app.services.code_parser import ExtractedCall
from app.services.symbol_table import CALLABLE_KINDS, SymbolEntry, SymbolTable

logger = logging.getLogger(__name__)

CONFIDENCE = {
    "same-file": 0.95,
    "import-scoped": 0.90,
    "interface-dispatch": 0.70,
    "global": 0.50,
}

BUILTIN_SKIP = {
    "print", "len", "range", "str", "int", "float", "bool", "list", "dict",
    "set", "tuple", "type", "super", "isinstance", "hasattr", "getattr",
    "setattr", "open", "enumerate", "zip", "map", "filter", "sorted",
    "reversed", "min", "max", "sum", "any", "all", "abs", "round", "input",
    "format", "repr", "id", "hash", "next", "iter", "vars", "dir", "help",
    "hex", "oct", "bin", "ord", "chr", "ascii", "staticmethod",
    "classmethod", "property",
    "require", "console", "setTimeout", "setInterval", "fetch", "JSON",
    "Object", "Array", "String", "Number", "Boolean", "Promise", "Error",
    "Math", "Date", "RegExp", "Map", "Set", "Symbol", "parseInt",
    "parseFloat", "isNaN", "isFinite", "encodeURIComponent",
    "decodeURIComponent", "alert", "confirm", "prompt",
}


class CallResolver:
    def __init__(
        self,
        symbol_table: SymbolTable,
        import_map: dict[str, set[str]],
        type_envs=None,
        named_imports=None,
        wildcard_imports=None,
        named_import_map: dict[str, dict[str, tuple[str, str]]] | None = None,
        wildcard_import_map: dict[str, set[str]] | None = None,
        topological_order: list[str] | None = None,
    ):
        self.symbols = symbol_table
        self.import_map = import_map
        self.type_envs = type_envs or {}
        self.named_imports = named_import_map or named_imports or {}
        self.wildcard_imports = wildcard_import_map or wildcard_imports or {}
        self.topological_order = topological_order
        self._cache: dict[tuple[str, str, str | None], tuple[str, float] | None] = {}

    def resolve(self, call: ExtractedCall, from_file: str) -> tuple[str, float] | None:
        if call.called_name in BUILTIN_SKIP:
            return None

        cache_key = (from_file, call.called_name, getattr(call, "receiver_name", None))
        if cache_key in self._cache:
            return self._cache[cache_key]

        if call.call_form == "member" and call.receiver_name and from_file in self.type_envs:
            env = self.type_envs[from_file]
            receiver_type = env.resolve(call.receiver_name)
            if receiver_type:
                owner_methods = self.symbols.lookup_by_owner(receiver_type, call.called_name)
                filtered = self._filter(owner_methods, call)
                if len(filtered) == 1:
                    result = (filtered[0].node_id, 0.92)
                    self._cache[cache_key] = result
                    return result
                if len(filtered) > 1:
                    interface_hit = self._try_interface_dispatch(filtered, call)
                    if interface_hit:
                        self._cache[cache_key] = interface_hit
                        return interface_hit

        if call.call_form == "member" and call.receiver_name:
            receiver_methods = self.symbols.lookup_by_owner(call.receiver_name, call.called_name)
            filtered = self._filter(receiver_methods, call)
            if len(filtered) == 1:
                result = (filtered[0].node_id, 0.80)
                self._cache[cache_key] = result
                return result

        locals_ = self.symbols.lookup_local(from_file, call.called_name)
        if locals_:
            filtered = self._filter(locals_, call)
            if len(filtered) == 1:
                result = (filtered[0].node_id, CONFIDENCE["same-file"])
                self._cache[cache_key] = result
                return result

        if call.called_name in self.named_imports.get(from_file, {}):
            source_file, exported_name = self.named_imports[from_file][call.called_name]
            alias_candidates = self.symbols.lookup_local(source_file, exported_name)
            if not alias_candidates:
                alias_candidates = self.symbols.lookup_global(exported_name)
                alias_candidates = [c for c in alias_candidates if c.file_path == source_file]
            filtered = self._filter(alias_candidates, call)
            if len(filtered) == 1:
                result = (filtered[0].node_id, CONFIDENCE["import-scoped"])
                self._cache[cache_key] = result
                return result

        imported_files = self.import_map.get(from_file, set())
        candidates = self.symbols.lookup_global(call.called_name)
        import_scoped = [c for c in candidates if c.file_path in imported_files]
        if import_scoped:
            filtered = self._filter(import_scoped, call)
            if len(filtered) == 1:
                result = (filtered[0].node_id, CONFIDENCE["import-scoped"])
                self._cache[cache_key] = result
                return result

        if self.wildcard_imports and from_file in self.wildcard_imports:
            wildcard_files = self.wildcard_imports[from_file]
            wildcard_candidates = [c for c in candidates if c.file_path in wildcard_files]
            if wildcard_candidates:
                filtered = self._filter(wildcard_candidates, call)
                if len(filtered) == 1:
                    result = (filtered[0].node_id, 0.85)
                    self._cache[cache_key] = result
                    return result

        if candidates:
            filtered = self._filter(candidates, call)
            if len(filtered) == 1:
                result = (filtered[0].node_id, CONFIDENCE["global"])
                self._cache[cache_key] = result
                return result

        self._cache[cache_key] = None
        return None

    def _try_interface_dispatch(
        self, candidates: list[SymbolEntry], call: ExtractedCall
    ) -> tuple[str, float] | None:
        """Pick the single interface/abstract declaration among ambiguous candidates."""
        iface_hits = [
            c for c in candidates
            if c.kind in ("method", "function") and c.owner_id is None
        ]
        if len(iface_hits) == 1:
            return (iface_hits[0].node_id, CONFIDENCE["interface-dispatch"])
        return None

    def _filter(self, candidates: list[SymbolEntry], call: ExtractedCall) -> list[SymbolEntry]:
        if call.call_form == "constructor":
            result = [c for c in candidates if c.kind in ("class", "struct", "constructor")]
            if not result:
                result = [c for c in candidates if c.kind in CALLABLE_KINDS]
        else:
            result = [c for c in candidates if c.kind in CALLABLE_KINDS or c.kind == "class"]

        if call.arg_count is not None and len(result) > 1:
            exact_arity = [c for c in result if c.param_count == call.arg_count]
            lenient_arity = [
                c for c in result
                if c.param_count is None
                or c.param_count == call.arg_count
                or abs((c.param_count or 0) - call.arg_count) <= 1
            ]
            if exact_arity:
                result = exact_arity
            elif lenient_arity:
                result = lenient_arity

        return result

    def resolve_chain(self, calls: list[ExtractedCall], from_file: str) -> list[tuple[str, float]]:
        """Resolve a chain of member calls by walking return types."""
        results = []
        current_type = None

        for call in calls:
            if current_type and call.call_form == "member":
                methods = self.symbols.lookup_by_owner(current_type, call.called_name)
                if not methods:
                    methods = [e for e in self.symbols.lookup_global(call.called_name) if e.kind in ("method", "function")]
                filtered = self._filter(methods, call)
                if len(filtered) == 1:
                    results.append((filtered[0].node_id, 0.88))
                    current_type = filtered[0].return_type
                    continue

            result = self.resolve(call, from_file)
            if result:
                results.append(result)
                entry = next(
                    (e for e in self.symbols.lookup_global(call.called_name) if e.node_id == result[0]),
                    None,
                )
                if entry:
                    current_type = entry.return_type
            else:
                current_type = None

        return results


def build_import_map(
    file_paths: list[str],
    file_imports: dict[str, list[str]],
) -> dict[str, set[str]]:
    path_set = set(file_paths)
    path_stems: dict[str, str] = {}
    for fp in file_paths:
        stem = Path(fp).stem
        path_stems[stem] = fp
        parts = fp.replace("\\", "/").split("/")
        for i in range(len(parts)):
            module_name = (
                ".".join(parts[i:])
                .replace("/", ".")
                .removesuffix(".py")
                .removesuffix(".ts")
                .removesuffix(".js")
                .removesuffix(".tsx")
                .removesuffix(".jsx")
            )
            if module_name:
                path_stems[module_name] = fp

    import_map: dict[str, set[str]] = {}
    for file_path, imports in file_imports.items():
        resolved: set[str] = set()
        for imp in imports:
            imp_clean = imp.strip().split(" ")[-1].strip("'\"").strip()
            if imp_clean.startswith("."):
                base_dir = str(Path(file_path).parent)
                relative = (Path(base_dir) / imp_clean).resolve()
                for ext in ("", ".py", ".ts", ".tsx", ".js", ".jsx", "/index.ts", "/index.js"):
                    candidate = str(relative) + ext
                    normalized = candidate.replace("\\", "/")
                    tail = normalized.split("/", 1)[-1] if "/" in normalized else normalized
                    for fp in file_paths:
                        if fp.replace("\\", "/").endswith(tail):
                            resolved.add(fp)
                            break
            else:
                parts = imp_clean.replace("-", "_").replace("/", ".").split(".")
                for i in range(len(parts), 0, -1):
                    key = ".".join(parts[:i])
                    if key in path_stems:
                        resolved.add(path_stems[key])
                        break
        import_map[file_path] = resolved

    return import_map


def build_named_imports(
    file_imports: dict[str, list[str]],
    file_paths: list[str],
) -> dict[str, dict[str, tuple[str, str]]]:
    """Build named import map: file -> {local_name: (source_module, exported_name)}"""
    path_set = set(file_paths)
    result: dict[str, dict[str, tuple[str, str]]] = {}

    for file_path, imports in file_imports.items():
        named: dict[str, tuple[str, str]] = {}
        for imp in imports:
            if "import" in imp and "from" in imp:
                parts = imp.split("import")
                if len(parts) == 2:
                    module = parts[0].replace("from", "").strip()
                    names = parts[1].strip()
                    for name_part in names.split(","):
                        name_part = name_part.strip()
                        if " as " in name_part:
                            exported, local = name_part.split(" as ")
                            named[local.strip()] = (module.strip(), exported.strip())
                        elif name_part:
                            named[name_part] = (module.strip(), name_part)
        if named:
            result[file_path] = named

    return result


def build_wildcard_imports(
    file_imports: dict[str, list[str]],
    file_paths: list[str],
) -> dict[str, set[str]]:
    """Find files that use wildcard imports and map them to source files."""
    result: dict[str, set[str]] = {}
    for file_path, imports in file_imports.items():
        for imp in imports:
            if "import *" in imp or "import *" in imp.replace(" ", ""):
                parts = imp.split("import")
                if len(parts) >= 2:
                    module = parts[0].replace("from", "").strip()
                    for fp in file_paths:
                        if fp.endswith(module.replace(".", "/") + ".py") or fp.endswith(module.replace(".", "/") + "/__init__.py"):
                            result.setdefault(file_path, set()).add(fp)
    return result
