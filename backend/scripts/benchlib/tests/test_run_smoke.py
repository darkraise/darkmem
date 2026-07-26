import re

import pytest
from sqlalchemy import select

from benchlib import bench_db, run_smoke
from benchlib.caching_llm import CachingLLMOrchestrator
from benchlib.ingest import GateConfig, run_ingest

pytestmark = pytest.mark.usefixtures("_bench_db")


class _StubLLM(CachingLLMOrchestrator):
    """Stub the parent LLM calls so falsifiability tests need no live model."""
    async def _live_embed_batch(self, texts):
        return ([[0.1, 0.2, 0.3] for _ in texts], "stub-embed|3")

    async def _live_chat(self, purpose, messages, **kwargs):
        return (
            '{"entities": [], "relationships": [], "memory_type": "fact", '
            '"importance": 0.5, "summary": "s", "emotions": [], "flags": []}'
        )


class _MustNotGoLive(CachingLLMOrchestrator):
    """Raises instead of making a network call -- proves a code path would
    have reached the model rather than silently reporting live_calls == 0."""
    async def _live_embed_batch(self, texts):
        raise AssertionError("must not hit the model")

    async def _live_chat(self, purpose, messages, **kwargs):
        raise AssertionError("must not hit the model")


def _corpus(n: int) -> list[dict]:
    return [{"content": f"Fact number {i} about the smoke corpus."} for i in range(n)]


# ── require_deepseek_api_key ─────────────────────────────────────────


def test_require_deepseek_api_key_returns_the_env_value():
    assert run_smoke.require_deepseek_api_key({"DEEPSEEK_API_KEY": "sk-abc123"}) == "sk-abc123"


def test_require_deepseek_api_key_raises_a_readable_error_when_unset():
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        run_smoke.require_deepseek_api_key({})


def test_require_deepseek_api_key_raises_when_blank():
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        run_smoke.require_deepseek_api_key({"DEEPSEEK_API_KEY": ""})


# ── purpose_config_specs ─────────────────────────────────────────────


def test_purpose_config_specs_matches_the_pinned_live_stack():
    specs = {s["purpose"]: s for s in run_smoke.purpose_config_specs("sk-the-key")}

    assert specs["embedding"]["api_kind"] == "ollama"
    assert specs["embedding"]["base_url"] == "http://192.168.0.196:11434"
    assert specs["embedding"]["model"] == "qwen3-embedding:0.6b"
    assert specs["embedding"]["dimensions"] == 1024
    assert specs["embedding"]["api_key"] is None

    for purpose in ("extraction", "classification"):
        assert specs[purpose]["api_kind"] == "deepseek"
        assert specs[purpose]["base_url"] == "https://api.deepseek.com/v1"
        assert specs[purpose]["model"] == "deepseek-v4-flash"
        assert specs[purpose]["api_key"] == "sk-the-key"


def test_purpose_config_specs_seeds_reasoning_as_a_purpose_of_its_own():
    """The full-context baseline arm dispatches through ``reasoning``. It
    must not borrow ``extraction``'s row: benchlib.twin attributes token cost
    per purpose, so a shared purpose would file the full-context arm's cost
    under the ingest arm's."""
    specs = {s["purpose"]: s for s in run_smoke.purpose_config_specs("sk-the-key")}

    assert specs["reasoning"]["api_kind"] == "deepseek"
    assert specs["reasoning"]["base_url"] == "https://api.deepseek.com/v1"
    assert specs["reasoning"]["model"] == "deepseek-v4-flash"
    assert specs["reasoning"]["api_key"] == "sk-the-key"
    assert specs["reasoning"]["params"] == {"temperature": 0}

    # The no-borrowing rule as code rather than as a tautology: the arm's
    # purpose must be seeded here AND must not be one the ingest path already
    # spends under, or the twin's per-purpose attribution merges two arms.
    from benchlib import full_context
    assert full_context.FULL_CONTEXT_PURPOSE in specs
    assert full_context.FULL_CONTEXT_PURPOSE not in ("extraction", "classification")


@pytest.mark.asyncio
async def test_seed_llm_purpose_configs_writes_a_usable_reasoning_config():
    from app.services.config import get_llm_config

    await run_smoke.seed_llm_purpose_configs(bench_db.session_factory, "sk-reasoning")

    async with bench_db.session_factory() as session:
        cfg = await get_llm_config(session)

    assert cfg["reasoning"].api_kind == "deepseek"
    assert cfg["reasoning"].api_key == "sk-reasoning"
    assert cfg["reasoning"].params == {"temperature": 0}


def test_purpose_config_specs_never_puts_the_key_on_the_embedding_purpose():
    specs = run_smoke.purpose_config_specs("sk-the-key")
    embedding = next(s for s in specs if s["purpose"] == "embedding")
    assert "sk-the-key" not in repr(embedding)


