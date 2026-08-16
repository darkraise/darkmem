"""Corroboration counts distinct origins, never rows.

Echo is not evidence: one chatty source re-asserting a claim ten times is one
witness, and a count that says otherwise promotes a fact nothing corroborates.
These tests pin that arithmetic from both sides — the count that must not follow
rows, and the threshold that must not be lowered by a single origin talking to
itself — plus the structural exclusions (derived kinds, unknown identity) that
keep the count from being inflated by construction.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import text

from app.api.mcp.client_identity import UNKNOWN_ORIGIN_PREFIX, resolve_origin_key
from app.repositories.fact_sources import (
    CORROBORATION_N_DEFAULT,
    CORROBORATION_N_DIVERSE,
    CORROBORATION_TIME_GAP_DAYS,
    SOURCE_KINDS,
    FactSourceRepository,
    _UNKNOWN_ORIGIN_MATCH,
)
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.triple_key import compute_triple_key

PROJECT = "t202-fact-sources"
NOW = datetime(2026, 7, 29, 12, 0, 0, tzinfo=timezone.utc)


async def _fact(session, *, subject: str = "postgres", project: str = PROJECT) -> str:
    row = await KnowledgeTripleRepository(session).insert_open(
        triple_key=compute_triple_key(project, subject, "RUNS_ON", "linux"),
        subject_name=subject,
        object_name="linux",
        rel_type="RUNS_ON",
        fact=f"{subject} runs on linux",
        reference_time=NOW,
        project=project,
    )
    return row["id"]


async def _backdate(session, source_id: str, when: datetime) -> None:
    """Move a source row's capture time.

    ``created_at`` carries a server default, so the time-gap gate can only be
    exercised by rewriting it after the fact.
    """
    await session.execute(
        text(
            "UPDATE fact_sources SET created_at = CAST(:when AS timestamptz) "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"when": when, "id": source_id},
    )


async def _add(
    repo: FactSourceRepository,
    fact_id: str,
    *,
    kind: str = "memory",
    ref: str,
    origin: str | None,
    at: datetime | None = None,
    detail: dict | None = None,
) -> dict:
    row = await repo.add_source(
        fact_id=fact_id,
        source_kind=kind,
        source_ref=ref,
        origin_key=origin,
        detail=detail,
    )
    if at is not None:
        await _backdate(repo.session, row["id"], at)
    return row


async def _row_count(session, fact_id: str) -> int:
    result = await session.execute(
        text("SELECT COUNT(*) FROM fact_sources WHERE fact_id = CAST(:id AS uuid)"),
        {"id": fact_id},
    )
    return int(result.scalar_one())


# ── Rule 1: distinct origins, never rows ────────────────────────────


async def test_ten_rows_from_one_origin_count_as_one_origin(session):
    """The Done-when guard: a row-counting implementation returns 10 here.

    Ten *distinct* rows — different source_ref each, so the dedupe key does not
    collapse them — all carrying one origin_key. The table genuinely holds ten
    rows; the corroboration count must still be one.
    """
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    for index in range(10):
        await _add(repo, fact_id, ref=f"memory-{index}", origin="mcp:agent-run-1")

    assert await _row_count(session, fact_id) == 10
    assert await repo.count_distinct_origins(fact_id) == 1
    assert (await repo.origin_profile(fact_id)).origin_count == 1


async def test_the_same_source_asserting_ten_times_is_one_origin(session):
    """The Done-when's own wording, on the other path: one row, one origin.

    Ten calls with the identical dedupe key write one row, so both the row
    count and the origin count are one.
    """
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    for _ in range(10):
        await _add(repo, fact_id, ref="memory-a", origin="mcp:agent-run-1")

    assert await _row_count(session, fact_id) == 1
    assert await repo.count_distinct_origins(fact_id) == 1


async def test_distinct_origins_count_separately(session):
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    for index in range(3):
        await _add(repo, fact_id, ref=f"memory-{index}", origin=f"mcp:agent-run-{index}")

    assert await repo.count_distinct_origins(fact_id) == 3

    profile = await repo.origin_profile(fact_id)
    assert profile.origin_count == 3
    assert sorted(o.origin_key for o in profile.origins) == [
        "mcp:agent-run-0",
        "mcp:agent-run-1",
        "mcp:agent-run-2",
    ]


async def test_one_origin_asserting_across_many_commits_stays_one_origin(session):
    """Code's stated rule: one origin per repo regardless of commit count."""
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    for index in range(5):
        await _add(
            repo,
            fact_id,
            kind="code",
            ref=f"symbol::file.py::owner@sha{index}",
            origin="repo-42",
            detail={"commit_sha": f"sha{index}"},
        )

    assert await _row_count(session, fact_id) == 5
    assert await repo.count_distinct_origins(fact_id) == 1


