"""T2.20 — the pin-suggestion diff (doc 09 §3.4): label-stable diffing across
runs, subject-keyed gating, and durable accept/dismiss.

**The organising principle.** `memory_communities` is delete-and-rewritten
per project on every detection run (doc 06 §7), so every fixture below
simulates "run N, then run N+1" the same way `test_community_reports.py`
does: call `repo.replace_project_communities` twice, in sequence, on the
same project. No pipeline, no clustering, no LLM — this suite is offline,
matching its siblings.

Fact-floor and article-subject gating read `knowledge_triples` /
`knowledge_articles` directly (raw INSERTs below), exactly like
`test_facts_channel.py`'s own fixtures.
"""
from __future__ import annotations

import json

from sqlalchemy import text

from app.repositories import memory_communities as repo
from app.repositories import pinned_subjects
from app.services import memory_community_detection as detection
from app.services import pin_suggestions as pins
from app.utils.ids import new_id

PROJECT = "t220-pins"

_INSERT_MEMORY = text(
    "INSERT INTO memories (id, content, source, project, status) "
    "VALUES (CAST(:id AS uuid), :content, 'api', CAST(:project AS text), 'active')"
)

_INSERT_FACT = text(
    "INSERT INTO knowledge_triples "
    "(id, subject_name, object_name, rel_type, reference_time, fact, "
    " project, triple_key, verification_status) "
    "VALUES (CAST(:id AS uuid), :subject_name, :object_name, :rel_type, "
    " now(), :fact, CAST(:project AS text), :triple_key, :verification_status)"
)

_INSERT_ARTICLE = text(
    "INSERT INTO knowledge_articles "
    "(id, subject_key, project, content, status) "
    "VALUES (CAST(:id AS uuid), :subject_key, CAST(:project AS text), :content, :status)"
)


async def seed_memory(session, project: str = PROJECT, content: str = "seeded memory"):
    memory_id = new_id()
    await session.execute(
        _INSERT_MEMORY, {"id": str(memory_id), "content": content, "project": project}
    )
    return memory_id


async def seed_fact(
    session,
    *,
    subject_name: str,
    project: str = PROJECT,
    object_name: str = "object",
    rel_type: str = "RELATED_TO",
    # `confirmed` rather than `corroborated` (T2.99): the fact floor is
    # measured on the rungs a reader is *served*, and `corroborated` is
    # withheld while G-C's promotion record is absent. Every test below whose
    # subject is the diff — split, merge, dedup, the article gate, accept and
    # dismiss — wants a subject that anchors verified support at either gate
    # state, and only the human-ratified rung does that. The gate's own effect
    # on this count is asserted at the door, in
    # `tests/test_claim_serving_gates.py`.
    status: str = "confirmed",
):
    fact_id = new_id()
    triple_key = f"{project}:{subject_name}:{rel_type}:{object_name}:{fact_id}"
    await session.execute(
        _INSERT_FACT,
        {
            "id": str(fact_id),
            "subject_name": subject_name,
            "object_name": object_name,
            "rel_type": rel_type,
            "fact": f"{subject_name} {rel_type} {object_name}",
            "project": project,
            "triple_key": triple_key,
            "verification_status": status,
        },
    )
    return fact_id


async def seed_article(session, *, subject_key: str, project: str = PROJECT, status: str = "corroborated"):
    article_id = new_id()
    await session.execute(
        _INSERT_ARTICLE,
        {
            "id": str(article_id),
            "subject_key": subject_key,
            "project": project,
            "content": "an existing article",
            "status": status,
        },
    )
    return article_id


def _draft(label, memory_ids, dominant_name, dominant_type, size=None):
    return repo.CommunityDraft(
        label=label,
        memory_ids=tuple(memory_ids),
        properties={
            "size": size if size is not None else len(memory_ids),
            "dominant_entities": [
                {"name": dominant_name, "type": dominant_type, "display_name": dominant_name}
            ],
        },
    )


# ---------------------------------------------------------------------------
# diff_topics — new / grown / stable / decayed
# ---------------------------------------------------------------------------


