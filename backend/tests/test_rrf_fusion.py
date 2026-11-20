"""RRF fusion and the unified ``rank_fusion_factor`` (doc 07 §3).

The read path has two classes of signal and they must not collapse into
each other, because both end up multiplying a number:

* ranked lists join **one** RRF at ``k = 60`` under a *list weight*
  (``semantic_weight``), which moves ``rrf_score`` and nothing else;
* per-row scalars are a deterministic **post-fusion** multiplier composed
  by ``rank_fusion_factor``, which moves a row's final score and never the
  list ordering inside the fusion.

Folding one into the other passes most tests and makes both untunable, so
the separation is asserted structurally here, not just behaviourally.
"""
from __future__ import annotations

import inspect
import uuid
from dataclasses import fields

import pytest
from sqlalchemy import text

from app.config import FEATURE_FLAGS_DEFAULTS
from app.models.memory import Memory
from app.services.confidence import CONFIDENCE_DEFAULT
from app.services.embedder_registry import child_table
from app.services.hybrid_search import HybridSearchService
from app.services.rank_fusion import (
    LIST_WEIGHT_KEYS,
    RANK_ARMS,
    RRF_K,
    RankArm,
    RankedList,
    any_arm_active,
    arm_factor,
    normalize_row_id,
    rank_fusion_breakdown,
    rank_fusion_factor,
    rrf_fuse,
)

FINGERPRINT = "rrf-fusion-test|4"
DIMS = 4


# ── the two classes never collapse (doc 07 §3) ───────────────────────


def test_arm_flags_are_never_list_weights():
    arm_flags = {arm.flag for arm in RANK_ARMS}
    assert arm_flags.isdisjoint(LIST_WEIGHT_KEYS)
    arm_names = {arm.name for arm in RANK_ARMS}
    assert arm_names.isdisjoint(LIST_WEIGHT_KEYS)


def test_neither_class_can_reach_the_other_through_its_signature():
    # The fusion takes ranked lists and a limit — there is no parameter
    # through which a per-row scalar or its weight could arrive. The factor
    # takes signals and weights — there is no rank and no list.
    assert set(inspect.signature(rrf_fuse).parameters) == {"lists", "limit"}
    assert set(inspect.signature(rank_fusion_factor).parameters) == {"signals", "weights"}
    assert {f.name for f in fields(RankedList)} == {"name", "rows", "weight"}


def test_a_list_weight_cannot_move_the_post_fusion_factor():
    signals = {"confidence": 0.9, "importance": 0.9}
    for weight in (0.0, 0.7, 0.99):
        assert rank_fusion_factor(signals, {"semantic_weight": weight}) == 1.0


def test_a_list_weight_moves_the_fusion():
    semantic = [{"memory_id": "s", "score": 0.1}]
    keyword = [{"memory_id": "k", "score": 0.1}]

    semantic_heavy = HybridSearchService._rrf_fuse(semantic, keyword, 0.9, 10)
    keyword_heavy = HybridSearchService._rrf_fuse(semantic, keyword, 0.1, 10)

    assert semantic_heavy[0]["memory_id"] == "s"
    assert keyword_heavy[0]["memory_id"] == "k"


def test_a_per_row_scalar_cannot_move_the_fusion():
    # Rows carry a confidence that would invert the order if the fusion
    # ever read it. Fusion is rank-driven, so the order stays a, b.
    semantic = [
        {"memory_id": "a", "score": 0.9, "confidence": 0.1},
        {"memory_id": "b", "score": 0.8, "confidence": 0.99},
    ]
    fused = rrf_fuse([RankedList("semantic", semantic, 0.7)], limit=10)
    assert [r["memory_id"] for r in fused] == ["a", "b"]
    assert fused[0]["rrf_score"] > fused[1]["rrf_score"]


# ── rrf_score is the ONLY ordering signal ────────────────────────────