# ── seed_llm_purpose_configs ──────────────────────────────────────────


@pytest.mark.asyncio
async def test_seed_llm_purpose_configs_writes_rows_get_llm_config_reads_back():
    from app.services.config import get_llm_config

    await run_smoke.seed_llm_purpose_configs(bench_db.session_factory, "sk-seed-test")

    async with bench_db.session_factory() as session:
        cfg = await get_llm_config(session)

    assert cfg["embedding"].api_kind == "ollama"
    assert cfg["embedding"].base_url == "http://192.168.0.196:11434"
    assert cfg["embedding"].dimensions == 1024
    assert cfg["extraction"].api_kind == "deepseek"
    assert cfg["extraction"].api_key == "sk-seed-test"
    assert cfg["classification"].api_kind == "deepseek"
    assert cfg["classification"].api_key == "sk-seed-test"


@pytest.mark.asyncio
async def test_seed_llm_purpose_configs_is_idempotent_across_a_reset():
    """reset_bench_db() drops every llm_* row on every call; the seed step
    must be safe to run again against a schema that either still has last
    run's rows (re-seed without a reset in between) or has none at all
    (fresh schema) -- both are real call patterns in run_smoke.main()."""
    await run_smoke.seed_llm_purpose_configs(bench_db.session_factory, "sk-first")
    await run_smoke.seed_llm_purpose_configs(bench_db.session_factory, "sk-second")

    from app.services.config import get_llm_config
    async with bench_db.session_factory() as session:
        rows = (await session.execute(
            select(run_smoke.LLMPurposeConfigRow.purpose)
        )).scalars().all()
        cfg = await get_llm_config(session)

    assert sorted(p for p in rows if p in ("embedding", "extraction", "classification")) == [
        "classification", "embedding", "extraction",
    ]
    assert cfg["extraction"].api_key == "sk-second"
    assert cfg["classification"].api_key == "sk-second"


# ── git_sha ────────────────────────────────────────────────────────────


def test_git_sha_returns_a_full_hex_sha():
    sha = run_smoke.git_sha()
    assert re.fullmatch(r"[0-9a-f]{40}", sha)


# ── build_run_record ──────────────────────────────────────────────────


def test_build_run_record_carries_all_six_ledger_fields():
    class _Result:
        fingerprint = "model|1024"
        gate_config = {"ml_profile_ref": None, "classification_mode": "simple", "relation_rescue": True}
        live_calls = 0

    record = run_smoke.build_run_record(_Result(), pass1_live_calls=5, sha="a" * 40)

    assert set(record) == {"run_id", "timestamp", "corpus_id", "fingerprint", "git_sha", "metrics"}
    assert record["corpus_id"] == run_smoke.CORPUS_ID
    assert record["fingerprint"] == "model|1024"
    assert record["git_sha"] == "a" * 40
    assert record["metrics"]["pass1_live_calls"] == 5
    assert record["metrics"]["pass2_live_calls"] == 0
    assert record["metrics"]["gate_config"] == _Result.gate_config
    # timestamp is UTC and ISO-formatted
    assert record["timestamp"].endswith("+00:00")


# ── find_outcome_failures / summarize_pass ─────────────────────────────


def _ok_outcome(memory_id="m-1", **overrides):
    outcome = {
        "memory_id": memory_id,
        "embed": "ok",
        "extract": "ok",
        "vector": "ok",
        "graph": "ok",
        "entities_count": 2,
        "relations_count": 1,
        "error": None,
    }
    outcome.update(overrides)
    return outcome


def test_find_outcome_failures_is_empty_for_a_healthy_pass():
    outcomes = [_ok_outcome("m-1"), _ok_outcome("m-2"), _ok_outcome("m-3")]
    assert run_smoke.find_outcome_failures(outcomes, expected_count=3) == []


def test_find_outcome_failures_catches_a_short_outcome_count():
    outcomes = [_ok_outcome("m-1")]
    failures = run_smoke.find_outcome_failures(outcomes, expected_count=3)
    assert any("expected 3" in f for f in failures)


@pytest.mark.parametrize("step", ["embed", "extract", "vector", "graph"])
def test_find_outcome_failures_catches_an_error_status_in_any_step(step):
    outcomes = [_ok_outcome("m-1", **{step: "error"})]
    failures = run_smoke.find_outcome_failures(outcomes, expected_count=1)
    assert any("m-1" in f and step in f for f in failures)


def test_find_outcome_failures_catches_a_non_null_error_even_with_ok_statuses():
    """A "partial" extract with a degraded-but-non-null error still fails
    the gate -- the review's exact wording is "no outcome has a non-null
    error," independent of whether any status field literally reads
    "error"."""
    outcomes = [_ok_outcome("m-1", extract="partial", error="Extraction degraded: timeout")]
    failures = run_smoke.find_outcome_failures(outcomes, expected_count=1)
    assert any("m-1" in f and "Extraction degraded" in f for f in failures)


