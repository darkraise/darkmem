"""Distribution: the managed-block targets, the content policy, the curb.

Doc 13 §6.5 puts distribution's *configuration* in Settings and its
*observable* half in the event stream. This is the configuration half's read
and write surface, and it is deliberately small: three GETs' worth of state and
one switch.

**The curb is a single control that stops all injection, and it is enforced
server-side.** Doc 01's F10 promise is context before the first prompt; the
obligation is that a human can always stop it. A curb honoured only by the
client would be a setting that appears to work and does not — the client is the
thing being curbed. So the flag lives in a ``config`` row that the inject
selection **will read**, and this door is what writes it. Present tense would
be a claim, not a description: the inject writer is T3.10's and is held by G-D,
so today this row has exactly one reader — the GET below. The flag is inert and
correct, which is the repo's standing inert-implementation pattern; describing
it as enforced is the thing invariant 23 guards against.

**Single-door (REST only), and that is a stated exception rather than an
oversight.** Invariant 17's parity applies to surfaces an agent uses; this one
configures what agents are *told*, and exposing "stop telling agents things" to
an agent inverts the control. Recorded in the parity table with that reason.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import SessionDep
from app.models.config import Config
from app.services.inject_adapters import REFRESH_WATCH, get_registry
from app.services.inject_journal import record_inject_curbed

router = APIRouter(prefix="/api/v1/distribution", tags=["distribution"])

DISTRIBUTION_CONFIG_KEY = "distribution_policy"

# The curb is global, and the journal says so rather than naming a target it
# did not single out.
CURB_ALL_TARGETS = "*"

DEFAULT_POLICY = {
    # The token budget doc 15 §3.4 spends truth-first. Conservative: an
    # injected block competes with the human's own prompt for the model's
    # attention, and a budget nobody set should not dominate it.
    "token_budget": 2000,
    # The curb. False means push is live; True stops every target at once.
    "curbed": False,
    # Watch mode (T4.06, doc 15 §3.5): re-inject as the working context
    # shifts, rather than at session start only. Off, and defaulted off here
    # rather than only in the service, so an install that never saw this
    # surface is not watched either.
    "watch_enabled": False,
}


class DistributionPolicy(BaseModel):
    token_budget: int = Field(default=2000, ge=0, le=100_000)
    curbed: bool = False
    watch_enabled: bool = False


class DistributionTarget(BaseModel):
    tool: str
    context_file: str
    mcp_config: str
    refresh: str
    # Whether this target is *actually* watched, which `refresh` alone does not
    # answer: an adapter declaring `watch` while the install has watch off is
    # refused by `resolve_adapter`, so a screen reading the raw field would
    # report a cadence the writer would not serve. Computed here, beside the
    # policy read, so the tab and the door agree by construction.
    watched: bool = False


class RejectedTarget(BaseModel):
    tool: str
    reason: str


class DistributionState(BaseModel):
    targets: list[DistributionTarget]
    policy: DistributionPolicy
    # Configured tools the registry refused. Served rather than logged-only:
    # an operator editing `inject_adapters` watched their row vanish from the
    # screen with the reason on the server, which is the same silent drop
    # invariant 14 forbids of retrieval.
    rejected: list[RejectedTarget] = []


async def _policy(session: AsyncSession) -> DistributionPolicy:
    row = (await session.execute(
        select(Config).where(Config.key == DISTRIBUTION_CONFIG_KEY)
    )).scalar_one_or_none()
    stored = row.value if row is not None and isinstance(row.value, dict) else {}
    return DistributionPolicy(**{**DEFAULT_POLICY, **stored})


@router.get("", response_model=DistributionState)
async def get_distribution(
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    """Every target's block path, and the policy in force.

    The targets come from T3.11's registry rather than a list here, so the tab
    shows what the inject writer would actually use — a second list would be a
    screen that agrees with itself and not with the system.
    """
    adapters, rejected = await get_registry(session)
    policy = await _policy(session)
    return DistributionState(
        targets=[
            DistributionTarget(
                tool=adapter.tool,
                context_file=adapter.context_file,
                mcp_config=adapter.mcp_config,
                refresh=adapter.refresh,
                watched=policy.watch_enabled and adapter.refresh == REFRESH_WATCH,
            )
            for adapter in sorted(adapters.values(), key=lambda a: a.tool)
        ],
        policy=policy,
        rejected=[
            RejectedTarget(tool=tool, reason=reason)
            for tool, reason in sorted(rejected.items())
        ],
    )


@router.put("/policy", response_model=DistributionPolicy)
async def put_policy(
    body: DistributionPolicy,
    _user=Depends(require_auth),
    session: AsyncSession = SessionDep,
):
    """Write the policy. 200 with the effective value, not 204.

    The curb is the reason: a human turning push off needs to see the state
    that is now in force, and an empty response would leave the screen
    asserting what it hopes rather than what it was told.

    **Turning the curb on journals it** (doc 15 §7: "the curb … journals the
    curb as an ``inject_curbed`` ``events`` row"). Until T3.10 ships the block
    writer, a human flipping this flag is the only curb act the system can
    observe, so it is the only one there is to record — and an unrecorded one
    would leave doc 15 §7's own mermaid edge with no producer at all.

    One row, not one per target: the control is global ("every target stops at
    once"), and per-target rows would describe per-target curbs that do not
    exist. **Releasing the curb journals nothing**, deliberately —
    ``EVENT_TYPES`` is a closed vocabulary and there is no release event in it;
    adding one is taxonomy-first work in doc 04 §8.1, not a value invented at a
    call site. The asymmetry is stated rather than quietly closed.

    A failed journal does not fail the curb. Stopping push is the safety act
    and the one thing a human reaching for this control must get; the strict
    ``JournalWriteFailed`` contract belongs to the verification transitions
    whose metrics are SQL over that table.
    """
    row = (await session.execute(
        select(Config).where(Config.key == DISTRIBUTION_CONFIG_KEY)
    )).scalar_one_or_none()
    was_curbed = (await _policy(session)).curbed
    if row is None:
        session.add(Config(key=DISTRIBUTION_CONFIG_KEY, value=body.model_dump()))
    else:
        row.value = body.model_dump()
    if body.curbed and not was_curbed:
        await record_inject_curbed(
            session,
            tool=CURB_ALL_TARGETS,
            context_file=CURB_ALL_TARGETS,
            reason="push curbed by a human on the distribution surface",
        )
    await session.commit()
    return body
