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

from app.services import relations
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


def _claims_promoting_without_the_time_gate(entries) -> set[str]:
    """Claims that corroborate on the ``--no-capture-time-simulation`` pass.

    Without the simulated clock every ``fact_sources`` row carries its write
    time, so the time-gap gate cannot fire and the ``time_gap`` claims hold at
    two origins against N=3.
    """
    return {
        pc.claim_key(entry["key"])
        for entry in entries
        if entry["group"] not in pc.NON_PROMOTING_GROUPS
        and entry["group"] != "time_gap"
    }


def test_corpus_clears_the_audit_band_on_both_passes(entries):
    """Past the band, not merely past the decidability floor.

    One genuine false promotion in a window of N corroborations is a rate of
    ``1/N``, so a corpus anywhere in 20–99 is either vacuous or failing however
    correct the ladder is. The corpus is what moves; the bar is derived from
    ``promotion_bars`` rather than restated, so tightening the bar tightens this
    check and loosening it can never quietly satisfy it.
    """
    import math

    from benchlib.promotion_bars import PROMOTION_BAR_DEFAULTS

    bar = PROMOTION_BAR_DEFAULTS["verification_false_promotion_bar"]
    needed = math.floor(1 / bar) + 1
    unsimulated = _claims_promoting_without_the_time_gate(entries)
    assert len(unsimulated) >= needed, (
        f"{len(unsimulated)} claims corroborate without the simulated capture "
        f"clock; one dispute against that denominator is "
        f"{1 / len(unsimulated):.4f}, and the bar is a strict < {bar}"
    )


def test_the_arming_pair_is_one_claim_the_audit_can_count(entries):
    """The arm has to be armed against a claim that corroborates first."""
    unsimulated = _claims_promoting_without_the_time_gate(entries)
    subject = {
        pc.claim_key(entry["key"])
        for entry in entries
        if entry["group"] == pc.ARMING_SUBJECT_GROUP
    }
    assert len(subject) == 1
    assert subject <= unsimulated


def test_claim_key_strips_only_a_single_character_variant():
    assert pc.claim_key("at-k8s-a") == "at-k8s"
    assert pc.claim_key("ld-postgres-3") == "ld-postgres"
    assert pc.claim_key("pg-httpx") == "pg-httpx"
    assert pc.claim_key("ld-undersourced-1") == "ld-undersourced"


def test_loader_refuses_a_variant_marker_with_no_sibling(entries):
    """``claim_key``'s convention, guarded where it is fragile.

    A lone ``pg-c`` reads as a variant of an invented claim ``pg``, and the
    design check would then validate a grouping nobody wrote down.
    """
    broken = copy.deepcopy(entries)
    broken[0] = {**broken[0], "key": "pg-c"}
    with pytest.raises(ValueError, match="no other entry shares the claim"):
        pc.validate_claim_key_convention(broken)


def test_the_committed_corpus_keeps_the_claim_key_convention(entries):
    pc.validate_claim_key_convention(entries)


def test_every_diversity_claim_is_seconded_by_a_fixture_import(entries):
    """The cross-file half of the diversity design, proven rather than assumed."""
    resolved = pc.validate_diversity_group_against_fixture(
        entries, pc.load_repo_fixture()
    )
    claims = {
        pc.claim_key(entry["key"])
        for entry in entries
        if entry["group"] == "diversity"
    }
    assert set(resolved) == claims
    assert len(set(resolved.values())) == len(resolved)


def test_diversity_guard_refuses_a_claim_whose_import_is_missing(entries):
    """The silent edit: a claim loads, validates, runs — and holds at one origin."""
    fixture = pc.load_repo_fixture()
    fixture["imports"] = [
        edge for edge in fixture["imports"] if edge["target_key"] != "redis"
    ]
    with pytest.raises(ValueError, match="names none of the repository's"):
        pc.validate_diversity_group_against_fixture(entries, fixture)


def test_diversity_guard_refuses_two_claims_naming_one_dependency(entries):
    broken = copy.deepcopy(entries)
    claims = [e for e in broken if e["group"] == "diversity"]
    claims[0]["content"] = claims[1]["content"] + " (restated)"
    with pytest.raises(ValueError, match="both name"):
        pc.validate_diversity_group_against_fixture(broken, pc.load_repo_fixture())


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