# ── Rule 4: unknown origin identity merges to one ───────────────────


async def test_null_origin_keys_merge_to_a_single_origin(session):
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    for index in range(5):
        await _add(repo, fact_id, ref=f"memory-{index}", origin=None)

    assert await _row_count(session, fact_id) == 5
    assert await repo.count_distinct_origins(fact_id) == 1

    profile = await repo.origin_profile(fact_id)
    assert profile.origin_count == 1
    assert profile.has_unknown_origin is True
    assert profile.origins[0].origin_key is None
    assert profile.origins[0].row_count == 5


async def test_unknown_origins_never_inflate_a_known_count(session):
    """Adding anonymous rows to a real origin adds exactly one bucket, once."""
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    await _add(repo, fact_id, ref="memory-known", origin="mcp:agent-run-1")
    assert await repo.count_distinct_origins(fact_id) == 1

    for index in range(4):
        await _add(repo, fact_id, ref=f"memory-anon-{index}", origin=None)

    assert await repo.count_distinct_origins(fact_id) == 2


async def test_every_flavour_of_unknown_identity_shares_one_bucket(session):
    """Blank, whitespace, and the capture layer's per-door unknown keys.

    ``resolve_origin_key`` merges unattributed captures per (source, project),
    so two doors produce two different ``unknown:`` keys for what is not two
    witnesses. This layer is deliberately coarser and folds them together.
    """
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    unknowns = [
        None,
        "",
        "   ",
        UNKNOWN_ORIGIN_PREFIX,
        resolve_origin_key(None, None, source="mcp", project=PROJECT),
        resolve_origin_key(None, None, source="api", project=PROJECT),
        resolve_origin_key(None, None, source="mcp", project="other-project"),
    ]
    for index, origin in enumerate(unknowns):
        await _add(repo, fact_id, ref=f"memory-{index}", origin=origin)

    assert await _row_count(session, fact_id) == len(unknowns)
    assert await repo.count_distinct_origins(fact_id) == 1


def test_the_unknown_marker_tracks_the_capture_layer():
    """A rename of the capture-side prefix must fail here, not silently split."""
    assert _UNKNOWN_ORIGIN_MATCH["unknown_exact"] == UNKNOWN_ORIGIN_PREFIX
    assert _UNKNOWN_ORIGIN_MATCH["unknown_like"] == f"{UNKNOWN_ORIGIN_PREFIX}:%"


async def test_origin_keys_differing_only_in_case_or_padding_merge(session):
    """Merge-only normalisation: it may undercount, it may never split."""
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    for index, origin in enumerate(["mcp:Agent-1", "mcp:agent-1", "  mcp:agent-1  "]):
        await _add(repo, fact_id, ref=f"memory-{index}", origin=origin)

    assert await _row_count(session, fact_id) == 3
    assert await repo.count_distinct_origins(fact_id) == 1


# ── Rule 3: derived rows are a structural exclusion ─────────────────


@pytest.mark.parametrize("kind", ["fact", "triple", "article", "knowledge_article"])
async def test_a_derived_kind_is_rejected_and_writes_nothing(session, kind):
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)

    with pytest.raises(ValueError, match="derived layer"):
        await repo.add_source(
            fact_id=fact_id,
            source_kind=kind,
            source_ref="article-1",
            origin_key="mcp:agent-run-1",
        )

    assert await _row_count(session, fact_id) == 0
    assert await repo.count_distinct_origins(fact_id) == 0