def _disagreeing_lists() -> tuple[list[dict], list[dict]]:
    """Two lists whose ``score`` order and ``rrf_score`` order disagree.

    ``a`` wins on raw semantic score but appears in one list; ``b`` scores
    poorly on the semantic side and wins on rank mass by appearing in both.
    A fixture where the two orders agree would not detect a consumer that
    sorts by ``score``.
    """
    semantic = [
        {"memory_id": "a", "score": 0.99, "source": "semantic"},
        {"memory_id": "b", "score": 0.10, "source": "semantic"},
    ]
    keyword = [{"memory_id": "b", "score": 9.0, "source": "keyword"}]
    return semantic, keyword


def test_the_fixture_actually_disagrees():
    semantic, keyword = _disagreeing_lists()
    fused = HybridSearchService._rrf_fuse(semantic, keyword, 0.7, 10)
    by_rrf = [r["memory_id"] for r in sorted(fused, key=lambda r: -r["rrf_score"])]
    by_score = [r["memory_id"] for r in sorted(fused, key=lambda r: -r["score"])]
    assert by_rrf != by_score


def test_fusion_orders_by_rrf_score_not_by_raw_score():
    semantic, keyword = _disagreeing_lists()
    fused = HybridSearchService._rrf_fuse(semantic, keyword, 0.7, 10)

    assert [r["memory_id"] for r in fused] == ["b", "a"]
    expected_b = 0.7 / (RRF_K + 2) + 0.3 / (RRF_K + 1)
    expected_a = 0.7 / (RRF_K + 1)
    assert fused[0]["rrf_score"] == pytest.approx(expected_b)
    assert fused[1]["rrf_score"] == pytest.approx(expected_a)


def test_per_modality_score_survives_as_the_first_seen_side():
    semantic, keyword = _disagreeing_lists()
    fused = HybridSearchService._rrf_fuse(semantic, keyword, 0.7, 10)
    scores = {r["memory_id"]: r["score"] for r in fused}

    # b is on both sides; the semantic list is scanned first, so its raw
    # 0.10 survives rather than the keyword side's 9.0.
    assert scores["b"] == pytest.approx(0.10)
    assert scores["a"] == pytest.approx(0.99)
    # ...and the per-side tag does not.
    assert all("source" not in r for r in fused)


# ── the memory_id type boundary (invariant 9) ────────────────────────


def test_uuid_and_string_ids_fuse_into_one_row():
    mid = uuid.uuid4()
    semantic = [{"memory_id": mid, "score": 0.9}]
    keyword = [{"memory_id": str(mid), "score": 4.0}]

    fused = HybridSearchService._rrf_fuse(semantic, keyword, 0.7, 10)

    assert len(fused) == 1, "a UUID and its string form are the same memory"
    assert fused[0]["rrf_score"] == pytest.approx(0.7 / (RRF_K + 1) + 0.3 / (RRF_K + 1))


def test_fused_id_is_normalised_to_str():
    mid = uuid.uuid4()
    fused = rrf_fuse([RankedList("semantic", [{"memory_id": mid, "score": 0.9}], 0.7)], 10)
    assert fused[0]["memory_id"] == str(mid)
    assert isinstance(fused[0]["memory_id"], str)

    chunk = uuid.uuid4()
    fused_code = rrf_fuse([RankedList("code", [{"id": chunk, "score": 0.9}], 1.0)], 10)
    assert fused_code[0]["id"] == str(chunk)


def test_rows_without_an_id_are_dropped_not_merged():
    assert normalize_row_id({"score": 1.0}) is None
    assert normalize_row_id({"memory_id": ""}) is None
    fused = rrf_fuse([RankedList("semantic", [{"score": 1.0}, {"memory_id": "x"}], 0.7)], 10)
    assert [r["memory_id"] for r in fused] == ["x"]


# ── the confidence arm, spent today ──────────────────────────────────


def _gamma(value: float) -> dict:
    return {"confidence_rank_gamma": value}


def test_factor_is_identity_when_gamma_zero():
    assert rank_fusion_factor({"confidence": 0.5}, _gamma(0.0)) == 1.0
    assert rank_fusion_factor({"confidence": 0.9}, _gamma(0.0)) == 1.0


def test_factor_boosts_high_confidence():
    assert rank_fusion_factor({"confidence": 0.9}, _gamma(1.0)) == pytest.approx(1.15)