# ── the arming design, and every way it goes quietly vacuous ──────────────


def _arming(entries, group):
    return [entry for entry in entries if entry["group"] == group]


def test_the_committed_corpus_keeps_the_arming_design(entries):
    pc.validate_arming_design(entries)


def test_loader_refuses_a_measured_claim_held_back_to_wave_two(tmp_path, entries):
    import json

    broken = copy.deepcopy(entries)
    victim = next(e for e in broken if e["group"] == "none")
    victim["wave"] = 2
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({"memories": broken}), encoding="utf-8")
    with pytest.raises(ValueError, match="Only the arming groups"):
        pc.load_promotion_corpus(path)


def test_arming_guard_refuses_a_counterpart_that_arrives_in_wave_one(entries):
    """The vacuum this whole design exists to avoid.

    A counterpart present from the start disputes the fact straight out of
    ``candidate``: the veto is checked before the count, so the fact is never
    journaled ``corroborated`` and the audit's numerator reads 0 with the arm
    fully armed.
    """
    broken = copy.deepcopy(entries)
    for entry in _arming(broken, pc.ARMING_COUNTERPART_GROUP):
        entry["wave"] = 1
    with pytest.raises(ValueError, match="no corroboration to count against"):
        pc.validate_arming_design(broken)


def test_arming_guard_refuses_a_counterpart_sharing_the_subject_origin(entries):
    """The veto's echo test asks whether the counterpart brings a new witness."""
    broken = copy.deepcopy(entries)
    subject = _arming(broken, pc.ARMING_SUBJECT_GROUP)[0]
    for entry in _arming(broken, pc.ARMING_COUNTERPART_GROUP):
        entry["origin_key"] = subject["origin_key"]
    with pytest.raises(ValueError, match="a shared origin is an echo"):
        pc.validate_arming_design(broken)


def test_arming_guard_refuses_a_subject_with_no_wave_two_re_assertion(entries):
    """Without it nothing re-enqueues the corroborated fact for the fast arm."""
    broken = [
        entry for entry in copy.deepcopy(entries)
        if not (
            entry["group"] == pc.ARMING_SUBJECT_GROUP
            and entry.get("wave", pc.DEFAULT_WAVE) == 2
        )
    ]
    with pytest.raises(ValueError, match="no wave-2 entry"):
        pc.validate_arming_design(broken)


def test_arming_guard_refuses_a_subject_short_of_origins_in_wave_one(entries):
    broken = copy.deepcopy(entries)
    first = pc.entries_for_wave(_arming(broken, pc.ARMING_SUBJECT_GROUP), 1)
    for entry in first[1:]:
        entry["origin_key"] = first[0]["origin_key"]
    with pytest.raises(ValueError, match="origin\\(s\\) in wave 1"):
        pc.validate_arming_design(broken)


def test_arming_guard_refuses_a_subject_stretched_past_the_gap(entries):
    """A time-gap-carried subject would not corroborate on the unsimulated pass."""
    broken = copy.deepcopy(entries)
    first = sorted(
        pc.entries_for_wave(_arming(broken, pc.ARMING_SUBJECT_GROUP), 1),
        key=lambda entry: entry["created_at"],
    )
    earliest = datetime.fromisoformat(first[0]["created_at"])
    first[-1]["created_at"] = (earliest + timedelta(days=30)).isoformat()
    with pytest.raises(ValueError, match="unsimulated pass"):
        pc.validate_arming_design(broken)


def test_arming_guard_refuses_a_counterpart_that_is_not_the_inverse(entries):
    broken = copy.deepcopy(entries)
    for entry in _arming(broken, pc.ARMING_COUNTERPART_GROUP):
        subject, obj = entry["replaces"]
        # the subject claim's own direction, which contradicts nothing
        entry["replaces"] = [obj, subject]
        entry["content"] = f"{obj} replaces {subject} after the rollback."
    with pytest.raises(ValueError, match="not the inverse"):
        pc.validate_arming_design(broken)


def test_arming_guard_refuses_a_declared_name_the_content_never_states(entries):
    broken = copy.deepcopy(entries)
    counterpart = _arming(broken, pc.ARMING_COUNTERPART_GROUP)[0]
    counterpart["content"] = "The warehouse rollback is complete."
    with pytest.raises(ValueError, match="never names"):
        pc.validate_arming_design(broken)


