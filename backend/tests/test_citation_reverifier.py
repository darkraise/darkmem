"""Doc 10 §6's citation re-verifier, and the code-fact lifecycle around it.

Three clauses carry T2.48, and each has a shape that passes while proving
nothing:

* **A changed symbol downgrades rather than expiring.** A test that asserts only
  the demotion passes on an implementation that *also* expires the fact, so
  every downgrade assertion below checks ``expired_at`` and ``invalid_at`` are
  still NULL and the provenance row still exists. And the downgrade is driven
  through the registered job's own runner, not through the module function, so
  the wiring is part of what is asserted.
* **Sole-source removal invalidates without deleting.** The negative half is the
  whole point: a fact a live memory still sources must *not* be invalidated when
  its code source goes. Asserted here even though T2.28 already built this half
  (see the module note below), because nothing else pins the asymmetry against a
  future edit to either producer.
* **Re-verification is idempotent per repo run.** Both directions. Two ticks
  produce one marking, one journal row and one enqueue — *and* a run whose file
  set moved but whose citations all still resolve emits nothing at all. Only the
  second direction can tell a correct no-op from a job that does nothing.

**The marker only means something because it changes an arithmetic.**
``test_a_stale_citation_stops_corroborating`` is the load-bearing one: without
``LIVE_SOURCE_PREDICATE`` in ``repositories/fact_sources.py`` a stale row still
counts as an origin, ``parse_is_the_verification`` still holds the born rung,
and every downgrade test here would pass for the wrong reason on a re-verifier
that wrote a decorative flag.

**What T2.48's brief expected to be unbuilt and was not.** The brief reads
``fact_provenance``'s memory-kind restriction as meaning the code-side
withdrawal is unbuilt. It is not: T2.28 landed ``reconcile_code_sources`` /
``_withdraw_code_sources`` in the lift, which withdraws a code source the graph
no longer supports and closes the window (``invalid_at``, never ``expired_at``)
of whatever that orphans. It is a separate sequence from ``_withdraw`` on
purpose and correctly so — the memory half *expires* a fact whose last source
vanished, the code half *closes its belief window*, because a repository that
stopped importing a package did not stop having imported it. Two verbs, two
sequences. The clause-2 tests below therefore exercise the existing producer
rather than duplicating it.
"""

from __future__ import annotations

import ast
import json
import re
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from sqlalchemy import text

from app.main import app as fastapi_app
from app.repositories.fact_sources import (
    CODE_SOURCE_KIND,
    FactSourceRepository,
    STALE_DETAIL_KEY,
)
from app.services import citation_reverify as reverify_mod
from app.services.citation_reverify import (
    CITATION_REVERIFY_CONFIG_SCHEMA,
    CITATION_REVERIFY_JOB_KEY,
    REVERIFIED_AT_SHA_KEY,
    STALE_AT_SHA_KEY,
    reverify_citations,
)
from app.services.code_deriver import assert_repo_graph
from app.services.events import CITATION_STALE, EVENT_TYPES
from app.services.fact_lift import (
    CODE_FACT_PROJECT,
    run_code_lift,
)
from app.services.fact_provenance import memory_source_ref
from app.services.job_runners import make_citation_reverify_runner
from app.services.triple_key import compute_triple_key
from app.services.verification_recompute import run_recompute

BACKEND = Path(__file__).resolve().parents[1]

BORN_SHA = "c0ffee0"
NEW_SHA = "deadbee"

REPO_FILES = [
    ("backend/app/services/store.py", "python"),
    ("frontend/src/Panel.tsx", "typescript"),
]
PY_FILE = REPO_FILES[0][0]

# The fast arm refuses to read an event newer than `now - 5s` (the commit-skew
# margin), and inside the test fixture's single long transaction `created_at`
# is the transaction's start time. Anchoring the tick 30s into the future is
# how `test_verification_recompute.py` makes a just-written event drainable;
# spelled the same way here for the same reason.
_SAFE_MARGIN_BUFFER = timedelta(seconds=30)


def _safe_now() -> datetime:
    return datetime.now(timezone.utc) + _SAFE_MARGIN_BUFFER


# ───────────────────────────── fixtures ─────────────────────────────


