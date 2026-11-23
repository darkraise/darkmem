"""Doc 10 §6 / doc 08 §4.1 — lifting a repository's assertions to Layer 2.

Three properties carry this task, and each of them has a shape that passes a
naive test while proving nothing:

* **One origin per repository, however many commits.** Re-deriving over an
  *unchanged* import set is a no-op — the lift finds the source already
  present and writes nothing — so a test that re-derives twice and counts one
  origin may be observing the no-op rather than the rule. Every re-index below
  changes the import set, so the derivation genuinely re-executes, and the
  count is taken with the repository's own ``COUNT(DISTINCT origin_key)``, and
  its negative control counts a *shared* fact reading two — a control over two
  differently-named repositories asserts scoping, not the counter.
* **Born-corroborated is the ladder's only exception.** Asserted from three
  directions, because the exception is only as narrow as its narrowest guard:
  the minting function refuses every other source kind, the predicate that
  keeps the rung through a recompute cannot be satisfied by one, and a scan
  pins the single caller of each door onto the rung — in any position, since
  an aliased ``f = repo.open_born_corroborated`` is the same door reached
  through a name. The rung is **restored** on the same evidence it was granted
  on (fix round 1), which is why the veto's precedence and the count's
  ownership of every other fact are asserted here rather than assumed.
* **Withdrawal invalidates.** The row survives with ``invalid_at`` closed and
  ``expired_at`` NULL, and a fact another live source still holds is untouched
  — which is the half a withdrawal test usually skips.

**The doors are driven with the gate closed, and that is not redundant with
T2.95's scan.** The scan cannot see a module that copies a fact row wholesale
and never calls the producer, which is deliberate; so the surfaces here are
asked what they actually serve rather than being argued about.
"""

from __future__ import annotations

import ast
import json
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.api.mcp import server as mcp_server
from app.main import app as fastapi_app
from app.repositories.fact_sources import (
    CODE_SOURCE_KIND,
    FactSourceRepository,
    OriginObservation,
    OriginProfile,
)
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.code_deriver import assert_repo_graph
from app.services.contradiction_veto import adjudicate_contradiction
from app.services.events import CONTRADICTION_SCANNED, record_event
from app.services.fact_lift import (
    CODE_FACT_PROJECT,
    IMPORT_BASIS,
    LANGUAGE_BASIS,
    _CodeCandidate,
    code_source_detail,
    mint_born_corroborated,
    reconcile_code_sources,
    repo_witnesses,
    restore_born_rung,
    run_code_lift,
    run_lift,
)
from app.services.fact_provenance import MEMORY_SOURCE_KIND, memory_source_ref
from app.services.triple_key import compute_triple_key
from app.services.verification_ladder import recompute_fact

BACKEND = Path(__file__).resolve().parents[1]

FACTS_ROUTE = "/api/v1/knowledge/facts"

# Two files in two languages, so the language half of the deriver has
# something to assert and the import half has a witness whose language gate
# actually passes.
REPO_FILES = [
    ("backend/app/services/store.py", "python"),
    ("frontend/src/Panel.tsx", "typescript"),
]
PY_FILE = REPO_FILES[0][0]

# `httpx` is the dependency every round keeps: it is what makes "one origin
# after N re-indexes" a statement about a *surviving* fact rather than about a
# fact that happened to be minted once. Both names land on the `tool` type and
# so on `DEPENDS_ON`; `redis` would land on `database` and `USES`, which is the
# deriver's own taxonomy ladder doing its job rather than something to work
# around, but it makes for a test that reads as if it were asserting one thing
# while asserting another.
STABLE_IMPORTS = ["httpx", "fastapi"]


async def _seed_repo(
    session,
    *,
    name: str,
    imports: list[str] | None = None,
    commit: str = "c0ffee0",
) -> str:
    repo_id = str(uuid4())
    await session.execute(
        text(
            "INSERT INTO repositories (id, name, status, "
            "last_indexed_commit) VALUES (CAST(:id AS uuid), :name, "
            "'ready', :sha)"
        ),
        {"id": repo_id, "name": name, "sha": commit},
    )
    for file_path, language in REPO_FILES:
        await session.execute(
            text(
                "INSERT INTO code_files (id, repo_id, file_path, language) "
                "VALUES (CAST(:id AS uuid), CAST(:rid AS uuid), :fp, :lang)"
            ),
            {"id": str(uuid4()), "rid": repo_id, "fp": file_path, "lang": language},
        )
        await session.execute(
            text(
                "INSERT INTO code_graph_nodes (repo_id, kind, key, label) "
                "VALUES (CAST(:rid AS uuid), 'file', :key, :key) "
                "ON CONFLICT DO NOTHING"
            ),
            {"rid": repo_id, "key": file_path},
        )
    await _set_imports(session, repo_id, imports if imports is not None else STABLE_IMPORTS)
    await session.flush()
    return repo_id


async def _set_imports(session, repo_id: str, imports: list[str]) -> None:
    """Replace a repository's import edges, the way a re-index would."""
    await session.execute(
        text(
            "DELETE FROM code_edges WHERE repo_id = CAST(:rid AS uuid) "
            "AND edge_type = 'imports'"
        ),
        {"rid": repo_id},
    )
    for source in imports:
        await session.execute(
            text(
                "INSERT INTO code_graph_nodes (repo_id, kind, key, label) "
                "VALUES (CAST(:rid AS uuid), 'module', :key, :key) "
                "ON CONFLICT DO NOTHING"
            ),
            {"rid": repo_id, "key": source},
        )
        await session.execute(
            text("""
                INSERT INTO code_edges
                    (repo_id, source_kind, source_key, target_kind, target_key,
                     edge_type)
                VALUES (CAST(:rid AS uuid), 'file', :src, 'module', :tgt,
                        'imports')
                ON CONFLICT DO NOTHING
            """),
            {"rid": repo_id, "src": PY_FILE, "tgt": source},
        )
    await session.flush()


async def _reindex(session, repo_id: str, imports: list[str], *, commit: str) -> None:
    """A full re-index: a new HEAD, a new import set, a re-derivation."""
    await session.execute(
        text(
            "UPDATE repositories SET last_indexed_commit = :sha "
            "WHERE id = CAST(:rid AS uuid)"
        ),
        {"rid": repo_id, "sha": commit},
    )
    await _set_imports(session, repo_id, imports)
    await assert_repo_graph(session, repo_id)
    await session.flush()


