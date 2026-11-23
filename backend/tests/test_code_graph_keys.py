"""Code graph keys that survive re-indexing: property nodes owned by their
file and class, community keys that do not churn, phases 09-10 skipped when
the call graph did not move, and a per-file type environment."""
from __future__ import annotations

import ast
import inspect
import json
import re
import subprocess
import uuid
from pathlib import Path
from uuid import uuid4

from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from app.models.code import Repository
from app.repositories.fact_sources import CODE_SOURCE_KIND, STALE_DETAIL_KEY
from app.services import community_detector, process_tracer
from app.services.citation_reverify import reverify_citations
from app.services.code_pipeline import CodePipeline
from app.services.community_detector import CommunityDetector
from app.services.process_tracer import ProcessTracer, _compute_entry_score
from app.services.repo_manager import RepoManager
from app.utils.leiden import PartitionResult


class _Statements:
    def __init__(self):
        self.seen: list[str] = []

    def __enter__(self):
        event.listen(Engine, "before_cursor_execute", self._capture)
        return self

    def __exit__(self, *exc):
        event.remove(Engine, "before_cursor_execute", self._capture)

    def _capture(self, conn, cursor, statement, parameters, context, executemany):
        if "SAVEPOINT" not in statement.upper():
            self.seen.append(" ".join(statement.split()))

    def matching(self, pattern: str) -> list[str]:
        return [s for s in self.seen if re.search(pattern, s)]


def _git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
        cwd=root, check=True, capture_output=True,
    )


def _write(root: Path, files: dict[str, str]) -> None:
    for rel, content in files.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")


async def _run(session, repo: Repository, *, full: bool = False) -> dict:
    return await CodePipeline(
        session=session, llm=None, vector_repo=None, repo_manager=RepoManager(session),
    ).run(repo.id, full=full, pull=False)


async def _indexed(session, root: Path, files: dict[str, str]) -> Repository:
    _write(root, files)
    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "init")
    repo = Repository(
        name=f"keys-{uuid.uuid4().hex[:8]}", local_path=str(root),
        provider="local", status="ready",
    )
    session.add(repo)
    await session.commit()
    await _run(session, repo)
    return repo


async def _commit_and_run(session, root: Path, repo: Repository, files: dict[str, str]) -> None:
    _write(root, files)
    _git(root, "commit", "-qam", "change")
    await _run(session, repo)


async def _rows(session, sql: str, repo: Repository) -> list:
    return list((await session.execute(text(sql), {"r": repo.id})).all())


CLUSTERED = {
    "x.py": (
        "# v1\n"
        "def a1():\n    return a2()\n\n\n"
        "def a2():\n    return a3()\n\n\n"
        "def a3():\n    return a1()\n"
    ),
    "y.py": (
        "def b1():\n    return b2()\n\n\n"
        "def b2():\n    return b3()\n\n\n"
        "def b3():\n    return b1()\n"
    ),
}


async def test_reindexing_one_file_keeps_another_files_property(session, tmp_path):
    repo = await _indexed(session, tmp_path, {
        "a.ts": 'export class A {\n  name: string = "a";\n}\n',
        "b.ts": 'export class B {\n  name: string = "b";\n}\n',
    })

    await _commit_and_run(session, tmp_path, repo, {
        "a.ts": 'export class A {\n  name: string = "a2";\n}\n',
    })

    properties = {
        row.key: row.properties
        for row in await _rows(
            session,
            "SELECT key, properties FROM code_graph_nodes "
            "WHERE repo_id = :r AND kind = 'property'",
            repo,
        )
    }
    assert set(properties) == {"name::a.ts::A", "name::b.ts::B"}
    dangling = await _rows(session, """
        SELECT e.target_key FROM code_edges e
        WHERE e.repo_id = :r AND e.edge_type = 'has_property'
          AND NOT EXISTS (
              SELECT 1 FROM code_graph_nodes n
              WHERE n.repo_id = e.repo_id AND n.kind = 'property' AND n.key = e.target_key
          )
    """, repo)
    assert dangling == []
    owners = await _rows(
        session,
        "SELECT source_key FROM code_edges WHERE repo_id = :r AND edge_type = 'has_property' "
        "ORDER BY source_key",
        repo,
    )
    assert [row.source_key for row in owners] == ["A::a.ts", "B::b.ts"]


