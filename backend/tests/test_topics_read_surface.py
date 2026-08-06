"""T2.39a — the topics read surface and the pin-suggestion door.

T2.20 shipped `topic_browsing.py` and `pin_suggestions.py` with zero
callers anywhere in `app/`. This suite drives the REST doors this task
adds under `/api/v1/knowledge` and proves the properties the task's
Done-when clauses name: a pending report reads as pending rather than
absent, the pin-suggestion door serves `diff_topics`' output rather than
just the current set, accept/dismiss persist keyed on the stable
dominant-entity label rather than the churning community id, every door is
project-scoped, and accept/dismiss journal to `events` with an
already-vocabulary event type.
"""
from __future__ import annotations

from urllib.parse import quote

from sqlalchemy import text

from app.repositories import memory_communities as repo
from app.repositories import pinned_subjects
from app.services import memory_community_detection as detection
from app.services import pin_suggestions as pins
from app.utils.ids import new_id

PROJECT = "t239a-topics"
OTHER_PROJECT = "t239a-other"

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
    # `confirmed` rather than `corroborated` (T2.99): this door's fact floor
    # is measured on the served rung, and `corroborated` is withheld while
    # G-C's promotion record is absent. These tests are about the diff, the
    # project scoping and the accept/dismiss round trip, so they seed the one
    # verified rung that reads the same at either gate state.
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


def _draft(label, memory_ids, dominant_name=None, dominant_type=None, size=None):
    properties = {"size": size if size is not None else len(memory_ids)}
    if dominant_name is not None:
        properties["dominant_entities"] = [
            {"name": dominant_name, "type": dominant_type, "display_name": dominant_name}
        ]
    return repo.CommunityDraft(
        label=label, memory_ids=tuple(memory_ids), properties=properties
    )


def _quoted(label: str) -> str:
    return quote(label, safe="")


# ---------------------------------------------------------------------------
# GET /topics — list
# ---------------------------------------------------------------------------


async def test_list_topics_serves_browse_topics_shape(session, client, auth_headers):
    a = await seed_memory(session)
    b = await seed_memory(session)
    c = await seed_memory(session)
    await repo.replace_project_communities(
        session, PROJECT, [_draft("alpha", (a, b, c), "alpha", "concept")]
    )
    await session.flush()

    response = await client.get(
        f"/api/v1/knowledge/topics?project={PROJECT}", headers=auth_headers
    )
    assert response.status_code == 200
    items = response.json()["items"]
    assert len(items) == 1
    item = items[0]
    assert item["project"] == PROJECT
    assert item["label"] == "alpha"
    assert item["member_count"] == 3
    assert item["report_status"] == "pending"
    assert item["report"] is None


async def test_a_pending_report_reads_as_pending_never_absent(session, client, auth_headers):
    """Invariant 14's shape: a topic with no report yet must carry
    `report_status == "pending"` with `report is None`, and once a report
    is generated it must carry `report_status == "ready"` with the real
    text — the two states are never collapsed into "report is null or
    not". (`report_status()` treats an empty/falsy `report_string` as "no
    report yet" by design — `generate_reports`' only producer of
    `report_string` is a real LLM completion, so a deliberately-empty
    "generated but nothing to say" state does not exist to distinguish.)
    """
    a = await seed_memory(session)
    b = await seed_memory(session)
    c = await seed_memory(session)
    (community_id,) = await repo.replace_project_communities(
        session, PROJECT, [_draft("eligible", (a, b, c))]
    )
    await session.flush()

    response = await client.get(
        f"/api/v1/knowledge/topics?project={PROJECT}", headers=auth_headers
    )
    item = response.json()["items"][0]
    assert item["report_status"] == "pending"
    assert item["report"] is None

    await repo.set_report(session, community_id, report_string="a generated report")
    await session.flush()

    response = await client.get(
        f"/api/v1/knowledge/topics?project={PROJECT}", headers=auth_headers
    )
    item = response.json()["items"][0]
    assert item["report_status"] == "ready"
    assert item["report"] == "a generated report"


