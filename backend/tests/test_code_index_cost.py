"""What an index run and a drift scan cost: work kept off the event loop,
statements batched per phase, and a deriver tick that skips an unmoved HEAD."""
from __future__ import annotations

import hashlib
import os
import re
import subprocess
import threading
import uuid
from pathlib import Path

from sqlalchemy import event, text
from sqlalchemy.engine import Engine

from app.models.code import Repository
from app.services import code_deriver, code_pipeline, code_reconcile
from app.services.code_pipeline import CodePipeline
from app.services.code_reconcile import compute_working_tree_drift
from app.services.job_runners import make_code_deriver_runner
from app.services.repo_manager import RepoManager
from app.utils.graph_keys import compose_key


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


async def _local_repo(session, root: Path) -> Repository:
    repo = Repository(
        name=f"cost-{uuid.uuid4().hex[:8]}", local_path=str(root),
        provider="local", status="ready",
    )
    session.add(repo)
    await session.flush()
    return repo


def _pipeline(session, repo: Repository, root: Path) -> CodePipeline:
    pipe = CodePipeline(session, None, None, None)
    pipe._repo = repo
    pipe._work_dir = root
    pipe._repo_id_str = str(repo.id)
    pipe._stats = {
        "status": "indexed", "commit": "t", "files_changed": 0, "files_deleted": 0,
        "files_skipped": 0, "symbols_indexed": 0, "chunks_stored": 0,
        "calls_resolved": 0, "accesses": 0, "errors": [],
    }
    return pipe


async def _first_index(session, root: Path, files: dict[str, str]) -> Repository:
    _write(root, files)
    repo = await _local_repo(session, root)
    pipe = _pipeline(session, repo, root)
    await pipe.phase_01_file_discovery(None, "testsha", full=True)
    await pipe.phase_02_parsing()
    await pipe.phase_03_structure()
    await session.flush()
    return repo


async def test_drift_scan_hashes_off_the_event_loop(session, tmp_path, monkeypatch):
    _write(tmp_path, {"a.py": "x = 1\n", "b.py": "y = 2\n"})
    repo = await _local_repo(session, tmp_path)
    loop_thread = threading.get_ident()
    threads: list[int] = []
    original = code_reconcile._file_hash

    def _recording_hash(path):
        threads.append(threading.get_ident())
        return original(path)

    monkeypatch.setattr(code_reconcile, "_file_hash", _recording_hash)

    changed, _deleted = await compute_working_tree_drift(session, repo, tmp_path)

    assert sorted(changed) == ["a.py", "b.py"]
    assert threads and loop_thread not in threads


async def test_unchanged_stat_is_not_rehashed(session, tmp_path, monkeypatch):
    _write(tmp_path, {"a.py": "x = 1\n", "b.py": "y = 2\n"})
    old = 1_700_000_000
    for name in ("a.py", "b.py"):
        os.utime(tmp_path / name, (old, old))
    repo = await _local_repo(session, tmp_path)
    await compute_working_tree_drift(session, repo, tmp_path)

    calls: list[Path] = []
    original = code_reconcile._file_hash

    def _counting_hash(path):
        calls.append(path)
        return original(path)

    monkeypatch.setattr(code_reconcile, "_file_hash", _counting_hash)

    changed, _deleted = await compute_working_tree_drift(session, repo, tmp_path)

    assert sorted(changed) == ["a.py", "b.py"]
    assert calls == []


async def test_unparseable_file_is_not_drift(session, tmp_path, monkeypatch):
    bad_source = "def broken(:\n    pass\n"
    real_parse = code_pipeline.parse_file

    def _parse(rel_path, content):
        if rel_path == "bad.py":
            raise RuntimeError("parser blew up")
        return real_parse(rel_path, content)

    monkeypatch.setattr(code_pipeline, "parse_file", _parse)
    repo = await _first_index(session, tmp_path, {
        "good.py": "def good():\n    return 1\n",
        "bad.py": bad_source,
    })

    row = (await session.execute(
        text("""
            SELECT f.content_hash, f.language,
                   (SELECT count(*) FROM code_symbols s WHERE s.file_id = f.id) AS symbols
            FROM code_files f WHERE f.repo_id = :r AND f.file_path = 'bad.py'
        """),
        {"r": repo.id},
    )).one()
    assert row.content_hash == hashlib.sha256(bad_source.encode()).hexdigest()
    assert row.symbols == 0
    assert row.language is None

    changed, deleted = await compute_working_tree_drift(session, repo, tmp_path)
    assert (changed, deleted) == ([], [])

    (tmp_path / "bad.py").write_text(bad_source + "# edited, longer\n")
    changed, _deleted = await compute_working_tree_drift(session, repo, tmp_path)
    assert changed == ["bad.py"]