def test_factor_dampens_low_confidence():
    assert rank_fusion_factor({"confidence": 0.5}, _gamma(1.0)) == pytest.approx(0.75)


def test_factor_clamps_at_zero_for_pathological_gamma():
    # Without the clamp this is 1 + 10*(0.5-0.75) = -1.5, which inverts the
    # order when multiplied against a positive base score.
    assert rank_fusion_factor({"confidence": 0.5}, _gamma(10.0)) == 0.0
    assert rank_fusion_factor({"confidence": 0.0}, _gamma(10.0)) == 0.0


def test_clamping_is_per_arm_so_two_negative_arms_cannot_multiply_back():
    weights = {"confidence_rank_gamma": 10.0, "w_importance": 10.0}
    signals = {"confidence": 0.5, "importance": 0.0}
    assert rank_fusion_factor(signals, weights) == 0.0


def test_a_missing_signal_leaves_its_arm_at_identity():
    assert rank_fusion_factor({}, _gamma(2.0)) == 1.0


# ── the three future arms: slots exist, wired at zero ────────────────


FUTURE_ARMS = tuple(arm for arm in RANK_ARMS if arm.name != "confidence")


def test_all_four_arms_have_a_formula_slot():
    assert [arm.name for arm in RANK_ARMS] == ["confidence", "importance", "heat", "recency"]


def test_future_arms_are_zero_weighted_by_default():
    for arm in FUTURE_ARMS:
        assert float(FEATURE_FLAGS_DEFAULTS.get(arm.flag, 0.0) or 0.0) == 0.0, arm.flag


def test_future_arms_name_their_activation_task():
    for arm in FUTURE_ARMS:
        assert arm.activation, f"{arm.name} must name the task that turns it on"


def test_a_zero_weighted_arm_is_exactly_identity():
    signals = {"confidence": 0.5, "importance": 0.9, "heat": 1.0, "recency": 1.0}
    for arm in FUTURE_ARMS:
        assert arm_factor(arm, signals, {}) == 1.0
        assert arm_factor(arm, signals, {arm.flag: 0.0}) == 1.0


def test_arms_at_zero_are_bit_identical_to_arms_absent():
    """The property T1.31's acceptance rests on.

    An arm at weight zero contributes exactly ``1.0`` and multiplying a
    float by ``1.0`` is exact in IEEE-754, so composing four arms with
    three at zero produces the same bits as the confidence arm alone.
    """
    signals = {"confidence": 0.9, "importance": 0.9, "heat": 1.0, "recency": 1.0}
    absent = {"confidence_rank_gamma": 1.7}
    at_zero = {**absent, "w_importance": 0.0, "w_heat": 0.0, "w_recency": 0.0}

    confidence_only = arm_factor(RANK_ARMS[0], signals, absent)
    assert rank_fusion_factor(signals, absent) == confidence_only
    assert rank_fusion_factor(signals, at_zero) == confidence_only
    assert rank_fusion_factor(signals, at_zero).hex() == confidence_only.hex()


def test_a_future_arm_composes_once_it_carries_a_weight():
    # The slot is real, not decorative: give importance a weight and the
    # composed factor is the product of the two arms.
    signals = {"confidence": 0.9, "importance": 0.7}
    weights = {"confidence_rank_gamma": 1.0, "w_importance": 2.0}
    assert rank_fusion_factor(signals, weights) == pytest.approx(1.15 * 1.4)


def test_breakdown_reports_every_arm():
    breakdown = rank_fusion_breakdown({"confidence": 0.9}, _gamma(1.0))
    assert set(breakdown) == {arm.name for arm in RANK_ARMS}
    assert breakdown["confidence"] == pytest.approx(1.15)
    assert breakdown["importance"] == 1.0


def test_any_arm_active_is_false_at_repo_defaults():
    assert any_arm_active(FEATURE_FLAGS_DEFAULTS) is False
    assert any_arm_active({"confidence_rank_gamma": 0.5}) is True
    assert any_arm_active({"w_heat": 0.5}) is True


