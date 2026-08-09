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
selection reads, and this door is what writes it.

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
from app.database import get_session
from app.models.config import Config
from app.services.inject_adapters import get_adapters

router = APIRouter(prefix="/api/v1/distribution", tags=["distribution"])

DISTRIBUTION_CONFIG_KEY = "distribution_policy"

DEFAULT_POLICY = {
    # The token budget doc 15 §3.4 spends truth-first. Conservative: an
    # injected block competes with the human's own prompt for the model's
    # attention, and a budget nobody set should not dominate it.
    "token_budget": 2000,
    # The curb. False means push is live; True stops every target at once.
    "curbed": False,
}


class DistributionPolicy(BaseModel):
    token_budget: int = Field(default=2000, ge=0, le=100_000)
    curbed: bool = False


class DistributionTarget(BaseModel):
    tool: str
    context_file: str
    mcp_config: str
    refresh: str


class DistributionState(BaseModel):
    targets: list[DistributionTarget]
    policy: DistributionPolicy


async def _policy(session: AsyncSession) -> DistributionPolicy:
    row = (await session.execute(
        select(Config).where(Config.key == DISTRIBUTION_CONFIG_KEY)
    )).scalar_one_or_none()
    stored = row.value if row is not None and isinstance(row.value, dict) else {}
    return DistributionPolicy(**{**DEFAULT_POLICY, **stored})


@router.get("", response_model=DistributionState)
async def get_distribution(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Every target's block path, and the policy in force.

    The targets come from T3.11's registry rather than a list here, so the tab
    shows what the inject writer would actually use — a second list would be a
    screen that agrees with itself and not with the system.
    """
    adapters = await get_adapters(session)
    return DistributionState(
        targets=[
            DistributionTarget(
                tool=adapter.tool,
                context_file=adapter.context_file,
                mcp_config=adapter.mcp_config,
                refresh=adapter.refresh,
            )
            for adapter in sorted(adapters.values(), key=lambda a: a.tool)
        ],
        policy=await _policy(session),
    )


@router.put("/policy", response_model=DistributionPolicy)
async def put_policy(
    body: DistributionPolicy,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    """Write the policy. 200 with the effective value, not 204.

    The curb is the reason: a human turning push off needs to see the state
    that is now in force, and an empty response would leave the screen
    asserting what it hopes rather than what it was told.
    """
    row = (await session.execute(
        select(Config).where(Config.key == DISTRIBUTION_CONFIG_KEY)
    )).scalar_one_or_none()
    if row is None:
        session.add(Config(key=DISTRIBUTION_CONFIG_KEY, value=body.model_dump()))
    else:
        row.value = body.model_dump()
    await session.commit()
    return body
