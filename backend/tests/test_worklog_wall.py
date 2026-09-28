"""Spec §7's wall, structurally: the work log and the memory side never import each other."""
from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

from tests._reachability_scan import import_closure, module_path
from tests.test_block_retrieval import VAULT_WRITERS, _attributes_named, _promoting_vault_methods

BACKEND = Path(__file__).resolve().parent.parent

WORKLOG_MODULES = frozenset({
    "app.services.worklog",
    "app.services.worklog_embeddings",
    "app.services.worklog_cleanup",
    "app.models.worklog",
    "app.schemas.worklog",
    "app.api.routes.worklog",
})

MEMORY_SIDE = (
    "app.services.pipeline",
    "app.services.hybrid_search",
    "app.services.layer_composition",
    "app.services.chat",
)


@pytest.mark.parametrize("seed", MEMORY_SIDE + VAULT_WRITERS)
def test_no_memory_or_vault_module_reaches_the_work_log(seed):
    reached = import_closure(BACKEND, seed) & WORKLOG_MODULES
    assert not reached, f"{seed} reaches {sorted(reached)} — the work log is walled off (spec §7)"


# The route module is transport: it reaches the fact repository only through
# the auth layer every router shares, and holds no logic of its own.
WORKLOG_SERVICE_LAYER = WORKLOG_MODULES - {"app.api.routes.worklog"}


@pytest.mark.parametrize("module", sorted(WORKLOG_SERVICE_LAYER))
def test_the_work_log_service_layer_reaches_neither_the_pipeline_nor_the_vault(module):
    forbidden = {"app.services.pipeline", *VAULT_WRITERS} & import_closure(BACKEND, module)
    assert not forbidden, f"{module} reaches {sorted(forbidden)}"


WORKLOG_TABLES = ("workstreams", "worklog_entries")

# SQL that touches a work-log table, not prose that names one: the MCP tool
# `worklog_entries` shares the table's name, and `app.services.prompt` -- in
# the pipeline's and chat's closure -- must name every tool.
_WORKLOG_TABLE_SQL = re.compile(
    rf"\b(?:from|join|into|update|table|truncate)\s+(?:{'|'.join(WORKLOG_TABLES)})\b",
    re.IGNORECASE,
)


def _names_a_worklog_table(source: str) -> bool:
    return _WORKLOG_TABLE_SQL.search(source) is not None


def test_the_table_scan_ignores_the_tool_that_shares_a_table_name():
    assert not _names_a_worklog_table(
        "- **worklog_workstreams** / **worklog_entries** — list a project's workstreams"
    )
    assert _names_a_worklog_table("DELETE FROM workstreams WHERE id = :id")


def test_every_scan_seed_resolves_to_a_file():
    """import_closure returns an unresolvable seed alone, which would pass every scan."""
    for seed in (*MEMORY_SIDE, *VAULT_WRITERS, *WORKLOG_MODULES):
        assert module_path(seed, BACKEND) is not None, f"{seed} moved — re-point the wall"


@pytest.mark.parametrize("seed", MEMORY_SIDE + VAULT_WRITERS)
def test_no_memory_or_vault_module_names_a_work_log_table(seed):
    """Raw SQL is invisible to the import scan, so the table names are scanned too."""
    for module in sorted(import_closure(BACKEND, seed) - WORKLOG_MODULES):
        path = module_path(module, BACKEND)
        if path is not None:
            assert not _names_a_worklog_table(path.read_text(encoding="utf-8")), (
                f"{module}, reached from {seed}, names a work-log table"
            )


def test_the_table_scan_sees_a_planted_query():
    assert _names_a_worklog_table("text('SELECT body FROM worklog_entries')")
    assert not _names_a_worklog_table("object_type = 'workstream'")


@pytest.mark.parametrize("module", sorted(WORKLOG_MODULES))
def test_no_work_log_module_can_write_or_promote_a_fact(module):
    source = module_path(module, BACKEND).read_text(encoding="utf-8")
    named = _attributes_named(source) & _promoting_vault_methods()
    assert not named, f"{module} names vault methods {sorted(named)}"


def test_the_method_scan_sees_a_planted_call():
    promoting = _promoting_vault_methods()
    planted = next(iter(sorted(promoting)))
    assert _attributes_named(f"repository.{planted}(fact)") & promoting == {planted}


def test_the_scan_sees_an_import_hidden_in_a_function(tmp_path):
    """Negative control: a function-level import must count, or the wall is decorative."""
    services = tmp_path / "app" / "services"
    services.mkdir(parents=True)
    (tmp_path / "app" / "__init__.py").write_text("")
    (services / "__init__.py").write_text("")
    (services / "alpha.py").write_text("def later():\n    from app.services import beta\n")
    (services / "beta.py").write_text("")
    assert "app.services.beta" in import_closure(tmp_path, "app.services.alpha")


# The registry names every family because it creates every family's child
# tables; no other module on the memory side has a reason to.
_FAMILY_REGISTRY = "app.services.embedder_registry"


def _names_the_worklog_family(source: str) -> bool:
    return "worklog_embeddings" in source


