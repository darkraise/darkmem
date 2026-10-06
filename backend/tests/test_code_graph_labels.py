"""Code Graph names a human reads: community labels and process names.

Communities were all named after one folder ("tests" for 100 of darkmem's
240), and process names leaked their key's entry-kind prefix
("scored:main::src/service.py").
"""
from __future__ import annotations

import pytest

from app.services.code_query import CodeQueryService
from app.services.community_detector import label_communities
from app.services.process_tracer import process_display_label
from tests.test_code_graph_lod import FILES, _add_community, _add_process
from tests.test_code_pipeline_integration import index_repo


def test_a_unique_folder_keeps_its_short_label():
    labels = label_communities({
        "a": ["app/services/x.py", "app/services/y.py"],
        "b": ["web/src/c.ts"],
    })
    assert labels == {"a": "services", "b": "src"}


def test_communities_sharing_a_folder_are_told_apart_by_file_then_number():
    labels = label_communities({
        "big": ["tests/test_events.py"] * 3,
        "small": ["tests/test_events.py"],
        "other": ["tests/test_door_parity.py", "tests/test_door_parity.py", "tests/test_x.py"],
    })
    assert labels == {
        "big": "tests/test_events",
        "small": "tests/test_events (2)",
        "other": "tests/test_door_parity",
    }
    assert len(set(labels.values())) == len(labels)


def test_a_community_with_no_file_still_gets_a_label():
    assert label_communities({"x": [None]}) == {"x": "community"}


@pytest.mark.parametrize(("key", "label"), [
    ("scored:main::src/service.py", "main (src/service.py)"),
    ("scored:__init__::src/service.py::Service", "Service.__init__ (src/service.py)"),
    ("route_tool:DELETE /by-uri", "DELETE /by-uri"),
    ("main (src/service.py)", "main (src/service.py)"),
])
def test_process_names_drop_the_entry_kind_prefix(key, label):
    assert process_display_label(key) == label


@pytest.mark.asyncio
async def test_the_graph_serves_clean_names_for_rows_indexed_before_the_fix(session, tmp_path):
    repo = await index_repo(session, tmp_path, FILES)
    # Stored as the old detector and tracer wrote them: label = folder, label = key.
    await _add_community(session, repo.id, "pkg_0", ["run::pkg/a.py", "again::pkg/a.py"])
    await _add_community(session, repo.id, "pkg_1", ["helper::pkg/b.py", "inner::pkg/b.py"])
    await _add_process(session, repo.id, "scored:run::pkg/a.py", ["run::pkg/a.py", "helper::pkg/b.py"])

    for kwargs in ({}, {"level": "file"}, {"scope": "pkg/a.py"}):
        graph = await CodeQueryService(session).get_code_graph(repo.id, **kwargs)
        labels = {n["id"]: n["label"] for n in graph["nodes"]}
        assert labels["scored:run::pkg/a.py"] == "run (pkg/a.py)"
        assert labels["pkg_0"] == "pkg/a"
        if "pkg_1" in labels:
            assert labels["pkg_1"] == "pkg/b"
