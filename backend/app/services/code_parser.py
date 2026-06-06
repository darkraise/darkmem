from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

try:
    from tree_sitter import Language, Parser, Node, Query, QueryCursor
    TREE_SITTER_AVAILABLE = True
except ImportError:
    TREE_SITTER_AVAILABLE = False

_GRAMMAR_MODULES: dict[str, str] = {
    "python": "tree_sitter_python",
    "javascript": "tree_sitter_javascript",
    "typescript": "tree_sitter_typescript",
    "go": "tree_sitter_go",
    "rust": "tree_sitter_rust",
    "csharp": "tree_sitter_c_sharp",
    "cpp": "tree_sitter_cpp",
    "c": "tree_sitter_c",
    "java": "tree_sitter_java",
    "ruby": "tree_sitter_ruby",
    "php": "tree_sitter_php",
    "bash": "tree_sitter_bash",
    "html": "tree_sitter_html",
    "css": "tree_sitter_css",
    "json": "tree_sitter_json",
    "scala": "tree_sitter_scala",
    "haskell": "tree_sitter_haskell",
    "kotlin": "tree_sitter_kotlin",
    "swift": "tree_sitter_swift",
    "lua": "tree_sitter_lua",
    "toml": "tree_sitter_toml",
    "yaml": "tree_sitter_yaml",
    "sql": "tree_sitter_sql",
    "julia": "tree_sitter_julia",
    "ocaml": "tree_sitter_ocaml",
    "zig": "tree_sitter_zig",
    "elixir": "tree_sitter_elixir",
    "xml": "tree_sitter_xml",
    "regex": "tree_sitter_regex",
    "cmake": "tree_sitter_cmake",
    "make": "tree_sitter_make",
    "objc": "tree_sitter_objc",
    "markdown": "tree_sitter_markdown",
}

_loaded_languages: dict[str, object] = {}
_failed_languages: set[str] = set()

EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".pyi": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".mjs": "javascript",
    ".cjs": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".cs": "csharp",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
    ".h": "cpp",
    ".c": "c",
    ".java": "java",
    ".rb": "ruby",
    ".php": "php",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".html": "html",
    ".htm": "html",
    ".css": "css",
    ".scss": "css",
    ".json": "json",
    ".scala": "scala",
    ".sc": "scala",
    ".hs": "haskell",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".swift": "swift",
    ".lua": "lua",
    ".toml": "toml",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".sql": "sql",
    ".jl": "julia",
    ".ml": "ocaml",
    ".mli": "ocaml",
    ".zig": "zig",
    ".ex": "elixir",
    ".exs": "elixir",
    ".xml": "xml",
    ".svg": "xml",
    ".cmake": "cmake",
    ".m": "objc",
    ".md": "markdown",
    ".markdown": "markdown",
    "Makefile": "make",
    "Dockerfile": "bash",
    "CMakeLists.txt": "cmake",
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

# Body wrappers that tree-sitter inserts between a class/function node and its
# nested symbols (methods, nested functions, nested classes). Methods are NOT
# direct children of the class node — they live one level down under the body —
# so nested-symbol collection must recurse through these.
BODY_CONTAINER_TYPES: set[str] = {
    "block",
    "statement_block",
    "declaration_list",
    "class_body",
    "interface_body",
    "enum_body",
    "object_type",
    "field_declaration_list",
    "compound_statement",
}

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
    return_type: str | None = None


@dataclass
class ExtractedImport:
    source: str
    names: list[str]


@dataclass
class ExtractedCall:
    called_name: str
    call_form: str
    receiver_name: str | None = None
    arg_count: int | None = None
    line: int = 0


@dataclass
class ExtractedHeritage:
    symbol_name: str
    base_name: str
    relation: str  # "extends" or "implements"


@dataclass
class ExtractedProperty:
    name: str
    owner_name: str
    type_annotation: str | None = None
    line: int = 0
    visibility: str | None = None
    is_static: bool = False


@dataclass
class ExtractedRoute:
    path: str
    method: str | None = None
    handler_name: str = ""
    kind: str = "route"  # "route", "tool", "query"
    framework: str | None = None
    line: int = 0


