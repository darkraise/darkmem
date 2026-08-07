"""T2.108 — the measurement corpus's design, and the two mechanisms it rests on.

Two halves, deliberately split the way ``test_retrieval_gold`` /
``test_retrieval_seed`` are. The pure half validates the committed corpus and
the guards that keep its corroboration structure honest; the DB-backed half
proves the two things the corpus needs from the harness and that no other test
covers — that the seeder writes ``origin_key`` at all (T2.40's root cause), and
that the capture-time stamp touches one column of one source kind.
"""
import copy
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select, text

from benchlib import bench_db, promotion_corpus as pc


# ── the committed corpus, and the guards on its design ────────────────────


@pytest.fixture(scope="module")
def entries():
    return pc.load_promotion_corpus()


def test_corpus_loads_and_covers_every_group(entries):
    groups = {entry["group"] for entry in entries}
    assert groups == pc.CORPUS_GROUPS


def test_every_capture_carries_an_attributable_origin(entries):
    for entry in entries:
        origin = entry["origin_key"].strip().lower()
        assert origin
        assert origin != "unknown"
        assert not origin.startswith("unknown:")


def test_memory_ids_are_derived_stable_and_unique(entries):
    ids = [entry["memory_id"] for entry in entries]
    assert len(set(ids)) == len(ids)
    for entry in entries:
        assert entry["memory_id"] == pc.memory_id_for_key(entry["key"])
        uuid.UUID(entry["memory_id"])


def test_all_three_gate_buckets_have_enough_claims_to_be_powered(entries):
    """The corpus must be able to power every bucket, by its own design.

    Not a restatement of the measured result: this counts *claims* in the
    corpus definition, so a corpus edited down below the committed power floor
    fails here rather than at the next gate run.
    """
    from benchlib.promotion_bars import PROMOTION_BAR_DEFAULTS

    floor = PROMOTION_BAR_DEFAULTS["promotion_rate_min_eligible"]
    claims_per_group: dict[str, set[str]] = {}
    for entry in entries:
        claims_per_group.setdefault(entry["group"], set()).add(
            pc.claim_key(entry["key"])
        )
    for group in ("diversity", "time_gap", "none"):
        assert len(claims_per_group[group]) >= floor, group


def test_corpus_carries_enough_promotable_claims_for_the_audit(entries):
    """The false-promotion audit's denominator floor, checked in the corpus."""
    from benchlib.promotion_bars import PROMOTION_BAR_DEFAULTS

    promotable = {
        pc.claim_key(entry["key"])
        for entry in entries
        if entry["group"] not in pc.NON_PROMOTING_GROUPS
    }
    assert len(promotable) >= PROMOTION_BAR_DEFAULTS["false_promotion_min_corroborations"]


def test_claim_key_strips_only_a_single_character_variant():
    assert pc.claim_key("at-k8s-a") == "at-k8s"
    assert pc.claim_key("ld-postgres-3") == "ld-postgres"
    assert pc.claim_key("pg-httpx") == "pg-httpx"
    assert pc.claim_key("ld-undersourced-1") == "ld-undersourced"


@pytest.mark.parametrize("origin", [None, "", "   ", "unknown", "unknown:mcp:default"])
def test_loader_refuses_an_unattributed_origin(tmp_path, entries, origin):
    """T2.40's defect, refused at the door.

    An entry whose origin folds into the reserved unknown bucket cannot
    corroborate anything, and one arriving by accident is indistinguishable
    from a fact that merely failed to promote.
    """
    import json

    broken = copy.deepcopy(entries)
    broken[0]["origin_key"] = origin
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({"memories": broken}), encoding="utf-8")
    with pytest.raises(ValueError, match="origin_key"):
        pc.load_promotion_corpus(path)


def test_design_guard_refuses_an_echo_that_grew_a_second_origin(entries):
    """The tempting edit: give each save its own origin and everything promotes."""
    broken = copy.deepcopy(entries)
    echoes = [e for e in broken if e["group"] == "echo"]
    assert len(echoes) >= 2
    echoes[1]["origin_key"] = "codex:deadbeef"
    with pytest.raises(ValueError, match="at most 1"):
        pc.validate_corroboration_design(broken)


def test_design_guard_refuses_a_time_gap_pair_pulled_inside_the_window(entries):
    broken = copy.deepcopy(entries)
    pair = [e for e in broken if e["group"] == "time_gap"]
    claim = pc.claim_key(pair[0]["key"])
    members = sorted(
        (e for e in pair if pc.claim_key(e["key"]) == claim),
        key=lambda e: e["created_at"],
    )
    assert len(members) == 2
    earlier = datetime.fromisoformat(members[0]["created_at"])
    members[1]["created_at"] = (earlier + timedelta(days=1)).isoformat()
    with pytest.raises(ValueError, match="time-gap gate needs"):
        pc.validate_corroboration_design(broken)


def test_design_guard_refuses_a_none_claim_stretched_past_the_gap(entries):
    broken = copy.deepcopy(entries)
    trio = [e for e in broken if e["group"] == "none"]
    claim = pc.claim_key(trio[0]["key"])
    members = sorted(
        (e for e in trio if pc.claim_key(e["key"]) == claim),
        key=lambda e: e["created_at"],
    )
    earliest = datetime.fromisoformat(members[0]["created_at"])
    members[-1]["created_at"] = (earliest + timedelta(days=30)).isoformat()
    with pytest.raises(ValueError, match="time-gap gate fires"):
        pc.validate_corroboration_design(broken)


