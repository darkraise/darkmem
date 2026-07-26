"""Tests for the full-context baseline arm and the two-arm comparator (T0.09).

Prompt construction, answer parsing, the id audit and the comparator are all
pure and DB-free. The arm itself is exercised against a stubbed
``TwinningOrchestrator`` -- the real caching/token-attribution class with only
its model round trip replaced -- so the cache, the live/cache latency split
and the per-purpose token ledger under test are the shipped ones, not a
lookalike.
"""
import json
import uuid

import pytest

from benchlib import full_context, ledger, twin
from benchlib.retrieval_scorer import ScoreReport, score_retrieval

pytestmark = pytest.mark.usefixtures("_bench_db")


# ── fixtures and helpers ─────────────────────────────────────────────────


def _mid(key: str) -> str:
    return str(uuid.uuid5(uuid.NAMESPACE_URL, f"darkmem://test/full-context/{key}"))


def _corpus(n: int = 4) -> list[dict]:
    return [
        {"memory_id": _mid(f"m{i}"), "content": f"memory number {i} about topic {i}"}
        for i in range(n)
    ]


def _pairs(corpus: list[dict]) -> list[dict]:
    return [
        {
            "id": f"fc-{i:04d}", "query": f"what is topic {i}?",
            "relevant_memory_ids": [entry["memory_id"]], "slice_tags": ["exact"],
        }
        for i, entry in enumerate(corpus)
    ]


def _answer(*memory_ids: str) -> str:
    return json.dumps({full_context.RESPONSE_KEY: list(memory_ids)})


class _StubLLM(twin.TwinningOrchestrator):
    """The shipped orchestrator with only the model round trip replaced."""

    def __init__(self, *args, responder=None, usage=None, **kwargs):
        super().__init__(*args, **kwargs)
        self._responder = responder or (lambda purpose, messages, kwargs: _answer())
        self._stub_usage = usage
        self.calls: list[dict] = []

    async def _live_chat(self, purpose, messages, **kwargs):
        self.calls.append({"purpose": purpose, "messages": messages, "kwargs": kwargs})
        if self._stub_usage is not None:
            self._log_usage(purpose, "stub-model", self._stub_usage)
        return self._responder(purpose, messages, kwargs)


def _gold_answering_responder(corpus, pairs):
    """Answers each query with its own gold memory id, read out of the
    prompt the arm actually built -- so a broken prompt fails the test."""
    by_query = {p["query"]: p["relevant_memory_ids"][0] for p in pairs}

    def responder(purpose, messages, kwargs):
        user = messages[1]["content"]
        for query, memory_id in by_query.items():
            if f"<query>\n{query}\n</query>" in user:
                return _answer(memory_id)
        return _answer()

    return responder


def _score(ranked, pairs, *, k=1, retrieval_limit=1, min_pairs=1) -> ScoreReport:
    return score_retrieval(
        ranked, pairs, retrieval_limit=retrieval_limit, k=k, min_pairs=min_pairs,
    )


def _twin(*, live=1, cache=1, tokens=None, embed=0) -> twin.Twin:
    """A twin with a controlled end_to_end population split and token block.

    ``live``/``cache`` are SAMPLE COUNTS, so a test can put an arm into the
    warm-replay or the live state the caveat derivations read.
    """
    recorder = twin.LatencyRecorder()
    for _ in range(live):
        recorder.record("end_to_end", 0.9, "live")
    for _ in range(cache):
        recorder.record("end_to_end", 0.001, "cache")
    for _ in range(embed):
        recorder.record("embed_query", 0.0001, "cache")
    captured = twin.Twin.capture(
        recorder, twin.TokenLedger(),
        min_samples=1, declared_channels=full_context.CHANNELS,
    )
    if tokens is None:
        return captured
    return twin.Twin(
        channels=captured.channels, tokens_by_purpose=tokens,
        min_samples_for_percentile=1,
    )


