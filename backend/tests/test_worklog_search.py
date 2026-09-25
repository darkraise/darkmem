"""worklog.search: a keyword arm and a semantic arm, fused by RRF, scoped to one project in SQL."""
from __future__ import annotations

import pytest
from sqlalchemy import text

from app.config import settings
from app.services import worklog
from app.services.embedder_registry import EmbedderInfo, child_table, embedder_registry
from app.services.rank_fusion import fusion_fetch_depth
from app.services.worklog_embeddings import PARENT_TABLE, embed_entries

SEARCH_FINGERPRINT = "worklog-search-test|4"
FOREIGN_FINGERPRINT = "another-model|4"


class TopicEmbedder:
    """One axis per topic, so a query can match an entry by meaning while
    sharing no word with it: 'release' lands where 'deploy' does."""

    TOPICS = (("deploy", "release"), ("database", "postgres"), ("login", "password"))

    def __init__(self):
        self.fingerprint = SEARCH_FINGERPRINT
        self.calls = 0

    def _vector(self, value: str) -> list[float]:
        lowered = value.lower()
        vector = [0.0, 0.0, 0.0, 0.0]
        for axis, words in enumerate(self.TOPICS):
            if any(word in lowered for word in words):
                vector[axis] = 1.0
                return vector
        vector[3] = 1.0
        return vector

    async def embed(self, value: str):
        self.calls += 1
        return self._vector(value), self.fingerprint

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        return [self._vector(t) for t in texts], self.fingerprint


class DownEmbedder:
    async def embed(self, value: str):
        raise ConnectionError("embedder unreachable")

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        raise ConnectionError("embedder unreachable")


@pytest.fixture(autouse=True)
def _forget_search_fingerprint():
    embedder_registry.forget(SEARCH_FINGERPRINT)
    yield
    embedder_registry.forget(SEARCH_FINGERPRINT)


async def _note(session, body, *, project="proj", key="plan-a", kind="note"):
    result = await worklog.append(
        session, project=project, key=key, run_key="claude:run-1",
        entries=[{"kind": kind, "body": body}],
    )
    return str(result.entry_ids[0])


async def _embed(session, *entry_ids):
    await embed_entries(session, TopicEmbedder(), entry_ids=list(entry_ids))


def _ids(answer):
    return [item["entry"]["id"] for item in answer["items"]]


async def test_the_keyword_arm_answers_alone_without_an_orchestrator(session):
    hit = await _note(session, "Task 3 fixed the flaky migration test")
    await _note(session, "Unrelated housekeeping")
    answer = await worklog.search(session, None, project="proj", query="migration")
    assert answer["semantic_ran"] is False
    assert _ids(answer) == [hit]
    assert answer["items"][0]["arms"] == ["keyword"]
    assert answer["items"][0]["workstream"] == "plan-a"
    assert answer["items"][0]["entry"]["body"] == "Task 3 fixed the flaky migration test"


async def test_the_semantic_arm_finds_an_entry_that_shares_no_word(session):
    release = await _note(session, "The release pipeline broke overnight")
    rotated = await _note(session, "Rotated the postgres credentials")
    await _embed(session, release, rotated)
    answer = await worklog.search(session, TopicEmbedder(), project="proj", query="deploy failed")
    assert answer["semantic_ran"] is True
    assert _ids(answer) == [release, rotated]
    assert answer["items"][0]["arms"] == ["semantic"]


async def test_an_entry_both_arms_find_ranks_first(session):
    both = await _note(session, "The deploy script now retries")
    meaning = await _note(session, "Release notes drafted")
    other = await _note(session, "Database vacuum tuned")
    await _embed(session, both, meaning, other)
    answer = await worklog.search(session, TopicEmbedder(), project="proj", query="deploy")
    assert _ids(answer) == [both, meaning, other]
    assert answer["items"][0]["arms"] == ["keyword", "semantic"]
    assert answer["items"][1]["arms"] == ["semantic"]
    # Semantic ties on distance fall back to newest first: meaning 1, both 2, other 3.
    assert [item["rrf_score"] for item in answer["items"]] == pytest.approx(
        [1 / 61 + 1 / 62, 1 / 61, 1 / 63]
    )


