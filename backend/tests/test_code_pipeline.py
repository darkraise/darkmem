from unittest.mock import AsyncMock, Mock

import pytest

from app.services import code_pipeline
from app.services.code_pipeline import CodePipeline
from app.services.reindex_files import canonicalise_paths, classify_union_files


@pytest.mark.parametrize("legacy_metadata", [False, True])
async def test_incremental_imports_keep_unchanged_targets_and_binding_chains(
    session, tmp_path, monkeypatch, legacy_metadata,
):
    from sqlalchemy import select, text
    from app.models.code import CodeFile, CodeSymbol, Repository
    from app.services.repo_manager import RepoManager

    sources = {
        "target.py": "def original():\n    return 1\n",
        "other.py": "def original():\n    return 2\n",
        "bridge.py": "from target import original as exported\n",
        "caller.py": "from bridge import exported as local\ndef caller():\n    return local()\n",
        "wild.py": "from target import *\ndef wildcard():\n    return original()\n",
        "removed.py": "def removed():\n    return 0\n",
    }
    for name, content in sources.items():
        (tmp_path / name).write_text(content)
    repo = Repository(name="incremental-bindings", local_path=str(tmp_path))
    session.add(repo)
    await session.flush()
    manager = RepoManager(session)
    monkeypatch.setattr(manager, "pull_repo", AsyncMock(return_value="first"))
    await CodePipeline(session, None, None, manager).run(repo.id, full=True)
    unchanged_before = (await session.execute(
        select(CodeSymbol.id).join(CodeFile).where(
            CodeFile.repo_id == repo.id, CodeFile.file_path.in_(["target.py", "other.py"]),
        ).order_by(CodeSymbol.id)
    )).scalars().all()
    if legacy_metadata:
        await session.execute(text(
            "UPDATE code_graph_nodes SET properties = properties - 'binding_metadata' "
            "WHERE repo_id = :repo_id AND kind = 'file'"
        ), {"repo_id": repo.id})
    (tmp_path / "caller.py").write_text(sources["caller.py"] + "\nextra = 1\n")
    (tmp_path / "wild.py").write_text(sources["wild.py"] + "\nextra = 1\n")
    (tmp_path / "removed.py").unlink()
    pipeline = CodePipeline(session, None, None, manager)
    parser = AsyncMock(wraps=pipeline._parse_one)
    monkeypatch.setattr(pipeline, "_parse_one", parser)
    await pipeline.run(repo.id, forced_files=(["caller.py", "wild.py"], ["removed.py"]))

    assert set(pipeline._parsed) == {"caller.py", "wild.py"}
    if not legacy_metadata:
        assert {call.args[1] for call in parser.await_args_list} == {"caller.py", "wild.py"}
    assert set(pipeline._all_file_paths) == {"caller.py", "wild.py"}
    assert pipeline._resolved_import_map["caller.py"] == {"bridge.py"}
    assert pipeline._named_import_map["caller.py"]["local"] == ("target.py", "original")
    assert pipeline._named_import_map["wild.py"]["original"] == ("target.py", "original")
    edges = (await session.execute(text(
        "SELECT source_key, target_key FROM code_edges WHERE repo_id = :repo_id "
        "AND edge_type = 'calls'"
    ), {"repo_id": repo.id})).all()
    assert ("caller::caller.py", "original::target.py") in edges
    assert ("wildcard::wild.py", "original::target.py") in edges
    assert "removed.py" not in pipeline._repository_file_paths
    unchanged_after = (await session.execute(
        select(CodeSymbol.id).join(CodeFile).where(
            CodeFile.repo_id == repo.id, CodeFile.file_path.in_(["target.py", "other.py"]),
        ).order_by(CodeSymbol.id)
    )).scalars().all()
    assert unchanged_before == unchanged_after


@pytest.mark.parametrize("entry", ["absolute_link", "relative_link", "directory_link", "traversal", "absolute_path"])
async def test_parser_boundary_rejects_external_content(session, tmp_path, monkeypatch, entry):
    root = tmp_path / "repo"
    root.mkdir()
    external = tmp_path / "external.py"
    external.write_text("def external_secret():\n    return 'SENTINEL_EXTERNAL'\n")
    if entry == "absolute_link":
        (root / "secret.py").symlink_to(external)
        name = "secret.py"
    elif entry == "relative_link":
        (root / "secret.py").symlink_to("../external.py")
        name = "secret.py"
    elif entry == "directory_link":
        (root / "outside").symlink_to(tmp_path, target_is_directory=True)
        name = "outside/external.py"
    elif entry == "traversal":
        name = "../external.py"
    else:
        name = str(external)

    parser = Mock(wraps=code_pipeline.parse_file)
    monkeypatch.setattr(code_pipeline, "parse_file", parser)
    embedder = Mock(embed_batch_chunked=AsyncMock(side_effect=RuntimeError("No live embedding provider")))
    pipeline = CodePipeline(session, embedder, Mock(), Mock())
    pipeline._work_dir = root
    pipeline._changed_files = [name]
    pipeline._stats = {"files_skipped": 0, "errors": []}
    await pipeline.phase_02_parsing()
    await pipeline.phase_12_embeddings()

    assert pipeline._parsed == {}
    parser.assert_not_called()
    embedder.embed_batch_chunked.assert_not_awaited()
    assert pipeline._stats["files_skipped"] == 1