async def _seed_repo(
    session,
    *,
    name: str,
    imports: list[str] | None = None,
    commit: str = BORN_SHA,
) -> str:
    """A repository with two indexed files and a set of external imports.

    The same shape ``test_deriver_lift`` seeds, because the citations under test
    have to be the ones the real producer mints — a hand-written
    ``fact_sources`` row would let this suite drift from the detail shape the
    lift actually writes.
    """
    repo_id = str(uuid4())
    await session.execute(
        text(
            "INSERT INTO repositories (id, name, auto_sync, status, "
            "last_indexed_commit) VALUES (CAST(:id AS uuid), :name, false, "
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
        await _add_node(session, repo_id, kind="file", key=file_path)
    await _set_imports(session, repo_id, imports if imports is not None else ["httpx"])
    await session.flush()
    return repo_id


async def _add_node(session, repo_id: str, *, kind: str, key: str) -> None:
    await session.execute(
        text(
            "INSERT INTO code_graph_nodes (repo_id, kind, key, label) "
            "VALUES (CAST(:rid AS uuid), :kind, :key, :key) "
            "ON CONFLICT DO NOTHING"
        ),
        {"rid": repo_id, "kind": kind, "key": key},
    )


async def _drop_node(session, repo_id: str, key: str) -> None:
    """What a re-index does to a symbol that no longer exists at the new HEAD.

    The Layer-1 assertion is deliberately left standing: the deriver has no
    production trigger yet (T2.96's lane), so a re-index rebuilds the code graph
    while ``entity_relations.repo_ids`` keeps whatever the last derivation
    wrote. That is exactly the state the re-verifier exists for — the claim
    survives, its recorded address does not.
    """
    await session.execute(
        text(
            "DELETE FROM code_graph_nodes WHERE repo_id = CAST(:rid AS uuid) "
            "AND key = :key"
        ),
        {"rid": repo_id, "key": key},
    )


async def _set_imports(session, repo_id: str, imports: list[str]) -> None:
    await session.execute(
        text(
            "DELETE FROM code_edges WHERE repo_id = CAST(:rid AS uuid) "
            "AND edge_type = 'imports'"
        ),
        {"rid": repo_id},
    )
    for source in imports:
        await _add_node(session, repo_id, kind="module", key=source)
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


async def _set_head(session, repo_id: str, sha: str) -> None:
    await session.execute(
        text(
            "UPDATE repositories SET last_indexed_commit = :sha "
            "WHERE id = CAST(:rid AS uuid)"
        ),
        {"rid": repo_id, "sha": sha},
    )
    await session.flush()


async def _fact_for(session, subject: str, rel_type: str, obj: str) -> dict:
    key = compute_triple_key(CODE_FACT_PROJECT, subject, rel_type, obj)
    rows = (await session.execute(
        text(
            "SELECT CAST(id AS text) AS id, verification_status, invalid_at, "
            "expired_at, demotion_pending_since, review_state "
            "FROM knowledge_triples WHERE triple_key = :key "
            "ORDER BY created_at, id"
        ),
        {"key": key},
    )).mappings().all()
    assert len(rows) == 1, f"expected exactly one row on {key}, found {len(rows)}"
    return dict(rows[0])


async def _sources(session, fact_id: str) -> list[dict]:
    rows = (await session.execute(
        text(
            "SELECT CAST(id AS text) AS id, source_kind, source_ref, detail "
            "FROM fact_sources WHERE fact_id = CAST(:fid AS uuid) "
            "ORDER BY source_kind, source_ref"
        ),
        {"fid": fact_id},
    )).mappings().all()
    return [dict(row) for row in rows]


async def _events(session, event_type: str, fact_id: str | None = None) -> list[dict]:
    sql = (
        "SELECT payload FROM events WHERE event_type = :et"
        + (" AND object_id = CAST(:oid AS uuid)" if fact_id else "")
        + " ORDER BY created_at, id"
    )
    params: dict = {"et": event_type}
    if fact_id:
        params["oid"] = fact_id
    rows = (await session.execute(text(sql), params)).mappings().all()
    return [dict(row)["payload"] for row in rows]


async def _run_job(session) -> None:
    """Drive the re-verifier the way production does: through the runner the
    registry holds, not through ``reverify_citations`` directly.

    A test that called the function would pass on a job wired to the wrong
    runner, to no runner, or to a runner that swallowed its own outcome.
    """
    @asynccontextmanager
    async def _factory():
        yield session

    await make_citation_reverify_runner(fastapi_app, _factory)()


async def _no_hysteresis(session) -> None:
    """Set the demotion grace to 0 for the tests that assert the rung moved.

    Zero is a shipped, documented value of ``verification_demote_grace_cycles``
    ("the conservative end of this knob"), and it is what lets a downgrade test
    assert the *rung* rather than T2.46's interim label. The label itself is
    asserted separately, under the shipped default, by
    ``test_the_downgrade_is_visible_on_the_first_cycle_under_the_shipped_grace``.
    """
    await session.execute(
        text(
            "INSERT INTO config (key, value) VALUES "
            "('verification_demote_grace_cycles', CAST(:v AS jsonb)) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ),
        {"v": json.dumps({"cycles": 0})},
    )
    await session.flush()


async def _seed_memory(session, *, content: str) -> str:
    memory_id = str(uuid4())
    await session.execute(
        text(
            "INSERT INTO memories (id, content, source, project, origin_key) "
            "VALUES (CAST(:id AS uuid), :content, 'api', :project, 'session:shared')"
        ),
        {"id": memory_id, "content": content, "project": CODE_FACT_PROJECT},
    )
    await session.flush()
    return memory_id


async def _lifted(session, *, name: str, imports: list[str] | None = None) -> str:
    repo_id = await _seed_repo(session, name=name, imports=imports)
    await assert_repo_graph(session, repo_id)
    await run_code_lift(session)
    return repo_id


# ────────── clause 1: a changed symbol downgrades, never expires ──────────


async def test_a_broken_citation_downgrades_the_badge_and_expires_nothing(session):
    """The clause, whole: the badge moved **and** the fact is still believed.

    Half of this assertion is the negative one. An implementation that marked
    the citation stale and then expired the fact it justified would satisfy
    "the badge moved" perfectly, and it is exactly what doc 10 §6 forbids —
    a deleted symbol may be a rename a human should confirm.
    """
    await _no_hysteresis(session)
    repo_id = await _lifted(session, name="Break-Repo")
    fact = await _fact_for(session, "break-repo", "DEPENDS_ON", "httpx")
    assert fact["verification_status"] == "corroborated"

    await _drop_node(session, repo_id, "httpx")
    await _set_head(session, repo_id, NEW_SHA)
    await _run_job(session)

    sources = await _sources(session, fact["id"])
    assert len(sources) == 1, "the citation must survive being marked stale"
    detail = sources[0]["detail"]
    assert detail[STALE_DETAIL_KEY] is True
    assert detail[STALE_AT_SHA_KEY] == NEW_SHA, "doc 10 §6: the sha it broke at"
    assert detail["commit_sha"] == BORN_SHA, "the birth sha is not overwritten"

    await run_recompute(session, now=_safe_now())

    after = await _fact_for(session, "break-repo", "DEPENDS_ON", "httpx")
    assert after["verification_status"] == "candidate", "the badge did not downgrade"
    assert after["expired_at"] is None, "a lost citation must never expire a fact"
    assert after["invalid_at"] is None, "a lost citation is not a belief withdrawal"
    assert len(await _sources(session, fact["id"])) == 1


async def test_the_downgrade_target_is_never_disputed(session):
    """A lost source is not a contradiction (doc 10 §6, doc 08 §4.2).

    ``disputed`` is reserved for a counterpart claim, and it is reachable only
    through the veto. Pinned because "downgrade" is a word that would read
    equally well as either target to someone implementing from the sentence.
    """
    await _no_hysteresis(session)
    repo_id = await _lifted(session, name="Target-Repo")
    fact = await _fact_for(session, "target-repo", "DEPENDS_ON", "httpx")

    await _drop_node(session, repo_id, "httpx")
    await _set_head(session, repo_id, NEW_SHA)
    await _run_job(session)
    await run_recompute(session, now=_safe_now())

    after = await _fact_for(session, "target-repo", "DEPENDS_ON", "httpx")
    assert after["verification_status"] == "candidate"
    assert after["verification_status"] != "disputed"
    assert fact["id"] == after["id"]


async def test_the_downgrade_is_visible_on_the_first_cycle_under_the_shipped_grace(
    session,
):
    """Invariant 14 under the default grace: the demotion is *held*, not hidden.

    With ``verification_demote_grace_cycles`` at its shipped 1, the rung does not
    move on the cycle that detects the loss. What must still happen is that the
    fact is labelled ``under-sourced`` and queued — otherwise a citation could
    break and nothing anywhere would show it for a whole cycle, which is the
    silent degradation the invariant forbids.
    """
    repo_id = await _lifted(session, name="Grace-Repo")
    await _drop_node(session, repo_id, "httpx")
    await _set_head(session, repo_id, NEW_SHA)
    await _run_job(session)
    await run_recompute(session, now=_safe_now())

    held = await _fact_for(session, "grace-repo", "DEPENDS_ON", "httpx")
    assert held["verification_status"] == "corroborated", "grace holds the rung"
    assert held["demotion_pending_since"] is not None, "the loss left no mark"
    assert held["review_state"] == "open", "the human was not asked to look"
    assert held["expired_at"] is None


async def test_the_outcome_journals_with_the_address_and_both_shas(session):
    """Doc 10 §6: "the re-verify outcome journals to ``events``"."""
    repo_id = await _lifted(session, name="Journal-Repo")
    fact = await _fact_for(session, "journal-repo", "DEPENDS_ON", "httpx")

    await _drop_node(session, repo_id, "httpx")
    await _set_head(session, repo_id, NEW_SHA)
    await _run_job(session)

    payloads = await _events(session, CITATION_STALE, fact["id"])
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["symbol_key"] == "httpx"
    assert payload["repo_id"] == repo_id
    assert payload["minted_at_sha"] == BORN_SHA
    assert payload["broken_at_sha"] == NEW_SHA
    # Write-time minimisation: a journal row outlives its subject, so the
    # address is copied and the claim's prose is not.
    assert "fact" not in payload and "content" not in payload


async def test_the_badge_moves_through_the_recompute_not_through_this_module(session):
    """``recompute_fact`` is the sole journaller of verification transitions.

    Two halves. The re-verifier's own tick must move no status — if it wrote one
    directly the journal would stop describing the vault — and the transition
    must then appear in the ``verified`` stream once the recompute runs.
    """
    await _no_hysteresis(session)
    repo_id = await _lifted(session, name="Sole-Journal-Repo")
    fact = await _fact_for(session, "sole-journal-repo", "DEPENDS_ON", "httpx")

    await _drop_node(session, repo_id, "httpx")
    await _set_head(session, repo_id, NEW_SHA)
    await _run_job(session)

    mid = await _fact_for(session, "sole-journal-repo", "DEPENDS_ON", "httpx")
    assert mid["verification_status"] == "corroborated", (
        "the re-verifier wrote a verification status of its own"
    )
    assert await _events(session, "verified", fact["id"]) == []

    await run_recompute(session, now=_safe_now())
    verdicts = await _events(session, "verified", fact["id"])
    assert verdicts, "the downgrade never reached the journal"
    assert verdicts[-1]["outcome"] == "demote"


# ───────────── the arithmetic that makes the marker mean something ─────────────


async def test_a_stale_citation_stops_corroborating(session):
    """The load-bearing one. A marker with no effect on the count is decoration.

    If ``LIVE_SOURCE_PREDICATE`` is removed from ``origin_profiles``, the stale
    row keeps its origin, ``parse_is_the_verification`` keeps holding the born
    rung, and every downgrade test in this file passes on a re-verifier that
    changed nothing observable.
    """
    repo_id = await _lifted(session, name="Count-Repo")
    fact = await _fact_for(session, "count-repo", "DEPENDS_ON", "httpx")
    sources = FactSourceRepository(session)

    before = await sources.origin_profile(fact["id"])
    assert before.origin_count == 1
    assert before.parse_is_the_verification is True

    await _drop_node(session, repo_id, "httpx")
    await _set_head(session, repo_id, NEW_SHA)
    await _run_job(session)

    after = await sources.origin_profile(fact["id"])
    assert after.origin_count == 0, "a stale citation still corroborates"
    assert after.source_kinds == ()
    assert after.parse_is_the_verification is False
    assert await sources.count_distinct_origins(fact["id"]) == 0


async def test_the_stale_origin_is_still_audited_just_not_counted(session):
    """The count and the audit have to stay reconcilable.

    ``sources_by_origin`` is what makes a badge's number checkable by hand, so
    dropping the stale row from it would make the demotion look like evidence
    that silently vanished. It stays, flagged, and the badge's number is the
    count of the groups that are not flagged.
    """
    repo_id = await _lifted(session, name="Audit-Repo")
    fact = await _fact_for(session, "audit-repo", "DEPENDS_ON", "httpx")

    await _drop_node(session, repo_id, "httpx")
    await _set_head(session, repo_id, NEW_SHA)
    await _run_job(session)

    groups = await FactSourceRepository(session).sources_by_origin(fact["id"])
    assert len(groups) == 1, "the broken citation vanished from the audit"
    assert groups[0].is_stale is True
    live = [group for group in groups if not group.is_stale]
    profile = await FactSourceRepository(session).origin_profile(fact["id"])
    assert len(live) == profile.origin_count


async def test_the_fact_detail_surface_serves_the_stale_flag(session):
    """Doc 13 renders the badge; a downgrade with no visible cause is the
    silent degradation invariant 14 forbids."""
    from app.services.facts_read import get_fact

    repo_id = await _lifted(session, name="Surface-Repo")
    fact = await _fact_for(session, "surface-repo", "DEPENDS_ON", "httpx")

    await _drop_node(session, repo_id, "httpx")
    await _set_head(session, repo_id, NEW_SHA)
    await _run_job(session)

    served = await get_fact(session, fact["id"])
    assert served is not None
    assert served["sources"][0]["stale"] is True
    assert served["sources"][0]["sources"][0]["detail"][STALE_DETAIL_KEY] is True


# ──────────── clause 3: idempotent per repo run, in both directions ────────────


async def test_two_ticks_over_one_run_mark_once_and_enqueue_once(session):
    repo_id = await _lifted(session, name="Twice-Repo")
    fact = await _fact_for(session, "twice-repo", "DEPENDS_ON", "httpx")
    before_enqueues = len(await _events(session, "sources_changed", fact["id"]))

    await _drop_node(session, repo_id, "httpx")
    await _set_head(session, repo_id, NEW_SHA)

    first = await reverify_citations(session)
    second = await reverify_citations(session)

    assert first.marked_stale == 1
    assert second.citations_scanned == 0, (
        "the second tick re-selected a citation the first already settled"
    )
    assert second.marked_stale == 0
    assert len(await _events(session, CITATION_STALE, fact["id"])) == 1
    assert (
        len(await _events(session, "sources_changed", fact["id"])) - before_enqueues
    ) == 1


async def test_a_run_whose_citations_all_resolve_emits_nothing_at_all(session):
    """The provenance no-op, and the direction a passing test most easily fakes.

    A job that did nothing would satisfy the idempotency clause above. This is
    what separates the two: HEAD moved, the citation was genuinely re-resolved
    (``confirmed``), and still no event and no verification change followed.
    """
    repo_id = await _lifted(session, name="Noop-Repo")
    fact = await _fact_for(session, "noop-repo", "DEPENDS_ON", "httpx")
    before_stale = len(await _events(session, CITATION_STALE, fact["id"]))
    before_enqueues = len(await _events(session, "sources_changed", fact["id"]))

    await _set_head(session, repo_id, NEW_SHA)
    outcome = await reverify_citations(session)

    assert outcome.citations_scanned > 0, "nothing was re-resolved; the no-op is vacuous"
    assert outcome.confirmed >= 1
    assert outcome.marked_stale == 0 and outcome.cleared == 0
    assert outcome.facts_enqueued == 0
    assert len(await _events(session, CITATION_STALE, fact["id"])) == before_stale
    assert (
        len(await _events(session, "sources_changed", fact["id"])) == before_enqueues
    )

    detail = (await _sources(session, fact["id"]))[0]["detail"]
    assert detail[REVERIFIED_AT_SHA_KEY] == NEW_SHA
    assert STALE_DETAIL_KEY not in detail

    await run_recompute(session, now=_safe_now())
    after = await _fact_for(session, "noop-repo", "DEPENDS_ON", "httpx")
    assert after["verification_status"] == "corroborated"
    assert after["demotion_pending_since"] is None


async def test_a_citation_minted_at_the_current_head_costs_nothing(session):
    """A freshly lifted citation was resolved against this very graph a moment
    ago, so the first tick after a lift must find nothing to do. Without the
    ``COALESCE`` onto ``commit_sha`` every new citation would be re-resolved
    once for no reason."""
    await _lifted(session, name="Fresh-Repo")
    assert (await reverify_citations(session)).citations_scanned == 0


async def test_a_restored_symbol_clears_the_marker_and_the_badge_recovers(session):
    """Only *expiry* is reserved for the human. A badge is evidence-driven in
    both directions, so a rename undone at a later HEAD un-stales the citation
    and the same recompute that demoted the fact promotes it back."""
    await _no_hysteresis(session)
    repo_id = await _lifted(session, name="Restore-Repo")
    fact = await _fact_for(session, "restore-repo", "DEPENDS_ON", "httpx")

    await _drop_node(session, repo_id, "httpx")
    await _set_head(session, repo_id, NEW_SHA)
    await _run_job(session)
    await run_recompute(session, now=_safe_now())
    assert (
        await _fact_for(session, "restore-repo", "DEPENDS_ON", "httpx")
    )["verification_status"] == "candidate"

    await _add_node(session, repo_id, kind="module", key="httpx")
    await _set_head(session, repo_id, "restored")
    outcome = await reverify_citations(session)
    assert outcome.cleared == 1
    assert outcome.facts_enqueued == 1

    detail = (await _sources(session, fact["id"]))[0]["detail"]
    assert STALE_DETAIL_KEY not in detail
    assert STALE_AT_SHA_KEY not in detail

    # The recompute alone leaves it a candidate, and that is the ladder being
    # honest rather than a gap: one origin is below every threshold, and the
    # born rung is *held* by `parse_is_the_verification`, never granted by it.
    # Restoring the rung is the lift's `restore_born_rung`, on the same
    # evidence it was granted on -- so recovery is the two Tier-C jobs
    # composing, and the stale marker is what suspends it in the meantime.
    await run_recompute(session, now=_safe_now() + timedelta(seconds=1))
    assert (
        await _fact_for(session, "restore-repo", "DEPENDS_ON", "httpx")
    )["verification_status"] == "candidate"

    assert (await run_code_lift(session)).rungs_restored == 1
    healed = await _fact_for(session, "restore-repo", "DEPENDS_ON", "httpx")
    assert healed["verification_status"] == "corroborated"
    assert healed["expired_at"] is None and healed["invalid_at"] is None


# ───────────────── the keyless input distribution, measured ─────────────────


async def test_a_keyless_citation_is_counted_and_never_marked_stale(session):
    """"Cannot be checked" is not "checked and broken".

    ``fact_lift`` logs a citation it could find no witness for, and doc 10 §6's
    detail shape keeps all four keys with ``symbol_key`` NULL. Marking such a
    row stale would demote a badge on the strength of missing bookkeeping, and
    silently skipping it would let the tick report success over evidence it
    never examined — so it is counted and reported instead.
    """
    repo_id = await _lifted(session, name="Keyless-Repo")
    fact = await _fact_for(session, "keyless-repo", "DEPENDS_ON", "httpx")
    await session.execute(
        text(
            "UPDATE fact_sources SET detail = CAST(:d AS jsonb) "
            "WHERE fact_id = CAST(:fid AS uuid)"
        ),
        {
            "fid": fact["id"],
            "d": json.dumps({
                "commit_sha": BORN_SHA, "basis": None,
                "file_path": None, "symbol_key": None,
            }),
        },
    )
    await _set_head(session, repo_id, NEW_SHA)

    outcome = await reverify_citations(session)
    assert outcome.keyless == 1
    assert outcome.marked_stale == 0
    assert outcome.facts_enqueued == 0

    detail = (await _sources(session, fact["id"]))[0]["detail"]
    assert STALE_DETAIL_KEY not in detail
    assert detail[REVERIFIED_AT_SHA_KEY] == NEW_SHA, (
        "an unverifiable row must stop re-entering every tick forever"
    )
    assert (await reverify_citations(session)).citations_scanned == 0


async def test_the_keyless_fraction_of_a_real_derivation_is_measured(session):
    """The input distribution, taken from the producer rather than assumed.

    T2.48's brief asks for the fraction of code citations carrying a resolvable
    key. Measured 2026-08-07 over the producer: **12 of 12** on this import set,
    and 8 of 8 on a deliberately awkward one (a scoped npm package, a Go module
    path, a dotted Java package, mixed casing). Both bases key reliably — an
    import cites the module key the edge carries, a language cites the file path
    — so the keyless population is a defensive path, not a fraction of live
    traffic. The floor is 0.9 rather than 1.0 because the witness lookup is a
    name match between two independently normalised strings, and a taxonomy
    change on either side is a plausible way for one to start missing.

    Two things a bare fraction would not establish are asserted with it: every
    key that *is* recorded resolves against the graph it was read from (an
    address, not a string), and the keyless share is counted rather than
    inferred.
    """
    repo_id = await _lifted(
        session,
        name="Census-Repo",
        imports=["httpx", "fastapi", "sqlalchemy", "pydantic", "redis"],
    )
    rows = (await session.execute(
        text(
            "SELECT detail FROM fact_sources WHERE source_kind = :kind "
            "AND source_ref = :ref"
        ),
        {"kind": CODE_SOURCE_KIND, "ref": repo_id},
    )).scalars().all()
    details = [row or {} for row in rows]
    assert details, "the derivation minted no citations to measure"

    keyed = [d for d in details if d.get("symbol_key")]
    resolvable = 0
    for detail in keyed:
        found = (await session.execute(
            text(
                "SELECT 1 FROM code_graph_nodes WHERE repo_id = CAST(:rid AS uuid) "
                "AND key = :key LIMIT 1"
            ),
            {"rid": repo_id, "key": detail["symbol_key"]},
        )).scalar_one_or_none()
        resolvable += int(found is not None)

    assert resolvable == len(keyed), (
        f"{len(keyed) - resolvable} recorded keys do not resolve against the "
        "graph they were read from; the address is a string, not an address"
    )
    assert len(keyed) / len(details) >= 0.9, (
        f"only {len(keyed)} of {len(details)} citations carry a key; the "
        "re-verifier can check nothing about the rest"
    )


# ──────── clause 2: sole-source removal invalidates without deleting ────────


async def test_sole_source_removal_invalidates_without_deleting(session):
    """The dependency-removed transition, through T2.28's existing producer.

    ``invalid_at`` closes, the row survives, and the fact stays readable as
    history. ``expired_at`` stays NULL: the repository that stopped importing
    the package did not stop having imported it.
    """
    repo_id = await _lifted(session, name="Drop-Repo", imports=["httpx", "fastapi"])
    fact = await _fact_for(session, "drop-repo", "DEPENDS_ON", "fastapi")
    assert fact["invalid_at"] is None

    await _set_imports(session, repo_id, ["httpx"])
    await assert_repo_graph(session, repo_id)
    await run_code_lift(session)

    after = await _fact_for(session, "drop-repo", "DEPENDS_ON", "fastapi")
    assert after["id"] == fact["id"], "the fact row was replaced, not retained"
    assert after["invalid_at"] is not None, "the belief window never closed"
    assert after["expired_at"] is None, "invalidate-not-delete became expire"
    assert await _sources(session, fact["id"]) == []


async def test_a_fact_a_memory_also_sources_is_not_invalidated(session):
    """The asymmetry that is the whole point of the clause.

    Sole-source removal closes a window. Non-sole removal must not: another
    live origin still asserts the claim, and closing anyway would retire a
    belief on the strength of one withdrawn witness.
    """
    repo_id = await _lifted(session, name="Shared-Repo", imports=["httpx", "fastapi"])
    fact = await _fact_for(session, "shared-repo", "DEPENDS_ON", "fastapi")

    memory_id = await _seed_memory(session, content="shared-repo uses fastapi")
    await FactSourceRepository(session).add_source(
        fact_id=fact["id"],
        source_kind="memory",
        source_ref=memory_source_ref(memory_id),
        origin_key="session:shared",
    )
    await session.flush()

    await _set_imports(session, repo_id, ["httpx"])
    await assert_repo_graph(session, repo_id)
    await run_code_lift(session)

    after = await _fact_for(session, "shared-repo", "DEPENDS_ON", "fastapi")
    assert after["invalid_at"] is None, (
        "a fact a live memory still sources was invalidated by a code "
        "withdrawal"
    )
    assert after["expired_at"] is None
    remaining = await _sources(session, fact["id"])
    assert [row["source_kind"] for row in remaining] == ["memory"]


async def test_a_stale_citation_is_not_a_withdrawal(session):
    """The line between the two clauses, which nothing else pins.

    A dependency *removed* withdraws the row and closes the belief window. An
    address that stopped *resolving* does neither: the repository still asserts
    the claim, so the row stays, the window stays open, and only the badge
    moves. Conflating them is the single most likely way an implementation of
    this task retires a claim doc 10 §6 says only a human may retire.
    """
    await _no_hysteresis(session)
    repo_id = await _lifted(session, name="Line-Repo")
    fact = await _fact_for(session, "line-repo", "DEPENDS_ON", "httpx")

    await _drop_node(session, repo_id, "httpx")
    await _set_head(session, repo_id, NEW_SHA)
    await _run_job(session)
    await run_recompute(session, now=_safe_now())

    after = await _fact_for(session, "line-repo", "DEPENDS_ON", "httpx")
    assert after["verification_status"] == "candidate"
    assert after["invalid_at"] is None, "a stale address closed a belief window"
    assert after["expired_at"] is None
    assert len(await _sources(session, fact["id"])) == 1, (
        "the citation was withdrawn rather than labelled"
    )

    # And the lift's own reconcile, run afterwards, must not read the stale row
    # as a withdrawal either: the repository still asserts the triple.
    outcome = await run_code_lift(session)
    assert outcome.sources_withdrawn == 0
    assert outcome.facts_invalidated == 0
    assert len(await _sources(session, fact["id"])) == 1
    # Nor may it put the born rung back while the citation is broken: the
    # restore reads the same `OriginProfile` the ladder does, so a stale row
    # suspends the rung on both paths rather than on one.
    assert outcome.rungs_restored == 0
    assert (
        await _fact_for(session, "line-repo", "DEPENDS_ON", "httpx")
    )["verification_status"] == "candidate"


# ───────────────────────── structural guards ─────────────────────────


def _module_source() -> str:
    return (BACKEND / "app" / "services" / "citation_reverify.py").read_text()


def _sql_literals(source: str) -> list[tuple[int, str]]:
    """Every non-docstring string literal in the module, with its line.

    Two things this has to get right or the guards below read stronger than
    they are. **Docstrings are excluded by structural role, never by matching
    their text** — prose about the never-join rule necessarily names both
    sides, so a text-matched exemption would be loosened away by the very
    paragraph that explains the rule. And **an f-string is folded back into one
    string**: ``ast`` gives a ``JoinedStr`` whose constant parts are separate
    nodes, so a query interpolating a key name would be scanned in fragments
    and a statement naming both graphs across an interpolation would pass
    unseen. Every SQL statement in this module that carries an interpolation is
    exactly that shape.
    """
    tree = ast.parse(source)
    docstring_ids = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef,
                             ast.AsyncFunctionDef)):
            if ast.get_docstring(node, clean=False) is not None:
                docstring_ids.add(id(node.body[0].value))

    literals: list[tuple[int, str]] = []
    seen: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.JoinedStr):
            seen.update(
                id(part) for part in ast.walk(node) if isinstance(part, ast.Constant)
            )
            folded = "".join(
                part.value
                for part in node.values
                if isinstance(part, ast.Constant) and isinstance(part.value, str)
            )
            literals.append((node.lineno, folded))
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and id(node) not in docstring_ids
            and id(node) not in seen
        ):
            literals.append((node.lineno, node.value))
    return literals