@dataclass
class ParseResult:
    language: str
    symbols: list[ExtractedSymbol]
    imports: list[ExtractedImport]
    chunks: list[dict]
    calls: list[ExtractedCall] = field(default_factory=list)
    heritage: list[ExtractedHeritage] = field(default_factory=list)
    properties: list[ExtractedProperty] = field(default_factory=list)
    routes: list[ExtractedRoute] = field(default_factory=list)


def detect_language(file_path: str) -> str | None:
    basename = os.path.basename(file_path)
    if basename in EXTENSION_TO_LANGUAGE:
        return EXTENSION_TO_LANGUAGE[basename]
    _, ext = os.path.splitext(file_path)
    return EXTENSION_TO_LANGUAGE.get(ext.lower())


def _get_language(lang_name: str) -> "Language | None":
    if not TREE_SITTER_AVAILABLE:
        return None

    if lang_name in _loaded_languages:
        return _loaded_languages[lang_name]

    if lang_name in _failed_languages:
        return None

    module_name = _GRAMMAR_MODULES.get(lang_name)
    if module_name is None:
        return None

    try:
        import importlib
        mod = importlib.import_module(module_name)
        if lang_name == "typescript":
            lang = Language(mod.language_typescript())
        elif lang_name == "php":
            lang = Language(mod.language_php())
        elif hasattr(mod, "language"):
            lang = Language(mod.language())
        else:
            logger.warning("Grammar module %s has no language() function", module_name)
            _failed_languages.add(lang_name)
            return None
        _loaded_languages[lang_name] = lang
        return lang
    except ImportError:
        logger.debug("Grammar package %s not installed, skipping %s", module_name, lang_name)
        _failed_languages.add(lang_name)
        return None
    except Exception as exc:
        logger.warning("Failed to load tree-sitter language %s: %s", lang_name, exc)
        _failed_languages.add(lang_name)
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

    calls = extract_calls(tree, source, lang_name, file_path)
    heritage = extract_heritage(tree, source, lang_name)
    properties = extract_properties(symbols, tree, source, lang_name)
    routes = extract_routes(tree, source, lang_name, file_path)
    chunks = _build_chunks(symbols, content, file_path)
    return ParseResult(
        language=lang_name,
        symbols=symbols,
        imports=imports,
        chunks=chunks,
        calls=calls,
        heritage=heritage,
        properties=properties,
        routes=routes,
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


def _collect_nested_symbols(node: "Node", source: bytes) -> list["ExtractedSymbol"]:
    """Collect symbols nested under ``node``, descending through body wrappers.

    A symbol child is extracted directly; a body wrapper (the ``block`` /
    ``class_body`` etc. that holds a class's methods or a function's nested
    defs) is recursed into so the methods/nested symbols one level down are
    captured rather than silently dropped.
    """
    collected: list[ExtractedSymbol] = []
    for child in node.children:
        if child.type in SYMBOL_NODE_TYPES:
            sym = _extract_symbol(child, source)
            if sym:
                collected.append(sym)
        elif child.type in BODY_CONTAINER_TYPES or child.type == "decorated_definition":
            # tree-sitter wraps a decorated def/class in ``decorated_definition``;
            # the real symbol node sits one level down, so a class's
            # @property/@staticmethod/@pytest.fixture methods are skipped unless
            # we recurse through the wrapper (matching _walk_tree's recursion).
            collected.extend(_collect_nested_symbols(child, source))
    return collected


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

    children = _collect_nested_symbols(node, source)

    return_type = _extract_return_type(node, source)

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
        return_type=return_type,
    )


def _string_literal_text(node: "Node", source: bytes) -> str:
    """Return a string-literal node's inner text, stripped of quotes.

    Tree-sitter exposes the unquoted content as a ``*_fragment`` child;
    fall back to stripping common quote characters off the raw text.
    """
    for child in node.children:
        if child.type.endswith("_fragment"):
            return _get_text(child, source)
    return _get_text(node, source).strip("\"'`")