async def test_a_stable_community_across_runs_is_classified_stable_by_label(session):
    """The load-bearing property: the community *id* changes on every
    rewrite, but a same-label, same-size community must read `stable`, not
    `new` — which is only possible if the diff keys on the label, not the id."""
    a = await seed_memory(session)
    b = await seed_memory(session)

    (first_id,) = await repo.replace_project_communities(
        session, PROJECT, [_draft("alpha", (a, b), "alpha", "concept")]
    )
    await session.flush()
    prior = await pins.snapshot_topics(session, PROJECT)

    (second_id,) = await repo.replace_project_communities(
        session, PROJECT, [_draft("alpha", (a, b), "alpha", "concept")]
    )
    await session.flush()
    assert second_id != first_id

    current = await repo.list_with_members(session, PROJECT)
    entries = pins.diff_topics(prior, current)

    assert len(entries) == 1
    assert entries[0].label == "alpha"
    assert entries[0].status == pins.STATUS_STABLE


async def test_a_new_label_with_no_prior_snapshot_is_new(session):
    a = await seed_memory(session)
    prior: dict = {}
    await repo.replace_project_communities(
        session, PROJECT, [_draft("fresh-topic", (a,), "fresh-topic", "concept")]
    )
    await session.flush()
    current = await repo.list_with_members(session, PROJECT)

    entries = pins.diff_topics(prior, current)
    assert entries[0].status == pins.STATUS_NEW
    assert entries[0].prior_member_count is None


async def test_a_grown_community_crosses_the_threshold(session):
    a = await seed_memory(session)
    b = await seed_memory(session)
    c = await seed_memory(session)
    d = await seed_memory(session)

    await repo.replace_project_communities(
        session, PROJECT, [_draft("alpha", (a, b), "alpha", "concept")]
    )
    await session.flush()
    prior = await pins.snapshot_topics(session, PROJECT)

    await repo.replace_project_communities(
        session, PROJECT, [_draft("alpha", (a, b, c, d), "alpha", "concept")]
    )
    await session.flush()
    current = await repo.list_with_members(session, PROJECT)

    entries = pins.diff_topics(prior, current, growth_threshold=2)
    assert entries[0].status == pins.STATUS_GROWN
    assert entries[0].member_count == 4
    assert entries[0].prior_member_count == 2


async def test_a_label_with_no_successor_is_decayed(session):
    a = await seed_memory(session)
    await repo.replace_project_communities(
        session, PROJECT, [_draft("vanishing", (a,), "vanishing", "concept")]
    )
    await session.flush()
    prior = await pins.snapshot_topics(session, PROJECT)

    await repo.replace_project_communities(session, PROJECT, [])
    await session.flush()
    current = await repo.list_with_members(session, PROJECT)

    entries = pins.diff_topics(prior, current)
    assert len(entries) == 1
    assert entries[0].label == "vanishing"
    assert entries[0].status == pins.STATUS_DECAYED


async def test_a_split_decays_the_parent_and_creates_new_children(session):
    """Design question from the brief: a split is two label-level events
    (parent decays, children are new) — the subject-level suppression that
    keeps this safe is proven separately below."""
    a = await seed_memory(session)
    b = await seed_memory(session)
    c = await seed_memory(session)
    d = await seed_memory(session)

    await repo.replace_project_communities(
        session, PROJECT, [_draft("postgres, backups", (a, b, c, d), "postgres", "tool")]
    )
    await session.flush()
    prior = await pins.snapshot_topics(session, PROJECT)

    await repo.replace_project_communities(
        session, PROJECT,
        [
            _draft("postgres, replication", (a, b), "postgres", "tool"),
            _draft("backups, retention", (c, d), "backups", "concept"),
        ],
    )
    await session.flush()
    current = await repo.list_with_members(session, PROJECT)

    entries = {e.label: e.status for e in pins.diff_topics(prior, current)}
    assert entries == {
        "postgres, backups": pins.STATUS_DECAYED,
        "postgres, replication": pins.STATUS_NEW,
        "backups, retention": pins.STATUS_NEW,
    }