async def test_fusion_sums_each_arms_reciprocal_rank(session):
    dense = await _note(session, "deploy deploy deploy")
    plan = await _note(session, "Release plan for the deploy")
    notes = await _note(session, "Release notes drafted")
    await _embed(session, dense, plan, notes)
    answer = await worklog.search(session, TopicEmbedder(), project="proj", query="deploy")
    # keyword: dense 1, plan 2; semantic (all one direction, newest first): notes 1, plan 2, dense 3
    assert _ids(answer) == [dense, plan, notes]
    assert [item["rrf_score"] for item in answer["items"]] == pytest.approx(
        [1 / 61 + 1 / 63, 1 / 62 + 1 / 62, 1 / 61]
    )


async def test_the_keyword_arm_ranks_by_ts_rank_not_recency(session):
    dense = await _note(session, "deploy deploy deploy checklist")
    sparse = await _note(session, "deploy checklist reviewed twice over")
    answer = await worklog.search(session, None, project="proj", query="deploy")
    assert _ids(answer) == [dense, sparse]
    assert [item["rrf_score"] for item in answer["items"]] == pytest.approx([1 / 61, 1 / 62])


async def test_a_hit_carries_the_entry_its_workstream_and_its_score(session):
    await _note(session, "deploy delta")
    (item,) = (await worklog.search(session, None, project="proj", query="deploy"))["items"]
    assert set(item) == {"entry", "workstream", "rrf_score", "arms"}
    assert set(item["entry"]) == {
        "id", "workstream_id", "seq", "run_key", "kind", "body", "properties", "created_at",
    }
    assert item["rrf_score"] == pytest.approx(1 / 61)


async def test_an_unreachable_embedder_leaves_the_keyword_arm_answering(session):
    hit = await _note(session, "deploy script retries")
    answer = await worklog.search(session, DownEmbedder(), project="proj", query="deploy")
    assert answer["semantic_ran"] is False
    assert _ids(answer) == [hit]


async def test_a_read_only_instance_never_calls_the_embedder(session, monkeypatch):
    hit = await _note(session, "deploy script retries")
    monkeypatch.setattr(settings, "read_only", True)
    llm = TopicEmbedder()
    answer = await worklog.search(session, llm, project="proj", query="deploy")
    assert llm.calls == 0
    assert answer["semantic_ran"] is False
    assert _ids(answer) == [hit]


async def test_an_unembedded_project_still_answers_by_keyword(session):
    hit = await _note(session, "deploy gamma")
    answer = await worklog.search(session, TopicEmbedder(), project="proj", query="deploy")
    assert answer["semantic_ran"] is True
    assert _ids(answer) == [hit]
    assert answer["items"][0]["arms"] == ["keyword"]


async def test_another_projects_entries_never_appear(session):
    mine = await _note(session, "deploy one", project="proj")
    theirs = await _note(session, "deploy two", project="other")
    await _embed(session, mine, theirs)
    answer = await worklog.search(session, TopicEmbedder(), project="proj", query="deploy")
    assert _ids(answer) == [mine]


async def test_workstream_and_kind_narrow_the_search(session):
    alpha = await _note(session, "deploy alpha", key="plan-a", kind="note")
    beta = await _note(session, "deploy beta\n", key="plan-b", kind="ledger")
    by_key = await worklog.search(session, None, project="proj", query="deploy", workstream="plan-b")
    by_kind = await worklog.search(session, None, project="proj", query="deploy", kind="note")
    assert _ids(by_key) == [beta]
    assert _ids(by_kind) == [alpha]


async def test_filters_bind_the_semantic_arm_too(session):
    alpha = await _note(session, "Release alpha", key="plan-a", kind="note")
    beta = await _note(session, "Release beta\n", key="plan-b", kind="ledger")
    await _embed(session, alpha, beta)
    by_key = await worklog.search(
        session, TopicEmbedder(), project="proj", query="deploy", workstream="plan-b",
    )
    by_kind = await worklog.search(
        session, TopicEmbedder(), project="proj", query="deploy", kind="note",
    )
    assert _ids(by_key) == [beta]
    assert _ids(by_kind) == [alpha]
    assert by_key["items"][0]["arms"] == ["semantic"]