def _usage(**overrides) -> dict:
    base = {
        "live_calls": 0, "live_prompt_tokens": 0, "live_completion_tokens": 0,
        "live_cached_prompt_tokens": 0, "live_unknown_calls": 0,
        "cache_known_calls": 0, "cache_known_prompt_tokens": 0,
        "cache_known_completion_tokens": 0, "cache_known_cached_prompt_tokens": 0,
        "cache_unknown_calls": 0,
    }
    return {**base, **overrides}


def _eval_run(score, **twin_kwargs) -> twin.EvalRun:
    return twin.EvalRun(score=score, twin=_twin(**twin_kwargs))


def _comparison(
    corpus=None, pairs=None, context=None, retrieval_twin=None, full_context_twin=None,
) -> full_context.Comparison:
    corpus = corpus or _corpus()
    pairs = pairs or _pairs(corpus)
    perfect = {p["id"]: p["relevant_memory_ids"] for p in pairs}
    empty = {p["id"]: [] for p in pairs}
    return full_context.Comparison(
        retrieval=_eval_run(_score(perfect, pairs), **(retrieval_twin or {})),
        full_context=_eval_run(_score(empty, pairs), **(full_context_twin or {})),
        id_audit=full_context.IdAudit(queries=len(pairs)),
        context=context or full_context.build_context(corpus),
    )


def _kinds(comparison) -> set[str]:
    return {caveat.kind for caveat in comparison.caveats}


# ── prompt construction and the context-window policy (ruling 4) ─────────


def test_the_context_block_carries_every_corpus_entry_verbatim():
    corpus = _corpus(6)
    block = full_context.build_context(corpus)

    assert block.complete is True
    assert block.dropped_ids == ()
    assert [str(e["memory_id"]) for e in corpus] == list(block.included_ids)
    for entry in corpus:
        assert entry["memory_id"] in block.text
        assert entry["content"] in block.text


def test_every_query_shares_one_byte_identical_prompt_prefix():
    corpus = _corpus()
    block = full_context.build_context(corpus)
    first = full_context.build_messages(block.text, "query one", 10)
    second = full_context.build_messages(block.text, "query two", 10)

    assert first[0] == second[0]
    prefix = f"<corpus>\n{block.text}\n</corpus>"
    assert first[1]["content"].startswith(prefix)
    assert second[1]["content"].startswith(prefix)


def test_the_default_policy_declares_no_bound_at_all():
    block = full_context.build_context(_corpus(3))
    assert block.describe()["policy"] == {
        "kind": "no-truncation", "max_prompt_chars": None, "on_overflow": "raise",
    }
    assert block.describe()["dropped_entries"] == 0


def test_a_corpus_that_does_not_fit_raises_rather_than_truncating():
    with pytest.raises(ValueError, match="does not fit"):
        full_context.build_context(
            _corpus(6), full_context.ContextPolicy(max_prompt_chars=200),
        )


def test_an_explicit_bound_records_exactly_what_it_dropped():
    corpus = _corpus(6)
    block = full_context.build_context(
        corpus,
        full_context.ContextPolicy(max_prompt_chars=200, on_overflow="drop-tail"),
    )

    assert block.complete is False
    assert block.dropped_ids
    assert set(block.included_ids) | set(block.dropped_ids) == {
        str(e["memory_id"]) for e in corpus
    }
    for dropped in block.dropped_ids:
        assert dropped not in block.text
    described = block.describe()
    assert described["dropped_ids"] == list(block.dropped_ids)
    assert described["complete"] is False


def test_a_bounded_context_puts_a_caveat_on_every_number_it_affects():
    corpus = _corpus(6)
    bounded = full_context.build_context(
        corpus,
        full_context.ContextPolicy(max_prompt_chars=200, on_overflow="drop-tail"),
    )
    comparison = _comparison(corpus=corpus, context=bounded)

    assert full_context.CAVEAT_CONTEXT_TRUNCATED in _kinds(comparison)
    assert "CAVEAT" in full_context.render_comparison(comparison)
    assert comparison.to_ledger_payload()["comparison"]["caveats"] == [
        caveat.as_dict() for caveat in comparison.caveats
    ]