CODE_SIDE_TABLES = ("code_graph_nodes", "code_edges", "code_files", "repositories")
VAULT_SIDE_TABLES = ("fact_sources", "knowledge_triples")


def test_no_statement_reads_the_code_graph_and_the_vault_together():
    """Doc 01 §3.6's never-join rule, made structural.

    The crossing is sanctioned precisely because it is application-level and
    one-direction: read the code graph, then write the vault. A single statement
    naming both sides is the join the rule forbids, and it is exactly what a
    later "simplification" of the two-statement shape would produce.
    """
    offenders = [
        f"line {lineno}: {literal[:80]!r}"
        for lineno, literal in _sql_literals(_module_source())
        if any(table in literal for table in CODE_SIDE_TABLES)
        and any(table in literal for table in VAULT_SIDE_TABLES)
    ]
    assert not offenders, (
        "a statement names both graphs: " + " | ".join(offenders)
    )


def test_the_never_join_guard_can_actually_see_an_interpolated_statement():
    """The guard above is only as good as its literal extraction.

    Both of this module's vault-side statements interpolate a key name, so a
    scanner that read ``JoinedStr`` fragments instead of the folded string
    would find no statement naming both graphs no matter what the module did.
    Pinned by construction rather than by trusting the helper.
    """
    folded = _sql_literals(
        'from x import y\nQ = f"SELECT * FROM fact_sources JOIN {y} '
        'ON code_graph_nodes"\n'
    )
    assert any(
        "fact_sources" in literal and "code_graph_nodes" in literal
        for _lineno, literal in folded
    )