def test_find_outcome_failures_does_not_look_at_live_calls_at_all():
    """This is the exact review scenario: live_calls == 0 (a warm cache)
    while the pipeline's own write failed underneath it. The check must
    catch the broken outcome regardless -- it has no live_calls parameter
    to consult in the first place."""
    outcomes = [_ok_outcome("m-1", vector="error", error="Vector write failed: boom")]
    failures = run_smoke.find_outcome_failures(outcomes, expected_count=1)
    assert failures != []


def test_find_work_shortfalls_is_empty_when_the_floor_is_met():
    outcomes = [_ok_outcome("m-1", entities_count=3, relations_count=2),
                _ok_outcome("m-2", entities_count=3, relations_count=1)]
    expected = {"memories": 2, "entities": 6, "relations": 3}
    assert run_smoke.find_work_shortfalls(outcomes, expected) == []


def test_find_work_shortfalls_catches_a_clean_pass_that_did_less_work():
    """The reviewed scenario: one cached chat entry replaced by VALID JSON
    carrying empty entities/relationships. Every outcome is ok, live calls
    are 0, and relations quietly drop 3 -> 2 against the healthy baseline."""
    outcomes = [_ok_outcome("m-1", entities_count=3, relations_count=2),
                _ok_outcome("m-2", entities_count=3, relations_count=0)]
    expected = {"memories": 2, "entities": 6, "relations": 3}

    assert run_smoke.find_outcome_failures(outcomes, expected_count=2) == []
    failures = run_smoke.find_work_shortfalls(outcomes, expected)
    assert failures == ["expected at least 3 relations, got 2"]


def test_find_work_shortfalls_reports_every_count_that_fell_short():
    outcomes = [_ok_outcome("m-1", entities_count=1, relations_count=0)]
    failures = run_smoke.find_work_shortfalls(
        outcomes, {"memories": 3, "entities": 6, "relations": 3},
    )
    assert len(failures) == 3


def test_find_work_shortfalls_has_no_floor_for_a_corpus_that_declares_none():
    """Gold corpora carry no expectations; absence must not synthesise a
    floor of zero or crash the gate."""
    outcomes = [_ok_outcome("m-1", entities_count=0, relations_count=0)]
    assert run_smoke.find_work_shortfalls(outcomes, None) == []


def test_the_gate_reads_its_floor_from_the_corpus_not_from_this_module():
    """The numbers are declared data. A future corpus edit must move the
    floor without touching run_smoke.py."""
    from benchlib import corpus as corpus_module

    declared = corpus_module.load_expectations(run_smoke.CORPUS_PATH)
    assert declared == {"memories": 3, "entities": 6, "relations": 3}

    source = (run_smoke.HERE / "run_smoke.py").read_text(encoding="utf-8")
    assert "load_expectations" in source


def test_summarize_pass_totals_entities_and_relations():
    outcomes = [_ok_outcome("m-1", entities_count=2, relations_count=1),
                _ok_outcome("m-2", entities_count=3, relations_count=0)]
    summary = run_smoke.summarize_pass(outcomes)
    assert "2 memories ingested" in summary
    assert "5 entities" in summary
    assert "1 relations" in summary


# ── outcome-health gate: reproduces the reviewed bug directly ─────────


@pytest.mark.asyncio
async def test_gate_fails_when_a_write_errors_even_though_live_calls_is_zero(tmp_path):
    """Direct reproduction of the review finding: the stale
    embedder_registry cache this task's bench_db.py fix addresses left a
    fingerprint marked "known" while its partition table was gone, so a
    fully-cached pass (live_calls == 0) silently failed every vector
    write. Simulate that exact state by hand (mark the fingerprint known,
    then drop its table out from under it) and confirm
    find_outcome_failures flags it even though the run made zero live
    calls."""
    from sqlalchemy import text as sa_text
    from app.services.embedder_registry import child_table, embedder_registry

    cache_dir = tmp_path / "cache"
    entries = _corpus(1)
    gate = GateConfig()

    warm = _StubLLM({}, cache_dir=str(cache_dir))
    healthy = await run_ingest(warm, entries, gate)
    assert healthy.live_calls > 0
    assert run_smoke.find_outcome_failures(healthy.outcomes, len(entries)) == []

    fingerprint = healthy.fingerprint
    table = child_table("memory_embeddings", fingerprint)
    try:
        async with bench_db.engine.begin() as conn:
            await conn.execute(sa_text(f"DROP TABLE {table} CASCADE"))
        # embedder_registry still believes `fingerprint` is known -- this
        # is the exact stale state a second reset_bench_db() used to leave
        # behind before the bench_db.py fix (that fix now forgets it on
        # every reset; here we recreate the state directly, without a
        # reset, to test find_outcome_failures in isolation).
        assert embedder_registry.is_known(fingerprint)

        cold = _StubLLM({}, cache_dir=str(cache_dir))
        broken = await run_ingest(cold, entries, gate)

        assert broken.live_calls == 0
        failures = run_smoke.find_outcome_failures(broken.outcomes, len(entries))
        assert failures, "expected the gate to flag the silently-failed vector write"
        assert any("vector" in f for f in failures)
    finally:
        embedder_registry.forget(fingerprint)