# ---------------------------------------------------------------------------
# compute_pin_suggestions — the gate
# ---------------------------------------------------------------------------


async def test_a_new_community_with_facts_produces_a_suggestion(session):
    a = await seed_memory(session)
    await seed_fact(session, subject_name="postgres")
    await repo.replace_project_communities(
        session, PROJECT, [_draft("postgres, tuning", (a,), "postgres", "tool")]
    )
    await session.flush()
    current = await repo.list_with_members(session, PROJECT)
    entries = pins.diff_topics({}, current)

    suggestions = await pins.compute_pin_suggestions(session, PROJECT, entries)

    assert len(suggestions) == 1
    suggestion = suggestions[0]
    assert suggestion.subject_key == pins.subject_soft_key("postgres", "tool")
    assert suggestion.why == pins.STATUS_NEW
    assert suggestion.verified_fact_count == 1


async def test_two_communities_sharing_a_dominant_entity_produce_one_suggestion(session):
    """Fable review finding: a split can leave two sibling communities with
    the same dominant entity in the same pass ("postgres, replication" and
    "postgres, tuning" both dominated by `postgres`). Without a seen-set,
    each nominates `postgres::tool` separately, and since `events` is
    append-only, `journal_pin_suggestions` on the un-deduped result would
    write two permanent rows for one subject."""
    a = await seed_memory(session)
    b = await seed_memory(session)
    await seed_fact(session, subject_name="postgres")
    await repo.replace_project_communities(
        session, PROJECT,
        [
            _draft("postgres, replication", (a,), "postgres", "tool"),
            _draft("postgres, tuning", (b,), "postgres", "tool"),
        ],
    )
    await session.flush()
    current = await repo.list_with_members(session, PROJECT)
    entries = pins.diff_topics({}, current)
    assert len(entries) == 2

    suggestions = await pins.compute_pin_suggestions(session, PROJECT, entries)
    assert len(suggestions) == 1
    assert suggestions[0].subject_key == pins.subject_soft_key("postgres", "tool")

    await pins.journal_pin_suggestions(session, PROJECT, suggestions)
    await session.flush()

    rows = (
        await session.execute(
            text(
                "SELECT payload FROM events WHERE event_type = 'consolidated' "
                "AND object_type = 'topic' AND project = CAST(:p AS text) "
                "AND payload->>'action' = 'pin_suggested'"
            ),
            {"p": PROJECT},
        )
    ).all()
    assert len(rows) == 1


async def test_subject_soft_key_round_trips_through_decode(session):
    key = pins.subject_soft_key("postgres", "tool")
    assert pins.decode_subject_soft_key(key) == ("postgres", "tool")


async def test_decode_subject_soft_key_handles_a_colon_bearing_name(session):
    """The reason `rsplit` and not `split`: entity names in this domain can
    contain `::` themselves (`std::vector`), so only the *last* separator is
    guaranteed to be the name/type boundary."""
    key = pins.subject_soft_key("std::vector", "concept")
    assert pins.decode_subject_soft_key(key) == ("std::vector", "concept")


async def test_a_stable_community_never_suggests(session):
    a = await seed_memory(session)
    b = await seed_memory(session)
    await seed_fact(session, subject_name="postgres")
    await repo.replace_project_communities(
        session, PROJECT, [_draft("alpha", (a, b), "postgres", "tool")]
    )
    await session.flush()
    prior = await pins.snapshot_topics(session, PROJECT)
    await repo.replace_project_communities(
        session, PROJECT, [_draft("alpha", (a, b), "postgres", "tool")]
    )
    await session.flush()
    current = await repo.list_with_members(session, PROJECT)
    entries = pins.diff_topics(prior, current)

    suggestions = await pins.compute_pin_suggestions(session, PROJECT, entries)
    assert suggestions == []