async def _fact_for(session, subject: str, rel_type: str, obj: str) -> dict | None:
    """The one row on this triple, and it refuses to pick between two.

    Strict on purpose, and the strictness was earned: an earlier version took
    the newest row, and a mutation drill that wrongly invalidated a fact passed
    anyway — the next tick minted a fresh open row on the same key and the
    assertion landed on that instead. A helper that silently chooses is a
    helper that can hide the failure it was called to detect. Two rows on one
    key is a real state (invalidate-not-delete plus a later re-assertion opens
    a new window), so a test that wants it has to say so.
    """
    key = compute_triple_key(CODE_FACT_PROJECT, subject, rel_type, obj)
    rows = (await session.execute(
        text(
            "SELECT id, verification_status, invalid_at, expired_at "
            "FROM knowledge_triples WHERE triple_key = :key "
            "ORDER BY created_at, id"
        ),
        {"key": key},
    )).mappings().all()
    if not rows:
        return None
    assert len(rows) == 1, (
        f"{len(rows)} rows on triple_key {key}: "
        + "; ".join(f"{r['id']} invalid_at={r['invalid_at']}" for r in rows)
    )
    row = rows[0]
    # Normalised at the boundary: asyncpg hands `id` back as a UUID while every
    # repository method returns the text spelling, and a bare `==` between the
    # two is False (invariant 9).
    return {**dict(row), "id": str(row["id"])}


async def _sources(session, fact_id) -> list[dict]:
    rows = (await session.execute(
        text(
            "SELECT source_kind, source_ref, origin_key, detail FROM fact_sources "
            "WHERE fact_id = CAST(:fid AS uuid) ORDER BY source_kind, source_ref"
        ),
        {"fid": str(fact_id)},
    )).mappings().all()
    return [dict(row) for row in rows]


async def _seed_memory(session, *, content: str, origin_key: str) -> str:
    memory_id = str(uuid4())
    await session.execute(
        text(
            "INSERT INTO memories (id, content, source, project, origin_key) "
            "VALUES (CAST(:id AS uuid), :content, 'api', :project, :origin)"
        ),
        {
            "id": memory_id,
            "content": content,
            "project": CODE_FACT_PROJECT,
            "origin": origin_key,
        },
    )
    await session.flush()
    return memory_id


# ── clause 1: one origin per repository, however many commits ────────────


async def test_a_repo_indexed_a_hundred_times_is_still_one_origin(session):
    """The truth-critical rule (doc 10 §6, doc 08 §4.1).

    The import set changes on every round, so each re-index really re-derives:
    a churning dependency enters and leaves the graph, which is asserted, and
    new facts are minted along the way. The surviving `redis` fact is the one
    the count is taken over, and it is taken with the repository's own
    ``COUNT(DISTINCT origin_key)`` rather than by counting rows — the two
    differ exactly when the rule is broken.
    """
    repo_id = await _seed_repo(session, name="Origin-Repo")
    await assert_repo_graph(session, repo_id)
    await run_code_lift(session)

    fact = await _fact_for(session, "origin-repo", "DEPENDS_ON", "httpx")
    assert fact is not None
    born_id = fact["id"]

    rounds = 100
    for index in range(rounds):
        # A dependency unique to this round, so the derivation cannot be a
        # no-op and the strip-and-rewrite genuinely re-executes.
        churn = f"pkg-round-{index}"
        await _reindex(
            session,
            repo_id,
            STABLE_IMPORTS + [churn],
            commit=f"sha{index:04d}",
        )
        assert await _entity_exists(session, churn), (
            "the re-derivation did not execute: this round's dependency never "
            "reached Layer 1, so the count below would prove nothing"
        )
        await run_code_lift(session, batch_size=500)

    # The churning dependency of the last round is in the graph; the one
    # before it is not — the strip really ran on every round.
    assert await _entity_exists(session, f"pkg-round-{rounds - 1}")
    assert not await _entity_exists(session, f"pkg-round-{rounds - 2}")

    survivor = await _fact_for(session, "origin-repo", "DEPENDS_ON", "httpx")
    assert survivor["id"] == born_id, "the surviving fact was re-minted, not reused"

    repo = FactSourceRepository(session)
    assert await repo.count_distinct_origins(born_id) == 1
    rows = await _sources(session, born_id)
    assert len(rows) == 1, f"{rounds} re-indexes wrote {len(rows)} provenance rows"
    assert rows[0]["origin_key"] == repo_id
    assert rows[0]["source_ref"] == repo_id


async def _entity_exists(session, name: str) -> bool:
    found = (await session.execute(
        text("SELECT 1 FROM entities WHERE name = :name"), {"name": name}
    )).scalar_one_or_none()
    return found is not None


async def test_one_repositorys_sources_do_not_bleed_onto_anothers_fact(session):
    """Two differently-named repositories lift two *different* facts, because
    each repo's own name is the subject. Each fact carries only its own repo's
    provenance — which is a statement about scoping, not about the counter."""
    first = await _seed_repo(session, name="Alpha-Repo", imports=["httpx"])
    second = await _seed_repo(session, name="Beta-Repo", imports=["httpx"])
    for repo_id in (first, second):
        await assert_repo_graph(session, repo_id)
    await run_code_lift(session)

    fact = await _fact_for(session, "alpha-repo", "DEPENDS_ON", "httpx")
    other = await _fact_for(session, "beta-repo", "DEPENDS_ON", "httpx")
    assert fact["id"] != other["id"]

    rows = await _sources(session, fact["id"])
    assert [row["origin_key"] for row in rows] == [first]


async def test_two_repositories_asserting_one_fact_are_two_origins(session):
    """The counter's genuine negative control, and it needs a *shared* fact.

    The clause-1 test above proves one repository re-indexed a hundred times
    counts once. A rule that collapsed *any* code provenance to a single origin
    would pass it and be wrong, so the count has to be seen reading two — which
    only happens when two repositories assert the same triple. Since the
    subject of a derived dependency fact is the repository's own name, that
    means two repositories of the same name (the shape
    ``test_a_fact_a_second_live_repo_still_asserts_survives`` also uses).
    """
    first = await _seed_repo(session, name="Counted-Repo", imports=["httpx"])
    await assert_repo_graph(session, first)
    await run_code_lift(session)
    fact = await _fact_for(session, "counted-repo", "DEPENDS_ON", "httpx")
    assert await FactSourceRepository(session).count_distinct_origins(fact["id"]) == 1

    second = await _seed_repo(session, name="Counted-Repo", imports=["httpx"])
    await assert_repo_graph(session, second)
    await run_code_lift(session)

    same = await _fact_for(session, "counted-repo", "DEPENDS_ON", "httpx")
    assert same["id"] == fact["id"], "the second repo minted its own fact"
    assert await FactSourceRepository(session).count_distinct_origins(fact["id"]) == 2
    assert sorted(row["origin_key"] for row in await _sources(session, fact["id"])) == (
        sorted([first, second])
    )


# ── the provenance shape T2.48 consumes ──────────────────────────────────


