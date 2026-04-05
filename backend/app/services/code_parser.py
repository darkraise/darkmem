from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    import tree_sitter_python as tspython
    import tree_sitter_javascript as tsjavascript
    import tree_sitter_typescript as tstypescript
    import tree_sitter_go as tsgo
    import tree_sitter_rust as tsrust
    import tree_sitter_c_sharp as tscsharp
    import tree_sitter_cpp as tscpp
    from tree_sitter import Language, Parser, Node

    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".h": "cpp",
}

FUNCTION_NODE_TYPES: set[str] = {
    "function_definition",
    "function_declaration",
    "method_definition",
    "method_declaration",
    "arrow_function",
    "function_item",
}

CLASS_NODE_TYPES: set[str] = {
    "class_definition",
    "class_declaration",
    "class_specifier",
    "struct_item",
    "struct_specifier",
    "interface_declaration",
    "trait_item",
    "enum_item",
    "enum_declaration",
    "namespace_definition",
    "impl_item",
    "type_alias_declaration",
}

IMPORT_NODE_TYPES: set[str] = {
    "import_statement",
    "import_from_statement",
    "import_declaration",
    "use_declaration",
    "using_directive",
    "preproc_include",
}

KIND_MAP: dict[str, str] = {
    "function_definition": "function",
    "function_declaration": "function",
    "function_item": "function",
    "arrow_function": "function",
    "method_definition": "method",
    "method_declaration": "method",
    "class_definition": "class",
    "class_declaration": "class",
    "class_specifier": "class",
    "struct_item": "struct",
    "struct_specifier": "struct",
    "interface_declaration": "interface",
    "trait_item": "trait",
    "enum_item": "enum",
    "enum_declaration": "enum",
    "namespace_definition": "namespace",
    "impl_item": "impl",
    "type_alias_declaration": "type",
}

SYMBOL_NODE_TYPES = FUNCTION_NODE_TYPES | CLASS_NODE_TYPES

MAX_SYMBOL_LINES = 200
LARGE_WINDOW = 100
LARGE_OVERLAP = 20
LINE_CHUNK_WINDOW = 100
LINE_CHUNK_OVERLAP = 20


@dataclass
class ExtractedSymbol:
    name: str
    kind: str
    line_start: int
    line_end: int
    signature: str | None
    docstring: str | None
    visibility: str | None
    source_code: str
    children: list[ExtractedSymbol] = field(default_factory=list)


@dataclass
class ExtractedImport:
    source: str
    names: list[str]


@dataclass
class ParseResult:
    language: str
    symbols: list[ExtractedSymbol]
    imports: list[ExtractedImport]
    chunks: list[dict]


def detect_language(file_path: str) -> str | None:
    _, ext = os.path.splitext(file_path)
    return EXTENSION_TO_LANGUAGE.get(ext.lower())


def _get_language(lang_name: str) -> "Language | None":
    if not TREE_SITTER_AVAILABLE:
        return None

    loaders: dict[str, object] = {
        "python": lambda: Language(tspython.language()),
        "javascript": lambda: Language(tsjavascript.language()),
        "typescript": lambda: Language(tstypescript.language_typescript()),
        "go": lambda: Language(tsgo.language()),
        "rust": lambda: Language(tsrust.language()),
        "csharp": lambda: Language(tscsharp.language()),
        "cpp": lambda: Language(tscpp.language()),
    }
    loader = loaders.get(lang_name)
    if loader is None:
        return None
    try:
        return loader()
    except Exception as exc:
        logger.warning("Failed to load tree-sitter language %s: %s", lang_name, exc)
        return None


def parse_file(file_path: str, content: str) -> ParseResult | None:
    lang_name = detect_language(file_path)
    if lang_name is None:
        return _fallback_parse(file_path, content)

    if not TREE_SITTER_AVAILABLE:
        logger.debug("tree-sitter not installed, falling back to line-based parsing")
        return _fallback_parse(file_path, content)

    language = _get_language(lang_name)
    if language is None:
        return _fallback_parse(file_path, content)

    parser = Parser(language)
    source = content.encode("utf-8")
    tree = parser.parse(source)

    symbols: list[ExtractedSymbol] = []
    imports: list[ExtractedImport] = []

    _walk_tree(tree.root_node, source, symbols, imports)

    chunks = _build_chunks(symbols, content, file_path)
    return ParseResult(
        language=lang_name,
        symbols=symbols,
        imports=imports,
        chunks=chunks,
    )


def _fallback_parse(file_path: str, content: str) -> ParseResult:
    lang_name = detect_language(file_path) or "unknown"
    chunks = _line_based_chunks(content, file_path)
    return ParseResult(
        language=lang_name,
        symbols=[],
        imports=[],
        chunks=chunks,
    )


def _walk_tree(
    node: "Node",
    source: bytes,
    symbols: list[ExtractedSymbol],
    imports: list[ExtractedImport],
) -> None:
    for child in node.children:
        if child.type in IMPORT_NODE_TYPES:
            imp = _extract_import(child, source)
            if imp:
                imports.append(imp)
        elif child.type in SYMBOL_NODE_TYPES:
            sym = _extract_symbol(child, source)
            if sym:
                symbols.append(sym)
        else:
            _walk_tree(child, source, symbols, imports)