def test_arm_baselines_match_their_column_defaults():
    by_name = {arm.name: arm for arm in RANK_ARMS}
    assert by_name["confidence"].baseline == CONFIDENCE_DEFAULT
    assert by_name["importance"].baseline == 0.5
    # heat_norm and recency_norm are already normalised to [0, 1].
    assert by_name["heat"].baseline == 0.0
    assert by_name["recency"].baseline == 0.0


def test_rank_arm_is_frozen():
    with pytest.raises(Exception):
        RANK_ARMS[0].baseline = 0.1  # type: ignore[misc]
    assert isinstance(RANK_ARMS[0], RankArm)


# ── post-fusion weighting and the rerank order (doc 07 §3) ───────────


class _StubLLM:
    async def embed(self, query: str):
        return [1.0, 0.0, 0.0, 0.0], FINGERPRINT


class _SingleSessionFactory:
    """Hands the pipeline the test's own transactional session.

    ``semantic_search`` opens its own session from the factory; a real one
    would be a separate connection that cannot see the fixture's uncommitted
    rows.
    """

    def __init__(self, session):
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *exc):
        return False


async def _seed_memory(
    session, *, content: str, confidence: float, importance: float = 0.5,
) -> uuid.UUID:
    mem = Memory(
        id=uuid.uuid4(),
        content=content,
        source="test",
        project="rrf-fusion-test",
        confidence=confidence,
        importance=importance,
    )
    session.add(mem)
    await session.flush()
    return mem.id


@pytest.mark.asyncio
async def test_weighting_reorders_when_no_rerank_ran(session):
    from app.services.pipeline import ProcessingPipeline

    low = await _seed_memory(session, content="low confidence row", confidence=0.5)
    high = await _seed_memory(session, content="high confidence row", confidence=0.9)

    search = HybridSearchService(_StubLLM(), session)
    rows = [
        {"memory_id": str(low), "rrf_score": 0.010},
        {"memory_id": str(high), "rrf_score": 0.009},
    ]
    out = await search.apply_rank_fusion_factor(
        rows, {"confidence_rank_gamma": 2.0}, preserve_order=False,
    )

    # 0.010 * 0.5 = 0.005 vs 0.009 * 1.3 = 0.0117 — the high-confidence row
    # overtakes.
    assert [r["memory_id"] for r in out] == [str(high), str(low)]


@pytest.mark.asyncio
async def test_weighting_preserves_a_reranked_order_while_rescaling(session):
    from app.services.pipeline import ProcessingPipeline

    low = await _seed_memory(session, content="low confidence row", confidence=0.5)
    high = await _seed_memory(session, content="high confidence row", confidence=0.9)

    search = HybridSearchService(_StubLLM(), session)
    rows = [
        {"memory_id": str(low), "rrf_score": 0.010},
        {"memory_id": str(high), "rrf_score": 0.009},
    ]
    out = await search.apply_rank_fusion_factor(
        rows, {"confidence_rank_gamma": 2.0}, preserve_order=True,
    )

    assert [r["memory_id"] for r in out] == [str(low), str(high)]
    # Rescaled, not merely left alone.
    assert out[0]["rrf_score"] == pytest.approx(0.010 * 0.5)
    assert out[1]["rrf_score"] == pytest.approx(0.009 * 1.3)


# ── the importance signal is wired, and inert at weight zero (T2.30) ──


@pytest.mark.asyncio
async def test_importance_signal_reorders_when_w_importance_is_on(session):
    """``memories.importance`` must actually reach ``rank_fusion_factor``.

    With the signal unwired the importance arm reads no signal and returns
    exactly 1.0 at any weight, so this reorder is the wiring's existence
    proof, not a formula check (the formula is test_rrf_fusion's arm tests).
    """
    from app.services.pipeline import ProcessingPipeline

    dull = await _seed_memory(
        session, content="dull row", confidence=0.75, importance=0.2,
    )
    vital = await _seed_memory(
        session, content="vital row", confidence=0.75, importance=0.9,
    )

    search = HybridSearchService(_StubLLM(), session)
    rows = [
        {"memory_id": str(dull), "rrf_score": 0.010},
        {"memory_id": str(vital), "rrf_score": 0.009},
    ]
    out = await search.apply_rank_fusion_factor(
        rows, {"w_importance": 1.0}, preserve_order=False,
    )

    # 0.010 * (1 + 1.0*(0.2-0.5)) = 0.0070 vs 0.009 * (1 + 1.0*(0.9-0.5))
    # = 0.0126 — the important row overtakes.
    assert [r["memory_id"] for r in out] == [str(vital), str(dull)]
    assert out[0]["rrf_score"] == pytest.approx(0.009 * 1.4)
    assert out[1]["rrf_score"] == pytest.approx(0.010 * 0.7)