FORBIDDEN_WRITES = (
    "expired_at",
    "invalid_at",
    "verification_status",
    "close_window",
    "expire",
)


def test_the_reverifier_writes_neither_axis_itself():
    """Never auto-expire, and never be a second writer of the ladder.

    Both halves are one scan because both are the same failure: this module
    reaching past the evidence it owns into a state some other module is the
    sole writer of. ``recompute_fact`` journals every verification transition,
    and only a human retires a claim.
    """
    source = _module_source()
    offenders = [
        f"{name!r} at line {lineno}"
        for lineno, literal in _sql_literals(source)
        for name in FORBIDDEN_WRITES
        if name in literal
    ]
    offenders += [
        f"{node.attr!r} at line {node.lineno}"
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Attribute) and node.attr in FORBIDDEN_WRITES
    ]
    assert not offenders, (
        "the re-verifier reaches the belief or verification axis directly: "
        + ", ".join(offenders)
    )


def test_the_reverifier_is_not_a_dream_job_family_member():
    """Contract 6 fixes that family at six; ``ppr_snapshot`` is the precedent
    for a Tier-C job deliberately outside it. A member added here would trip
    ``test_dream_jobs``'s own scan, so this states the intent at the source
    rather than leaving it to a failure elsewhere."""
    from app.services.dream_jobs import DREAM_JOB_KEYS

    assert CITATION_REVERIFY_JOB_KEY not in DREAM_JOB_KEYS
    assert len(DREAM_JOB_KEYS) == 6
    source = _module_source()
    assert "dream_jobs" not in source