async def test_community_keys_are_stable_across_runs(session, tmp_path, monkeypatch):
    repo = await _indexed(session, tmp_path, CLUSTERED)
    community_sql = (
        "SELECT key FROM code_graph_nodes WHERE repo_id = :r AND kind = 'community' ORDER BY key"
    )
    first = [row.key for row in await _rows(session, community_sql, repo)]
    assert first, "the fixture formed no community"

    with _Statements() as statements:
        await _run(session, repo, full=True)

    assert [row.key for row in await _rows(session, community_sql, repo)] == first
    member_writes = (
        r"INSERT INTO code_edges.*'member_of'|DELETE FROM code_edges.*edge_type = 'member_of'"
    )
    assert statements.matching(member_writes) == []

    # A new cluster whose members sort first renumbers Leiden's communities;
    # the existing communities keep their keys.
    raw: list[list[int]] = []
    real_partition = community_detector.partition_graph

    async def _spy_partition(*args, **kwargs):
        result = await real_partition(*args, **kwargs)
        raw.append(list(result.membership or []))
        return result

    # The detector's node order: the repository's clusterable symbols by key.
    node_sql = (
        "SELECT key FROM code_graph_nodes WHERE repo_id = :r AND kind = 'symbol' "
        "AND properties->>'kind' IN ('function', 'method', 'class', 'interface', 'struct', "
        "'trait') ORDER BY key"
    )

    async def _raw_ids() -> dict[str, int]:
        keys = [row.key for row in await _rows(session, node_sql, repo)]
        return dict(zip(keys, raw[-1], strict=True))

    monkeypatch.setattr(community_detector, "partition_graph", _spy_partition)
    await _run(session, repo, full=True)
    before = await _raw_ids()
    _write(tmp_path, {"a0.py": CLUSTERED["y.py"].replace("b", "c")})
    _git(tmp_path, "add", "a0.py")
    _git(tmp_path, "commit", "-qm", "third cluster")
    with _Statements() as statements:
        await _run(session, repo)
    renumbered = await _raw_ids()
    assert any(renumbered[key] != cid for key, cid in before.items()), (
        "adding a0.py no longer renumbers Leiden's raw communities"
    )
    # The pattern above still names the membership writes a real change makes.
    assert statements.matching(member_writes)
    after = [row.key for row in await _rows(session, community_sql, repo)]
    assert len(after) == len(first) + 1
    assert set(first) <= set(after)


async def test_unchanged_call_graph_skips_phases_nine_and_ten(session, tmp_path, monkeypatch):
    repo = await _indexed(session, tmp_path, CLUSTERED)
    member_sql = (
        "SELECT source_key, target_key FROM code_edges "
        "WHERE repo_id = :r AND edge_type = 'member_of' ORDER BY 1, 2"
    )
    members_before = await _rows(session, member_sql, repo)
    assert members_before
    ran: list[str] = []
    real_detect, real_trace = CommunityDetector.detect, ProcessTracer.trace

    async def _detect(self):
        ran.append("communities")
        return await real_detect(self)

    async def _trace(self, *args, **kwargs):
        ran.append("processes")
        return await real_trace(self, *args, **kwargs)

    monkeypatch.setattr(CommunityDetector, "detect", _detect)
    monkeypatch.setattr(ProcessTracer, "trace", _trace)

    await _commit_and_run(session, tmp_path, repo, {
        "x.py": CLUSTERED["x.py"].replace("# v1", "# v2"),
    })

    assert ran == []
    assert await _rows(session, member_sql, repo) == members_before


async def _layer(session, repo: Repository) -> tuple[list, list]:
    members = await _rows(
        session,
        "SELECT source_key, target_key FROM code_edges "
        "WHERE repo_id = :r AND edge_type = 'member_of' ORDER BY 1, 2",
        repo,
    )
    communities = await _rows(
        session,
        "SELECT key FROM code_graph_nodes WHERE repo_id = :r AND kind = 'community' ORDER BY 1",
        repo,
    )
    return members, communities


async def test_a_graph_with_no_calls_left_keeps_no_community(session, tmp_path):
    repo = await _indexed(session, tmp_path, CLUSTERED)
    assert (await _layer(session, repo))[0]

    await _commit_and_run(session, tmp_path, repo, {
        "x.py": "def a1():\n    return 1\n\n\ndef a2():\n    return 2\n\n\ndef a3():\n    return 3\n",
        "y.py": "def b1():\n    return 1\n\n\ndef b2():\n    return 2\n\n\ndef b3():\n    return 3\n",
    })

    assert await _layer(session, repo) == ([], [])