def test_design_guard_refuses_a_none_claim_short_of_origins(entries):
    broken = copy.deepcopy(entries)
    trio = [e for e in broken if e["group"] == "none"]
    claim = pc.claim_key(trio[0]["key"])
    members = [e for e in trio if pc.claim_key(e["key"]) == claim]
    shared = members[0]["origin_key"]
    for member in members:
        member["origin_key"] = shared
    with pytest.raises(ValueError, match="at least 3"):
        pc.validate_corroboration_design(broken)


def test_repo_fixture_imports_are_derivable_dependencies():
    """Every fixture import must survive the deriver's own two refusals.

    A target the deriver declines (a stdlib module, a name matching an indexed
    file's suffix) asserts nothing, so the memory that names it would have no
    second origin and would quietly drop out of the diversity bucket.
    """
    from app.services.code_deriver import dependency_name, is_internal_import
    from app.services.suffix_index import SuffixIndex

    fixture = pc.load_repo_fixture()
    paths = [entry["file_path"] for entry in fixture["files"]]
    index = SuffixIndex(paths)
    for edge in fixture["imports"]:
        target = edge["target_key"]
        assert not is_internal_import(target, index), target
        assert dependency_name(target) is not None, target
    assert {edge["source_key"] for edge in fixture["imports"]} <= set(paths)


# ── the two mechanisms, against the real bench database ───────────────────


_PROBE_ORIGIN = "claude-code:t2108probe"
_PROBE_ENTRIES = [
    {
        "key": "t2108-probe-a",
        "memory_id": str(uuid.uuid5(pc.MEMORY_ID_NAMESPACE, "t2108-probe-a")),
        "content": "The probe service uses the probe datastore.",
        "memory_type": "fact",
        "project": "t2108-probe",
        "source": "claude-code",
        "origin_key": _PROBE_ORIGIN,
        "created_at": "2026-02-03T09:00:00+00:00",
    },
]


@pytest.mark.usefixtures("_bench_db")
class TestAgainstBenchDatabase:
    @pytest.mark.asyncio
    async def test_seeder_writes_origin_key_onto_the_memory_row(self):
        """The root cause T2.40 traced, fixed and asserted on disk.

        ``origin_key`` is absent from ``MemoryResponse``, so no door echoes it
        and only a direct database read can observe it — which is why this
        reads the row rather than the seeder's return value.
        """
        from app.models.memory import Memory

        await pc.seed_memory_rows(bench_db.session_factory, copy.deepcopy(_PROBE_ENTRIES))
        async with bench_db.session_factory() as session:
            row = (
                await session.execute(
                    select(Memory).where(
                        Memory.id == uuid.UUID(_PROBE_ENTRIES[0]["memory_id"])
                    )
                )
            ).scalar_one()
        assert row.origin_key == _PROBE_ORIGIN
        assert row.project == "t2108-probe"
        assert row.created_at == datetime(2026, 2, 3, 9, 0, tzinfo=timezone.utc)

    @pytest.mark.asyncio
    async def test_capture_time_stamp_moves_memory_rows_and_nothing_else(self):
        from app.repositories.fact_sources import FactSourceRepository
        from app.repositories.knowledge_triples import KnowledgeTripleRepository

        memory_id = uuid.uuid5(pc.MEMORY_ID_NAMESPACE, "t2108-stamp-probe")
        captured = datetime(2026, 1, 9, 7, 30, tzinfo=timezone.utc)
        entry = {
            **_PROBE_ENTRIES[0],
            "key": "t2108-stamp-probe",
            "memory_id": str(memory_id),
            "created_at": captured.isoformat(),
        }
        await pc.seed_memory_rows(bench_db.session_factory, [entry])

        async with bench_db.session_factory() as session:
            fact = await KnowledgeTripleRepository(session).insert_open(
                triple_key="t2108-stamp-probe-key",
                subject_name="probe service",
                object_name="probe datastore",
                rel_type="USES",
                fact="probe service uses probe datastore",
                reference_time=captured,
                project="t2108-probe",
            )
            sources = FactSourceRepository(session)
            await sources.add_source(
                fact_id=fact["id"], source_kind="memory",
                source_ref=str(memory_id), origin_key=_PROBE_ORIGIN,
            )
            await sources.add_source(
                fact_id=fact["id"], source_kind="code",
                source_ref=str(uuid.uuid4()), origin_key="repo-probe",
                detail={"basis": "import"},
            )
            await session.commit()

        stamped = await pc.simulate_capture_time_provenance(bench_db.session_factory)
        assert stamped >= 1

        async with bench_db.session_factory() as session:
            rows = (
                await session.execute(
                    text(
                        "SELECT source_kind, source_ref, origin_key, detail, created_at "
                        "FROM fact_sources WHERE fact_id = CAST(:id AS uuid)"
                    ),
                    {"id": fact["id"]},
                )
            ).mappings().all()
        by_kind = {row["source_kind"]: row for row in rows}
        assert by_kind["memory"]["created_at"] == captured
        assert by_kind["memory"]["origin_key"] == _PROBE_ORIGIN
        assert by_kind["memory"]["detail"] is None
        # The repository really was indexed now; only the memory half is a
        # backfill of a capture that happened earlier.
        assert by_kind["code"]["created_at"] > captured
        assert by_kind["code"]["detail"] == {"basis": "import"}