async def test_per_file_delete_uses_the_expression_indexes(session, tmp_path):
    names = set((await session.execute(
        text("SELECT indexname FROM pg_indexes WHERE tablename = 'code_edges'")
    )).scalars().all())
    assert {"ix_code_edges_source_file", "ix_code_edges_target_file"} <= names

    # A populated repository: on an empty table any repo_id index wins, and
    # that plan still reads every edge of the repository.
    repo = await _local_repo(session, tmp_path)
    await session.execute(
        text("""
            INSERT INTO code_edges
                (repo_id, source_kind, source_key, target_kind, target_key, edge_type, properties)
            SELECT :r, 'symbol', 'f' || g || '::src/m' || (g % 400) || '.py',
                   'symbol', 'g' || g || '::src/n' || (g % 400) || '.py', 'calls', '{}'
            FROM generate_series(1, 4000) AS g
        """),
        {"r": repo.id},
    )
    await session.execute(text("ANALYZE code_edges"))
    await session.execute(text("SET LOCAL enable_seqscan = off"))
    plan = "\n".join((await session.execute(
        text("EXPLAIN " + code_pipeline._EDGE_DELETE_SQL),
        {"repo_id": str(repo.id), "files": ["src/m1.py", "src/n2.py"]},
    )).scalars().all())

    assert "ix_code_edges_source_file" in plan, plan
    assert "ix_code_edges_target_file" in plan, plan
    assert "Seq Scan" not in plan, plan


async def test_full_reindex_deletes_in_batches(session, tmp_path):
    files = {"mod0.py": "def f0():\n    return 0\n"}
    for i in range(1, 40):
        files[f"mod{i}.py"] = (
            f"from mod{i - 1} import f{i - 1}\n\n"
            f"def f{i}():\n    return f{i - 1}()\n"
        )
    _write(tmp_path, files)
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "add", ".")
    _git(tmp_path, "commit", "-qm", "init")
    repo = await _local_repo(session, tmp_path)
    await session.commit()
    pipeline = CodePipeline(
        session=session, llm=None, vector_repo=None, repo_manager=RepoManager(session),
    )
    await pipeline.run(repo.id)

    with _Statements() as statements:
        result = await CodePipeline(
            session=session, llm=None, vector_repo=None, repo_manager=RepoManager(session),
        ).run(repo.id, full=True)

    assert result["files_changed"] == 40
    edge_deletes = statements.matching(r"^DELETE FROM code_edges\b")
    sweeps = statements.matching(r"DELETE FROM code_graph_nodes n .*'route', 'tool'")
    assert len(edge_deletes) <= 6, edge_deletes
    assert len(sweeps) == 1, sweeps


async def test_store_graph_batches_its_inserts(session, tmp_path):
    methods = "".join(f"    def m{i}(self):\n        return {i}\n" for i in range(30))
    functions = "".join(f"def f{i}():\n    return {i}\n\n" for i in range(69))
    _write(tmp_path, {"big.py": f"class Big:\n{methods}\n\n{functions}"})
    repo = await _local_repo(session, tmp_path)
    pipe = _pipeline(session, repo, tmp_path)
    await pipe.phase_01_file_discovery(None, "testsha", full=True)
    await pipe.phase_02_parsing()
    assert len(pipe._parsed["big.py"]["parse_result"].symbols) == 70

    with _Statements() as statements:
        await pipe.phase_03_structure()

    inserts = statements.matching(r"^INSERT INTO")
    assert len(inserts) <= 10, inserts
    nodes = (await session.execute(
        text("SELECT count(*) FROM code_graph_nodes WHERE repo_id = :r AND kind = 'symbol'"),
        {"r": repo.id},
    )).scalar_one()
    assert nodes == 100


async def test_named_bindings_update_files_in_one_statement(session, tmp_path):
    files = {f"m{i}.py": f"from m{i + 1} import g\n\ndef h{i}():\n    return g()\n" for i in range(5)}
    files["m5.py"] = "def g():\n    return 1\n"
    _write(tmp_path, files)
    repo = await _local_repo(session, tmp_path)
    pipe = _pipeline(session, repo, tmp_path)
    await pipe.phase_01_file_discovery(None, "testsha", full=True)
    await pipe.phase_02_parsing()
    await pipe.phase_03_structure()
    await pipe.phase_04_import_resolution()

    with _Statements() as statements:
        await pipe.phase_05_named_bindings()

    assert len(statements.matching(r"^UPDATE code_graph_nodes")) == 1
    stored = (await session.execute(
        text("""
            SELECT count(*) FROM code_graph_nodes
            WHERE repo_id = :r AND kind = 'file' AND properties ? 'binding_metadata'
        """),
        {"r": repo.id},
    )).scalar_one()
    assert stored == 6