def test_arming_guard_refuses_a_measured_claim_in_the_arming_project(entries):
    """A REPLACES memory supersedes its project; measured claims stay out of it."""
    broken = copy.deepcopy(entries)
    arming_project = _arming(broken, pc.ARMING_SUBJECT_GROUP)[0]["project"]
    victim = next(entry for entry in broken if entry["group"] == "none")
    victim["project"] = arming_project
    with pytest.raises(ValueError, match="share the arming project"):
        pc.validate_arming_design(broken)


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

    @staticmethod
    async def _open_replacement(project, key, subject, obj, origins):
        """One open REPLACES fact with the named attributable origins."""
        from app.repositories.fact_sources import FactSourceRepository
        from app.repositories.knowledge_triples import KnowledgeTripleRepository

        async with bench_db.session_factory() as session:
            fact = await KnowledgeTripleRepository(session).insert_open(
                triple_key=key,
                subject_name=subject,
                object_name=obj,
                rel_type="REPLACES",
                fact=f"{subject} replaces {obj}",
                reference_time=datetime(2026, 6, 10, tzinfo=timezone.utc),
                project=project,
            )
            sources = FactSourceRepository(session)
            for origin in origins:
                await sources.add_source(
                    fact_id=fact["id"], source_kind="memory",
                    source_ref=str(uuid.uuid4()), origin_key=origin,
                )
            await session.commit()
        return fact

    @staticmethod
    async def _recompute(fact_id):
        from app.services.verification_ladder import recompute_fact

        async with bench_db.session_factory() as session:
            decision = await recompute_fact(session, fact_id)
            await session.commit()
        return decision

    @pytest.mark.asyncio
    async def test_a_later_counterpart_disputes_an_already_corroborated_fact(self):
        """The property the corpus's two waves exist to reach.

        ``decide`` checks the veto ahead of both the count and the
        already-corroborated hold, and the demotion hysteresis is interposed
        only on ``demote`` — so a counterpart that arrives after the promotion
        flips the fact sideways at once, which is exactly the
        corroborated-then-disputed pair the false-promotion audit's numerator
        joins on.
        """
        project = "t2129-order"
        subject = await self._open_replacement(
            project, "t2129-order-subject", "t2129-alpha", "t2129-beta",
            ("t2129:a", "t2129:b", "t2129:c"),
        )

        promoted = await self._recompute(subject["id"])
        assert (promoted.outcome, promoted.target_status) == (
            "promote", "corroborated"
        )

        await self._open_replacement(
            project, "t2129-order-counterpart", "t2129-beta", "t2129-alpha",
            ("t2129:d",),
        )
        disputed = await self._recompute(subject["id"])
        assert (disputed.outcome, disputed.target_status) == ("dispute", "disputed")

        async with bench_db.session_factory() as session:
            back = await pc.read_back(session)
        rows = [row for row in back.disputes if row["project"] == project]
        assert len(rows) == 1, rows
        row = rows[0]
        assert row["rule"] == "inverse_replacement"
        assert row["witness_origin"] == "t2129:d"
        assert row["corroborated_first"] is True
        assert (row["counterpart_subject"], row["counterpart_object"]) == (
            "t2129-beta", "t2129-alpha"
        )
        assert back.disputes_after_corroboration >= 1

    @pytest.mark.asyncio
    async def test_a_counterpart_present_from_the_start_leaves_the_audit_at_zero(self):
        """Arming without the wave order is the same vacuum one layer down.

        The dispute is real, the detector fired, and the false-promotion
        audit's numerator still reads 0 — it joins a dispute to a *prior*
        corroboration, and there is none. This is the corpus edit
        ``validate_arming_design`` refuses, proven here against the ladder
        rather than argued in the corpus's prose.
        """
        project = "t2129-vacuum"
        subject = await self._open_replacement(
            project, "t2129-vacuum-subject", "t2129-gamma", "t2129-delta",
            ("t2129:e", "t2129:f", "t2129:g"),
        )
        await self._open_replacement(
            project, "t2129-vacuum-counterpart", "t2129-delta", "t2129-gamma",
            ("t2129:h",),
        )

        decision = await self._recompute(subject["id"])
        assert (decision.current_status, decision.outcome) == ("candidate", "dispute")

        async with bench_db.session_factory() as session:
            back = await pc.read_back(session)
        rows = [row for row in back.disputes if row["project"] == project]
        assert len(rows) == 1, rows
        assert rows[0]["rule"] == "inverse_replacement"
        assert rows[0]["corroborated_first"] is False

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