async def test_skipped_and_pending_are_distinguished_on_the_wire(session, client, auth_headers):
    a = await seed_memory(session)
    b = await seed_memory(session)
    c = await seed_memory(session)
    await repo.replace_project_communities(
        session, PROJECT,
        [
            repo.CommunityDraft(label="tiny", memory_ids=(a,), properties={"size": 1}),
            repo.CommunityDraft(label="big-enough", memory_ids=(b, c), properties={"size": 3}),
        ],
    )
    await session.flush()

    response = await client.get(
        f"/api/v1/knowledge/topics?project={PROJECT}", headers=auth_headers
    )
    by_label = {item["label"]: item for item in response.json()["items"]}
    assert by_label["tiny"]["report_status"] == "skipped"
    assert by_label["big-enough"]["report_status"] == "pending"
    assert by_label["tiny"]["report_status"] != by_label["big-enough"]["report_status"]


# ---------------------------------------------------------------------------
# GET /topics/{label} — detail, served through get_injectable_report
# ---------------------------------------------------------------------------


async def test_topic_detail_serves_the_injectable_report_when_ready(session, client, auth_headers):
    a = await seed_memory(session)
    (community_id,) = await repo.replace_project_communities(
        session, PROJECT, [_draft("alpha", (a,), size=3)]
    )
    await session.flush()

    response = await client.get(
        f"/api/v1/knowledge/topics/{_quoted('alpha')}?project={PROJECT}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert body["report_status"] == "pending"
    assert body["report"] is None

    await repo.set_report(session, community_id, report_string="the injectable text")
    await session.flush()

    response = await client.get(
        f"/api/v1/knowledge/topics/{_quoted('alpha')}?project={PROJECT}",
        headers=auth_headers,
    )
    body = response.json()
    assert body["report_status"] == "ready"
    assert body["report"] == "the injectable text"


async def test_topic_detail_404_for_a_missing_label(session, client, auth_headers):
    response = await client.get(
        f"/api/v1/knowledge/topics/{_quoted('nope')}?project={PROJECT}",
        headers=auth_headers,
    )
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# Project isolation — every door is scoped, cross-project reads fail
# ---------------------------------------------------------------------------


async def test_list_topics_never_leaks_another_projects_label(session, client, auth_headers):
    a = await seed_memory(session, project=PROJECT)
    b = await seed_memory(session, project=OTHER_PROJECT)
    await repo.replace_project_communities(
        session, PROJECT, [_draft("mine", (a,), "mine", "concept")]
    )
    await repo.replace_project_communities(
        session, OTHER_PROJECT, [_draft("theirs", (b,), "theirs", "concept")]
    )
    await session.flush()

    response = await client.get(
        f"/api/v1/knowledge/topics?project={PROJECT}", headers=auth_headers
    )
    labels = {item["label"] for item in response.json()["items"]}
    assert labels == {"mine"}
    assert "theirs" not in labels


async def test_topic_detail_cross_project_read_404s_rather_than_answers(
    session, client, auth_headers
):
    a = await seed_memory(session, project=OTHER_PROJECT)
    await repo.replace_project_communities(
        session, OTHER_PROJECT, [_draft("foreign-topic", (a,), "foreign", "concept")]
    )
    await session.flush()

    # The label exists, but not under PROJECT — a cross-project read must
    # fail, never silently answer with the other project's topic.
    response = await client.get(
        f"/api/v1/knowledge/topics/{_quoted('foreign-topic')}?project={PROJECT}",
        headers=auth_headers,
    )
    assert response.status_code == 404


async def test_pin_suggestions_door_is_project_scoped(session, client, auth_headers):
    a = await seed_memory(session, project=PROJECT)
    b = await seed_memory(session, project=OTHER_PROJECT)
    await seed_fact(session, subject_name="alpha-subject", project=PROJECT)
    await seed_fact(session, subject_name="beta-subject", project=OTHER_PROJECT)
    await repo.replace_project_communities(
        session, PROJECT,
        [_draft("alpha-topic", (a,), "alpha-subject", "concept")],
    )
    await repo.replace_project_communities(
        session, OTHER_PROJECT,
        [_draft("beta-topic", (b,), "beta-subject", "concept")],
    )
    await session.flush()

    response = await client.get(
        f"/api/v1/knowledge/topics/pin-suggestions?project={PROJECT}",
        headers=auth_headers,
    )
    body = response.json()
    diff_labels = {e["label"] for e in body["diff"]}
    suggestion_subjects = {s["subject_key"] for s in body["suggestions"]}
    assert diff_labels == {"alpha-topic"}
    assert suggestion_subjects == {pins.subject_soft_key("alpha-subject", "concept")}
    assert pins.subject_soft_key("beta-subject", "concept") not in suggestion_subjects


# ---------------------------------------------------------------------------
# GET /topics/pin-suggestions — diff_topics' output, not just the current set
# ---------------------------------------------------------------------------


async def test_pin_suggestions_serves_the_diff_with_statuses(session, client, auth_headers):
    a = await seed_memory(session)
    await seed_fact(session, subject_name="postgres")
    await repo.replace_project_communities(
        session, PROJECT, [_draft("postgres, tuning", (a,), "postgres", "tool")]
    )
    await session.flush()

    response = await client.get(
        f"/api/v1/knowledge/topics/pin-suggestions?project={PROJECT}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    body = response.json()
    assert len(body["diff"]) == 1
    entry = body["diff"][0]
    assert entry["label"] == "postgres, tuning"
    assert entry["status"] == "new"
    assert entry["project"] == PROJECT

    assert len(body["suggestions"]) == 1
    suggestion = body["suggestions"][0]
    assert suggestion["subject_key"] == pins.subject_soft_key("postgres", "tool")
    assert suggestion["why"] == "new"
    assert suggestion["verified_fact_count"] == 1
    assert body["pinned_subject_keys"] == []
    assert body["dismissed_subject_keys"] == []


async def test_pin_suggestions_read_door_does_not_journal(session, client, auth_headers):
    """`compute_pin_suggestions` is a safe read a browsing UI can call on
    every page load (T2.20's own docstring); `journal_pin_suggestions` is a
    one-time-per-run call the detection job owns. This door must call only
    the former, or every page view would write a permanent `events` row."""
    a = await seed_memory(session)
    await seed_fact(session, subject_name="postgres")
    await repo.replace_project_communities(
        session, PROJECT, [_draft("postgres, tuning", (a,), "postgres", "tool")]
    )
    await session.flush()

    for _ in range(3):
        response = await client.get(
            f"/api/v1/knowledge/topics/pin-suggestions?project={PROJECT}",
            headers=auth_headers,
        )
        assert response.status_code == 200

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
    assert rows == []


# ---------------------------------------------------------------------------
# accept / dismiss — persist, journal, and key on the dominant-entity label
# ---------------------------------------------------------------------------


async def test_accept_pin_suggestion_persists_and_suppresses_reads(session, client, auth_headers):
    a = await seed_memory(session)
    await seed_fact(session, subject_name="postgres")
    await repo.replace_project_communities(
        session, PROJECT, [_draft("postgres, tuning", (a,), "postgres", "tool")]
    )
    await session.flush()

    subject_key = pins.subject_soft_key("postgres", "tool")
    response = await client.post(
        "/api/v1/knowledge/topics/pin-suggestions/accept",
        headers=auth_headers,
        json={"project": PROJECT, "subject_key": subject_key, "label": "postgres, tuning"},
    )
    assert response.status_code == 204
    assert response.content == b""

    pinned, dismissed = await pinned_subjects.get_subject_lists(session, PROJECT)
    assert subject_key in pinned
    assert subject_key not in dismissed

    response = await client.get(
        f"/api/v1/knowledge/topics/pin-suggestions?project={PROJECT}",
        headers=auth_headers,
    )
    assert response.json()["suggestions"] == []
    assert response.json()["pinned_subject_keys"] == [subject_key]


async def test_dismiss_pin_suggestion_persists_and_suppresses_reads(session, client, auth_headers):
    a = await seed_memory(session)
    await seed_fact(session, subject_name="postgres")
    await repo.replace_project_communities(
        session, PROJECT, [_draft("postgres, tuning", (a,), "postgres", "tool")]
    )
    await session.flush()

    subject_key = pins.subject_soft_key("postgres", "tool")
    response = await client.post(
        "/api/v1/knowledge/topics/pin-suggestions/dismiss",
        headers=auth_headers,
        json={"project": PROJECT, "subject_key": subject_key, "label": "postgres, tuning"},
    )
    assert response.status_code == 204

    pinned, dismissed = await pinned_subjects.get_subject_lists(session, PROJECT)
    assert subject_key in dismissed
    assert subject_key not in pinned

    response = await client.get(
        f"/api/v1/knowledge/topics/pin-suggestions?project={PROJECT}",
        headers=auth_headers,
    )
    assert response.json()["suggestions"] == []
    assert response.json()["dismissed_subject_keys"] == [subject_key]


async def test_accept_and_dismiss_journal_pin_decision_events(session, client, auth_headers):
    subject_key = "postgres::tool"
    other_key = "other::tool"

    await client.post(
        "/api/v1/knowledge/topics/pin-suggestions/accept",
        headers=auth_headers,
        json={"project": PROJECT, "subject_key": subject_key, "label": "alpha"},
    )
    await client.post(
        "/api/v1/knowledge/topics/pin-suggestions/dismiss",
        headers=auth_headers,
        json={"project": PROJECT, "subject_key": other_key, "label": "beta"},
    )

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


async def test_accept_via_the_route_survives_a_community_id_change_across_runs(
    session, client, auth_headers
):
    """The clause that makes this task non-trivial (T2.20's Done-when):
    accept/dismiss must key on the stable dominant-entity label/soft-key,
    never the churning community id. `memory_communities` is
    delete-and-rewrite per project (doc 06 §7), so every detection run
    mints a brand new community id even when the dominant entity — and
    therefore the correct suppression key — is unchanged. A single-run
    fixture cannot see this: the guard only fires across two runs where
    the id changes and the entity does not.
    """
    a = await seed_memory(session)
    await seed_fact(session, subject_name="postgres")

    # Run 1.
    (first_id,) = await repo.replace_project_communities(
        session, PROJECT, [_draft("postgres, tuning", (a,), "postgres", "tool")]
    )
    await session.flush()

    response = await client.get(
        f"/api/v1/knowledge/topics/pin-suggestions?project={PROJECT}",
        headers=auth_headers,
    )
    suggestions = response.json()["suggestions"]
    assert len(suggestions) == 1
    subject_key = suggestions[0]["subject_key"]
    assert subject_key == pins.subject_soft_key("postgres", "tool")

    accept_response = await client.post(
        "/api/v1/knowledge/topics/pin-suggestions/accept",
        headers=auth_headers,
        json={"project": PROJECT, "subject_key": subject_key, "label": "postgres, tuning"},
    )
    assert accept_response.status_code == 204

    # Run 2: the same dominant entity, a different label (a plausible
    # relabel/split) and — because replace_project_communities always
    # deletes and re-inserts — a brand new community id.
    b = await seed_memory(session)
    c = await seed_memory(session)
    (second_id,) = await repo.replace_project_communities(
        session, PROJECT,
        [_draft("postgres, performance", (a, b, c), "postgres", "tool")],
    )
    await session.flush()
    assert second_id != first_id

    response = await client.get(
        f"/api/v1/knowledge/topics/pin-suggestions?project={PROJECT}",
        headers=auth_headers,
    )
    body = response.json()
    # The new community reads as `new` on this door (no cross-run snapshot
    # here), but the accept from run 1 must still suppress it — because
    # suppression is keyed on the dominant entity's soft key, which is
    # identical across the two runs, not on the community id, which is not.
    assert any(e["label"] == "postgres, performance" for e in body["diff"])
    assert body["suggestions"] == [], (
        "a suggestion reappeared for an already-accepted subject after a "
        "community-id-changing rewrite — the accept did not survive the "
        "churn, which is exactly what keying on the community id instead "
        "of the dominant-entity soft key would produce"
    )


# ---------------------------------------------------------------------------
# T2.91 — the door diffs against a durable prior, so a status other than
# `new` can actually reach the wire
# ---------------------------------------------------------------------------

_T291_INSERT_ENTITY = text(
    "INSERT INTO entities (name, entity_type, properties, memory_ids) "
    "VALUES (:name, 'tool', '{}'::jsonb, CAST(:memory_ids AS uuid[]))"
)

_T291_EXTEND_ENTITY = text(
    "UPDATE entities SET memory_ids = memory_ids || CAST(:memory_ids AS uuid[]) "
    "WHERE name = :name"
)


async def _t291_cluster(session, project, name, size=3):
    ids = [await seed_memory(session, project) for _ in range(size)]
    await session.flush()
    await session.execute(
        _T291_INSERT_ENTITY,
        {"name": name, "memory_ids": [str(m) for m in ids]},
    )
    await session.flush()


async def _t291_detect(session, project):
    await detection.detect_for_project(session, project)
    await session.flush()


async def _t291_diff(client, auth_headers, project):
    response = await client.get(
        f"/api/v1/knowledge/topics/pin-suggestions?project={project}",
        headers=auth_headers,
    )
    assert response.status_code == 200
    return {entry["dominant_name"]: entry for entry in response.json()["diff"]}


async def test_the_door_serves_stable_after_two_real_detection_runs(
    session, client, auth_headers
):
    """Before T2.91 this was unreachable: the door diffed against `{}`, so
    every entry read `new` no matter how many runs had happened."""
    project = "t291-door-stable"
    await _t291_cluster(session, project, "t291-door-stable-alpha")

    await _t291_detect(session, project)
    await _t291_detect(session, project)

    entry = (await _t291_diff(client, auth_headers, project))[
        "t291-door-stable-alpha"
    ]
    assert entry["status"] == "stable"
    assert entry["prior_member_count"] == 3


async def test_the_door_serves_grown_when_the_topic_actually_grew(
    session, client, auth_headers
):
    project = "t291-door-grown"
    await _t291_cluster(session, project, "t291-door-grown-alpha")
    await _t291_detect(session, project)

    extra = [await seed_memory(session, project) for _ in range(2)]
    await session.flush()
    await session.execute(
        _T291_EXTEND_ENTITY,
        {"name": "t291-door-grown-alpha", "memory_ids": [str(m) for m in extra]},
    )
    await session.flush()
    await _t291_detect(session, project)

    entry = (await _t291_diff(client, auth_headers, project))[
        "t291-door-grown-alpha"
    ]
    assert entry["status"] == "grown"
    assert entry["prior_member_count"] == 3
    assert entry["member_count"] == 5


async def test_the_door_serves_decayed_for_a_topic_with_no_successor(
    session, client, auth_headers
):
    project = "t291-door-decayed"
    await _t291_cluster(session, project, "t291-door-decayed-alpha")
    await _t291_cluster(session, project, "t291-door-decayed-beta")
    await _t291_detect(session, project)

    await session.execute(
        text("DELETE FROM entities WHERE name = 't291-door-decayed-beta'")
    )
    await session.flush()
    await _t291_detect(session, project)

    entries = await _t291_diff(client, auth_headers, project)
    assert entries["t291-door-decayed-beta"]["status"] == "decayed"
    assert entries["t291-door-decayed-beta"]["member_count"] == 0
    assert entries["t291-door-decayed-beta"]["prior_member_count"] == 3