def test_an_unbounded_context_carries_no_caveat():
    comparison = _comparison()
    assert full_context.CAVEAT_CONTEXT_TRUNCATED not in _kinds(comparison)


# ── derived caveats: the qualifiers travel with the numbers ──────────────


def test_two_directly_comparable_arms_carry_no_caveat_at_all():
    """The anti-spurious proof. A caveat surface that fires on every run
    carries no information, so the empty list has to be reachable: two arms
    both measured live, both billing one call per pair, neither with
    unrecorded cost, and an untruncated context qualify nothing."""
    comparison = _comparison(
        retrieval_twin={
            "live": 4, "cache": 0,
            "tokens": {"extraction": _usage(live_calls=4)},
        },
        full_context_twin={
            "live": 4, "cache": 0,
            "tokens": {"reasoning": _usage(live_calls=4)},
        },
    )

    assert comparison.caveats == []
    rendered = full_context.render_comparison(comparison)
    assert "CAVEAT" not in rendered
    assert "caveats: none" in rendered
    assert comparison.to_ledger_payload()["comparison"]["caveats"] == []


def test_a_warm_arm_against_a_live_arm_is_flagged_not_like_for_like():
    comparison = _comparison(
        retrieval_twin={"live": 0, "cache": 4},
        full_context_twin={"live": 4, "cache": 0},
    )

    assert full_context.CAVEAT_LATENCY_NOT_LIKE_FOR_LIKE in _kinds(comparison)
    text = next(
        c.text for c in comparison.caveats
        if c.kind == full_context.CAVEAT_LATENCY_NOT_LIKE_FOR_LIKE
    )
    assert full_context.ARM_RETRIEVAL in text
    assert full_context.ARM_FULL_CONTEXT in text


def test_two_arms_measured_the_same_way_are_not_flagged_not_like_for_like():
    for population in ({"live": 4, "cache": 0}, {"live": 0, "cache": 4}):
        comparison = _comparison(
            retrieval_twin=population, full_context_twin=population,
        )
        assert full_context.CAVEAT_LATENCY_NOT_LIKE_FOR_LIKE not in _kinds(comparison)


def test_two_fully_warm_arms_are_flagged_as_measuring_no_live_latency():
    comparison = _comparison(
        retrieval_twin={"live": 0, "cache": 4},
        full_context_twin={"live": 0, "cache": 4},
    )

    assert full_context.CAVEAT_LATENCY_NO_LIVE_SAMPLES in _kinds(comparison)


def test_unrecorded_cost_is_flagged_and_named_by_arm_and_purpose():
    comparison = _comparison(
        retrieval_twin={"tokens": {"extraction": _usage(cache_unknown_calls=94)}},
        full_context_twin={"tokens": {"reasoning": _usage(live_calls=4)}},
    )

    text = next(
        c.text for c in comparison.caveats
        if c.kind == full_context.CAVEAT_COST_UNMEASURED
    )
    assert "94 extraction" in text
    assert full_context.ARM_RETRIEVAL in text


def test_fully_measured_cost_is_not_flagged_as_unrecorded():
    comparison = _comparison(
        retrieval_twin={"tokens": {"extraction": _usage(cache_known_calls=94)}},
        full_context_twin={"tokens": {"reasoning": _usage(live_calls=4)}},
    )

    assert full_context.CAVEAT_COST_UNMEASURED not in _kinds(comparison)


def test_a_per_query_arm_against_an_indexing_arm_is_flagged_as_a_kind_mismatch():
    """4 pairs: the full-context arm bills 4 calls (one per pair, recurring
    every run) while the retrieval arm bills 94 (one-time indexing). Those
    are different quantities and subtracting them is meaningless."""
    comparison = _comparison(
        retrieval_twin={
            "tokens": {"extraction": _usage(live_calls=94)}, "embed": 4,
        },
        full_context_twin={"tokens": {"reasoning": _usage(live_calls=4)}},
    )

    text = next(
        c.text for c in comparison.caveats
        if c.kind == full_context.CAVEAT_COST_KIND_ASYMMETRY
    )
    assert "one-time indexing work" in text
    assert "4 query-embedding call(s)" in text