# ── the supersession-window clause (T2.129 pass 2) ───────────────────────────
#
# Pass 1 armed the detector and still reported a numerator of 0. Every clause
# above passed while it did: the failure was the arming captures' *dates*.
# These tests pin the date property and, more importantly, pin that the clause
# actually bites -- a guard that only ever passes is pinning nothing.

#: A clock the window arithmetic is measured against, so these tests do not
#: quietly stop testing anything once the committed dates recede far enough
#: that any date would pass. The pass-1 dates fail against this clock; after
#: roughly 2026-10-18 they would pass against a live one.
_ARMING_RUN_CLOCK = datetime(2026, 8, 14, 12, 0, 0, tzinfo=timezone.utc)

#: The dates the corpus actually carried when pass 1 measured a zero numerator.
_PASS_1_ARMING_DATES = {
    "wh-trino-1": "2026-06-10T09:30:00+00:00",
    "wh-trino-2": "2026-06-12T11:05:00+00:00",
    "wh-trino-3": "2026-06-15T14:20:00+00:00",
    "wh-trino-4": "2026-07-06T10:15:00+00:00",
    "wh-rollback": "2026-07-20T08:40:00+00:00",
}


def test_the_committed_arming_dates_sit_outside_the_supersession_window(entries):
    pc.validate_arming_design(entries, now=_ARMING_RUN_CLOCK)


def test_the_window_clause_bites_on_the_dates_pass_one_actually_ran(entries):
    """The failing side of the proof, recorded because the calendar erases it.

    Every one of pass 1's five arming captures sat inside the window. Against a
    live clock this stops being demonstrable once they age out, so the clock is
    pinned and the pass-1 dates are restated here rather than cited.
    """
    broken = copy.deepcopy(entries)
    for entry in broken:
        if entry["key"] in _PASS_1_ARMING_DATES:
            entry["created_at"] = _PASS_1_ARMING_DATES[entry["key"]]

    with pytest.raises(ValueError, match="supersession window") as excinfo:
        pc.validate_arming_design(broken, now=_ARMING_RUN_CLOCK)

    # All five, not just wave 1: the counterpart asserts the reverse edge, so a
    # wave-2 re-assertion left inside the window is a lawful supersession
    # candidate for it and step 3's "no superseded row" catch would be
    # unsatisfiable.
    message = str(excinfo.value)
    for key in _PASS_1_ARMING_DATES:
        assert key in message, f"{key} not named by the window clause"


def test_the_window_clause_reads_its_bound_from_the_application(entries):
    """The 90 is imported, not restated, so moving the window moves the guard."""
    assert pc.SUPERSESSION_WINDOW_DAYS == relations.SUPERSESSION_WINDOW_DAYS

    broken = copy.deepcopy(entries)
    subject = _arming(broken, pc.ARMING_SUBJECT_GROUP)
    # One day inside whatever the application's window currently is.
    inside = _ARMING_RUN_CLOCK - timedelta(days=relations.SUPERSESSION_WINDOW_DAYS - 1)
    subject[0]["created_at"] = inside.isoformat()
    with pytest.raises(ValueError, match="supersession window"):
        pc.validate_arming_design(broken, now=_ARMING_RUN_CLOCK)


# ── the blocked-hold group: the ruling's other arm, and its mirror guard ──
#
# Pass 2's arming window clause makes the supersession-blocked hold
# structurally unreachable in the arming groups (the independent probe's
# 2026-08-14 finding), so the `blocked_hold` group carries it in a project of
# its own. Its design property -- inside the look-back window at ingest -- is
# run-clock-relative, so the group's dates are spelled `now-<N>d` and resolved
# at load; these tests load with the pinned clock so resolution and validation
# share one `now` and the proofs do not decay with the calendar.


@pytest.fixture(scope="module")
def pinned_entries():
    return pc.load_promotion_corpus(now=_ARMING_RUN_CLOCK)