def _import_specifier_name(node: "Node", source: bytes) -> str:
    """Original (pre-alias) name of an import specifier.

    Handles Python ``aliased_import`` (``dotted_name as identifier``) and
    JS/TS ``import_specifier`` (``identifier as identifier``); the first
    named child is the imported symbol, the trailing one is the local alias.
    Downstream binding resolution keys off the original exported name, so we
    return that rather than the alias.
    """
    named = node.named_children
    if named:
        return _get_text(named[0], source)
    return _get_text(node, source)


def _extract_import(node: "Node", source: bytes) -> ExtractedImport | None:
    text = _get_text(node, source).strip()
    if not text:
        return None

    if node.type == "import_from_statement":
        return _extract_python_from_import(node, source, text)
    if node.type == "import_statement":
        return _extract_es_or_python_import(node, source, text)

    # Other grammars (Rust use, Go import_declaration, Java/C# scoped names,
    # C preproc_include, ...) keep the original one-level scan plus raw-text
    # fallback; their consumers only need ``source`` to carry the module path.
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


def _extract_python_from_import(
    node: "Node", source: bytes, text: str
) -> ExtractedImport:
    """``from <module> import a, b as c, *`` (Python ``import_from_statement``).

    The module ``dotted_name`` sits before the ``import`` keyword; every
    ``dotted_name`` / ``aliased_import`` / ``wildcard_import`` after it is an
    imported name. ``source`` always stays the module path.
    """
    module_source = ""
    names: list[str] = []
    seen_import_kw = False

    for child in node.children:
        if child.type == "import":
            seen_import_kw = True
            continue
        if not seen_import_kw:
            if child.type in ("dotted_name", "relative_import"):
                module_source = _get_text(child, source)
            continue
        if child.type == "wildcard_import":
            names.append("*")
        elif child.type in ("dotted_name", "aliased_import"):
            names.append(_import_specifier_name(child, source))
        elif child.type == "import_list":
            for grandchild in child.children:
                if grandchild.type in ("dotted_name", "aliased_import"):
                    names.append(_import_specifier_name(grandchild, source))

    if not names:
        names = [text]
    return ExtractedImport(source=module_source or text, names=names)


def _extract_es_or_python_import(
    node: "Node", source: bytes, text: str
) -> ExtractedImport:
    """``import ...`` statement shared by Python, JS and TS grammars.

    Python uses bare ``dotted_name`` / ``aliased_import`` children (the module
    is also the bound name). JS/TS nest specifiers under
    ``import_clause > named_imports > import_specifier`` with the module in a
    trailing ``string`` literal.
    """
    module_source = ""
    names: list[str] = []
    is_es_module = False

    for child in node.children:
        if child.type == "string":
            is_es_module = True
            module_source = _string_literal_text(child, source)
        elif child.type == "import_clause":
            for grandchild in child.children:
                if grandchild.type == "named_imports":
                    for spec in grandchild.children:
                        if spec.type == "import_specifier":
                            names.append(_import_specifier_name(spec, source))
                elif grandchild.type == "namespace_import":
                    names.append("*")
                elif grandchild.type == "identifier":
                    names.append(_get_text(grandchild, source))
        elif child.type in ("dotted_name", "aliased_import"):
            # Python ``import x`` / ``import a.b.c as abc``: module is the bound name.
            module_source = _get_text(
                child.named_children[0]
                if child.type == "aliased_import" and child.named_children
                else child,
                source,
            )
            names.append(_import_specifier_name(child, source))

    if not names:
        names = [module_source] if (is_es_module and module_source) else [text]
    return ExtractedImport(source=module_source or text, names=names)


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


def _extract_return_type(node: "Node", source: bytes) -> str | None:
    for field_name in ("return_type", "type", "result"):
        ret = node.child_by_field_name(field_name)
        if ret:
            text = _get_text(ret, source).lstrip(": ")
            if text:
                return text
    return None