async def test_the_detail_addresses_code_by_name_and_sha_not_by_node_id(session):
    """Doc 10 §6's fixed shape: ``{commit_sha, basis, file_path, symbol_key}``.

    ``symbol_key`` is re-resolved here against ``code_graph_nodes`` the way the
    citation re-verifier will, which is the only assertion that proves the key
    is an address rather than a string. A ``BIGSERIAL`` id would satisfy a
    shape check and fail this one after the next full re-index.
    """
    repo_id = await _seed_repo(session, name="Detail-Repo", imports=["httpx"])
    await assert_repo_graph(session, repo_id)
    await run_code_lift(session)

    fact = await _fact_for(session, "detail-repo", "DEPENDS_ON", "httpx")
    detail = (await _sources(session, fact["id"]))[0]["detail"]
    assert set(detail) == {"commit_sha", "basis", "file_path", "symbol_key"}
    assert detail["commit_sha"] == "c0ffee0"
    assert detail["basis"] == IMPORT_BASIS
    assert detail["file_path"] == PY_FILE
    assert detail["symbol_key"] == "httpx"

    resolved = (await session.execute(
        text(
            "SELECT id FROM code_graph_nodes WHERE repo_id = CAST(:rid AS uuid) "
            "AND key = :key"
        ),
        {"rid": repo_id, "key": detail["symbol_key"]},
    )).scalar_one_or_none()
    assert resolved is not None, "symbol_key does not resolve against the code graph"

    language_fact = await _fact_for(session, "detail-repo", "USES", "python")
    language_detail = (await _sources(session, language_fact["id"]))[0]["detail"]
    assert language_detail["basis"] == LANGUAGE_BASIS
    assert language_detail["symbol_key"] == PY_FILE


async def test_the_detail_keys_are_all_present_even_with_no_witness():
    """A key that is sometimes absent and sometimes null is two shapes wearing
    one name, and the re-verifier reads it with a subscript."""
    detail = code_source_detail(commit_sha=None, witness=None)
    assert set(detail) == {"commit_sha", "basis", "file_path", "symbol_key"}
    assert all(value is None for value in detail.values())


async def test_a_new_commit_refreshes_nothing_it_should_not(session):
    """First-assertion-wins on ``add_source`` means a re-index at a new HEAD
    keeps the sha the assertion was *born* at. Pinned because it is a
    consequence a reader would otherwise have to infer, and because T2.48 has
    to know which commit the recorded key is addressed against."""
    repo_id = await _seed_repo(session, name="Sha-Repo", imports=["httpx"])
    await assert_repo_graph(session, repo_id)
    await run_code_lift(session)

    await _reindex(session, repo_id, ["httpx", "pydantic"], commit="deadbee")
    await run_code_lift(session)

    fact = await _fact_for(session, "sha-repo", "DEPENDS_ON", "httpx")
    assert (await _sources(session, fact["id"]))[0]["detail"]["commit_sha"] == "c0ffee0"
    fresh = await _fact_for(session, "sha-repo", "DEPENDS_ON", "pydantic")
    assert (await _sources(session, fresh["id"]))[0]["detail"]["commit_sha"] == "deadbee"


# ── clause 2: born-corroborated is the only exception to the ladder ──────


async def test_the_fact_is_born_corroborated(session):
    repo_id = await _seed_repo(session, name="Born-Repo", imports=["httpx"])
    await assert_repo_graph(session, repo_id)
    outcome = await run_code_lift(session)

    assert outcome.facts_created >= 1
    fact = await _fact_for(session, "born-repo", "DEPENDS_ON", "httpx")
    assert fact["verification_status"] == "corroborated"
    assert fact["invalid_at"] is None and fact["expired_at"] is None


@pytest.mark.parametrize("kind", [MEMORY_SOURCE_KIND, "human"])
async def test_no_other_source_kind_can_take_the_exception(session, kind):
    """The Done-when's "impossible to widen by accident". The refusal is on the
    function that writes the rung, so it holds however the caller reaches it."""
    candidate = _CodeCandidate(
        repo_id=str(uuid4()),
        triple_key=compute_triple_key(CODE_FACT_PROJECT, "a", "USES", "b"),
        subject_name="a",
        rel_type="USES",
        object_name="b",
        subject_id=None,
        object_id=None,
    )
    before = (await session.execute(
        text("SELECT COUNT(*) FROM knowledge_triples")
    )).scalar_one()

    with pytest.raises(ValueError, match="can never open a fact above"):
        await mint_born_corroborated(
            session, candidate=candidate, source_kind=kind, detail={}
        )

    after = (await session.execute(
        text("SELECT COUNT(*) FROM knowledge_triples")
    )).scalar_one()
    assert after == before, "the refusal wrote a fact before refusing"


def _profile(*kinds: str) -> OriginProfile:
    moment = datetime(2026, 8, 6, tzinfo=timezone.utc)
    return OriginProfile(
        fact_id=str(uuid4()),
        origins=tuple(
            OriginObservation(
                origin_key=f"origin-{index}",
                source_kinds=(kind,),
                first_seen=moment,
                last_seen=moment,
                row_count=1,
            )
            for index, kind in enumerate(kinds)
        ),
    )


@pytest.mark.parametrize(
    "kinds,expected",
    [
        ((CODE_SOURCE_KIND,), True),
        ((CODE_SOURCE_KIND, MEMORY_SOURCE_KIND), True),
        ((MEMORY_SOURCE_KIND,), False),
        (("human",), False),
        ((MEMORY_SOURCE_KIND, MEMORY_SOURCE_KIND, "human"), False),
        ((), False),
    ],
)
def test_the_ladder_predicate_names_exactly_one_kind(kinds, expected):
    assert _profile(*kinds).parse_is_the_verification is expected