async def test_below_fact_floor_is_not_suggested(session):
    a = await seed_memory(session)
    # No facts seeded at all for "lonely".
    await repo.replace_project_communities(
        session, PROJECT, [_draft("lonely-topic", (a,), "lonely", "concept")]
    )
    await session.flush()
    current = await repo.list_with_members(session, PROJECT)
    entries = pins.diff_topics({}, current)

    suggestions = await pins.compute_pin_suggestions(session, PROJECT, entries)
    assert suggestions == []


async def test_an_existing_live_article_subject_is_not_suggested(session):
    a = await seed_memory(session)
    await seed_fact(session, subject_name="postgres")
    subject_key = pins.subject_soft_key("postgres", "tool")
    await seed_article(session, subject_key=subject_key)
    await repo.replace_project_communities(
        session, PROJECT, [_draft("postgres, tuning", (a,), "postgres", "tool")]
    )
    await session.flush()
    current = await repo.list_with_members(session, PROJECT)
    entries = pins.diff_topics({}, current)

    suggestions = await pins.compute_pin_suggestions(session, PROJECT, entries)
    assert suggestions == []


async def test_a_superseded_article_no_longer_blocks_a_suggestion(session):
    a = await seed_memory(session)
    await seed_fact(session, subject_name="postgres")
    subject_key = pins.subject_soft_key("postgres", "tool")
    await seed_article(session, subject_key=subject_key, status="superseded")
    await repo.replace_project_communities(
        session, PROJECT, [_draft("postgres, tuning", (a,), "postgres", "tool")]
    )
    await session.flush()
    current = await repo.list_with_members(session, PROJECT)
    entries = pins.diff_topics({}, current)

    suggestions = await pins.compute_pin_suggestions(session, PROJECT, entries)
    assert len(suggestions) == 1


# ---------------------------------------------------------------------------
# accept / dismiss — durable, and suppress the diff on a later run
# ---------------------------------------------------------------------------


async def test_dismiss_persists_and_suppresses_the_next_runs_suggestion(session):
    """The mandated guard: dismissal survives a subsequent run, read back
    from the database, not merely returned as a successful call."""
    a = await seed_memory(session)
    await seed_fact(session, subject_name="postgres")
    subject_key = pins.subject_soft_key("postgres", "tool")

    await repo.replace_project_communities(
        session, PROJECT, [_draft("postgres, tuning", (a,), "postgres", "tool")]
    )
    await session.flush()
    prior = await pins.snapshot_topics(session, PROJECT)
    current = await repo.list_with_members(session, PROJECT)
    entries = pins.diff_topics({}, current)
    first_pass = await pins.compute_pin_suggestions(session, PROJECT, entries)
    assert len(first_pass) == 1

    await pins.dismiss_pin_suggestion(session, PROJECT, subject_key, label="postgres, tuning")
    await session.flush()

    # A fresh read of the durable list, independent of any in-memory state.
    pinned, dismissed = await pinned_subjects.get_subject_lists(session, PROJECT)
    assert subject_key in dismissed
    assert subject_key not in pinned

    # Simulate a subsequent detection run where the same subject's community
    # *grows* — without the dismiss suppression this would re-trigger a
    # suggestion (status GROWN is one of the two statuses that gate-check),
    # so this is a real exercise of the suppression, not a vacuous pass.
    b = await seed_memory(session)
    c = await seed_memory(session)
    await repo.replace_project_communities(
        session, PROJECT, [_draft("postgres, tuning", (a, b, c), "postgres", "tool")]
    )
    await session.flush()
    current2 = await repo.list_with_members(session, PROJECT)
    entries2 = pins.diff_topics(prior, current2)
    assert entries2[0].status == pins.STATUS_GROWN

    second_pass = await pins.compute_pin_suggestions(session, PROJECT, entries2)
    assert second_pass == []


