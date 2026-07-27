"""Doc 12 §5's declared-context precedence chain: arg > header > project > none.

This module resolves **precedence** and nothing else. Turning the winning
raw mapping into the value matching consumes is
``rank_fusion.declared_context_from_wire``'s job (T1.34), and normalisation,
the axis vocabulary and the conflict rules all live there. Re-deriving any
of it here would give the system two answers to the same question.

Two properties the chain owes its terminal seam, both load-bearing:

``None`` is the only representation of undeclared. Not ``{}``, not
``{"env": null}``, and never the project name. ``DeclaredContext`` raises on
an empty axis set precisely so a vacuous declaration cannot exist: an
undeclared context that renders as a default is what T1.65 exists to catch.
"Declared and matched nothing" is a *different* fact — a real
``DeclaredContext`` with every row neutral — and the tier this module
returns alongside it is how a reader tells the two apart.

``project`` is never emitted. The chain reads it to find the tier-3 default,
but the isolation boundary and the context hint are different axes;
``DeclaredContext`` carries no ``project`` field and feeding the project
scope in as a context is the conflation T1.65 guards.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Mapping

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.project_registry import get_applies_when_default
from app.schemas.envelope import ContextEcho, DeclaredByTier
from app.services.rank_fusion import (
    ContextProvenance,
    DeclaredContext,
    declared_context_from_wire,
)

logger = logging.getLogger(__name__)

DECLARED_CONTEXT_HEADER = "x-darkmem-context"

# Never emitted into the declaration, however a caller spells it: `project`
# is the isolation boundary, not a context axis.
_NON_AXIS_KEYS = frozenset({"project"})


def _clean(raw: Any) -> dict[str, Any] | None:
    if not isinstance(raw, Mapping):
        return None
    cleaned = {
        str(key): value
        for key, value in raw.items()
        if str(key).strip().lower() not in _NON_AXIS_KEYS
    }
    return cleaned or None


def _from_header(headers: Mapping[str, str] | None) -> dict[str, Any] | None:
    """Parse the header's compact JSON object, or fall through.

    A malformed header is ignored and logged at debug, never raised: a
    request must not fail because an optional ranking hint was mistyped —
    the same rule ``resolve_client_source`` follows for attribution.
    """
    if headers is None:
        return None
    value = _header_lookup(headers, DECLARED_CONTEXT_HEADER)
    if not value or not value.strip():
        return None
    try:
        return _clean(json.loads(value))
    except (ValueError, TypeError):
        logger.debug("declared context header is not a JSON object", exc_info=True)
        return None


def _header_lookup(headers: Mapping[str, str], name: str) -> str:
    value = headers.get(name)
    if value is None:
        # A plain dict is case-sensitive where Starlette's Headers is not.
        lowered = {str(k).lower(): v for k, v in headers.items()}
        value = lowered.get(name)
    return value or ""


def resolve_declared_context(
    explicit: Mapping[str, Any] | None,
    *,
    headers: Mapping[str, str] | None = None,
    project_default: Mapping[str, Any] | None = None,
) -> tuple[DeclaredContext | None, DeclaredByTier | None]:
    """Run the precedence chain and hand the winner to T1.34's seam.

    A tier yielding nothing falls through to the next; a tier yielding a
    non-empty mapping wins outright and lower tiers are **not** merged into
    it, so a project default cannot quietly add an axis to a caller's own
    declaration.

    ``provenance`` is not a parameter. The declared caller context is
    trusted human input by definition (doc 12 §5); ``llm_guessed`` is a
    property of a *row's* ``applies_when``, which E2 writes. A caller able
    to self-declare ``llm_guessed`` would be handing itself a declaration
    that can never exclude — a behaviour switch with no owner.
    """
    tiers: tuple[tuple[DeclaredByTier, Mapping[str, Any] | None], ...] = (
        ("arg", _clean(explicit)),
        ("header", _from_header(headers)),
        ("project_default", _clean(project_default)),
    )
    for tier, raw in tiers:
        if not raw:
            continue
        declared = declared_context_from_wire(raw, ContextProvenance.HUMAN)
        if declared is not None:
            return declared, tier
    return None, None


async def resolve_declared_context_for_request(
    session: AsyncSession,
    *,
    explicit: Mapping[str, Any] | None,
    headers: Mapping[str, str] | None,
    project: str | None,
) -> tuple[DeclaredContext | None, DeclaredByTier | None]:
    """The request-path chain, with tier 3 read only when it can still win.

    Splitting the call this way keeps the precedence itself in
    ``resolve_declared_context`` — pass all three tiers at once and the
    ordering is identical — while sparing every declared request a query
    against a table that could not have changed the answer.
    """
    declared, tier = resolve_declared_context(explicit, headers=headers)
    if declared is not None:
        return declared, tier
    project_default = await get_applies_when_default(session, project)
    return resolve_declared_context(None, project_default=project_default)


def context_echo(
    declared: DeclaredContext | None, declared_by: DeclaredByTier | None,
) -> ContextEcho | None:
    """The envelope's rendering of what the chain decided.

    ``None`` for an undeclared context — the envelope's ``context`` key is
    then literally null, not an empty object and not a stand-in default.
    """
    if declared is None or declared_by is None:
        return None
    return ContextEcho(
        declared=dict(declared.axes),
        declared_by=declared_by,
        provenance=ContextProvenance.HUMAN.value,
    )