async def test_the_recompute_holds_the_born_rung_and_demotes_the_ordinary_one(session):
    """The exception's whole point, and the shape a birth-only test misses.

    Both facts sit at ``corroborated`` with one origin, which is below every
    threshold the ladder can pick. The code-sourced one holds; the
    memory-sourced one is demoted. Without the hold, a born-corroborated fact
    would carry its rung until the first recompute tick and no longer.
    """
    repo_id = await _seed_repo(session, name="Ladder-Repo", imports=["httpx"])
    await assert_repo_graph(session, repo_id)
    await run_code_lift(session)
    code_fact = await _fact_for(session, "ladder-repo", "DEPENDS_ON", "httpx")

    memory_fact = await KnowledgeTripleRepository(session).insert_open(
        triple_key=compute_triple_key(CODE_FACT_PROJECT, "kafka", "USES", "zookeeper"),
        subject_name="kafka",
        object_name="zookeeper",
        rel_type="USES",
        fact="kafka uses zookeeper",
        reference_time=datetime.now(timezone.utc),
        project=CODE_FACT_PROJECT,
    )
    memory_id = await _seed_memory(session, content="kafka uses zookeeper", origin_key="s1")
    await FactSourceRepository(session).add_source(
        fact_id=memory_fact["id"],
        source_kind=MEMORY_SOURCE_KIND,
        source_ref=memory_source_ref(memory_id),
        origin_key="s1",
    )
    await session.execute(
        text(
            "UPDATE knowledge_triples SET verification_status = 'corroborated' "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": memory_fact["id"]},
    )
    await session.flush()

    held = await recompute_fact(session, code_fact["id"])
    demoted = await recompute_fact(session, memory_fact["id"])

    assert (held.target_status, held.outcome) == ("corroborated", "hold")
    assert held.origin_count == 1 and held.required_n > 1, (
        "the hold has to be the exception firing, not the bar being met"
    )
    # The memory-sourced twin is decided `demote` and then interposed by the
    # grace window, so the *outcome* it reports is a hold too — which is
    # exactly why the assertion is taken on the row rather than on the word.
    # What separates them is the marker: one is on its way down, the other was
    # never on the ladder's count at all.
    assert await _row(session, code_fact["id"]) == ("corroborated", None)
    memory_status, memory_marker = await _row(session, memory_fact["id"])
    assert memory_status == "corroborated" and memory_marker is not None, (
        "the ordinary fact was not put on the demotion path, so the hold "
        "above proves nothing about the exception"
    )
    assert demoted.fact_id == str(memory_fact["id"])


async def _row(session, fact_id) -> tuple[str, object]:
    row = (await session.execute(
        text(
            "SELECT verification_status, demotion_pending_since "
            "FROM knowledge_triples WHERE id = CAST(:id AS uuid)"
        ),
        {"id": str(fact_id)},
    )).mappings().one()
    return row["verification_status"], row["demotion_pending_since"]


async def test_a_fact_a_memory_also_asserts_is_never_re_graded_by_the_code_lift(
    session,
):
    """A producer that reached into an existing row's rung would be grading its
    own output. A fact carrying evidence of its own belongs to the **count**:
    the repository's assertion joins as a second origin of a second kind and
    the recompute decides the rung on the ladder's own terms — journalling the
    promotion, which is the row G-C's promotion rate is made of.

    Driven across two ticks rather than one, because the restore added in fix
    round 1 runs over provenance the *previous* tick stored: a single-tick
    assertion would pass without saying anything about it.
    """
    subject, rel_type, obj = "regrade-repo", "DEPENDS_ON", "httpx"
    existing = await KnowledgeTripleRepository(session).insert_open(
        triple_key=compute_triple_key(CODE_FACT_PROJECT, subject, rel_type, obj),
        subject_name=subject,
        object_name=obj,
        rel_type=rel_type,
        fact=f"{subject} depends on {obj}",
        reference_time=datetime.now(timezone.utc),
        project=CODE_FACT_PROJECT,
    )
    assert existing["verification_status"] == "candidate"
    memory_id = await _seed_memory(session, content="regrade", origin_key="s7")
    await FactSourceRepository(session).add_source(
        fact_id=existing["id"],
        source_kind=MEMORY_SOURCE_KIND,
        source_ref=memory_source_ref(memory_id),
        origin_key="s7",
    )
    await session.flush()

    repo_id = await _seed_repo(session, name="Regrade-Repo", imports=["httpx"])
    await assert_repo_graph(session, repo_id)
    outcome = await run_code_lift(session)
    second_tick = await run_code_lift(session)

    after = await _fact_for(session, subject, rel_type, obj)
    assert after["id"] == existing["id"], "a second open row was minted on one key"
    assert after["verification_status"] == "candidate"
    assert outcome.sources_added >= 1
    assert (outcome.rungs_restored, second_tick.rungs_restored) == (0, 0)
    kinds = {row["source_kind"] for row in await _sources(session, existing["id"])}
    assert kinds == {CODE_SOURCE_KIND, MEMORY_SOURCE_KIND}

    # The count is what moves it, and it leaves the journal row the promotion
    # rate reads. Taking this here is what makes "the lift stayed out of the
    # count's way" a measured claim rather than an absence.
    decision = await recompute_fact(session, existing["id"])
    await session.flush()
    assert (decision.target_status, decision.outcome) == ("corroborated", "promote")
    assert await _verified_outcomes(session, existing["id"]) == ["promote"]


async def test_a_fact_whose_whole_evidence_is_one_parse_is_raised_to_the_rung(session):
    """The other side of the rule, stated so it cannot arrive as a surprise.

    The rung follows the *evidence*, not which producer got to the triple
    first: a fact whose entire provenance is one repository's parse holds it
    whether this path minted the row or found it. The alternative — a rung that
    depends on creation order — would give two facts with identical evidence
    two different labels.
    """
    subject, rel_type, obj = "found-repo", "DEPENDS_ON", "httpx"
    existing = await KnowledgeTripleRepository(session).insert_open(
        triple_key=compute_triple_key(CODE_FACT_PROJECT, subject, rel_type, obj),
        subject_name=subject,
        object_name=obj,
        rel_type=rel_type,
        fact=f"{subject} depends on {obj}",
        reference_time=datetime.now(timezone.utc),
        project=CODE_FACT_PROJECT,
    )
    repo_id = await _seed_repo(session, name="Found-Repo", imports=["httpx"])
    await assert_repo_graph(session, repo_id)

    adding = await run_code_lift(session)
    assert adding.rungs_restored == 0, (
        "the tick that adds a source must leave the rung to the next parse: "
        "the provenance it just wrote has not been re-read against the graph"
    )
    assert (await _fact_for(session, subject, rel_type, obj))["verification_status"] == (
        "candidate"
    )

    await _next_parse(session)
    restoring = await run_code_lift(session)
    assert restoring.rungs_restored == 1
    after = await _fact_for(session, subject, rel_type, obj)
    assert after["id"] == existing["id"]
    assert after["verification_status"] == "corroborated"


async def _verified_outcomes(session, fact_id) -> list[str]:
    rows = (await session.execute(
        text(
            "SELECT payload FROM events WHERE object_type = 'fact' "
            "AND event_type = 'verified' AND object_id = CAST(:id AS uuid) "
            "ORDER BY created_at, id"
        ),
        {"id": str(fact_id)},
    )).scalars().all()
    return [row.get("outcome") for row in rows]


async def _next_parse(session) -> None:
    """The deriver's next run that derived something: its state row is what
    moves the lift's code-graph stamp, so the next lift tick reconciles again."""
    await session.execute(
        text("""
            INSERT INTO config (key, value)
            VALUES ('code_deriver_state', jsonb_build_object(CAST(:k AS text), CAST(:k AS text)))
            ON CONFLICT (key) DO UPDATE SET value = config.value || EXCLUDED.value
        """),
        {"k": str(uuid4())},
    )


async def test_an_idle_deriver_tick_triggers_no_code_reconcile(session, monkeypatch):
    import app.services.fact_lift as fact_lift_module

    reconciles: list = []
    real = fact_lift_module.reconcile_code_sources

    async def counting(s):
        reconciles.append(1)
        return await real(s)

    monkeypatch.setattr(fact_lift_module, "reconcile_code_sources", counting)
    await run_code_lift(session)
    reconciles.clear()

    # What a code_deriver tick that derived nothing leaves behind: its run row.
    await session.execute(text(
        "INSERT INTO job_runs (job_key, outcome, started_at, duration_seconds) "
        "VALUES ('code_deriver', 'ok', clock_timestamp(), 0)"
    ))
    await run_code_lift(session)
    assert reconciles == []

    await _next_parse(session)
    await run_code_lift(session)
    assert reconciles == [1]


async def _born_fact(session, *, name: str) -> str:
    repo_id = await _seed_repo(session, name=name, imports=["httpx"])
    await assert_repo_graph(session, repo_id)
    await run_code_lift(session)
    fact = await _fact_for(session, name.lower(), "DEPENDS_ON", "httpx")
    assert fact["verification_status"] == "corroborated"
    return fact["id"]


async def test_a_lapsed_dispute_gets_the_born_rung_back_on_the_next_parse(session):
    """Fix round 1's finding I-1, driven end to end.

    The veto beats the exception — correctly — so a contradicted born fact
    goes to ``disputed``. When the dispute lapses, the ladder's recovery
    re-enters the ordinary count, which one origin never meets, so the fact
    lands ``candidate``; and the exception branch only *holds* a rung, so
    before this fix no machine path put it back. A judge false positive that
    later lapsed therefore converted a permanent-evidence fact into a permanent
    under-label. The next parse restores it, because the parse is the
    verification and the repository still asserts the triple.
    """
    fact_id = await _born_fact(session, name="Lapse-Repo")

    disputed = await recompute_fact(session, fact_id, open_contradiction=True)
    await session.flush()
    assert disputed.target_status == "disputed"

    recovered = await recompute_fact(session, fact_id, open_contradiction=False)
    await session.flush()
    assert (recovered.target_status, recovered.outcome) == ("candidate", "recover"), (
        "the fact has to reach candidate for this test to be about the finding"
    )

    await _next_parse(session)
    outcome = await run_code_lift(session)

    assert outcome.rungs_restored == 1
    assert await _row(session, fact_id) == ("corroborated", None)
    # The restore is a re-grade, not a re-birth and not new evidence.
    assert outcome.facts_created == 0 and outcome.sources_added == 0
    assert await FactSourceRepository(session).count_distinct_origins(fact_id) == 1

    # And it settles there: the ladder's own branch holds what the parse
    # restored, so the next tick is not a second re-grade.
    held = await recompute_fact(session, fact_id)
    await session.flush()
    assert (held.target_status, held.outcome) == ("corroborated", "hold")
    assert (await run_code_lift(session)).rungs_restored == 0


async def test_the_restore_never_lifts_a_fact_out_of_a_standing_dispute(session):
    """The veto's precedence, at the one place the fix could have broken it.

    The restore is an UPDATE whose WHERE names the rung it writes over, so a
    ``disputed`` fact is not a row it can reach — not a check the caller
    performs and a later refactor can drop.
    """
    fact_id = await _born_fact(session, name="Veto-Repo")

    await recompute_fact(session, fact_id, open_contradiction=True)
    await session.flush()
    assert (await _row(session, fact_id))[0] == "disputed"

    outcome = await run_code_lift(session)

    assert outcome.rungs_restored == 0
    assert (await _row(session, fact_id))[0] == "disputed"

    # Directly at the repository, so the refusal is the statement's and not the
    # reconcile's decision about which rows to offer it.
    assert await KnowledgeTripleRepository(session).restore_born_corroborated(
        fact_id
    ) is False
    assert (await _row(session, fact_id))[0] == "disputed"


async def test_the_restore_journals_nothing_and_stays_invisible_to_the_gate(session):
    """G-C's promotion rate and false-promotion audit read ``verified`` rows.

    A born fact enters neither, because its birth is not a transition anything
    journals. The restore makes the same claim on the same evidence, so it must
    not journal either — otherwise two identical claims would sit on two sides
    of the gate's own measurement.
    """
    fact_id = await _born_fact(session, name="Silent-Repo")
    assert await _verified_outcomes(session, fact_id) == []

    await recompute_fact(session, fact_id, open_contradiction=True)
    await session.flush()
    await recompute_fact(session, fact_id, open_contradiction=False)
    await session.flush()
    during_dispute = await _verified_outcomes(session, fact_id)
    assert during_dispute == ["dispute", "recover"]

    await _next_parse(session)
    assert (await run_code_lift(session)).rungs_restored == 1

    assert await _verified_outcomes(session, fact_id) == during_dispute


async def test_two_code_origins_are_left_to_the_count(session):
    """The restore's scope is exactly where the count cannot reach.

    Two repositories asserting one triple is two origins, which the ladder's
    thresholds do have an opinion about, so this path declines it rather than
    pre-empting a promotion the count would have journalled. The consequence is
    stated rather than hidden: such a fact stays ``candidate`` after a lapsed
    dispute until its origins meet the bar. It under-claims, and it keeps the
    promotion rate's numerator the count's alone.
    """
    first = await _seed_repo(session, name="Pair-Repo", imports=["httpx"])
    await assert_repo_graph(session, first)
    await run_code_lift(session)
    second = await _seed_repo(session, name="Pair-Repo", imports=["httpx"])
    await assert_repo_graph(session, second)
    await run_code_lift(session)

    fact = await _fact_for(session, "pair-repo", "DEPENDS_ON", "httpx")
    assert await FactSourceRepository(session).count_distinct_origins(fact["id"]) == 2

    await recompute_fact(session, fact["id"], open_contradiction=True)
    await session.flush()
    recovered = await recompute_fact(session, fact["id"], open_contradiction=False)
    await session.flush()
    assert recovered.target_status == "candidate" and recovered.required_n > 2

    outcome = await run_code_lift(session)

    assert outcome.rungs_restored == 0
    assert (await _row(session, fact["id"]))[0] == "candidate"


async def test_the_restore_reads_the_stored_kinds_not_a_callers_word(session):
    """The narrowing this path inherits is the predicate over stored evidence
    (narrowing 3), not the caller's string (narrowing 1): a fact whose single
    origin is a memory is refused at the service door, whatever asked."""
    fact_id = await _born_fact(session, name="Kinds-Repo")
    await session.execute(
        text(
            "UPDATE fact_sources SET source_kind = 'memory' "
            "WHERE fact_id = CAST(:id AS uuid)"
        ),
        {"id": fact_id},
    )
    await session.execute(
        text(
            "UPDATE knowledge_triples SET verification_status = 'candidate' "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": fact_id},
    )
    await session.flush()

    assert await restore_born_rung(session, fact_id=fact_id) is False
    assert (await _row(session, fact_id))[0] == "candidate"


async def test_a_suspected_contradiction_does_not_withhold_the_born_rung(session):
    """T2.109 — the model arm may flag; it may not withhold.

    Doc 08 §4.2's amendment takes the model scan off the veto, and the consult
    above is a veto consult. If the scan's journalled verdict still refused a
    born rung, the arm would keep exercising veto-adjacent power through a side
    door — withholding a label rather than removing one, which is the same
    instrument aimed downward. It does not: the rung is restored, and the
    suspicion reaches the human through the review queue instead.
    """
    fact_id = await _born_fact(session, name="Suspect-Repo")

    rival_repo = await _seed_repo(session, name="Rival-Repo", imports=["httpx"])
    await assert_repo_graph(session, rival_repo)
    await run_code_lift(session)
    rival = await _fact_for(session, "rival-repo", "DEPENDS_ON", "httpx")
    witness = (
        await FactSourceRepository(session).origin_profile(rival["id"])
    ).attributable_origins[0].origin_key

    await recompute_fact(session, fact_id, open_contradiction=True)
    await session.flush()
    await recompute_fact(session, fact_id, open_contradiction=False)
    await session.flush()
    assert (await _row(session, fact_id))[0] == "candidate"

    await record_event(
        session,
        event_type=CONTRADICTION_SCANNED,
        object_type="fact",
        object_id=UUID(fact_id),
        project=CODE_FACT_PROJECT,
        payload={
            "contradicted": True,
            "counterpart_id": str(rival["id"]),
            "witness_origin": witness,
        },
    )
    await session.flush()
    assert await adjudicate_contradiction(session, fact_id) is False, (
        "the model arm is no longer a veto input"
    )

    await _next_parse(session)
    assert (await run_code_lift(session)).rungs_restored == 1
    assert (await _row(session, fact_id))[0] == "corroborated"

    decision = await recompute_fact(session, fact_id)
    await session.flush()
    assert decision.contradiction_suspected is True
    assert decision.target_status != "disputed"
    review_state = (await session.execute(
        text(
            "SELECT review_state FROM knowledge_triples "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {"id": fact_id},
    )).scalar_one()
    assert review_state == "open"


async def test_the_restore_never_reopens_a_closed_belief_window(session):
    """Fix round 2's finding N-2: the open-belief half of the rung's WHERE.

    ``OPEN_BELIEF_PREDICATE`` is what stops the restore writing a machine label
    back over a closed belief — the state a human's rejection leaves (that door
    reaches the same predicate through ``expired_at``) and the state doc 10 §6's
    withdrawal leaves through ``invalid_at``. Deleting the predicate left the
    whole lift and honesty suite green, because only the status half of that
    WHERE had a test that could fail. This drives the ``invalid_at`` half, on a
    row that stays live as retained history.
    """
    fact_id = await _born_fact(session, name="Rejected-Repo")

    await recompute_fact(session, fact_id, open_contradiction=True)
    await session.flush()
    recovered = await recompute_fact(session, fact_id, open_contradiction=False)
    await session.flush()
    assert recovered.target_status == "candidate", (
        "the fact has to reach candidate or the window is not what refuses it"
    )

    closed = await KnowledgeTripleRepository(session).close_window(
        fact_id, datetime.now(timezone.utc)
    )
    await session.flush()
    assert closed is not None and closed["invalid_at"] is not None
    assert closed["expired_at"] is None, "the row stays live; only the window shut"

    assert await restore_born_rung(session, fact_id=fact_id) is False
    assert (await _row(session, fact_id))[0] == "candidate"

    assert (await run_code_lift(session)).rungs_restored == 0
    assert (await _row(session, fact_id))[0] == "candidate"


async def test_the_memory_lift_still_births_candidates(session):
    """The exception must not have leaked into the path it sits beside."""
    memory_id = await _seed_memory(session, content="darkmem uses pgvector", origin_key="s9")
    await _assert_memory_relation(session, memory_id, "darkmem", "USES", "pgvector")

    outcome = await run_lift(session)
    assert outcome.facts_created == 1
    row = (await session.execute(
        text(
            "SELECT verification_status FROM knowledge_triples "
            "WHERE subject_name = 'darkmem'"
        )
    )).scalar_one()
    assert row == "candidate"


async def _assert_memory_relation(
    session, memory_id: str, subject: str, rel_type: str, obj: str
) -> None:
    ids = {}
    for name in (subject, obj):
        entity_id = str(uuid4())
        await session.execute(
            text(
                "INSERT INTO entities (id, name, entity_type, memory_ids) "
                "VALUES (CAST(:id AS uuid), :name, 'tool', "
                "ARRAY[CAST(:mid AS uuid)]) "
                "ON CONFLICT (name, entity_type) DO UPDATE SET "
                "memory_ids = array_append(entities.memory_ids, CAST(:mid AS uuid)) "
                "RETURNING id"
            ),
            {"id": entity_id, "name": name, "mid": memory_id},
        )
        ids[name] = (await session.execute(
            text("SELECT id FROM entities WHERE name = :name AND entity_type = 'tool'"),
            {"name": name},
        )).scalar_one()
    await session.execute(
        text(
            "INSERT INTO entity_relations (id, source_entity_id, target_entity_id, "
            "rel_type, memory_ids) VALUES (CAST(:id AS uuid), :src, :tgt, :rel, "
            "ARRAY[CAST(:mid AS uuid)])"
        ),
        {
            "id": str(uuid4()),
            "src": ids[subject],
            "tgt": ids[obj],
            "rel": rel_type,
            "mid": memory_id,
        },
    )
    await session.flush()


def _references(tree: ast.AST, method: str) -> bool:
    """Whether a scope names ``method`` on an object, in *any* position.

    Deliberately not a call check. ``x.open_born_corroborated(...)`` in ``Call``
    position was the first version of this scan and a review defeated it in one
    line: ``f = repo.open_born_corroborated`` then ``await f(...)`` is the same
    call reached through a name, and an attribute in ``Load`` context is
    invisible to a call-shaped rule. ``getattr(repo, "…")`` is the same evasion
    spelled dynamically, so the string form counts too.
    """
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr == method:
            return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "getattr"
            and len(node.args) >= 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value == method
        ):
            return True
    return False


# Each door onto the born rung, and the single function in `app/` allowed to
# reach it. The rung's own statement is `_write_born_rung`, which both of these
# share, so this pins the whole population that can put a fact on it.
_RUNG_DOORS = {
    "open_born_corroborated": "mint_born_corroborated",
    "restore_born_corroborated": "restore_born_rung",
}


@pytest.mark.parametrize("method,enclosing_name", sorted(_RUNG_DOORS.items()))
def test_the_rung_has_exactly_one_writer_under_app(method, enclosing_name):
    """The repository owns the only statement that writes the rung, and each
    door onto it has exactly one caller in one function. A scan rather than a
    convention: the exception is narrow only while that stays true."""
    callers = [
        path.relative_to(BACKEND).as_posix()
        for path in sorted((BACKEND / "app").rglob("*.py"))
        if _references(ast.parse(path.read_text()), method)
    ]
    assert callers == ["app/services/fact_lift.py"], callers

    lift = ast.parse((BACKEND / "app" / "services" / "fact_lift.py").read_text())
    enclosing = [
        node.name
        for node in ast.walk(lift)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and _references(node, method)
    ]
    assert enclosing == [enclosing_name], enclosing


@pytest.mark.parametrize(
    "shape",
    [
        "async def f(repo):\n    await repo.{method}(x)\n",
        "async def f(repo):\n    alias = repo.{method}\n    await alias(x)\n",
        "async def f(repo):\n    await getattr(repo, '{method}')(x)\n",
    ],
)
def test_the_caller_scan_sees_an_aliased_door(shape):
    """A guard that cannot fail is not a guard, and the aliased shape is the
    one the call-position version of this scan walked straight past."""
    for method in _RUNG_DOORS:
        assert _references(ast.parse(shape.format(method=method)), method)


# ── clause 3: withdrawal invalidates, never deletes ──────────────────────


async def test_a_dropped_dependency_invalidates_the_fact_it_solely_sourced(session):
    repo_id = await _seed_repo(session, name="Drop-Repo", imports=["httpx", "fastapi"])
    await assert_repo_graph(session, repo_id)
    await run_code_lift(session)
    before = await _fact_for(session, "drop-repo", "DEPENDS_ON", "fastapi")
    assert before["invalid_at"] is None

    await _reindex(session, repo_id, ["httpx"], commit="sha0001")
    outcome = await run_code_lift(session)

    after = await _fact_for(session, "drop-repo", "DEPENDS_ON", "fastapi")
    assert after is not None, "the row was deleted; withdrawal invalidates"
    assert after["id"] == before["id"]
    assert after["invalid_at"] is not None
    assert after["expired_at"] is None, "invalidate closes a window, it does not expire"
    assert await _sources(session, after["id"]) == []
    assert (outcome.sources_withdrawn, outcome.facts_invalidated) == (1, 1)

    survivor = await _fact_for(session, "drop-repo", "DEPENDS_ON", "httpx")
    assert survivor["invalid_at"] is None
    assert len(await _sources(session, survivor["id"])) == 1


async def test_a_fact_a_live_memory_still_asserts_survives_the_withdrawal(session):
    """The case a withdrawal test usually skips. The repo's evidence goes; the
    fact does not, because a memory still stands behind it."""
    repo_id = await _seed_repo(session, name="Shared-Repo", imports=["httpx"])
    await assert_repo_graph(session, repo_id)
    await run_code_lift(session)
    fact = await _fact_for(session, "shared-repo", "DEPENDS_ON", "httpx")

    memory_id = await _seed_memory(session, content="shared", origin_key="s2")
    await FactSourceRepository(session).add_source(
        fact_id=fact["id"],
        source_kind=MEMORY_SOURCE_KIND,
        source_ref=memory_source_ref(memory_id),
        origin_key="s2",
    )
    await session.flush()

    await _reindex(session, repo_id, ["fastapi"], commit="sha0002")
    outcome = await run_code_lift(session)

    after = await _fact_for(session, "shared-repo", "DEPENDS_ON", "httpx")
    assert after["invalid_at"] is None, "a fact another live source holds was closed"
    assert outcome.facts_invalidated == 0
    kinds = {row["source_kind"] for row in await _sources(session, after["id"])}
    assert kinds == {MEMORY_SOURCE_KIND}


async def test_a_fact_a_second_live_repo_still_asserts_survives(session):
    """The same guard on the code side of the same question."""
    first = await _seed_repo(session, name="Twin-Repo", imports=["httpx"])
    await assert_repo_graph(session, first)
    await run_code_lift(session)
    fact = await _fact_for(session, "twin-repo", "DEPENDS_ON", "httpx")

    # A second repository asserting the *same* triple: give it the same name,
    # which is what makes the derived subject entity — and so the triple — one.
    second = await _seed_repo(session, name="Twin-Repo", imports=["httpx"])
    await assert_repo_graph(session, second)
    await run_code_lift(session)
    assert len(await _sources(session, fact["id"])) == 2

    await _reindex(session, first, ["fastapi"], commit="sha0003")
    await run_code_lift(session)

    after = await _fact_for(session, "twin-repo", "DEPENDS_ON", "httpx")
    assert after["id"] == fact["id"], "the fact was closed and re-opened"
    assert after["invalid_at"] is None
    assert [row["origin_key"] for row in await _sources(session, after["id"])] == [second]


async def test_removing_the_repository_outright_invalidates_its_facts(session):
    """Nobody is left to call a by-repo sweep, so the reconcile is driven by
    the stored provenance instead. Without that the fact keeps serving on
    evidence that no longer exists, with no error and no symptom."""
    repo_id = await _seed_repo(session, name="Gone-Repo", imports=["httpx"])
    await assert_repo_graph(session, repo_id)
    await run_code_lift(session)
    fact = await _fact_for(session, "gone-repo", "DEPENDS_ON", "httpx")

    await session.execute(
        text("DELETE FROM repositories WHERE id = CAST(:rid AS uuid)"),
        {"rid": repo_id},
    )
    await session.flush()

    withdrawn, invalidated, restored = await reconcile_code_sources(session)

    after = await _fact_for(session, "gone-repo", "DEPENDS_ON", "httpx")
    assert after is not None and after["id"] == fact["id"]
    assert after["invalid_at"] is not None and after["expired_at"] is None
    assert withdrawn >= 1 and invalidated >= 1
    assert restored == 0, "a dead repository's rows are withdrawn, never restored"


async def test_re_adding_a_dependency_opens_a_new_window_not_the_closed_one(session):
    """The lifecycle invalidate-not-delete implies and nothing else states.

    A closed window is history and stays closed; a dependency that comes back
    is a new belief, so it gets a new open row. Resurrecting the old one by
    clearing ``invalid_at`` would erase the interval in which the repository
    genuinely did not depend on it — which is the one thing the belief axis
    exists to record.
    """
    repo_id = await _seed_repo(session, name="Return-Repo", imports=["httpx", "fastapi"])
    await assert_repo_graph(session, repo_id)
    await run_code_lift(session)
    closed = await _fact_for(session, "return-repo", "DEPENDS_ON", "fastapi")

    await _reindex(session, repo_id, ["httpx"], commit="sha0005")
    await run_code_lift(session)
    await _reindex(session, repo_id, ["httpx", "fastapi"], commit="sha0006")
    await run_code_lift(session)

    key = compute_triple_key(CODE_FACT_PROJECT, "return-repo", "DEPENDS_ON", "fastapi")
    rows = (await session.execute(
        text(
            "SELECT id, invalid_at, expired_at, verification_status "
            "FROM knowledge_triples WHERE triple_key = :key ORDER BY created_at, id"
        ),
        {"key": key},
    )).mappings().all()
    assert len(rows) == 2
    assert str(rows[0]["id"]) == closed["id"] and rows[0]["invalid_at"] is not None
    assert rows[1]["invalid_at"] is None
    assert rows[1]["verification_status"] == "corroborated"
    assert all(row["expired_at"] is None for row in rows), "nothing was deleted"


async def test_an_unchanged_reindex_withdraws_and_emits_nothing(session):
    """A provenance no-op must stay one: an emit here reads to the drain as
    real evidence movement and thrashes the badge on facts nothing touched."""
    repo_id = await _seed_repo(session, name="Noop-Repo", imports=["httpx"])
    await assert_repo_graph(session, repo_id)
    await run_code_lift(session)

    await _reindex(session, repo_id, ["httpx"], commit="sha0004")
    outcome = await run_code_lift(session)

    assert (
        outcome.facts_created,
        outcome.sources_added,
        outcome.sources_withdrawn,
        outcome.events_emitted,
    ) == (0, 0, 0, 0)


# ── the doors, driven with the gate closed ───────────────────────────────


@pytest.fixture
def doors(session, monkeypatch):
    @asynccontextmanager
    async def _factory():
        yield session

    monkeypatch.setattr(mcp_server, "async_session_factory", _factory)
    monkeypatch.setattr(mcp_server, "_pipeline", None)


async def _lifted_code_fact(session) -> str:
    repo_id = await _seed_repo(session, name="Door-Repo", imports=["httpx"])
    await assert_repo_graph(session, repo_id)
    await run_code_lift(session)
    fact = await _fact_for(session, "door-repo", "DEPENDS_ON", "httpx")
    assert fact["verification_status"] == "corroborated"
    return fact["id"]


async def test_the_rest_list_serves_a_born_fact_as_candidate(
    client, auth_headers, session
):
    """No fixture, deliberately. The scan cannot see a surface that copies a
    row wholesale, so the surface is asked what it serves."""
    fact_id = await _lifted_code_fact(session)

    body = (await client.get(
        f"{FACTS_ROUTE}?project={CODE_FACT_PROJECT}", headers=auth_headers
    )).json()
    item = next(row for row in body["items"] if row["id"] == fact_id)

    assert item["verification_status"] == "candidate"
    assert item["badge"] is None
    assert item["unverified"] is True
    assert "verification_unmeasured" in item["label_suppressed"]


async def test_the_rest_detail_serves_a_born_fact_as_candidate(
    client, auth_headers, session
):
    fact_id = await _lifted_code_fact(session)

    body = (await client.get(f"{FACTS_ROUTE}/{fact_id}", headers=auth_headers)).json()

    assert body["verification_status"] == "candidate"
    assert body["badge"] is None
    assert "verification_unmeasured" in body["label_suppressed"]
    # The provenance groups are the badge's audit and are served whatever the
    # gate says: withholding a *label* is not withholding the evidence.
    assert body["sources"][0]["sources"][0]["source_kind"] == CODE_SOURCE_KIND


async def test_the_mcp_door_serves_a_born_fact_as_candidate(session, doors):
    fact_id = await _lifted_code_fact(session)

    body = json.loads(await mcp_server.fact_get(fact_id=fact_id))

    assert body["verification_status"] == "candidate"
    assert body["badge"] is None
    assert "verification_unmeasured" in body["label_suppressed"]


async def test_a_born_fact_is_unreachable_by_filtering_for_corroborated(
    client, auth_headers, session
):
    """The oracle T2.95's fix round closed, met by the rows that made it worth
    closing. Membership of a filtered set is an answer: if the filter ran on
    the column, asking for the withheld rung would return exactly the rows
    whose label was withheld, and two requests would recover per fact the rung
    the label refuses to say."""
    fact_id = await _lifted_code_fact(session)

    promoted = (await client.get(
        f"{FACTS_ROUTE}?project={CODE_FACT_PROJECT}&verification_status=corroborated",
        headers=auth_headers,
    )).json()
    assert promoted["total"] == 0
    assert promoted["items"] == []

    suppressed = (await client.get(
        f"{FACTS_ROUTE}?project={CODE_FACT_PROJECT}&verification_status=candidate",
        headers=auth_headers,
    )).json()
    assert fact_id in {row["id"] for row in suppressed["items"]}


async def test_minting_the_record_lights_the_born_rung_with_no_code_change(
    client, auth_headers, session, cleared_promotion_record
):
    """The reversibility the M1 split rests on, met at this task's own rows."""
    fact_id = await _lifted_code_fact(session)

    body = (await client.get(f"{FACTS_ROUTE}/{fact_id}", headers=auth_headers)).json()

    assert body["verification_status"] == "corroborated"
    assert body["label_suppressed"] is None
    assert body["unverified"] is False
    assert body["badge"]["origin_count"] == 1
    assert body["badge"]["origin_kinds"] == [CODE_SOURCE_KIND]

    promoted = (await client.get(
        f"{FACTS_ROUTE}?project={CODE_FACT_PROJECT}&verification_status=corroborated",
        headers=auth_headers,
    )).json()
    assert fact_id in {row["id"] for row in promoted["items"]}


# ── the crossing: one direction, no join ─────────────────────────────────


def _code_strings(tree: ast.AST):
    """String constants that are code, not prose.

    Docstrings are excluded by node identity rather than by position, the
    discipline ``test_claim_serving_gates`` arrived at: a module docstring that
    *discusses* the crossing names both sides of it by necessity, and a scan
    that fired on prose would be loosened the first time it did.
    """
    docstrings = set()
    for node in ast.walk(tree):
        if not isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            continue
        body = getattr(node, "body", None)
        if (
            body
            and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)
        ):
            docstrings.add(id(body[0].value))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstrings
        ):
            yield node.lineno, node.value