@pytest.mark.asyncio
async def test_importance_wiring_is_bit_identical_at_weight_zero(session):
    """Feeding the signal must change nothing while ``w_importance`` is 0.

    Varied importance on disk, confidence arm active: the scores must be
    the literal IEEE-754 values the confidence-only computation produces —
    ``.hex()``, not approx, per T1.31's bit-identity ruling.
    """
    from app.services.pipeline import ProcessingPipeline

    dull = await _seed_memory(
        session, content="dull row", confidence=0.5, importance=0.1,
    )
    vital = await _seed_memory(
        session, content="vital row", confidence=0.9, importance=0.9,
    )

    search = HybridSearchService(_StubLLM(), session)

    def rows():
        return [
            {"memory_id": str(dull), "rrf_score": 0.010},
            {"memory_id": str(vital), "rrf_score": 0.009},
        ]

    weighted = await search.apply_rank_fusion_factor(
        rows(), {"confidence_rank_gamma": 2.0, "w_importance": 0.0},
    )
    confidence_only = await search.apply_rank_fusion_factor(
        rows(), {"confidence_rank_gamma": 2.0},
    )

    by_id_weighted = {r["memory_id"]: r["rrf_score"] for r in weighted}
    by_id_conf = {r["memory_id"]: r["rrf_score"] for r in confidence_only}
    for mid in by_id_conf:
        assert by_id_weighted[mid].hex() == by_id_conf[mid].hex()


@pytest.mark.asyncio
async def test_semantic_search_preserves_the_rerank_verdict(session, monkeypatch):
    """The wiring, not just the helper.

    If ``preserve_order=reranked`` is dropped at the call site, confidence
    weighting silently re-sorts the reranked list and the rerank is thrown
    away — a worse ranking, never an error.
    """
    from app.services import pipeline as pipeline_mod
    from app.services.pipeline import ProcessingPipeline, _flag_cache_reset

    low = await _seed_memory(session, content="low confidence row", confidence=0.5)
    high = await _seed_memory(session, content="high confidence row", confidence=0.9)
    fused = [
        {"memory_id": str(high), "rrf_score": 0.009},
        {"memory_id": str(low), "rrf_score": 0.010},
    ]

    async def search(
        self, query, limit=20, semantic_weight=0.7, filters=None,
        ppr_weight=0.0, dual_weight=0.0, access_signals=False, embedded=None,
    ):
        return [dict(row) for row in fused]

    class _StubReranker:
        def __init__(self, llm):
            pass

        async def rerank(self, query, documents, top_k=10, **kwargs):
            # The reranker's verdict: the low-confidence row is the better
            # answer for this query.
            ordered = sorted(documents, key=lambda d: d["memory_id"] != str(low))
            return ordered[:top_k]

    async def _flags(_factory):
        return {
            "hybrid_search_enabled": True,
            "reranker_enabled": True,
            "confidence_rank_gamma": 2.0,
        }

    monkeypatch.setattr(
        "app.services.hybrid_search.HybridSearchService.search", search, raising=True,
    )
    monkeypatch.setattr(
        "app.services.reranker.RerankerService", _StubReranker, raising=True,
    )
    monkeypatch.setattr("app.services.feature_flags.get_feature_flags_dict", _flags, raising=True)

    pipe = ProcessingPipeline(_StubLLM(), _SingleSessionFactory(session))
    _flag_cache_reset()
    try:
        results = await pipe.semantic_search("q", limit=10)
    finally:
        _flag_cache_reset()

    assert [r["memory_id"] for r in results] == [str(low), str(high)], (
        "confidence weighting must not re-sort a reranked list"
    )