@pytest.mark.parametrize("restricted_exports", [False, True])
async def test_incremental_reexpands_unchanged_wildcard_bridge(
    session, tmp_path, monkeypatch, restricted_exports,
):
    from sqlalchemy import select, text
    from app.models.code import CodeFile, Repository
    from app.services.repo_manager import RepoManager

    bridge_source = "from target import *\n"
    if restricted_exports:
        bridge_source += "__all__ = ['old_fn', 'new_fn']\n"
    sources = {
        "target.py": "def old_fn():\n    return 1\n",
        "bridge.py": bridge_source,
        "caller.py": "from bridge import old_fn as selected\ndef caller():\n    return selected()\n",
    }
    for name, content in sources.items():
        (tmp_path / name).write_text(content)
    repo = Repository(name="wildcard-growth", local_path=str(tmp_path))
    session.add(repo)
    await session.flush()
    manager = RepoManager(session)
    monkeypatch.setattr(manager, "pull_repo", AsyncMock(return_value="first"))
    await CodePipeline(session, None, None, manager).run(repo.id, full=True)
    bridge_before = (await session.execute(select(CodeFile.id, CodeFile.content_hash).where(
        CodeFile.repo_id == repo.id, CodeFile.file_path == "bridge.py",
    ))).one()

    (tmp_path / "target.py").write_text(
        sources["target.py"] + "def new_fn():\n    return 2\ndef hidden_fn():\n    return 3\n"
    )
    (tmp_path / "caller.py").write_text(
        "from bridge import new_fn as selected\ndef caller():\n    return selected()\n"
    )
    monkeypatch.setattr(manager, "pull_repo", AsyncMock(return_value="second"))
    monkeypatch.setattr(code_pipeline, "_diff_files", AsyncMock(return_value=(
        ["target.py", "caller.py"], [],
    )))
    pipeline = CodePipeline(session, None, None, manager)
    parser = AsyncMock(wraps=pipeline._parse_one)
    monkeypatch.setattr(pipeline, "_parse_one", parser)

    result = await pipeline.run(repo.id)

    edges = (await session.execute(text(
        "SELECT source_key, target_key FROM code_edges WHERE repo_id = :repo_id "
        "AND edge_type = 'calls'"
    ), {"repo_id": repo.id})).all()
    assert ("caller::caller.py", "new_fn::target.py") in edges
    assert pipeline._named_import_map["bridge.py"]["new_fn"] == ("target.py", "new_fn")
    assert ("hidden_fn" in pipeline._named_import_map["bridge.py"]) is not restricted_exports
    assert set(pipeline._changed_files) == {"target.py", "caller.py"}
    assert set(pipeline._parsed) == {"target.py", "caller.py"}
    assert set(pipeline._all_file_paths) == {"target.py", "caller.py"}
    assert {call.args[1] for call in parser.await_args_list} == {"target.py", "caller.py"}
    assert result["index_debt_queued"] == 0
    assert result["files_changed"] == 2
    bridge_after = (await session.execute(select(CodeFile.id, CodeFile.content_hash).where(
        CodeFile.repo_id == repo.id, CodeFile.file_path == "bridge.py",
    ))).one()
    assert bridge_before == bridge_after
    metadata = (await session.execute(text(
        "SELECT properties->'binding_metadata' FROM code_graph_nodes "
        "WHERE repo_id = :repo_id AND kind = 'file' AND key = 'bridge.py'"
    ), {"repo_id": repo.id})).scalar_one()
    assert metadata["named"] == {}
    assert metadata["wildcard_exports"] == {
        "target.py": ["old_fn", "new_fn"] if restricted_exports else None,
    }

    (tmp_path / "target.py").write_text("def new_fn():\n    return 4\n")
    monkeypatch.setattr(manager, "pull_repo", AsyncMock(return_value="third"))
    monkeypatch.setattr(code_pipeline, "_diff_files", AsyncMock(return_value=(["target.py"], [])))
    pipeline = CodePipeline(session, None, None, manager)
    await pipeline.run(repo.id)
    assert "old_fn" not in pipeline._named_import_map["bridge.py"]
    assert "hidden_fn" not in pipeline._named_import_map["bridge.py"]
    assert set(pipeline._changed_files) == {"target.py", "caller.py"}
    assert (await session.execute(text(
        "SELECT target_key FROM code_edges WHERE repo_id = :repo_id "
        "AND edge_type = 'calls' AND source_key = 'caller::caller.py'"
    ), {"repo_id": repo.id})).scalar_one() == "new_fn::target.py"


async def test_parser_keeps_safe_internal_symlink(tmp_path):
    source = tmp_path / "source.py"
    source.write_text("def safe_function():\n    return 42\n")
    (tmp_path / "link.py").symlink_to("source.py")
    pipeline = CodePipeline(None, None, None, None)

    parsed = await pipeline._parse_one(tmp_path, "link.py")

    assert parsed["content"] == source.read_text()
    assert parsed["parse_result"].symbols[0].name == "safe_function"


def test_reindex_classifier_rechecks_replaced_link_before_hashing(tmp_path, monkeypatch):
    root = tmp_path / "repo"
    root.mkdir()
    source = root / "source.py"
    source.write_text("def safe_function():\n    return 42\n")
    names, invalid = canonicalise_paths(root, ["source.py"])
    assert invalid == []
    external = tmp_path / "external.py"
    external.write_text("SENTINEL_EXTERNAL")
    source.unlink()
    source.symlink_to(external)
    from app.services import reindex_files
    hasher = Mock(wraps=reindex_files._file_hash)
    monkeypatch.setattr(reindex_files, "_file_hash", hasher)

    buckets = classify_union_files(root, names, {})

    assert buckets.skipped_unindexable == ["source.py"]
    assert buckets.accepted == []
    hasher.assert_not_called()