def test_no_capture_or_retrieval_module_reaches_the_reverifier():
    """Invariant 15 binds by proximity: reconciliation stays off the hot path.

    The re-verifier is what a re-index *enqueues into*, never something a
    capture or a query may call to settle a badge sooner.
    """
    hot_path = [
        "pipeline.py", "extraction_clean.py", "memory_buffer.py", "wait_process.py",
        "hybrid_search.py", "layer_composition.py", "chat.py", "code_query.py",
        "facts_channel.py", "rank_fusion.py",
    ]
    offenders = []
    for name in hot_path:
        path = BACKEND / "app" / "services" / name
        if path.exists() and "citation_reverify" in path.read_text():
            offenders.append(name)
    for path in (BACKEND / "app" / "api").rglob("*.py"):
        if "citation_reverify" in path.read_text():
            offenders.append(str(path.relative_to(BACKEND)))
    assert not offenders, (
        "a hot-path module reaches the Tier-C re-verifier: " + ", ".join(offenders)
    )


def test_the_event_type_landed_in_the_vocabulary_before_its_emitter():
    assert CITATION_STALE in EVENT_TYPES
    assert CITATION_STALE == "citation_stale"
    # Imported by name rather than re-spelled: a second literal would be a
    # second chance to widen the vocabulary by accident, which is the whole
    # reason the value lives beside its writer.
    assert "CITATION_STALE" in _module_source()
    assert "citation_stale" not in [
        literal for _lineno, literal in _sql_literals(_module_source())
    ]