async def test_accept_persists_as_a_pinned_subject(session):
    a = await seed_memory(session)
    await seed_fact(session, subject_name="postgres")
    subject_key = pins.subject_soft_key("postgres", "tool")

    await repo.replace_project_communities(
        session, PROJECT, [_draft("postgres, tuning", (a,), "postgres", "tool")]
    )
    await session.flush()
    current = await repo.list_with_members(session, PROJECT)
    entries = pins.diff_topics({}, current)
    suggestions = await pins.compute_pin_suggestions(session, PROJECT, entries)
    assert len(suggestions) == 1

    await pins.accept_pin_suggestion(session, PROJECT, subject_key, label="postgres, tuning")
    await session.flush()

    pinned, dismissed = await pinned_subjects.get_subject_lists(session, PROJECT)
    assert subject_key in pinned
    assert subject_key not in dismissed

    # Re-suggesting the same still-`new` community must not double-nominate
    # an already-pinned subject.
    again = await pins.compute_pin_suggestions(session, PROJECT, entries)
    assert again == []


async def test_accept_is_idempotent_not_a_growing_list(session):
    subject_key = "postgres::tool"
    await pins.accept_pin_suggestion(session, PROJECT, subject_key)
    await pins.accept_pin_suggestion(session, PROJECT, subject_key)
    await session.flush()

    length = (
        await session.execute(
            text(
                "SELECT jsonb_array_length(properties -> 'pinned_subjects') "
                "FROM projects WHERE name = CAST(:p AS text)"
            ),
            {"p": PROJECT},
        )
    ).scalar_one()
    assert length == 1


async def test_accept_and_dismiss_journal_events(session):
    subject_key = "postgres::tool"
    await pins.accept_pin_suggestion(session, PROJECT, subject_key, label="alpha")
    await pins.dismiss_pin_suggestion(session, PROJECT, "other::tool", label="beta")
    await session.flush()

    rows = (
        await session.execute(
            text(
                "SELECT payload FROM events WHERE event_type = 'pin_decision' "
                "AND object_type = 'topic' AND project = CAST(:p AS text) "
                "ORDER BY payload->>'verdict'"
            ),
            {"p": PROJECT},
        )
    ).all()
    verdicts = {row[0]["verdict"] for row in rows}
    assert verdicts == {"accepted", "dismissed"}


async def test_journal_pin_suggestions_writes_one_row_per_suggestion(session):
    a = await seed_memory(session)
    await seed_fact(session, subject_name="postgres")
    await repo.replace_project_communities(
        session, PROJECT, [_draft("postgres, tuning", (a,), "postgres", "tool")]
    )
    await session.flush()
    current = await repo.list_with_members(session, PROJECT)
    entries = pins.diff_topics({}, current)
    suggestions = await pins.compute_pin_suggestions(session, PROJECT, entries)

    await pins.journal_pin_suggestions(session, PROJECT, suggestions)
    await session.flush()

    rows = (
        await session.execute(
            text(
                "SELECT payload FROM events WHERE event_type = 'consolidated' "
                "AND object_type = 'topic' AND project = CAST(:p AS text) "
                "AND payload->>'action' = 'pin_suggested'"
            ),
            {"p": PROJECT},
        )
    ).all()
    assert len(rows) == 1
    assert rows[0][0]["subject_key"] == pins.subject_soft_key("postgres", "tool")


# ---------------------------------------------------------------------------
# T2.91 — the durable prior, proven across two real detection runs
#
# Every test above simulates the rewrite with `replace_project_communities`,
# which is the right shape for testing the diff in isolation. These four
# cannot: the property under test is that the prior is *captured by the
# detector itself* and survives to the next run, so they drive
# `detect_for_project` for real and let it label, cluster and rewrite. A
# single-run fixture cannot see `grown`, `stable` or `decayed` at all, which
# is why the gap was invisible until review.
# ---------------------------------------------------------------------------

_INSERT_ENTITY = text(
    "INSERT INTO entities (name, entity_type, properties, memory_ids) "
    "VALUES (:name, 'tool', CAST(:properties AS jsonb), CAST(:memory_ids AS uuid[])) "
    "RETURNING id"
)

_EXTEND_ENTITY = text(
    "UPDATE entities SET memory_ids = memory_ids || CAST(:memory_ids AS uuid[]) "
    "WHERE name = :name"
)