def test_two_per_query_arms_are_not_flagged_as_a_kind_mismatch():
    comparison = _comparison(
        retrieval_twin={"tokens": {"reranker": _usage(live_calls=4)}},
        full_context_twin={"tokens": {"reasoning": _usage(live_calls=4)}},
    )

    assert full_context.CAVEAT_COST_KIND_ASYMMETRY not in _kinds(comparison)


def test_every_derived_caveat_reaches_both_the_payload_and_the_render():
    comparison = _comparison(
        retrieval_twin={
            "live": 0, "cache": 4,
            "tokens": {"extraction": _usage(cache_unknown_calls=94)},
        },
        full_context_twin={
            "live": 4, "cache": 0,
            "tokens": {"reasoning": _usage(live_calls=4)},
        },
    )

    assert _kinds(comparison) == {
        full_context.CAVEAT_LATENCY_NOT_LIKE_FOR_LIKE,
        full_context.CAVEAT_COST_UNMEASURED,
        full_context.CAVEAT_COST_KIND_ASYMMETRY,
    }
    payload = comparison.to_ledger_payload()["comparison"]["caveats"]
    assert {entry["kind"] for entry in payload} == _kinds(comparison)
    rendered = full_context.render_comparison(comparison)
    for caveat in comparison.caveats:
        assert f"CAVEAT [{caveat.kind}]" in rendered


def test_context_policy_rejects_an_unknown_overflow_mode():
    with pytest.raises(ValueError, match="on_overflow"):
        full_context.ContextPolicy(max_prompt_chars=10, on_overflow="truncate")


# ── parsing the answer, and the id audit (ruling 1) ──────────────────────


def test_a_clean_answer_is_kept_in_the_order_the_model_gave_it():
    corpus = _corpus(3)
    ids = [e["memory_id"] for e in corpus]
    parsed = full_context.parse_ranked_ids(_answer(ids[2], ids[0]), ids, 10)

    assert list(parsed.ranked_ids) == [ids[2], ids[0]]
    assert parsed.returned == 2
    assert (parsed.malformed, parsed.hallucinated, parsed.duplicate) == (0, 0, 0)


def test_a_malformed_id_is_dropped_and_counted():
    ids = [e["memory_id"] for e in _corpus(2)]
    parsed = full_context.parse_ranked_ids(_answer("not-a-uuid", ids[0]), ids, 10)

    assert list(parsed.ranked_ids) == [ids[0]]
    assert parsed.malformed == 1
    assert parsed.returned == 2


def test_an_id_absent_from_the_corpus_is_dropped_and_counted():
    ids = [e["memory_id"] for e in _corpus(2)]
    invented = str(uuid.uuid4())
    parsed = full_context.parse_ranked_ids(_answer(invented, ids[1]), ids, 10)

    assert list(parsed.ranked_ids) == [ids[1]]
    assert parsed.hallucinated == 1


def test_a_near_miss_id_is_never_repaired_onto_a_real_one():
    ids = [e["memory_id"] for e in _corpus(2)]
    near_miss = ids[0][:-1] + ("0" if ids[0][-1] != "0" else "1")
    parsed = full_context.parse_ranked_ids(_answer(near_miss), ids, 10)

    assert parsed.ranked_ids == ()
    assert parsed.hallucinated == 1


def test_a_repeated_id_is_dropped_and_counted():
    ids = [e["memory_id"] for e in _corpus(2)]
    parsed = full_context.parse_ranked_ids(_answer(ids[0], ids[0]), ids, 10)

    assert list(parsed.ranked_ids) == [ids[0]]
    assert parsed.duplicate == 1