async def test_an_unrecognised_kind_is_rejected_and_writes_nothing(session):
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)

    with pytest.raises(ValueError, match="unknown source_kind"):
        await repo.add_source(
            fact_id=fact_id,
            source_kind="rumour",
            source_ref="somewhere",
            origin_key="mcp:agent-run-1",
        )

    assert await _row_count(session, fact_id) == 0


@pytest.mark.parametrize("kind,hint", [("document", "'block'")])
async def test_a_reserved_kind_names_its_missing_producer(session, kind, hint):
    """`document` is doc 08 §4.1's wording for content that arrives as `block`.

    `block` was the other row here until TH1.12 shipped its producer — the
    reservation read "no producer writes one yet", which stopped being true
    rather than being relaxed. `document` stays reserved because doc 04 §8.3's
    column vocabulary still has no such value, and a caller following doc 08's
    wording deserves to be pointed at where document content actually lands.
    """
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)

    with pytest.raises(ValueError, match="reserved") as raised:
        await repo.add_source(
            fact_id=fact_id,
            source_kind=kind,
            source_ref="block-1",
            origin_key="doc-1",
        )

    assert hint in str(raised.value)
    assert await _row_count(session, fact_id) == 0


@pytest.mark.parametrize("field,kwargs", [
    ("source_kind", {"source_kind": "  ", "source_ref": "memory-a"}),
    ("source_ref", {"source_kind": "memory", "source_ref": "  "}),
])
async def test_an_empty_identity_field_is_rejected(session, field, kwargs):
    """The dedupe key cannot deduplicate NULLs, so it must never see one."""
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)

    with pytest.raises(ValueError, match=rf"fact_sources\.{field} must"):
        await repo.add_source(fact_id=fact_id, origin_key=None, **kwargs)

    assert await _row_count(session, fact_id) == 0


# ── Source kinds round-trip ─────────────────────────────────────────


async def test_each_source_kind_round_trips(session):
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    assert SOURCE_KINDS == {"memory", "code", "block", "human"}

    await _add(repo, fact_id, kind="memory", ref="memory-1", origin="mcp:agent-run-1")
    await _add(
        repo,
        fact_id,
        kind="code",
        ref="parse::app.py::Repo",
        origin="repo-42",
        detail={"commit_sha": "abc123", "file_path": "app.py"},
    )
    # TH1.12: the ref is the block, the origin is its document — which is what
    # makes a many-block document one origin rather than many.
    await _add(repo, fact_id, kind="block", ref="block-9", origin="document-3")
    human = await _add(repo, fact_id, kind="human", ref="user-7", origin="human:user-7")

    profile = await repo.origin_profile(fact_id)
    assert profile.source_kinds == ("block", "code", "human", "memory")
    assert profile.origin_count == 4
    assert human["source_kind"] == "human"
    assert human["source_ref"] == "user-7"

    stored = {o.origin_key: o.source_kinds for o in profile.origins}
    assert stored["document-3"] == ("block",)
    assert stored["repo-42"] == ("code",)
    assert stored["human:user-7"] == ("human",)
    assert stored["mcp:agent-run-1"] == ("memory",)


async def test_detail_round_trips_per_kind(session):
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    row = await _add(
        repo,
        fact_id,
        kind="code",
        ref="parse::app.py::Repo",
        origin="repo-42",
        detail={"commit_sha": "abc123", "basis": "import"},
    )

    assert row["detail"] == {"commit_sha": "abc123", "basis": "import"}


# ── Idempotency on the dedupe key ───────────────────────────────────