def _blocked(entries):
    return [e for e in entries if e["group"] == pc.BLOCKED_HOLD_GROUP]


def test_relative_dates_resolve_against_the_given_clock(pinned_entries):
    resolved = {e["key"]: e["created_at"] for e in _blocked(pinned_entries)}
    assert resolved == {
        "sch-dagster-1": (_ARMING_RUN_CLOCK - timedelta(days=12)).isoformat(),
        "sch-dagster-2": (_ARMING_RUN_CLOCK - timedelta(days=10)).isoformat(),
        "sch-dagster-3": (_ARMING_RUN_CLOCK - timedelta(days=8)).isoformat(),
    }


def test_the_committed_corpus_keeps_the_blocked_hold_design(pinned_entries):
    pc.validate_blocked_hold_design(pinned_entries, now=_ARMING_RUN_CLOCK)


def test_blocked_hold_clause_bites_on_a_date_outside_the_window(pinned_entries):
    """The failing side of the mirror clause.

    Outside the window supersession never fires, no memory is retired, the
    hold never journals, and `blocked = 0` is unreachability again -- with no
    symptom, because the corpus keeps loading.
    """
    broken = copy.deepcopy(pinned_entries)
    outside = _ARMING_RUN_CLOCK - timedelta(
        days=relations.SUPERSESSION_WINDOW_DAYS + 1
    )
    _blocked(broken)[0]["created_at"] = outside.isoformat()
    with pytest.raises(ValueError, match="outside the .*supersession window"):
        pc.validate_blocked_hold_design(broken, now=_ARMING_RUN_CLOCK)


def test_blocked_hold_clause_reads_its_bound_from_the_application(pinned_entries):
    broken = copy.deepcopy(pinned_entries)
    # One day outside whatever the application's window currently is.
    outside = _ARMING_RUN_CLOCK - timedelta(
        days=relations.SUPERSESSION_WINDOW_DAYS + 1
    )
    _blocked(broken)[0]["created_at"] = outside.isoformat()
    with pytest.raises(ValueError, match="supersession window"):
        pc.validate_blocked_hold_design(broken, now=_ARMING_RUN_CLOCK)
    # And one day inside it still validates.
    inside = _ARMING_RUN_CLOCK - timedelta(
        days=relations.SUPERSESSION_WINDOW_DAYS - 1
    )
    healed = copy.deepcopy(pinned_entries)
    _blocked(healed)[0]["created_at"] = inside.isoformat()
    pc.validate_blocked_hold_design(healed, now=_ARMING_RUN_CLOCK)


def test_loader_refuses_an_absolute_date_in_the_blocked_hold_group(
    tmp_path, pinned_entries
):
    """An absolute date here is a silent 90-day fuse.

    The corpus would keep loading after the date recedes past the window,
    supersession would quietly stop firing, and the blocked count would
    return to the zero this group exists to make non-vacuous.
    """
    import json

    broken = copy.deepcopy(pinned_entries)
    # The resolved ISO stamp is exactly what a well-meaning editor would
    # commit; the loader must refuse it even though it is inside the window
    # today.
    assert "T" in _blocked(broken)[0]["created_at"]
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({"memories": broken}), encoding="utf-8")
    with pytest.raises(ValueError, match="fuse"):
        pc.load_promotion_corpus(path, now=_ARMING_RUN_CLOCK)


def test_loader_refuses_a_relative_date_outside_the_blocked_hold_group(
    tmp_path, pinned_entries
):
    """Every other group's timeline is a committed fact and stays absolute."""
    import json

    broken = copy.deepcopy(pinned_entries)
    victim = next(e for e in broken if e["group"] == "none")
    victim["created_at"] = "now-5d"
    path = tmp_path / "corpus.json"
    path.write_text(json.dumps({"memories": broken}), encoding="utf-8")
    with pytest.raises(ValueError, match="resolve against the run clock"):
        pc.load_promotion_corpus(path, now=_ARMING_RUN_CLOCK)


def test_blocked_hold_guard_refuses_a_corpus_without_the_group(pinned_entries):
    """Deleting the group re-forecloses the hold, so the deletion must bite."""
    broken = [
        e for e in copy.deepcopy(pinned_entries)
        if e["group"] != pc.BLOCKED_HOLD_GROUP
    ]
    with pytest.raises(ValueError, match="structurally unreachable"):
        pc.validate_blocked_hold_design(broken, now=_ARMING_RUN_CLOCK)