async def test_a_deleted_file_leaves_its_community_when_clustering_is_unavailable(
    session, tmp_path, monkeypatch,
):
    repo = await _indexed(session, tmp_path, CLUSTERED)
    members, communities = await _layer(session, repo)
    assert len(communities) == 2

    async def _unavailable(*_args, **_kwargs):
        return PartitionResult(membership=None, outcome="unavailable")

    monkeypatch.setattr(community_detector, "partition_graph", _unavailable)
    _git(tmp_path, "rm", "-q", "y.py")
    _git(tmp_path, "commit", "-qm", "drop y")
    await _run(session, repo)

    members_after, communities_after = await _layer(session, repo)
    assert members_after == [m for m in members if "::y.py" not in m.source_key]
    assert len(communities_after) == 1


async def test_a_visibility_change_reruns_the_process_tracer(session, tmp_path, monkeypatch):
    source = (
        "export class Svc {\n"
        "  public run(): number { return this.a() + this.b(); }\n"
        "  a(): number { return this.c(); }\n"
        "  b(): number { return 1; }\n"
        "  c(): number { return 2; }\n"
        "}\n"
    )
    repo = await _indexed(session, tmp_path, {"svc.ts": source})
    ran: list[str] = []
    real_trace = ProcessTracer.trace

    async def _trace(self, *args, **kwargs):
        ran.append("processes")
        return await real_trace(self, *args, **kwargs)

    monkeypatch.setattr(ProcessTracer, "trace", _trace)

    await _commit_and_run(session, tmp_path, repo, {
        "svc.ts": source.replace("public run()", "private run()"),
    })

    assert ran == ["processes"]


async def test_a_decorated_handler_becomes_a_process_entry(session, tmp_path):
    repo = await _indexed(session, tmp_path, {
        "app.py": (
            "def route(fn):\n    return fn\n\n\n"
            "@route\n"
            "def handle():\n    return step_a() + step_b()\n\n\n"
            "def step_a():\n    return step_c()\n\n\n"
            "def step_b():\n    return 1\n\n\n"
            "def step_c():\n    return 2\n"
        ),
    })

    entries = {
        row.source_key
        for row in await _rows(
            session,
            "SELECT source_key FROM code_edges WHERE repo_id = :r AND edge_type = 'entry_point_of'",
            repo,
        )
    }
    assert "handle::app.py" in entries


async def test_type_environment_is_seeded_per_file(session, tmp_path):
    repo = await _indexed(session, tmp_path, {
        "conf.py": (
            "class Settings:\n    def load(self):\n        return 1\n\n\n"
            "def config() -> Settings:\n    return Settings()\n"
        ),
        # A second `load`, so no name-only fallback can pick Settings.load.
        "cache.py": "class Cache:\n    def load(self):\n        return 0\n",
        "other.py": "def run(config):\n    return config.load()\n",
        "user.py": "from conf import config\n\n\ndef go():\n    return config.load()\n",
        "star.py": "from conf import *\n\n\ndef go_star():\n    return config.load()\n",
    })

    callers = {
        row.source_key
        for row in await _rows(
            session,
            "SELECT source_key FROM code_edges WHERE repo_id = :r AND edge_type = 'calls' "
            "AND target_key = 'load::conf.py::Settings'",
            repo,
        )
    }
    assert "go::user.py" in callers
    assert "go_star::star.py" in callers
    assert "run::other.py" not in callers


def test_process_tracer_reads_no_signature():
    source = inspect.getsource(process_tracer)
    assert "signature" not in source
    params = list(inspect.signature(_compute_entry_score).parameters)
    assert params == ["callers", "callees", "func_name", "is_exported"]
    tree = ast.parse(source)
    reads = {
        node.value
        for node in ast.walk(tree)
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
        and "properties->>" in node.value
    }
    assert all("sig" not in sql for sql in reads)

    # A decorated handler is scored on what the pipeline writes onto its
    # node: its call counts, its name and its visibility.
    assert _compute_entry_score(0, 3, "handle", True) > _compute_entry_score(0, 3, "helper", True)
    assert _compute_entry_score(0, 3, "helper", True) > 0