def extract_return_type_from_signature(signature: str | None, source_code: str | None) -> str | None:
    if not signature and not source_code:
        return None
    text = signature or ""
    if "->" in text:
        return text.split("->")[-1].strip().rstrip(":")
    if source_code:
        first_line = source_code.split("\n")[0]
        if "->" in first_line:
            ret = first_line.split("->")[-1].strip().rstrip(":").rstrip("{").strip()
            if ret:
                return ret
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


# ---------------------------------------------------------------------------
# Call extraction
# ---------------------------------------------------------------------------

CALL_QUERIES: dict[str, str] = {
    "python": """
(call function: (identifier) @call.name) @call
(call function: (attribute attribute: (identifier) @call.name)) @call
""",
    "javascript": """
(call_expression function: (identifier) @call.name) @call
(call_expression function: (member_expression property: (property_identifier) @call.name)) @call
(new_expression constructor: (identifier) @call.name) @call
""",
    "typescript": """
(call_expression function: (identifier) @call.name) @call
(call_expression function: (member_expression property: (property_identifier) @call.name)) @call
(new_expression constructor: (identifier) @call.name) @call
""",
    "go": """
(call_expression function: (identifier) @call.name) @call
(call_expression function: (selector_expression field: (field_identifier) @call.name)) @call
""",
    "rust": """
(call_expression function: (identifier) @call.name) @call
(call_expression function: (field_expression field: (field_identifier) @call.name)) @call
(call_expression function: (scoped_identifier name: (identifier) @call.name)) @call
""",
    "csharp": """
(invocation_expression function: (identifier) @call.name) @call
(invocation_expression function: (member_access_expression name: (identifier) @call.name)) @call
(object_creation_expression type: (identifier) @call.name) @call
""",
    "cpp": """
(call_expression function: (identifier) @call.name) @call
(call_expression function: (field_expression field: (field_identifier) @call.name)) @call
(call_expression function: (qualified_identifier name: (identifier) @call.name)) @call
""",
    "java": """
(method_invocation name: (identifier) @call.name) @call
(method_invocation object: (_) name: (identifier) @call.name) @call
(object_creation_expression type: (type_identifier) @call.name) @call
""",
}

CONSTRUCTOR_NODE_TYPES = {"new_expression", "object_creation_expression", "struct_expression"}
MEMBER_ACCESS_NODE_TYPES = {
    "member_expression", "attribute", "member_access_expression",
    "field_expression", "selector_expression",
}


def extract_calls(tree, source: bytes, language: str, file_path: str) -> list[ExtractedCall]:
    if not TREE_SITTER_AVAILABLE:
        return []

    query_str = CALL_QUERIES.get(language)
    if not query_str:
        return []

    lang_obj = _get_language(language)
    if not lang_obj:
        return []

    try:
        query = Query(lang_obj, query_str)
    except Exception as e:
        logger.debug("Failed to create call query for %s: %s", language, e)
        return []

    cursor = QueryCursor(query)
    matches = cursor.matches(tree.root_node)

    calls: list[ExtractedCall] = []
    for _pattern_idx, match_dict in matches:
        name_nodes = match_dict.get("call.name", [])
        call_nodes = match_dict.get("call", [])

        if not name_nodes:
            continue

        name_node = name_nodes[0]
        call_node = call_nodes[0] if call_nodes else name_node.parent

        called_name = _get_text(name_node, source)
        if not called_name:
            continue

        call_form = _infer_call_form(call_node, name_node, language)

        receiver_name = None
        if call_form == "member":
            receiver_name = _extract_receiver_name(name_node, source, language)

        arg_count = _count_args(call_node, language)

        calls.append(ExtractedCall(
            called_name=called_name,
            call_form=call_form,
            receiver_name=receiver_name,
            arg_count=arg_count,
            line=name_node.start_point[0] + 1,
        ))

    return calls


def _infer_call_form(call_node, name_node, language: str) -> str:
    if call_node.type in CONSTRUCTOR_NODE_TYPES:
        return "constructor"
    parent = name_node.parent
    if parent and parent.type in MEMBER_ACCESS_NODE_TYPES:
        return "member"
    if call_node.type == "method_invocation" and call_node.child_by_field_name("object"):
        return "member"
    return "free"