def test_ids_beyond_the_declared_fetch_depth_are_dropped_and_counted():
    corpus = _corpus(5)
    ids = [e["memory_id"] for e in corpus]
    parsed = full_context.parse_ranked_ids(_answer(*ids), ids, 2)

    assert list(parsed.ranked_ids) == ids[:2]
    assert parsed.over_limit == 3


def test_an_unreadable_answer_is_reported_not_salvaged():
    ids = [e["memory_id"] for e in _corpus(2)]
    fenced = f"```json\n{_answer(ids[0])}\n```"
    parsed = full_context.parse_ranked_ids(fenced, ids, 10)

    assert parsed.unparseable is True
    assert parsed.ranked_ids == ()


def test_a_json_answer_of_the_wrong_shape_is_reported_not_guessed_at():
    ids = [e["memory_id"] for e in _corpus(2)]
    parsed = full_context.parse_ranked_ids(json.dumps({"answer": ids}), ids, 10)

    assert parsed.unparseable is True
    assert parsed.ranked_ids == ()


def test_a_bare_list_deviates_from_the_prompt_contract_and_is_counted():
    """The prompt asks for {"memory_ids": [...]}. A bare list is readable
    JSON, but accepting it would let a shape deviation pass uncounted."""
    ids = [e["memory_id"] for e in _corpus(2)]
    parsed = full_context.parse_ranked_ids(json.dumps(ids), ids, 10)

    assert parsed.unparseable is True
    assert parsed.ranked_ids == ()


def test_saying_nothing_is_relevant_is_kept_apart_from_saying_only_junk():
    ids = [e["memory_id"] for e in _corpus(2)]
    said_nothing = full_context.IdAudit()
    said_nothing.add(full_context.parse_ranked_ids(_answer(), ids, 10))
    said_only_junk = full_context.IdAudit()
    said_only_junk.add(
        full_context.parse_ranked_ids(_answer(str(uuid.uuid4())), ids, 10)
    )

    assert (said_nothing.responses_empty, said_nothing.responses_all_dropped) == (1, 0)
    assert (said_only_junk.responses_empty, said_only_junk.responses_all_dropped) == (0, 1)
    assert said_only_junk.ids_hallucinated == 1


def test_an_uppercase_id_still_matches_at_the_memory_id_boundary():
    """CLAUDE.md's first cross-cutting invariant: a same-value id in a
    different rendering must be normalised at one named boundary, not
    silently compared as unequal and scored as a miss."""
    ids = [e["memory_id"] for e in _corpus(2)]
    parsed = full_context.parse_ranked_ids(_answer(ids[0].upper()), ids, 10)

    assert list(parsed.ranked_ids) == [ids[0]]
    assert parsed.hallucinated == 0


def test_audit_rates_are_unknown_rather_than_zero_when_nothing_was_returned():
    audit = full_context.IdAudit()
    audit.add(full_context.ParsedRanking(unparseable=True))
    described = audit.as_dict()

    assert described["responses_unparseable"] == 1
    assert described["malformed_rate"] is None
    assert described["hallucinated_rate"] is None


def test_audit_rates_are_measured_once_something_was_returned():
    ids = [e["memory_id"] for e in _corpus(2)]
    audit = full_context.IdAudit()
    audit.add(full_context.parse_ranked_ids(_answer("junk", ids[0]), ids, 10))

    described = audit.as_dict()
    assert described["ids_returned"] == 2
    assert described["malformed_rate"] == 0.5
    assert described["kept_rate"] == 0.5


# ── the arm ──────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_the_arm_answers_every_live_pair_and_skips_retired_ones(tmp_path):
    corpus = _corpus()
    pairs = _pairs(corpus)
    pairs[1] = {**pairs[1], "retired": True}
    llm = _StubLLM(
        {}, cache_dir=str(tmp_path),
        responder=_gold_answering_responder(corpus, pairs),
    )

    run = await full_context.run_full_context(llm, corpus, pairs, limit=3)

    assert set(run.ranked_ids_by_pair) == {p["id"] for p in pairs if not p.get("retired")}
    assert run.audit.queries == len(pairs) - 1
    assert len(llm.calls) == len(pairs) - 1