def test_blocked_hold_guard_refuses_a_second_claim(pinned_entries):
    broken = copy.deepcopy(pinned_entries)
    _blocked(broken)[2]["key"] = "sch-oozie-9"
    with pytest.raises(ValueError, match="holds 2 claims"):
        pc.validate_blocked_hold_design(broken, now=_ARMING_RUN_CLOCK)


def test_blocked_hold_guard_refuses_an_inverse_entry(pinned_entries):
    """An inverse entry is a contradiction, and the veto pre-empts the hold."""
    broken = copy.deepcopy(pinned_entries)
    entry = _blocked(broken)[2]
    entry["replaces"] = list(reversed(entry["replaces"]))
    with pytest.raises(ValueError, match="several replacement pairs"):
        pc.validate_blocked_hold_design(broken, now=_ARMING_RUN_CLOCK)


def test_blocked_hold_guard_refuses_names_the_arming_pair_asserts(pinned_entries):
    broken = copy.deepcopy(pinned_entries)
    for entry in _blocked(broken):
        entry["replaces"] = ["dagster", "hive"]
        entry["content"] += " Nothing moved to hive."
    with pytest.raises(ValueError, match="the arming pair also asserts"):
        pc.validate_blocked_hold_design(broken, now=_ARMING_RUN_CLOCK)


def test_blocked_hold_guard_refuses_a_measured_claim_in_its_project(pinned_entries):
    broken = copy.deepcopy(pinned_entries)
    victim = next(e for e in broken if e["group"] == "none")
    victim["project"] = _blocked(broken)[0]["project"]
    with pytest.raises(ValueError, match="share the blocked-hold project"):
        pc.validate_blocked_hold_design(broken, now=_ARMING_RUN_CLOCK)


def test_blocked_hold_guard_refuses_equal_capture_times(pinned_entries):
    broken = copy.deepcopy(pinned_entries)
    stamps = _blocked(broken)
    stamps[1]["created_at"] = stamps[0]["created_at"]
    with pytest.raises(ValueError, match="equal capture times"):
        pc.validate_blocked_hold_design(broken, now=_ARMING_RUN_CLOCK)


def test_design_guard_refuses_a_blocked_hold_claim_past_the_gap(pinned_entries):
    """Span the origins past seven days and the time-gap gate would carry it.

    The gate is unreachable on the unsimulated pass, so the fact would hold
    below its count there and the blocked hold would journal on one pass only.
    """
    broken = copy.deepcopy(pinned_entries)
    late = datetime.fromisoformat(_blocked(broken)[0]["created_at"]) + timedelta(days=8)
    _blocked(broken)[2]["created_at"] = late.isoformat()
    with pytest.raises(ValueError, match="time-gap gate fires"):
        pc.validate_corroboration_design(broken)


def test_design_guard_refuses_a_blocked_hold_claim_grown_a_fourth_origin(
    pinned_entries,
):
    broken = copy.deepcopy(pinned_entries)
    extra = copy.deepcopy(_blocked(broken)[2])
    extra["key"] = "sch-dagster-4"
    extra["origin_key"] = "codex:0f00ba44"
    broken.append(extra)
    with pytest.raises(ValueError, match="at most 3"):
        pc.validate_corroboration_design(broken)


def test_the_arming_window_clause_ignores_the_blocked_hold_group(pinned_entries):
    """The two window clauses guard opposite properties for disjoint groups.

    The committed blocked-hold dates sit INSIDE the window; if a future edit
    folded them into the arming clause's sweep, the corpus would stop loading
    entirely -- so the additivity is pinned as a passing validation, both
    guards at once, one clock.
    """
    pc.validate_arming_design(pinned_entries, now=_ARMING_RUN_CLOCK)
    pc.validate_blocked_hold_design(pinned_entries, now=_ARMING_RUN_CLOCK)
    cutoff = _ARMING_RUN_CLOCK - timedelta(days=relations.SUPERSESSION_WINDOW_DAYS)
    for entry in _blocked(pinned_entries):
        assert datetime.fromisoformat(entry["created_at"]) >= cutoff