async def test_add_source_is_idempotent_on_the_dedupe_key(session):
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    first = await _add(
        repo, fact_id, ref="memory-a", origin="mcp:agent-run-1", detail={"n": 1}
    )
    second = await repo.add_source(
        fact_id=fact_id,
        source_kind="memory",
        source_ref="memory-a",
        origin_key="mcp:agent-run-2",
        detail={"n": 2},
    )

    assert second["id"] == first["id"]
    assert await _row_count(session, fact_id) == 1
    # First assertion wins: a re-save must not move a counted row into another
    # origin bucket, which is the one way idempotency could raise the count.
    assert second["origin_key"] == "mcp:agent-run-1"
    assert second["detail"] == {"n": 1}
    assert await repo.count_distinct_origins(fact_id) == 1


async def test_the_same_ref_under_two_kinds_is_two_rows(session):
    """The dedupe key includes the kind, so it must not collapse them."""
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    await _add(repo, fact_id, kind="memory", ref="shared-ref", origin="mcp:agent-run-1")
    await _add(repo, fact_id, kind="code", ref="shared-ref", origin="repo-42")

    assert await _row_count(session, fact_id) == 2
    assert await repo.count_distinct_origins(fact_id) == 2


async def test_sources_are_scoped_to_their_fact(session):
    repo = FactSourceRepository(session)
    first = await _fact(session, subject="postgres")
    second = await _fact(session, subject="redis")
    await _add(repo, first, ref="memory-a", origin="mcp:agent-run-1")
    await _add(repo, second, ref="memory-b", origin="mcp:agent-run-2")

    assert await repo.count_distinct_origins(first) == 1
    assert await repo.count_distinct_origins(second) == 1
    assert (await repo.origin_profile(first)).origins[0].origin_key == "mcp:agent-run-1"


# ── Rule 2: the diversity-sensitive threshold ───────────────────────


async def test_diverse_kinds_lower_the_threshold_to_two(session):
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    await _add(repo, fact_id, kind="memory", ref="memory-a", origin="mcp:run-1", at=NOW)
    await _add(repo, fact_id, kind="code", ref="parse::a.py", origin="repo-42", at=NOW)

    profile = await repo.origin_profile(fact_id)
    assert profile.kinds_are_diverse is True
    assert profile.origin_count == 2
    assert profile.required_origin_count == CORROBORATION_N_DIVERSE == 2


async def test_same_kind_within_the_gap_needs_three(session):
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    await _add(repo, fact_id, ref="memory-a", origin="mcp:run-1", at=NOW)
    await _add(
        repo, fact_id, ref="memory-b", origin="mcp:run-2", at=NOW + timedelta(days=3)
    )

    profile = await repo.origin_profile(fact_id)
    assert profile.kinds_are_diverse is False
    assert profile.max_cross_origin_gap == timedelta(days=3)
    assert profile.required_origin_count == CORROBORATION_N_DEFAULT == 3


async def test_same_kind_across_the_gap_drops_back_to_two(session):
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    gap = timedelta(days=CORROBORATION_TIME_GAP_DAYS)
    await _add(repo, fact_id, ref="memory-a", origin="mcp:run-1", at=NOW)
    await _add(repo, fact_id, ref="memory-b", origin="mcp:run-2", at=NOW + gap)

    profile = await repo.origin_profile(fact_id)
    assert profile.kinds_are_diverse is False
    assert profile.max_cross_origin_gap == gap
    assert profile.required_origin_count == CORROBORATION_N_DIVERSE == 2


async def test_the_gap_is_inclusive_at_seven_days_and_open_below_it(session):
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    just_under = timedelta(days=CORROBORATION_TIME_GAP_DAYS, seconds=-1)
    await _add(repo, fact_id, ref="memory-a", origin="mcp:run-1", at=NOW)
    row = await _add(repo, fact_id, ref="memory-b", origin="mcp:run-2", at=NOW + just_under)

    assert (await repo.origin_profile(fact_id)).required_origin_count == 3

    await _backdate(session, row["id"], NOW + timedelta(days=CORROBORATION_TIME_GAP_DAYS))
    assert (await repo.origin_profile(fact_id)).required_origin_count == 2