CODE_TABLES = ("code_files", "code_edges", "code_graph_nodes", "code_symbols")
LAYER_ONE_TABLES = ("entity_relations", "entities", "knowledge_triples",
                    "fact_sources", "memories")


def test_no_statement_joins_the_code_graph_and_the_memory_graph():
    """Invariant: the bridge is an application-level crossing, not a join.

    ``repositories`` is deliberately not in either list — it is the registry
    both sides reference, and the baseline's own invariant-8 amendment already
    applies its liveness predicate inside ``PostgresGraphRepository``.
    """
    offenders = []
    for relpath in ("app/services/fact_lift.py", "app/services/code_deriver.py"):
        tree = ast.parse((BACKEND / relpath).read_text())
        for lineno, statement in _code_strings(tree):
            if "SELECT" not in statement.upper() and "INSERT" not in statement.upper():
                continue
            code_side = [t for t in CODE_TABLES if t in statement]
            memory_side = [t for t in LAYER_ONE_TABLES if t in statement]
            if code_side and memory_side:
                offenders.append(f"{relpath}:{lineno}: {code_side} + {memory_side}")
    assert not offenders, (
        "a statement names the code graph and the memory graph at once: "
        + "; ".join(offenders)
    )


def test_the_code_lift_is_inside_the_dream_job_family_scan():
    """Invariant 15 needs no new guard, and this says why rather than leaving a
    reader to check. ``run_code_lift`` lives in ``fact_lift``, which the
    umbrella imports, so ``test_dream_jobs``'s reachability scan already fails
    the build on any capture or retrieval path that reaches it. Splitting it
    into its own module would have put it outside that derivation."""
    from tests.test_dream_jobs import dream_job_implementation_modules

    assert "fact_lift" in dream_job_implementation_modules()
    umbrella = (BACKEND / "app" / "services" / "dream_jobs.py").read_text()
    assert "run_code_lift" in umbrella, "the code half is not wired to a Tier-C job"


async def test_the_witness_read_names_no_layer_one_table(session):
    """The other half of the same property, exercised rather than scanned: the
    code-side read runs to completion on a repository with no Layer-1 rows at
    all, which it could not if it joined one."""
    repo_id = await _seed_repo(session, name="Isolated-Repo", imports=["httpx"])
    commit_sha, witnesses = await repo_witnesses(session, repo_id)

    assert commit_sha == "c0ffee0"
    assert witnesses["httpx"].basis == IMPORT_BASIS
    assert witnesses["python"].basis == LANGUAGE_BASIS
    assert (await session.execute(
        text("SELECT COUNT(*) FROM entities")
    )).scalar_one() == 0
