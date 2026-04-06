import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class TypeBinding:
    name: str
    type_name: str
    source: str  # "annotation", "constructor", "assignment", "parameter"
    scope: str  # "file" or "function:func_name"


class TypeEnvironment:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._bindings: dict[str, list[TypeBinding]] = {}  # scope → bindings

    def add(self, name: str, type_name: str, source: str, scope: str = "file") -> None:
        key = f"{scope}::{name}"
        if key not in self._bindings:
            self._bindings[key] = []
        self._bindings[key].append(TypeBinding(name, type_name, source, scope))

    def resolve(self, name: str, scope: str = "file") -> str | None:
        key = f"{scope}::{name}"
        if key in self._bindings:
            return self._bindings[key][-1].type_name

        file_key = f"file::{name}"
        if file_key in self._bindings:
            return self._bindings[file_key][-1].type_name

        if name in ("self", "this", "$this"):
            return self._resolve_enclosing_class(scope)

        return None

    def _resolve_enclosing_class(self, scope: str) -> str | None:
        if "." in scope:
            return scope.split(".")[-2].split(":")[-1] if ":" in scope else None
        return None


def build_type_env(tree, source: bytes, language: str, file_path: str) -> TypeEnvironment:
    """Build a TypeEnvironment from a parsed tree by extracting type annotations and constructor calls."""
    env = TypeEnvironment(file_path)

    if not tree:
        return env

    _walk_for_types(tree.root_node, source, language, env, "file")
    return env


def _walk_for_types(node, source: bytes, language: str, env: TypeEnvironment, scope: str) -> None:
    current_scope = scope

    if node.type in ("function_definition", "function_declaration", "method_definition", "method_declaration"):
        func_name = None
        for child in node.children:
            if child.type in ("identifier", "property_identifier", "name"):
                func_name = _text(child, source)
                break
        if func_name:
            parent_class = scope.split(":")[-1] if scope.startswith("class:") else ""
            current_scope = f"function:{parent_class}.{func_name}" if parent_class else f"function:{func_name}"
            _extract_params(node, source, language, env, current_scope)

    if node.type in ("class_definition", "class_declaration", "class_specifier"):
        class_name = None
        for child in node.children:
            if child.type in ("identifier", "type_identifier", "name"):
                class_name = _text(child, source)
                break
        if class_name:
            current_scope = f"class:{class_name}"

    if language == "python":
        if node.type == "type" and node.parent and node.parent.type in ("assignment", "expression_statement"):
            _extract_python_typed_assignment(node, source, env, current_scope)

        if node.type == "assignment":
            _extract_constructor_assignment(node, source, env, current_scope)

    if language in ("typescript", "javascript"):
        if node.type in ("variable_declarator", "lexical_declaration"):
            _extract_ts_typed_declaration(node, source, env, current_scope)

    if language in ("java", "csharp"):
        if node.type == "local_variable_declaration":
            _extract_java_typed_declaration(node, source, env, current_scope)

    for child in node.children:
        _walk_for_types(child, source, language, env, current_scope)


def _extract_params(node, source: bytes, language: str, env: TypeEnvironment, scope: str) -> None:
    """Extract parameter type annotations from function definitions."""
    params_node = node.child_by_field_name("parameters")
    if not params_node:
        return

    for param in params_node.children:
        if param.type in ("typed_parameter", "typed_default_parameter"):
            name_node = param.child_by_field_name("name")
            type_node = param.child_by_field_name("type")
            if name_node and type_node:
                name = _text(name_node, source)
                type_name = _text(type_node, source)
                if name and type_name and name != "self":
                    env.add(name, type_name, "parameter", scope)

        elif param.type in ("required_parameter", "optional_parameter"):
            name_node = None
            type_node = param.child_by_field_name("type")
            for child in param.children:
                if child.type in ("identifier", "shorthand_property_identifier_pattern"):
                    name_node = child
                    break
            if name_node and type_node:
                name = _text(name_node, source)
                type_name = _text(type_node, source)
                if name and type_name:
                    env.add(name, type_name, "parameter", scope)

        elif param.type == "formal_parameter":
            type_node = param.child_by_field_name("type")
            name_node = param.child_by_field_name("name")
            if not name_node:
                children = [c for c in param.children if c.type in ("identifier",)]
                if children:
                    name_node = children[-1]
            if type_node and name_node:
                env.add(_text(name_node, source), _text(type_node, source), "parameter", scope)


def _extract_constructor_assignment(node, source: bytes, env: TypeEnvironment, scope: str) -> None:
    """Extract x = ClassName() patterns."""
    left = node.child_by_field_name("left")
    right = node.child_by_field_name("right")

    if not left or not right:
        children = list(node.children)
        if len(children) >= 3:
            left = children[0]
            right = children[2]

    if not left or not right:
        return

    if left.type != "identifier":
        return

    if right.type == "call":
        func = right.child_by_field_name("function")
        if func and func.type == "identifier":
            name = _text(func, source)
            if name and name[0].isupper():
                env.add(_text(left, source), name, "constructor", scope)


def _extract_python_typed_assignment(node, source: bytes, env: TypeEnvironment, scope: str) -> None:
    """Extract x: Type = ... patterns in Python."""
    parent = node.parent
    if not parent:
        return

    for child in parent.children:
        if child.type == "identifier" and child != node:
            var_name = _text(child, source)
            type_name = _text(node, source)
            if var_name and type_name:
                env.add(var_name, type_name, "annotation", scope)
            break


def _extract_ts_typed_declaration(node, source: bytes, env: TypeEnvironment, scope: str) -> None:
    """Extract const x: Type = ... or let x = new Foo() patterns in TypeScript."""
    if node.type == "variable_declarator":
        name_node = node.child_by_field_name("name")
        type_node = node.child_by_field_name("type")
        value_node = node.child_by_field_name("value")

        if name_node:
            name = _text(name_node, source)
            if type_node:
                env.add(name, _text(type_node, source), "annotation", scope)
            elif value_node and value_node.type == "new_expression":
                for child in value_node.children:
                    if child.type in ("identifier", "type_identifier"):
                        env.add(name, _text(child, source), "constructor", scope)
                        break


def _extract_java_typed_declaration(node, source: bytes, env: TypeEnvironment, scope: str) -> None:
    """Extract Type x = ... patterns in Java/C#."""
    type_node = node.child_by_field_name("type")
    if not type_node:
        return
    type_name = _text(type_node, source)

    for child in node.children:
        if child.type == "variable_declarator":
            name_node = child.child_by_field_name("name")
            if name_node:
                env.add(_text(name_node, source), type_name, "annotation", scope)


def propagate_types(type_envs: dict[str, TypeEnvironment], import_map: dict[str, set[str]], symbol_table=None) -> None:
    """Propagate exported type bindings from upstream files to downstream files.

    Uses iterative BFS so upstream files are propagated before downstream consumers.
    """
    max_passes = 3
    for _ in range(max_passes):
        changed = False
        for file_path, env in type_envs.items():
            imported_files = import_map.get(file_path, set())
            for imp_file in imported_files:
                imp_env = type_envs.get(imp_file)
                if not imp_env:
                    continue
                for key, bindings in imp_env._bindings.items():
                    if key.startswith("file::"):
                        name = key.split("::", 1)[1]
                        target_key = f"file::{name}"
                        if target_key not in env._bindings:
                            env._bindings[target_key] = bindings[:]
                            changed = True
        if not changed:
            break


def _text(node, source: bytes) -> str:
    return source[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