async def test_one_origin_talking_to_itself_for_a_month_cannot_lower_n(session):
    """The time gate needs two distinct origins, not two distant rows."""
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    await _add(repo, fact_id, ref="memory-a", origin="mcp:run-1", at=NOW)
    await _add(
        repo, fact_id, ref="memory-b", origin="mcp:run-1", at=NOW + timedelta(days=30)
    )

    profile = await repo.origin_profile(fact_id)
    assert profile.origin_count == 1
    assert profile.max_cross_origin_gap == timedelta(0)
    assert profile.required_origin_count == CORROBORATION_N_DEFAULT


async def test_one_origin_asserting_under_two_kinds_is_not_diverse(session):
    """An origin cannot differ from itself."""
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    await _add(repo, fact_id, kind="memory", ref="memory-a", origin="shared", at=NOW)
    await _add(repo, fact_id, kind="code", ref="parse::a.py", origin="shared", at=NOW)

    profile = await repo.origin_profile(fact_id)
    assert profile.origin_count == 1
    assert profile.origins[0].source_kinds == ("code", "memory")
    assert profile.kinds_are_diverse is False
    assert profile.required_origin_count == CORROBORATION_N_DEFAULT


async def test_the_unknown_bucket_cannot_lower_n_by_itself(session):
    """Anonymous rows are one origin, so neither gate can fire on them alone."""
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    await _add(repo, fact_id, kind="memory", ref="memory-a", origin=None, at=NOW)
    await _add(
        repo,
        fact_id,
        kind="code",
        ref="parse::a.py",
        origin=None,
        at=NOW + timedelta(days=30),
    )

    profile = await repo.origin_profile(fact_id)
    assert profile.origin_count == 1
    assert profile.kinds_are_diverse is False
    assert profile.max_cross_origin_gap == timedelta(0)
    assert profile.required_origin_count == CORROBORATION_N_DEFAULT


async def test_an_anonymous_row_cannot_supply_the_kind_diversity(session):
    """One attributable witness plus an anonymous capture is not promotion-ready.

    The bucket counts toward origin_count, so a gate firing on it would drop N
    from 3 to 2 and make this profile promotable on one real witness — the same
    chatty source manufacturing its own corroboration, one level up from the
    count.
    """
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    await _add(repo, fact_id, kind="memory", ref="memory-a", origin="mcp:run-1", at=NOW)
    await _add(repo, fact_id, kind="code", ref="parse::a.py", origin=None, at=NOW)

    profile = await repo.origin_profile(fact_id)
    assert profile.origin_count == 2
    assert profile.has_unknown_origin is True
    assert profile.source_kinds == ("code", "memory")
    assert profile.kinds_are_diverse is False
    assert profile.required_origin_count == CORROBORATION_N_DEFAULT


async def test_an_anonymous_row_cannot_supply_the_time_gap(session):
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    await _add(repo, fact_id, ref="memory-a", origin="mcp:run-1", at=NOW)
    await _add(
        repo, fact_id, ref="memory-b", origin=None, at=NOW + timedelta(days=8)
    )

    profile = await repo.origin_profile(fact_id)
    assert profile.origin_count == 2
    assert profile.max_cross_origin_gap == timedelta(0)
    assert profile.required_origin_count == CORROBORATION_N_DEFAULT


async def test_anonymous_rows_do_not_disarm_a_gate_two_real_origins_supply(session):
    """The other direction: the exclusion must not over-correct.

    Two attributable origins still open both gates with an anonymous bucket
    sitting alongside them; the bucket is ignored by the gates, not poisonous
    to them.
    """
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    await _add(repo, fact_id, kind="memory", ref="memory-a", origin="mcp:run-1", at=NOW)
    await _add(repo, fact_id, kind="code", ref="parse::a.py", origin="repo-42", at=NOW)
    await _add(repo, fact_id, kind="memory", ref="memory-anon", origin=None, at=NOW)

    profile = await repo.origin_profile(fact_id)
    assert profile.origin_count == 3
    assert profile.kinds_are_diverse is True
    assert profile.required_origin_count == CORROBORATION_N_DIVERSE

    gapped = await _fact(session, subject="redis")
    await _add(repo, gapped, ref="memory-a", origin="mcp:run-1", at=NOW)
    await _add(
        repo, gapped, ref="memory-b", origin="mcp:run-2", at=NOW + timedelta(days=9)
    )
    await _add(repo, gapped, ref="memory-anon", origin=None, at=NOW + timedelta(days=4))

    gapped_profile = await repo.origin_profile(gapped)
    assert gapped_profile.origin_count == 3
    assert gapped_profile.max_cross_origin_gap == timedelta(days=9)
    assert gapped_profile.required_origin_count == CORROBORATION_N_DIVERSE