def _extract_symbol(node: "Node", source: bytes) -> ExtractedSymbol | None:
    name = _extract_name(node, source)
    if name is None:
        return None

    kind = KIND_MAP.get(node.type, node.type)
    line_start = node.start_point[0] + 1
    line_end = node.end_point[0] + 1
    signature = _extract_signature(node, source)
    docstring = _find_docstring(node, source)
    visibility = _extract_visibility(node, source)
    source_code = _get_text(node, source)

    children: list[ExtractedSymbol] = []
    for child in node.children:
        if child.type in SYMBOL_NODE_TYPES:
            child_sym = _extract_symbol(child, source)
            if child_sym:
                children.append(child_sym)

    return ExtractedSymbol(
        name=name,
        kind=kind,
        line_start=line_start,
        line_end=line_end,
        signature=signature,
        docstring=docstring,
        visibility=visibility,
        source_code=source_code,
        children=children,
    )


def _extract_import(node: "Node", source: bytes) -> ExtractedImport | None:
    text = _get_text(node, source).strip()
    if not text:
        return None

    names: list[str] = []
    module_source = text

    for child in node.children:
        if child.type == "dotted_name" or child.type == "string":
            module_source = _get_text(child, source)
        elif child.type == "import_specifier" or child.type == "identifier":
            names.append(_get_text(child, source))
        elif child.type in ("import_clause", "named_imports", "import_list"):
            for grandchild in child.children:
                if grandchild.type in ("import_specifier", "identifier", "use_as_clause"):
                    names.append(_get_text(grandchild, source))

    if not names:
        names = [text]

    return ExtractedImport(source=module_source, names=names)


def _get_text(node: "Node", source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _find_docstring(node: "Node", source: bytes) -> str | None:
    prev = node.prev_named_sibling
    if prev and prev.type in ("comment", "block_comment"):
        return _get_text(prev, source).strip()

    if node.child_count == 0:
        return None

    body = None
    for child in node.children:
        if child.type in ("block", "statement_block", "declaration_list"):
            body = child
            break

    target = body if body is not None else node

    if target.named_child_count > 0:
        first = target.named_children[0]
        if first.type == "expression_statement" and first.named_child_count > 0:
            expr = first.named_children[0]
            if expr.type == "string":
                raw = _get_text(expr, source)
                return raw.strip("\"'").strip()
        if first.type in ("comment", "block_comment"):
            return _get_text(first, source).strip()

    return None


def _extract_name(node: "Node", source: bytes) -> str | None:
    for child in node.children:
        if child.type in ("identifier", "name", "type_identifier", "property_identifier"):
            return _get_text(child, source)
    return None


def _extract_signature(node: "Node", source: bytes) -> str | None:
    for child in node.children:
        if child.type in ("parameters", "formal_parameters", "parameter_list", "type_parameters"):
            return _get_text(child, source)
    return None


def _extract_visibility(node: "Node", source: bytes) -> str | None:
    for child in node.children:
        if child.type in ("visibility_modifier", "access_specifier", "accessibility_modifier"):
            return _get_text(child, source)
    if node.type in ("function_definition", "class_definition"):
        name = _extract_name(node, source)
        if name and name.startswith("_"):
            return "private"
    return None


def _build_chunks(
    symbols: list[ExtractedSymbol],
    content: str,
    file_path: str,
) -> list[dict]:
    if not symbols:
        return _line_based_chunks(content, file_path)

    chunks: list[dict] = []
    for sym in symbols:
        line_count = sym.line_end - sym.line_start + 1
        if line_count > MAX_SYMBOL_LINES:
            chunks.extend(_split_large_symbol(sym, file_path))
        else:
            chunks.append({
                "content": sym.source_code,
                "file_path": file_path,
                "symbol_name": sym.name,
                "line_start": sym.line_start,
                "line_end": sym.line_end,
            })
        for child in sym.children:
            child_line_count = child.line_end - child.line_start + 1
            if child_line_count > MAX_SYMBOL_LINES:
                chunks.extend(_split_large_symbol(child, file_path))
            else:
                chunks.append({
                    "content": child.source_code,
                    "file_path": file_path,
                    "symbol_name": child.name,
                    "line_start": child.line_start,
                    "line_end": child.line_end,
                })

    return chunks


def _split_large_symbol(sym: ExtractedSymbol, file_path: str) -> list[dict]:
    lines = sym.source_code.splitlines(keepends=True)
    chunks: list[dict] = []
    start = 0
    while start < len(lines):
        end = min(start + LARGE_WINDOW, len(lines))
        chunk_content = "".join(lines[start:end])
        chunks.append({
            "content": chunk_content,
            "file_path": file_path,
            "symbol_name": sym.name,
            "line_start": sym.line_start + start,
            "line_end": sym.line_start + end - 1,
        })
        if end >= len(lines):
            break
        start += LARGE_WINDOW - LARGE_OVERLAP
    return chunks


def _line_based_chunks(content: str, file_path: str) -> list[dict]:
    lines = content.splitlines(keepends=True)
    if not lines:
        return []

    chunks: list[dict] = []
    start = 0
    while start < len(lines):
        end = min(start + LINE_CHUNK_WINDOW, len(lines))
        chunk_content = "".join(lines[start:end])
        chunks.append({
            "content": chunk_content,
            "file_path": file_path,
            "symbol_name": None,
            "line_start": start + 1,
            "line_end": end,
        })
        if end >= len(lines):
            break
        start += LINE_CHUNK_WINDOW - LINE_CHUNK_OVERLAP
    return chunks