async def test_inherited_calls_load_the_heritage_maps_once(session, tmp_path):
    files = {
        "base.py": "class Base:\n    def helper(self):\n        return 1\n",
        # A second `helper` makes the bare name ambiguous and the children
        # import only `mid.py`, so only the enclosing class's inheritance
        # chain can resolve `self.helper()`.
        "other.py": "class Other:\n    def helper(self):\n        return 2\n",
        "mid.py": "from base import Base\n\nclass Mid(Base):\n    pass\n",
    }
    for i in range(4):
        files[f"child{i}.py"] = (
            "from mid import Mid\n\n"
            f"class Child{i}(Mid):\n"
            "    def run(self):\n"
            "        return self.helper()\n"
        )
    _write(tmp_path, files)
    repo = await _local_repo(session, tmp_path)
    pipe = _pipeline(session, repo, tmp_path)
    await pipe.phase_01_file_discovery(None, "testsha", full=True)
    await pipe.phase_02_parsing()
    await pipe.phase_03_structure()
    await pipe.phase_04_import_resolution()
    await pipe.phase_05_named_bindings()

    with _Statements() as statements:
        await pipe.phase_06_call_tracing()

    assert len(statements.matching(r"has_method")) <= 1, statements.matching("has_method")
    assert len(statements.matching(r"'extends'")) <= 1, statements.matching("'extends'")
    target = compose_key("symbol", "helper", "base.py", owner="Base")
    callers = set((await session.execute(
        text("""
            SELECT source_key FROM code_edges
            WHERE repo_id = :r AND edge_type = 'calls' AND target_key = :t
        """),
        {"r": repo.id, "t": target},
    )).scalars().all())
    assert callers == {
        compose_key("symbol", "run", f"child{i}.py", owner=f"Child{i}") for i in range(4)
    }


async def test_code_deriver_skips_a_repository_whose_head_did_not_move(
    session, session_factory, monkeypatch,
):
    derived: list = []

    async def _spy(repo_session, repo_id):
        derived.append(repo_id)
        return {"entities": 0, "relations": 0}

    monkeypatch.setattr(code_deriver, "assert_repo_graph", _spy)
    repo = Repository(
        name=f"derive-{uuid.uuid4().hex[:8]}", status="ready", last_indexed_commit="sha-1",
    )
    session.add(repo)
    await session.flush()
    runner = make_code_deriver_runner(session_factory)

    await runner()
    await runner()
    assert derived.count(repo.id) == 1

    await session.execute(
        text("UPDATE repositories SET last_indexed_commit = 'sha-2' WHERE id = :r"),
        {"r": repo.id},
    )
    await session.flush()
    await runner()
    assert derived.count(repo.id) == 2


async def _indexed_with_a_failing_file(session, root: Path, monkeypatch, failing: set[str]):
    real_parse = code_pipeline.parse_file
    parsed: list[str] = []

    def _parse(rel_path, content):
        parsed.append(rel_path)
        if rel_path in failing:
            raise RuntimeError("parser blew up")
        return real_parse(rel_path, content)

    monkeypatch.setattr(code_pipeline, "parse_file", _parse)
    _write(root, {
        "good.py": "def good():\n    return 1\n",
        "bad.py": "def bad():\n    return 2\n",
    })
    _git(root, "init", "-q")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "init")
    repo = await _local_repo(session, root)
    await session.commit()
    await CodePipeline(
        session=session, llm=None, vector_repo=None, repo_manager=RepoManager(session),
    ).run(repo.id)
    return repo, parsed


async def _next_commit_run(session, root: Path, repo: Repository, n: int) -> None:
    _write(root, {"good.py": f"def good():\n    return {n}\n"})
    _git(root, "commit", "-qam", f"change {n}")
    await CodePipeline(
        session=session, llm=None, vector_repo=None, repo_manager=RepoManager(session),
    ).run(repo.id)


async def test_an_unparseable_file_is_parsed_once_per_run(session, tmp_path, monkeypatch):
    failing = {"bad.py"}
    repo, parsed = await _indexed_with_a_failing_file(session, tmp_path, monkeypatch, failing)
    parsed.clear()
    in_phase_04: list[str] = []
    real_phase_04 = CodePipeline.phase_04_import_resolution

    async def _phase_04(self):
        before = len(parsed)
        await real_phase_04(self)
        in_phase_04.extend(parsed[before:])

    monkeypatch.setattr(CodePipeline, "phase_04_import_resolution", _phase_04)

    await _next_commit_run(session, tmp_path, repo, 3)

    assert parsed.count("bad.py") == 1
    assert "bad.py" not in in_phase_04
    language = (await session.execute(
        text("SELECT language FROM code_files WHERE repo_id = :r AND file_path = 'bad.py'"),
        {"r": repo.id},
    )).scalar_one()
    assert language is None


async def test_a_file_that_parses_on_retry_gains_its_symbols(session, tmp_path, monkeypatch):
    failing = {"bad.py"}
    repo, _parsed = await _indexed_with_a_failing_file(session, tmp_path, monkeypatch, failing)
    failing.clear()

    await _next_commit_run(session, tmp_path, repo, 3)

    row = (await session.execute(
        text("""
            SELECT f.language,
                   (SELECT count(*) FROM code_symbols s WHERE s.file_id = f.id) AS symbols
            FROM code_files f WHERE f.repo_id = :r AND f.file_path = 'bad.py'
        """),
        {"r": repo.id},
    )).one()
    assert row.language == "python"
    assert row.symbols == 1