async def test_other_projects_cannot_crowd_the_fetch_depth(session):
    """Newer, equally close vectors in another project fill the whole
    fusion_fetch_depth: a project filter applied after LIMIT would return nothing."""
    mine = await _note(session, "Release notes for this project")
    crowd: list[str] = []
    depth = fusion_fetch_depth(1)
    for start in range(0, depth, 100):
        result = await worklog.append(
            session, project="other", key=f"crowd-{start}", run_key="claude:run-1",
            entries=[
                {"kind": "note", "body": f"release {n}"} for n in range(start, min(start + 100, depth))
            ],
        )
        crowd.extend(str(entry_id) for entry_id in result.entry_ids)
    assert len(crowd) == depth
    await _embed(session, mine, *crowd)
    answer = await worklog.search(session, TopicEmbedder(), project="proj", query="deploy", limit=1)
    assert _ids(answer) == [mine]


async def _plant_vector(session, entry_id, *, fingerprint, project):
    """A vector row the writer would never produce, written straight into the table."""
    await session.execute(
        text(
            f"INSERT INTO {child_table(PARENT_TABLE, SEARCH_FINGERPRINT)} "
            "(entry_id, fingerprint, project, embedding) "
            "VALUES (CAST(:id AS uuid), :fp, :project, CAST(:vec AS vector))"
        ),
        {"id": entry_id, "fp": fingerprint, "project": project, "vec": "[1,0,0,0]"},
    )


async def test_a_vector_under_another_fingerprint_is_not_ranked(session):
    """Two long fingerprints can fold to one child table; each ranks only its own rows."""
    mine = await _note(session, "Release notes drafted")
    stranger = await _note(session, "Unrelated housekeeping")
    await _embed(session, mine)
    await embedder_registry.register(session, EmbedderInfo(
        fingerprint=FOREIGN_FINGERPRINT, model_id="another-model", dims=4, source="llm",
    ))
    try:
        await _plant_vector(session, stranger, fingerprint=FOREIGN_FINGERPRINT, project="proj")
        answer = await worklog.search(session, TopicEmbedder(), project="proj", query="deploy")
    finally:
        embedder_registry.forget(FOREIGN_FINGERPRINT)
    assert _ids(answer) == [mine]


async def test_a_vector_whose_entry_left_the_project_is_not_ranked(session):
    mine = await _note(session, "Release notes drafted")
    theirs = await _note(session, "Unrelated housekeeping", project="other")
    await _embed(session, mine)
    await _plant_vector(session, theirs, fingerprint=SEARCH_FINGERPRINT, project="proj")
    answer = await worklog.search(session, TopicEmbedder(), project="proj", query="deploy")
    assert _ids(answer) == [mine]


async def test_the_query_is_embedded_before_any_statement_runs(session, monkeypatch):
    order: list[str] = []
    execute = session.execute

    async def recording_execute(*args, **kwargs):
        order.append("execute")
        return await execute(*args, **kwargs)

    class RecordingEmbedder(TopicEmbedder):
        async def embed(self, value):
            order.append("embed")
            return await super().embed(value)

    monkeypatch.setattr(session, "execute", recording_execute)
    await worklog.search(session, RecordingEmbedder(), project="proj", query="deploy")
    assert order[0] == "embed"


async def test_limit_caps_the_hits(session):
    for n in range(3):
        await _note(session, f"deploy attempt {n}")
    answer = await worklog.search(session, None, project="proj", query="deploy", limit=2)
    assert len(answer["items"]) == 2


@pytest.mark.parametrize("kwargs", [
    {"query": "   "},
    {"query": "x" * 2_001},
    {"query": "deploy", "kind": "log"},
    {"query": "deploy", "limit": 0},
    {"query": "deploy", "limit": 101},
])
async def test_out_of_bounds_arguments_are_refused(session, kwargs):
    with pytest.raises(ValueError):
        await worklog.search(session, None, project="proj", **kwargs)