# ── end to end through the real service ──────────────────────────────


async def _seed_partition(session) -> None:
    await session.execute(
        text(
            "INSERT INTO embedders (fingerprint, model_id, dims, source) "
            "VALUES (:fp, :mid, :dims, 'llm') ON CONFLICT (fingerprint) DO NOTHING"
        ),
        {"fp": FINGERPRINT, "mid": "fake-embedder", "dims": DIMS},
    )
    child = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(text(
        f"CREATE TABLE IF NOT EXISTS {child} ("
        " memory_id UUID NOT NULL REFERENCES memories(id) ON DELETE CASCADE,"
        " fingerprint TEXT NOT NULL REFERENCES embedders(fingerprint),"
        f" embedding vector({DIMS}) NOT NULL,"
        " payload JSONB NOT NULL DEFAULT '{}'::jsonb,"
        " created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),"
        " PRIMARY KEY (memory_id, fingerprint))"
    ))


async def _seed_embedding(session, memory_id: uuid.UUID, vector: list[float]) -> None:
    child = child_table("memory_embeddings", FINGERPRINT)
    await session.execute(
        text(
            f"INSERT INTO {child} (memory_id, fingerprint, embedding, payload) "
            "VALUES (:mid, :fp, CAST(:vec AS vector), '{}'::jsonb)"
        ),
        {"mid": memory_id, "fp": FINGERPRINT, "vec": str(vector)},
    )
    await session.flush()


@pytest.mark.asyncio
async def test_search_orders_by_rrf_score_not_by_the_surviving_score_key(session):
    """Through ``HybridSearchService.search`` against the real database.

    The nearest-neighbour row wins on raw cosine ``score`` and loses on
    ``rrf_score`` to the row that both channels found. A consumer sorting
    by the surviving per-modality ``score`` would return the wrong answer
    first and look plausible doing it.
    """
    await _seed_partition(session)

    nearest = await _seed_memory(
        session, content="alpha beta gamma delta epsilon", confidence=CONFIDENCE_DEFAULT,
    )
    both = await _seed_memory(
        session, content="kubernetes ingress controller tuning", confidence=CONFIDENCE_DEFAULT,
    )
    await _seed_embedding(session, nearest, [1.0, 0.0, 0.0, 0.0])
    await _seed_embedding(session, both, [0.0, 1.0, 0.0, 0.0])

    svc = HybridSearchService(_StubLLM(), session)
    results = await svc.search("kubernetes ingress", limit=10)

    ids = [r["memory_id"] for r in results]
    assert ids == [str(both), str(nearest)]

    by_raw_score = [r["memory_id"] for r in sorted(results, key=lambda r: -r["score"])]
    assert by_raw_score == [str(nearest), str(both)], (
        "fixture must disagree, or it proves nothing"
    )
    assert results[0]["rrf_score"] > results[1]["rrf_score"]


@pytest.mark.asyncio
async def test_search_is_search_with_trace_results(session):
    import ast
    import textwrap

    await _seed_partition(session)
    seeded = [
        ("alpha beta gamma delta epsilon", [1.0, 0.0, 0.0, 0.0]),
        ("kubernetes ingress controller tuning", [0.0, 1.0, 0.0, 0.0]),
        ("postgres vacuum and ingress logs", [0.5, 0.5, 0.0, 0.0]),
    ]
    for content, vector in seeded:
        memory_id = await _seed_memory(session, content=content, confidence=CONFIDENCE_DEFAULT)
        await _seed_embedding(session, memory_id, vector)

    svc = HybridSearchService(_StubLLM(), session)
    for query in ("kubernetes ingress", "postgres vacuum", "epsilon"):
        plain = await svc.search(query, limit=10)
        traced = await svc.search_with_trace(query, limit=10)
        assert plain == traced.results

    body = ast.parse(textwrap.dedent(inspect.getsource(HybridSearchService.search)))
    called = {
        node.func.attr for node in ast.walk(body)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }
    assert "search_with_trace" in called
    assert not called & {"_rrf_fuse", "_run_channels", "embed_query", "_embed_query"}