def test_the_job_is_registered_with_a_floor_and_a_schema():
    tree = ast.parse((BACKEND / "app" / "main.py").read_text())
    keywords = None
    for node in ast.walk(tree):
        if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                and node.func.id == "Job"):
            kw = {k.arg: k.value for k in node.keywords}
            key = kw.get("key")
            if isinstance(key, ast.Name) and key.id == "CITATION_REVERIFY_JOB_KEY":
                keywords = kw
                break
    assert keywords is not None, "the citation re-verifier is not wired at boot"
    # The registration passes named constants, so the AST holds `Name` nodes;
    # the values are read off the module they came from rather than duplicated
    # here, which is what keeps this a wiring assertion instead of a second
    # copy of the schedule.
    assert isinstance(keywords["min_interval_seconds"], ast.Name)
    assert reverify_mod.CITATION_REVERIFY_MIN_INTERVAL_SECONDS >= 60
    assert reverify_mod.CITATION_REVERIFY_MAX_RUN_SECONDS > 0
    assert "config_schema" in keywords
    assert "max_run_seconds" in keywords
    assert isinstance(keywords["runner"], ast.Call)


def test_the_job_key_and_schema_are_coherent():
    from app.services.job_registry import is_valid_cron

    assert CITATION_REVERIFY_JOB_KEY == "citation_reverify"
    assert {fd.key for fd in CITATION_REVERIFY_CONFIG_SCHEMA} == {"batch_size"}
    assert is_valid_cron(reverify_mod.CITATION_REVERIFY_CRON)