async def _seed_cluster(session, project, name, size=3):
    ids = [await seed_memory(session, project) for _ in range(size)]
    await session.flush()
    await session.execute(
        _INSERT_ENTITY,
        {
            "name": name,
            "properties": json.dumps({}),
            "memory_ids": [str(m) for m in ids],
        },
    )
    await session.flush()
    return ids


async def _detect(session, project):
    await detection.detect_for_project(session, project)
    await session.flush()


async def _diff_after_run(session, project):
    """What the door computes: the stored prior against the live rows."""
    prior = await pins.load_topic_prior(session, project)
    current = await repo.list_with_members(session, project)
    return {
        entry.dominant_name: entry
        for entry in pins.diff_topics(prior, current)
    }


async def test_the_first_ever_run_has_no_prior_and_reads_new(session):
    project = "t291-new"
    await _seed_cluster(session, project, "t291-new-alpha")

    await _detect(session, project)

    entries = await _diff_after_run(session, project)
    entry = entries["t291-new-alpha"]
    assert entry.status == pins.STATUS_NEW
    assert entry.prior_member_count is None


async def test_stable_is_reachable_across_two_real_detection_runs(session):
    project = "t291-stable"
    await _seed_cluster(session, project, "t291-stable-alpha")

    await _detect(session, project)
    await _detect(session, project)

    entries = await _diff_after_run(session, project)
    entry = entries["t291-stable-alpha"]
    assert entry.status == pins.STATUS_STABLE
    assert entry.prior_member_count == entry.member_count == 3


async def test_grown_is_reachable_across_two_real_detection_runs(session):
    project = "t291-grown"
    await _seed_cluster(session, project, "t291-grown-alpha")

    await _detect(session, project)

    # The corpus grows between runs, past `DEFAULT_GROWTH_THRESHOLD`.
    extra = [await seed_memory(session, project) for _ in range(2)]
    await session.flush()
    await session.execute(
        _EXTEND_ENTITY,
        {"name": "t291-grown-alpha", "memory_ids": [str(m) for m in extra]},
    )
    await session.flush()

    await _detect(session, project)

    entries = await _diff_after_run(session, project)
    entry = entries["t291-grown-alpha"]
    assert entry.status == pins.STATUS_GROWN
    assert entry.prior_member_count == 3
    assert entry.member_count == 5


async def test_decayed_is_reachable_across_two_real_detection_runs(session):
    project = "t291-decayed"
    await _seed_cluster(session, project, "t291-decayed-alpha")
    await _seed_cluster(session, project, "t291-decayed-beta")

    await _detect(session, project)

    # Beta's entity is what held its memories together; without it they are
    # isolated nodes and the community has no successor in the next run.
    await session.execute(
        text("DELETE FROM entities WHERE name = 't291-decayed-beta'")
    )
    await session.flush()

    await _detect(session, project)

    entries = await _diff_after_run(session, project)
    assert entries["t291-decayed-beta"].status == pins.STATUS_DECAYED
    assert entries["t291-decayed-beta"].member_count == 0
    assert entries["t291-decayed-beta"].prior_member_count == 3
    assert entries["t291-decayed-alpha"].status == pins.STATUS_STABLE


async def test_the_prior_describes_the_previous_run_not_the_current_one(session):
    """The ordering property Phase P exists for: capture happens *before* the
    rewrite, so the stored prior can never be a copy of the rows it is meant
    to be compared against."""
    project = "t291-ordering"
    await _seed_cluster(session, project, "t291-ordering-alpha")

    await _detect(session, project)
    extra = [await seed_memory(session, project) for _ in range(2)]
    await session.flush()
    await session.execute(
        _EXTEND_ENTITY,
        {"name": "t291-ordering-alpha", "memory_ids": [str(m) for m in extra]},
    )
    await session.flush()
    await _detect(session, project)

    prior = await pins.load_topic_prior(session, project)
    current = await repo.list_with_members(session, project)
    live_counts = {row.label: len(row.memory_ids) for row in current}
    stored_counts = {label: s.member_count for label, s in prior.items()}

    assert stored_counts != live_counts
    assert set(stored_counts.values()) == {3}
    assert set(live_counts.values()) == {5}