@pytest.mark.asyncio
async def test_the_arms_output_scores_through_the_same_scorer(tmp_path):
    """Ruling 1: the same metric shape means this arm's output is fed to the
    same ``score_retrieval`` call the retrieval arm's output is."""
    corpus = _corpus()
    pairs = _pairs(corpus)
    llm = _StubLLM(
        {}, cache_dir=str(tmp_path),
        responder=_gold_answering_responder(corpus, pairs),
    )

    run = await full_context.run_full_context(llm, corpus, pairs, limit=3)
    report = score_retrieval(
        run.ranked_ids_by_pair, pairs, retrieval_limit=3, k=3, min_pairs=1,
    )

    assert isinstance(report, ScoreReport)
    assert report.aggregate_mrr == 1.0
    assert report.aggregate_hit_at_k == 1.0


@pytest.mark.asyncio
async def test_the_arm_dispatches_through_the_reasoning_purpose(tmp_path):
    """Ruling 2: not ``extraction``. The twin attributes cost per purpose, so
    a borrowed purpose would file this arm's cost under the ingest arm's."""
    corpus = _corpus(2)
    pairs = _pairs(corpus)
    llm = _StubLLM(
        {}, cache_dir=str(tmp_path), usage={"prompt_tokens": 900, "completion_tokens": 30},
        responder=_gold_answering_responder(corpus, pairs),
    )

    await full_context.run_full_context(llm, corpus, pairs, limit=2)

    assert {c["purpose"] for c in llm.calls} == {"reasoning"}
    tokens = llm.tokens.as_dict()
    assert set(tokens) == {"reasoning"}
    assert tokens["reasoning"]["live_prompt_tokens"] == 1800


@pytest.mark.asyncio
async def test_the_arm_forwards_a_content_derived_seed(tmp_path):
    from app.services.extraction import _content_seed

    corpus = _corpus(2)
    pairs = _pairs(corpus)
    llm = _StubLLM(
        {}, cache_dir=str(tmp_path),
        responder=_gold_answering_responder(corpus, pairs),
    )

    await full_context.run_full_context(llm, corpus, pairs, limit=2)

    for call in llm.calls:
        assert call["kwargs"]["seed"] == _content_seed(call["messages"][1]["content"])
    assert len({c["kwargs"]["seed"] for c in llm.calls}) == len(pairs)


@pytest.mark.asyncio
async def test_a_second_pass_over_the_same_corpus_costs_no_live_call(tmp_path):
    """Ruling 3: this is the expensive arm; a re-run must replay from disk."""
    corpus = _corpus()
    pairs = _pairs(corpus)
    responder = _gold_answering_responder(corpus, pairs)

    first = _StubLLM({}, cache_dir=str(tmp_path), responder=responder)
    first_run = await full_context.run_full_context(first, corpus, pairs, limit=3)

    second = _StubLLM({}, cache_dir=str(tmp_path), responder=responder)
    second_run = await full_context.run_full_context(second, corpus, pairs, limit=3)

    assert first.live_calls == len(pairs)
    assert second.live_calls == 0
    assert second_run.ranked_ids_by_pair == first_run.ranked_ids_by_pair


