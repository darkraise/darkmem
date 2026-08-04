"""Seed one real Layer-2 fact for the knowledge e2e (T2.90).

The Facts surface (``app/api/routes/facts.py``) is GET-only by design — facts
are *derived*, never posted, and adding a write door would put a second
producer on an axis whose single-producer property is what makes it
trustworthy. So a Playwright spec cannot create the fact it needs to look at
through any HTTP door, and until now the knowledge e2e could only exercise
the demo fixture (see ``frontend/tests/knowledge.spec.ts``'s own header).

This module is the seeding path instead, and it is deliberately **not** an
HTTP route: it lives under ``backend/scripts/e2e/``, which the production
Dockerfile never copies into the runtime image (see
``test_e2e_seed_unreachable.py``, which pins both that and the fact that
nothing under ``backend/app`` imports this package) — the seeding capability
does not exist in a deployed darkmem at all, by construction, not by a
runtime permission check on a route that does.

**What it inserts is what ``fact_lift`` would have produced, not a
hand-crafted fact row.** This never writes ``knowledge_triples`` directly. It
writes Layer-1 rows the same way Phase 5 of the real pipeline does — a
``memories`` row, an ``entities`` pair and one ``entity_relations`` row via
``PostgresGraphRepository``, the identical helper shape
``tests/test_fact_lift.py``'s own "Layer-1 bed" already uses to seed that
service's tests — and then calls ``app.services.fact_lift.run_lift`` for
real. The resulting fact and its ``fact_sources`` row are the real producer's
output over real input, so the e2e that reads them is proving the actual wire
shape ``fact_lift`` ships, not a fixture standing in for it.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.graph import PostgresGraphRepository
from app.services.fact_lift import fact_sentence, run_lift
from app.services.triple_key import compute_triple_key

DEFAULT_PROJECT = "t290-knowledge-e2e"
DEFAULT_ORIGIN_KEY = "t290-e2e-seed"
DEFAULT_SUBJECT = "kestrel-e2e-subject"
DEFAULT_SUBJECT_TYPE = "project"
DEFAULT_REL_TYPE = "USES"
DEFAULT_OBJECT = "marigold-e2e-object"
DEFAULT_OBJECT_TYPE = "tool"


@dataclass(frozen=True)
class SeededFact:
    """What the Playwright spec needs to find and verify the seeded fact.

    ``fact_text`` is ``fact_lift.fact_sentence``'s own output — the exact
    string ``FactDetailResponse.fact`` carries and the frontend renders
    unconditionally as ``fact.fact_text`` (see ``fact-detail.tsx``). Renaming
    that backend field without updating the frontend adapter makes this
    string stop appearing on the page — that is the wire-shape drift clause
    3 of T2.90 exists to catch.
    """

    fact_id: str
    project: str
    subject_name: str
    rel_type: str
    object_name: str
    fact_text: str


async def _seed_memory(session: AsyncSession, *, project: str, origin_key: str) -> str:
    memory_id = str(uuid4())
    await session.execute(
        text("""
            INSERT INTO memories (id, content, source, project, origin_key)
            VALUES (
                CAST(:id AS uuid), CAST(:content AS text), 'api',
                CAST(:project AS text), CAST(:origin_key AS text)
            )
        """),
        {
            "id": memory_id,
            "content": (
                "T2.90 e2e fixture: "
                f"{DEFAULT_SUBJECT} {DEFAULT_REL_TYPE.lower()} {DEFAULT_OBJECT}"
            ),
            "project": project,
            "origin_key": origin_key,
        },
    )
    return memory_id


async def seed_fact_fixture(
    session: AsyncSession,
    *,
    project: str = DEFAULT_PROJECT,
    subject_name: str = DEFAULT_SUBJECT,
    subject_type: str = DEFAULT_SUBJECT_TYPE,
    rel_type: str = DEFAULT_REL_TYPE,
    object_name: str = DEFAULT_OBJECT,
    object_type: str = DEFAULT_OBJECT_TYPE,
    origin_key: str = DEFAULT_ORIGIN_KEY,
) -> SeededFact:
    """Write one real Layer-1 assertion and lift it into a real Layer-2 fact.

    Commits at the end so a caller reading through a *different* connection
    (the disposable stack's own uvicorn process, in the intended use) sees
    the result immediately — Postgres is the shared point of truth, not this
    session's transaction.
    """
    memory_id = await _seed_memory(session, project=project, origin_key=origin_key)

    graph = PostgresGraphRepository(session)
    await graph.create_entity(subject_name, subject_type, {}, memory_id)
    await graph.create_entity(object_name, object_type, {}, memory_id)
    await graph.create_relationship(
        subject_name, object_name, rel_type, {}, 0.9, memory_id,
        source_type=subject_type, target_type=object_type,
    )

    outcome = await run_lift(session)
    if outcome.facts_created < 1:
        raise RuntimeError(
            "fact_lift did not create the seeded fact — either the relation "
            "failed to write or the salience bar rejected it "
            f"(outcome={outcome!r})"
        )

    triple_key = compute_triple_key(project, subject_name, rel_type, object_name)
    result = await session.execute(
        text("SELECT id FROM knowledge_triples WHERE triple_key = CAST(:key AS text)"),
        {"key": triple_key},
    )
    fact_id = result.scalar_one()

    await session.commit()

    return SeededFact(
        fact_id=str(fact_id),
        project=project,
        subject_name=subject_name,
        rel_type=rel_type,
        object_name=object_name,
        fact_text=fact_sentence(subject_name, rel_type, object_name),
    )