def _extract_receiver_name(name_node, source: bytes, language: str) -> str | None:
    parent = name_node.parent
    if not parent:
        return None

    receiver = (
        parent.child_by_field_name("object")
        or parent.child_by_field_name("value")
        or parent.child_by_field_name("operand")
    )

    if not receiver:
        if parent.parent and parent.parent.type == "method_invocation":
            receiver = parent.parent.child_by_field_name("object")

    if receiver and receiver.type in ("identifier", "simple_identifier", "this", "self"):
        return _get_text(receiver, source)

    return None


def _count_args(call_node, language: str) -> int | None:
    for child in call_node.children:
        if child.type in ("arguments", "argument_list"):
            return len([c for c in child.children if c.is_named and c.type != "comment"])
    return None


# ---------------------------------------------------------------------------
# Heritage extraction (extends / implements)
# ---------------------------------------------------------------------------

def extract_heritage(tree, source: bytes, language: str) -> list[ExtractedHeritage]:
    if not TREE_SITTER_AVAILABLE:
        return []
    results: list[ExtractedHeritage] = []

    def walk(node):
        # Python
        if language == "python" and node.type == "class_definition":
            class_name = None
            for child in node.children:
                if child.type == "identifier":
                    class_name = _get_text(child, source)
                if child.type == "argument_list" and class_name:
                    for arg in child.children:
                        if arg.type in ("identifier", "attribute"):
                            base = _get_text(arg, source)
                            if base and base not in ("object", "ABC"):
                                results.append(ExtractedHeritage(class_name, base, "extends"))
                        elif arg.type == "keyword_argument":
                            value = arg.child_by_field_name("value")
                            if value and value.type in ("identifier", "attribute"):
                                base = _get_text(value, source)
                                if base and base not in ("object", "ABC"):
                                    results.append(ExtractedHeritage(class_name, base, "extends"))

        # TypeScript/JavaScript
        if language in ("typescript", "javascript") and node.type == "class_declaration":
            class_name = None
            for child in node.children:
                if child.type in ("type_identifier", "identifier"):
                    class_name = _get_text(child, source)
                if child.type == "class_heritage" and class_name:
                    for clause in child.children:
                        if clause.type == "extends_clause":
                            for val in clause.children:
                                if val.type in ("identifier", "type_identifier"):
                                    results.append(ExtractedHeritage(class_name, _get_text(val, source), "extends"))
                        if clause.type == "implements_clause":
                            for val in clause.children:
                                if val.type in ("identifier", "type_identifier"):
                                    results.append(ExtractedHeritage(class_name, _get_text(val, source), "implements"))

        # Java/C#
        if language in ("java", "csharp") and node.type == "class_declaration":
            class_name = None
            for child in node.children:
                if child.type in ("identifier", "name"):
                    class_name = _get_text(child, source)
                if class_name:
                    sc = child if child.type == "superclass" else node.child_by_field_name("superclass")
                    if sc and sc.type == "superclass":
                        for t in sc.children:
                            if t.type in ("type_identifier", "identifier"):
                                results.append(ExtractedHeritage(class_name, _get_text(t, source), "extends"))
                    si = node.child_by_field_name("interfaces") or node.child_by_field_name("super_interfaces")
                    if si:
                        for t in si.named_children:
                            if t.type in ("type_identifier", "identifier", "type_list"):
                                for inner in (t.named_children if t.type == "type_list" else [t]):
                                    if inner.type in ("type_identifier", "identifier"):
                                        results.append(ExtractedHeritage(class_name, _get_text(inner, source), "implements"))

        # Rust
        if language == "rust" and node.type == "impl_item":
            trait_name = None
            struct_name = None
            for child in node.children:
                if child.type == "type_identifier":
                    if trait_name is None:
                        trait_name = _get_text(child, source)
                    else:
                        struct_name = _get_text(child, source)
            if trait_name and struct_name:
                results.append(ExtractedHeritage(struct_name, trait_name, "implements"))

        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return results