@pytest.mark.asyncio
async def test_live_and_cache_served_latency_stay_separate_populations(tmp_path):
    """Ruling 6: a replayed stuffed prompt is a disk read, not a model call,
    and must never enter the live latency distribution."""
    corpus = _corpus()
    pairs = _pairs(corpus)
    responder = _gold_answering_responder(corpus, pairs)

    first = _StubLLM({}, cache_dir=str(tmp_path), responder=responder)
    live_run = await full_context.run_full_context(first, corpus, pairs, limit=3)
    second = _StubLLM({}, cache_dir=str(tmp_path), responder=responder)
    warm_run = await full_context.run_full_context(second, corpus, pairs, limit=3)

    live = live_run.recorder.stats(
        min_samples=1, declared_channels=full_context.CHANNELS,
    )
    warm = warm_run.recorder.stats(
        min_samples=1, declared_channels=full_context.CHANNELS,
    )
    for channel in full_context.CHANNELS:
        assert live[channel].live.n == len(pairs)
        assert live[channel].cache.n == 0
        assert warm[channel].cache.n == len(pairs)
        assert warm[channel].live.n == 0


@pytest.mark.asyncio
async def test_a_twin_captured_from_the_arm_declares_only_its_own_channels(tmp_path):
    corpus = _corpus(2)
    pairs = _pairs(corpus)
    llm = _StubLLM(
        {}, cache_dir=str(tmp_path),
        responder=_gold_answering_responder(corpus, pairs),
    )

    run = await full_context.run_full_context(llm, corpus, pairs, limit=2)
    captured = twin.Twin.capture(
        run.recorder, llm.tokens, min_samples=1,
        declared_channels=full_context.CHANNELS,
    )

    assert set(captured.channels) == set(full_context.CHANNELS)
    assert "semantic_search" not in captured.channels


@pytest.mark.asyncio
async def test_a_truncated_answer_is_counted_rather_than_retried(tmp_path):
    from app.services.llm import LLMTruncationError

    corpus = _corpus(2)
    pairs = _pairs(corpus)

    def responder(purpose, messages, kwargs):
        raise LLMTruncationError("output cap reached")

    llm = _StubLLM({}, cache_dir=str(tmp_path), responder=responder)
    run = await full_context.run_full_context(llm, corpus, pairs, limit=2)

    assert run.audit.responses_truncated == len(pairs)
    assert all(ranked == [] for ranked in run.ranked_ids_by_pair.values())
    assert len(llm.calls) == len(pairs)


# ── the comparator: both sides, structurally (ruling 5) ──────────────────


def test_a_comparison_cannot_be_built_from_one_arm():
    corpus = _corpus()
    pairs = _pairs(corpus)
    run = _eval_run(_score({p["id"]: p["relevant_memory_ids"] for p in pairs}, pairs))

    with pytest.raises(TypeError, match="both sides"):
        full_context.Comparison(
            retrieval=run, full_context=None,
            id_audit=full_context.IdAudit(), context=full_context.build_context(corpus),
        )
    with pytest.raises(TypeError, match="both sides"):
        full_context.Comparison(
            retrieval=None, full_context=run,
            id_audit=full_context.IdAudit(), context=full_context.build_context(corpus),
        )


def test_a_comparison_cannot_be_built_from_a_bare_delta_dict():
    corpus = _corpus()
    with pytest.raises(TypeError, match="both sides"):
        full_context.Comparison(
            retrieval={"mrr_delta": -0.2}, full_context={"mrr_delta": -0.2},
            id_audit=full_context.IdAudit(), context=full_context.build_context(corpus),
        )


def test_a_comparison_refuses_a_score_the_shared_scorer_did_not_produce():
    corpus = _corpus()
    pairs = _pairs(corpus)
    real = _eval_run(_score({p["id"]: p["relevant_memory_ids"] for p in pairs}, pairs))
    hand_rolled = twin.EvalRun(score={"mrr": 0.9}, twin=_twin())

    with pytest.raises(TypeError, match="ScoreReport"):
        full_context.Comparison(
            retrieval=real, full_context=hand_rolled,
            id_audit=full_context.IdAudit(), context=full_context.build_context(corpus),
        )


def test_a_comparison_refuses_two_arms_scored_under_different_protocols():
    corpus = _corpus()
    pairs = _pairs(corpus)
    perfect = {p["id"]: p["relevant_memory_ids"] for p in pairs}

    with pytest.raises(ValueError, match="different protocols"):
        full_context.Comparison(
            retrieval=_eval_run(_score(perfect, pairs, k=1, retrieval_limit=1)),
            full_context=_eval_run(_score(perfect, pairs, k=3, retrieval_limit=3)),
            id_audit=full_context.IdAudit(), context=full_context.build_context(corpus),
        )