async def _cited_fact(session, repo: Repository, symbol_key: str, commit: str) -> str:
    fact_id = str(uuid4())
    await session.execute(
        text(
            "INSERT INTO knowledge_triples "
            "(id, subject_name, object_name, rel_type, reference_time, fact, "
            " triple_key, project, verification_status) "
            "VALUES (CAST(:id AS uuid), 's', 'o', 'RELATED_TO', now(), 'a fact', "
            "CAST(:id AS text), 'code', 'corroborated')"
        ),
        {"id": fact_id},
    )
    await session.execute(
        text(
            "INSERT INTO fact_sources (id, fact_id, source_kind, source_ref, origin_key, detail) "
            "VALUES (gen_random_uuid(), CAST(:f AS uuid), :kind, CAST(:ref AS text), "
            "CAST(:origin AS text), CAST(:detail AS jsonb))"
        ),
        {
            "f": fact_id, "kind": CODE_SOURCE_KIND, "ref": str(repo.id),
            "origin": f"repo:{repo.id}",
            "detail": json.dumps({
                "commit_sha": commit, "basis": "symbol",
                "file_path": "conf.py", "symbol_key": symbol_key,
            }),
        },
    )
    return fact_id


async def test_citation_symbol_keys_survive_the_rekey(session, tmp_path):
    repo = await _indexed(session, tmp_path, {
        "conf.py": (
            "class Settings:\n    def load(self):\n        return 1\n\n\n"
            "def config() -> Settings:\n    return Settings()\n"
        ),
    })
    commit = (await _rows(
        session, "SELECT last_indexed_commit FROM repositories WHERE id = :r", repo,
    ))[0].last_indexed_commit
    facts = [
        await _cited_fact(session, repo, "Settings::conf.py", commit),
        await _cited_fact(session, repo, "config::conf.py", commit),
    ]

    await _commit_and_run(session, tmp_path, repo, {
        "conf.py": (
            "class Settings:\n    def load(self):\n        return 2\n\n\n"
            "def config() -> Settings:\n    return Settings()\n"
        ),
    })
    await _run(session, repo, full=True)
    outcome = await reverify_citations(session)

    assert outcome.confirmed == 2 and outcome.marked_stale == 0
    for fact_id in facts:
        (detail,) = (await session.execute(
            text("SELECT detail FROM fact_sources WHERE fact_id = CAST(:f AS uuid)"),
            {"f": fact_id},
        )).scalars().all()
        assert STALE_DETAIL_KEY not in detail


_ROUTE_FILE = (
    "from fastapi import APIRouter\n"
    "from helpers import a1, b1, c1, d1\n\n"
    "router = APIRouter()\n\n\n"
    "@router.get(\"/items\")\n"
    "def alpha():\n    return a1()\n\n\n"
    "def beta():\n    return b1()\n\n\n"
    "def gamma():\n    return c1()\n\n\n"
    "def delta():\n    return d1()\n"
)
_HELPERS = "".join(f"def {n}():\n    return 1\n\n\n" for n in ("a1", "b1", "c1", "d1"))


async def test_reordering_functions_reruns_the_process_tracer(session, tmp_path, monkeypatch):
    repo = await _indexed(session, tmp_path, {"api.py": _ROUTE_FILE, "helpers.py": _HELPERS})
    step_sql = (
        "SELECT source_key FROM code_edges WHERE repo_id = :r AND edge_type = 'step_in_process'"
    )
    steps = {row.source_key for row in await _rows(session, step_sql, repo)}
    assert "gamma::api.py" in steps and "delta::api.py" not in steps
    ran: list[str] = []
    real_trace = ProcessTracer.trace

    async def _trace(self, *args, **kwargs):
        ran.append("processes")
        return await real_trace(self, *args, **kwargs)

    monkeypatch.setattr(ProcessTracer, "trace", _trace)

    # Every function moves down a line; their order, and so the tracer's
    # choice of entry functions, does not.
    await _commit_and_run(session, tmp_path, repo, {
        "api.py": _ROUTE_FILE.replace("\ndef ", "\n# note\ndef "),
    })
    assert ran == []

    swapped = _ROUTE_FILE.replace(
        "def gamma():\n    return c1()\n\n\ndef delta():\n    return d1()\n",
        "def delta():\n    return d1()\n\n\ndef gamma():\n    return c1()\n",
    )
    await _commit_and_run(session, tmp_path, repo, {"api.py": swapped})
    assert ran == ["processes"]
    steps = {row.source_key for row in await _rows(session, step_sql, repo)}
    assert "delta::api.py" in steps and "gamma::api.py" not in steps