# ── falsifiability: the zero-call assertion must be able to fail ──────


@pytest.mark.asyncio
async def test_gate_would_fail_without_a_cache_hit(tmp_path):
    """Minimum falsifiability bar: a fresh cache directory produces a
    nonzero live_calls count (the honest "pass 1" shape)."""
    warm = _StubLLM({}, cache_dir=str(tmp_path))
    first = await run_ingest(warm, _corpus(2), GateConfig())
    assert first.live_calls > 0


@pytest.mark.asyncio
async def test_wiping_the_cache_directory_makes_the_next_pass_reach_live_again(tmp_path):
    """Stronger falsifiability bar: populate a cache dir for real, confirm a
    second pass against it is fully cached, then wipe the directory and show
    the exact same entries now attempt a live call instead of silently
    reporting zero.

    ProcessingPipeline catches a phase's exception and marks that memory's
    outcome "error" rather than letting it propagate (CLAUDE.md's Phase-1
    contract), so _MustNotGoLive's AssertionError surfaces as an "error"
    outcome, not a raised exception out of run_ingest -- this asserts on
    that outcome instead of a pytest.raises, and is the real signal that a
    live call was attempted. Proves the zero on an intact cache is not a
    counter that can only ever read zero.
    """
    from app.config import LLMPurposeConfig

    cache_dir = tmp_path / "cache"
    entries = _corpus(2)
    gate = GateConfig()
    config = {"embedding": LLMPurposeConfig(model="stub-embed", dimensions=3)}

    warm = _StubLLM(config, cache_dir=str(cache_dir))
    first = await run_ingest(warm, entries, gate)
    assert first.live_calls > 0
    assert all(o["embed"] == "ok" for o in first.outcomes)

    still_warm = _MustNotGoLive(config, cache_dir=str(cache_dir))
    second = await run_ingest(still_warm, entries, gate)
    assert second.live_calls == 0
    assert all(o["embed"] == "ok" for o in second.outcomes)

    for cached_file in cache_dir.iterdir():
        cached_file.unlink()

    wiped = _MustNotGoLive(config, cache_dir=str(cache_dir))
    third = await run_ingest(wiped, entries, gate)
    assert all(o["embed"] == "error" for o in third.outcomes)


# ── main() plumbing ─────────────────────────────────────────────────


def test_main_reports_blocked_before_touching_the_db_when_key_is_unset(monkeypatch):
    """A missing key must fail fast and readable, not surface as a vendor
    401 partway through a run."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    import asyncio
    with pytest.raises(RuntimeError, match="DEEPSEEK_API_KEY"):
        asyncio.run(run_smoke.main())


def test_main_refuses_a_corpus_that_yields_zero_entries(monkeypatch, tmp_path, capsys):
    """A gate whose worst-case failure mode is a silent green is the one
    shape this batch was told not to ship: with no entries, both passes
    report zero memories as clean and pass-2 live calls are trivially 0.
    Nothing here may reach the database."""
    import asyncio

    empty = tmp_path / "corpus.json"
    empty.write_text('{"memories": []}', encoding="utf-8")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-not-used")
    monkeypatch.setattr(run_smoke, "CORPUS_PATH", empty)

    async def _must_not_run(*args, **kwargs):
        raise AssertionError("the gate reset the bench DB for a corpus of nothing")

    monkeypatch.setattr(run_smoke, "_reset_and_seed", _must_not_run)

    assert asyncio.run(run_smoke.main()) == 1
    assert "zero entries" in capsys.readouterr().err


def test_main_refuses_a_corpus_whose_memories_key_was_renamed(monkeypatch, tmp_path):
    """The same merge accident from the other side: the loader rejects the
    file outright rather than handing the gate an empty list."""
    import asyncio

    typo = tmp_path / "corpus.json"
    typo.write_text('{"memoires": [{"content": "x"}]}', encoding="utf-8")
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-not-used")
    monkeypatch.setattr(run_smoke, "CORPUS_PATH", typo)

    async def _must_not_run(*args, **kwargs):
        raise AssertionError("the gate reset the bench DB for an unreadable corpus")

    monkeypatch.setattr(run_smoke, "_reset_and_seed", _must_not_run)

    with pytest.raises(ValueError, match="no 'memories' key"):
        asyncio.run(run_smoke.main())