def test_a_comparison_refuses_two_arms_over_different_pair_sets():
    corpus = _corpus()
    pairs = _pairs(corpus)
    perfect = {p["id"]: p["relevant_memory_ids"] for p in pairs}
    # Same pair COUNT, different pair ids -- so the protocol check passes and
    # only the shared-pair-set check can catch this.
    renamed = [{**p, "id": p["id"].replace("fc-", "other-")} for p in pairs]

    with pytest.raises(ValueError, match="different gold pairs"):
        full_context.Comparison(
            retrieval=_eval_run(_score(perfect, pairs)),
            full_context=_eval_run(
                _score({p["id"]: p["relevant_memory_ids"] for p in renamed}, renamed)
            ),
            id_audit=full_context.IdAudit(), context=full_context.build_context(corpus),
        )


def test_the_ledger_payload_carries_both_arms_whole_metric_blocks():
    comparison = _comparison()
    payload = comparison.to_ledger_payload()["comparison"]

    assert set(payload["arms"]) == {
        full_context.ARM_RETRIEVAL, full_context.ARM_FULL_CONTEXT,
    }
    for arm in payload["arms"].values():
        assert arm["score"]["slices"]
        assert arm["score"]["aggregate_mrr"] is not None
        assert arm["twin"]["channels"]
        assert "tokens_by_purpose" in arm["twin"]
    assert payload["deltas"]["aggregate"]["mrr"] == -1.0
    assert payload["full_context_id_audit"]["queries"] == 4


def test_a_delta_is_unknown_where_either_side_is_under_powered():
    corpus = _corpus()
    pairs = _pairs(corpus)
    perfect = {p["id"]: p["relevant_memory_ids"] for p in pairs}
    empty = {p["id"]: [] for p in pairs}
    comparison = full_context.Comparison(
        retrieval=_eval_run(_score(perfect, pairs, min_pairs=99)),
        full_context=_eval_run(_score(empty, pairs, min_pairs=99)),
        id_audit=full_context.IdAudit(), context=full_context.build_context(corpus),
    )

    deltas = comparison.deltas()
    assert deltas["aggregate"]["mrr"] is None
    assert deltas["slices"]["exact"]["mrr"] is None


def test_the_rendered_report_states_both_sides_of_every_slice():
    comparison = _comparison()
    rendered = full_context.render_comparison(comparison)

    for arm in (full_context.ARM_RETRIEVAL, full_context.ARM_FULL_CONTEXT):
        assert f"--- {arm}: latency by channel" in rendered
        assert f"--- {arm}: token cost by purpose" in rendered
    for tag in comparison.retrieval.score.slices:
        line = next(line for line in rendered.splitlines() if line.startswith(tag))
        retrieval_slice = comparison.retrieval.score.slices[tag]
        full_slice = comparison.full_context.score.slices[tag]
        for value in (retrieval_slice.mrr, full_slice.mrr):
            assert ("n/a" if value is None else f"{value:.4f}") in line


def test_the_renderer_and_the_recorder_refuse_anything_but_a_comparison():
    with pytest.raises(TypeError, match="both arms"):
        full_context.render_comparison({"mrr_delta": -0.2})
    with pytest.raises(TypeError, match="both arms"):
        full_context.record_comparison({"mrr_delta": -0.2})


def test_a_recorded_comparison_round_trips_through_the_ledger(tmp_path):
    path = tmp_path / "comparison.jsonl"
    comparison = _comparison()

    full_context.record_comparison(comparison, path=path)

    runs = ledger.read_runs(path)
    assert len(runs) == 1
    assert runs[0] == json.loads(json.dumps(comparison.to_ledger_payload()))
