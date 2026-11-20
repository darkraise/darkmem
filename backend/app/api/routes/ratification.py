"""Human ratification — the single door to `confirmed` (doc 08 §4.4, T2.05).

Provides:
  - POST /api/v1/knowledge/facts/{fact_id}/ratify

**Single-door on purpose, and the reason is the whole design.** `/mcp` is
unauthenticated on the LAN behind only the Host allowlist (invariant 20), and
`confirmed` is the one rung the machine can never reach on its own. A twin on
that door would let any LAN peer forge the human's imprimatur, which is exactly
what the under-claiming rule exists to prevent. Doc 12 §3 records this as one
of the reshape's two sanctioned asymmetries so no later contributor "completes
the symmetry"; `tests/test_door_parity.py` is what stops them.

**Not on `facts.py`.** That module documents itself as a read-only surface and
is right to — belief is written by fact lifting and the verification axis by
the ladder's applier. Ratification is neither, so it gets its own module rather
than making a read surface's stated contract false.

**Authenticated by the session, never by a key scope.** `require_auth` decodes
a login JWT and nothing else. An API key is a credential a program holds, and a
program holding confirmed-power is the forged ratification doc 18 §2 names in
its threat table; doc 18 §5 keeps key mint itself behind the same single door
for the same reason ("a credential mint is confirmed-grade power"). When the
`ApiKey` activation lands, this route must not grow a scope for it.
"""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import SessionDep
from app.repositories.knowledge_triples import HumanSourceRequired
from app.schemas.facts import FactRatifyRequest
from app.services import human_adjudication

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.post("/facts/{fact_id}/ratify", status_code=status.HTTP_204_NO_CONTENT)
async def ratify_fact(
    fact_id: UUID,
    body: FactRatifyRequest | None = None,
    user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    """Ratify a fact: write the human source row, then confirm it.

    204, the shape the review queue's reject already established for a human
    adjudication verb. An earlier draft echoed the ratified fact so the caller
    could show the human the claim their own act produced — the badge is
    recomputed from the new provenance, so it does change. It was withdrawn
    because a verb that serves memory-derived content becomes a *content
    surface*: it inherits the project-scoping question in
    ``content_surfaces.py``, and the G-B isolation probe drives every declared
    door of such a surface. Driving a mutating door inside a read-isolation
    probe would change the state its later drivers observe and cost the probe
    the determinism it asserts. One re-read is the cheaper half of that trade.
    """
    try:
        await human_adjudication.ratify_fact(
            session,
            fact_id,
            actor=user.sub,
            shown=body.shown if body else None,
            note=body.note if body else None,
        )
    except human_adjudication.FactNotFound:
        raise HTTPException(status_code=404, detail="Fact not found")
    except HumanSourceRequired:  # pragma: no cover - the service writes the row first
        raise HTTPException(status_code=409, detail="Fact has no human source")
    await session.commit()