async def test_the_widest_cross_origin_gap_wins(session):
    """The gap is the widest span between two *different* origins."""
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    await _add(repo, fact_id, ref="memory-a", origin="mcp:run-1", at=NOW)
    await _add(
        repo, fact_id, ref="memory-b", origin="mcp:run-1", at=NOW + timedelta(days=20)
    )
    await _add(
        repo, fact_id, ref="memory-c", origin="mcp:run-2", at=NOW + timedelta(days=2)
    )

    profile = await repo.origin_profile(fact_id)
    assert profile.origin_count == 2
    assert profile.max_cross_origin_gap == timedelta(days=18)
    assert profile.required_origin_count == CORROBORATION_N_DIVERSE


async def test_a_fact_with_no_sources_profiles_empty(session):
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)

    profile = await repo.origin_profile(fact_id)
    assert profile.origin_count == 0
    assert profile.source_kinds == ()
    assert profile.max_cross_origin_gap == timedelta(0)
    assert profile.required_origin_count == CORROBORATION_N_DEFAULT
    assert await repo.count_distinct_origins(fact_id) == 0


# ── The reverse lookup ──────────────────────────────────────────────


async def test_facts_for_source_returns_what_a_source_asserts(session):
    repo = FactSourceRepository(session)
    first = await _fact(session, subject="postgres")
    second = await _fact(session, subject="redis")
    third = await _fact(session, subject="valkey")
    await _add(repo, first, ref="memory-a", origin="mcp:run-1")
    await _add(repo, second, ref="memory-a", origin="mcp:run-1")
    await _add(repo, third, ref="memory-b", origin="mcp:run-1")

    found = await repo.facts_for_source("memory", "memory-a", project=PROJECT)

    assert sorted(found) == sorted([first, second])
    assert third not in found


async def test_facts_for_source_does_not_cross_projects(session):
    """One human reviewer is the same source_ref in every project."""
    repo = FactSourceRepository(session)
    mine = await _fact(session, subject="postgres", project=PROJECT)
    theirs = await _fact(session, subject="postgres", project="t202-other-project")
    await _add(repo, mine, kind="human", ref="user-7", origin="human:user-7")
    await _add(repo, theirs, kind="human", ref="user-7", origin="human:user-7")

    assert await repo.facts_for_source("human", "user-7", project=PROJECT) == [mine]
    assert await repo.facts_for_source(
        "human", "user-7", project="t202-other-project"
    ) == [theirs]


# `block` left this list when TH1.12 gave it a producer; it is a writable
# kind now, so refusing it would refuse a real withdrawal sweep.
@pytest.mark.parametrize("kind", ["article", "document", "memories"])
async def test_facts_for_source_refuses_a_kind_add_source_could_not_write(session, kind):
    """A typo must raise, not answer "nothing to withdraw" with an empty list."""
    repo = FactSourceRepository(session)

    with pytest.raises(ValueError):
        await repo.facts_for_source(kind, "memory-a", project=PROJECT)


async def test_facts_for_source_is_empty_for_an_unknown_source(session):
    repo = FactSourceRepository(session)
    fact_id = await _fact(session)
    await _add(repo, fact_id, ref="memory-a", origin="mcp:run-1")

    assert await repo.facts_for_source("memory", "memory-zzz", project=PROJECT) == []
    assert await repo.facts_for_source("code", "memory-a", project=PROJECT) == []
