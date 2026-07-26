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