_NUMBER_WORDS = {
    word: value
    for value, word in enumerate(
        "zero one two three four five six seven eight nine ten eleven twelve "
        "thirteen fourteen fifteen sixteen seventeen eighteen nineteen "
        "twenty twenty-one twenty-two twenty-three twenty-four".split()
    )
}


def test_the_claude_md_job_count_matches_what_boots():
    """The baseline's count is what a reader trusts without opening ``main.py``,
    and it had already drifted once (T2.49 registered a job and left the
    sentence at sixteen) before this guard existed.

    Deliberately derived rather than pinned to a literal: a concurrent lane that
    registers a job and updates the sentence keeps this green, while one that
    registers a job and forgets the sentence does not. Pinning "18" here would
    make the guard fail on the *correct* change and pass on nothing extra.
    """
    from app.services.dream_jobs import DREAM_JOB_KEYS

    registered = sum(
        1
        for node in ast.walk(ast.parse((BACKEND / "app" / "main.py").read_text()))
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "Job"
    )
    baseline = (BACKEND.parent / "CLAUDE.md").read_text()

    total = re.search(r"\*\*([A-Za-z-]+)\*\* registered jobs", baseline)
    assert total is not None, "CLAUDE.md no longer states a registered-job count"
    assert _NUMBER_WORDS[total.group(1).lower()] == registered + len(DREAM_JOB_KEYS)

    live = re.search(r"The ([a-z-]+) live ones", baseline)
    assert live is not None
    assert _NUMBER_WORDS[live.group(1)] == registered
    assert f"`{CITATION_REVERIFY_JOB_KEY}`" in baseline