@pytest.mark.parametrize("seed", MEMORY_SIDE + VAULT_WRITERS)
def test_no_memory_or_vault_module_names_the_work_log_vector_family(seed):
    for module in sorted(import_closure(BACKEND, seed) - WORKLOG_MODULES - {_FAMILY_REGISTRY}):
        path = module_path(module, BACKEND)
        if path is not None:
            assert not _names_the_worklog_family(path.read_text(encoding="utf-8")), (
                f"{module}, reached from {seed}, names the worklog_embeddings family"
            )


def test_the_family_scan_sees_a_planted_name():
    assert _names_the_worklog_family("child_table('worklog_embeddings', fingerprint)")
    assert not _names_the_worklog_family("child_table('page_embeddings', fingerprint)")


# worklog_search never returns a memory (spec §7). SQL lives in string
# literals; docstrings are excluded because they carry prose such as "kept
# apart from memories", which is not a query.
_MEMORY_TABLE_SQL = re.compile(
    r"\b(?:from|join|into|update|table)\s+(?:\w+\.)?memor(?:ies|y_\w+)\b", re.IGNORECASE
)


def _code_strings(source: str) -> list[str]:
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            first = node.body[0] if node.body else None
            if (
                isinstance(first, ast.Expr)
                and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)
            ):
                docstrings.add(id(first.value))
    return [
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings
    ]


def _queries_a_memory_table(source: str) -> bool:
    return any(_MEMORY_TABLE_SQL.search(value) for value in _code_strings(source))


@pytest.mark.parametrize("module", sorted(WORKLOG_MODULES))
def test_no_work_log_module_reads_a_memory_table(module):
    source = module_path(module, BACKEND).read_text(encoding="utf-8")
    assert not _queries_a_memory_table(source), f"{module} queries a memory table"
    assert "memory_embeddings" not in source, f"{module} names the memory vector family"


def test_the_memory_scan_sees_a_planted_query():
    assert _queries_a_memory_table("q = 'select * from memories'")
    assert _queries_a_memory_table("q = 'SELECT * FROM public.memories'")
    assert _queries_a_memory_table("q = f'JOIN memory_tags mt ON mt.memory_id = {x}'")
    assert not _queries_a_memory_table('"""Kept apart from memories."""\nx = 1')


# Spec §7 as amended 2026-09-25: a scan for every repository method name
# cannot tell `session.get` from a repository's `get`, so the rule is stated
# on the names any fact read would need.
_FACT_STORE = re.compile(r"KnowledgeTripleRepository|knowledge_triples")


@pytest.mark.parametrize("module", sorted(WORKLOG_MODULES))
def test_no_work_log_module_names_the_fact_store(module):
    source = module_path(module, BACKEND).read_text(encoding="utf-8")
    assert not _FACT_STORE.search(source), f"{module} names the fact store"


def test_the_fact_store_scan_sees_a_planted_read():
    assert _FACT_STORE.search(
        "from app.repositories.knowledge_triples import KnowledgeTripleRepository"
    )
    assert _FACT_STORE.search("SELECT subject FROM knowledge_triples")
    assert not _FACT_STORE.search("await session.get(Workstream, workstream_id)")


# The SQL-literal scan above cannot see an ORM read such as select(Memory),
# so the models behind the memory tables are refused at the import.
_MEMORY_MODELS_MODULE = "app.models.memory"
_MEMORY_MODEL_NAMES = frozenset({"Memory", "MemoryBuffer", "Tag", "memory_tags", "memory"})


def _imports_a_memory_model(source: str, package: str) -> bool:
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            if any(alias.name.startswith(_MEMORY_MODELS_MODULE) for alias in node.names):
                return True
        elif isinstance(node, ast.ImportFrom):
            base = package.split(".")[: len(package.split(".")) - node.level + 1] if node.level else []
            target = ".".join([*base, *([node.module] if node.module else [])])
            if target.startswith(_MEMORY_MODELS_MODULE):
                return True
            if target == "app.models" and any(a.name in _MEMORY_MODEL_NAMES for a in node.names):
                return True
    return False


@pytest.mark.parametrize("module", sorted(WORKLOG_SERVICE_LAYER))
def test_no_work_log_module_imports_a_memory_model(module):
    for reached in sorted(import_closure(BACKEND, module) | {module}):
        path = module_path(reached, BACKEND)
        if path is None:
            continue
        package = reached if path.name == "__init__.py" else reached.rpartition(".")[0]
        assert not _imports_a_memory_model(path.read_text(encoding="utf-8"), package), (
            f"{reached}, reached from {module}, imports a memory model"
        )


def test_the_model_scan_sees_a_planted_import():
    assert _imports_a_memory_model("from app.models import Memory", "app.services")
    assert _imports_a_memory_model("from app.models.memory import Tag", "app.services")
    assert _imports_a_memory_model("import app.models.memory", "app.services")
    assert _imports_a_memory_model("from .memory import Memory", "app.models")
    assert _imports_a_memory_model("from ..models import MemoryBuffer", "app.services")
    assert not _imports_a_memory_model("from app.models import Workstream", "app.services")
    assert not _imports_a_memory_model("from .worklog import WorklogEntry", "app.models")