# ---------------------------------------------------------------------------
# Property extraction (class fields / properties)
# ---------------------------------------------------------------------------

def extract_properties(symbols: list[ExtractedSymbol], tree, source: bytes, language: str) -> list[ExtractedProperty]:
    if not TREE_SITTER_AVAILABLE:
        return []
    results: list[ExtractedProperty] = []

    def walk(node, owner_name: str | None = None):
        if node.type in CLASS_NODE_TYPES:
            name = _extract_name(node, source)
            if name:
                owner_name = name

        if node.type in ("field_definition", "public_field_definition", "field_declaration", "property_declaration") and owner_name:
            for child in node.children:
                if child.type in ("property_identifier", "identifier", "variable_declarator"):
                    prop_name = _get_text(child, source) if child.type != "variable_declarator" else None
                    if child.type == "variable_declarator":
                        for gc in child.children:
                            if gc.type in ("identifier", "name"):
                                prop_name = _get_text(gc, source)
                                break
                    if prop_name:
                        type_ann = None
                        ta = node.child_by_field_name("type") or node.child_by_field_name("type_annotation")
                        if ta:
                            type_ann = _get_text(ta, source)
                        vis = _extract_visibility(node, source)
                        results.append(ExtractedProperty(
                            name=prop_name, owner_name=owner_name,
                            type_annotation=type_ann, line=node.start_point[0] + 1,
                            visibility=vis,
                        ))

        for child in node.children:
            walk(child, owner_name)

    walk(tree.root_node)
    return results


# ---------------------------------------------------------------------------
# Route / tool extraction
# ---------------------------------------------------------------------------

def extract_routes(tree, source: bytes, language: str, file_path: str) -> list[ExtractedRoute]:
    if not TREE_SITTER_AVAILABLE:
        return []
    results: list[ExtractedRoute] = []

    def walk(node):
        # Python decorators: @app.get("/path"), @router.post("/path"), @mcp.tool()
        if language == "python" and node.type == "decorated_definition":
            for child in node.children:
                if child.type == "decorator":
                    dec_text = _get_text(child, source)
                    for method in ("get", "post", "put", "delete", "patch"):
                        if f".{method}(" in dec_text:
                            path = _extract_string_arg(child, source)
                            func_name = _get_decorated_func_name(node, source)
                            if path and func_name:
                                results.append(ExtractedRoute(
                                    path=path, method=method.upper(),
                                    handler_name=func_name, kind="route",
                                    framework="fastapi", line=node.start_point[0] + 1,
                                ))
                    if ".tool(" in dec_text:
                        func_name = _get_decorated_func_name(node, source)
                        if func_name:
                            results.append(ExtractedRoute(
                                path=func_name, method=None,
                                handler_name=func_name, kind="tool",
                                framework="mcp", line=node.start_point[0] + 1,
                            ))

        # JS/TS: app.get("/path", handler), router.post("/path", handler)
        if language in ("typescript", "javascript") and node.type == "call_expression":
            text = _get_text(node, source)
            for method in ("get", "post", "put", "delete", "patch"):
                if f".{method}(" in text.lower():
                    path = _extract_string_arg(node, source)
                    if path and path.startswith("/"):
                        results.append(ExtractedRoute(
                            path=path, method=method.upper(),
                            handler_name="", kind="route",
                            framework="express", line=node.start_point[0] + 1,
                        ))
                    break

        for child in node.children:
            walk(child)

    walk(tree.root_node)
    return results


def _extract_string_arg(node, source: bytes) -> str | None:
    for child in node.children:
        if child.type == "argument_list":
            for arg in child.children:
                if arg.type in ("string", "interpreted_string_literal"):
                    return _get_text(arg, source).strip("\"'`")
        if child.type in ("string", "interpreted_string_literal"):
            return _get_text(child, source).strip("\"'`")
        result = _extract_string_arg(child, source)
        if result:
            return result
    return None


def _get_decorated_func_name(node, source: bytes) -> str | None:
    for child in node.children:
        if child.type in ("function_definition", "function_declaration"):
            return _extract_name(child, source)
    return None
