"""Spec §7's wall, structurally: the work log and the memory side never import each other."""
from __future__ import annotations

from pathlib import Path

import pytest

import re

from tests._reachability_scan import import_closure, module_path
from tests.test_block_retrieval import VAULT_WRITERS, _attributes_named, _promoting_vault_methods

BACKEND = Path(__file__).resolve().parent.parent

WORKLOG_MODULES = frozenset({
    "app.services.worklog",
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


def test_the_work_log_reaches_neither_the_pipeline_nor_the_vault():
    reached = import_closure(BACKEND, "app.services.worklog")
    forbidden = {"app.services.pipeline", *VAULT_WRITERS} & reached
    assert not forbidden, f"app.services.worklog reaches {sorted(forbidden)}"


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
