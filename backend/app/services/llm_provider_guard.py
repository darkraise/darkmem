"""Keep the qualified judge's identity off the provider form.

``LLMConfigUpdate`` deliberately omits the judge's purpose from its write side:
that purpose is dispatched by a live service whose qualification record binds
to a resolved model identity, and repointing that identity from a settings form
is a real capability whose write-time safety half was scoped out as later
ladder work. Two of the six identity fields — ``base_url`` and ``api_kind`` —
now live on a provider row, so the same refusal has to hold on the provider
door or the restriction is decorative. The read side already fails closed, so
the damage is not wrong verdicts: it is that a cleared gate silently evaporates
on an unrelated settings edit, and the record is expensive to re-mint.

``api_key`` is deliberately NOT frozen. It is absent from the judge's identity
fields ("rotating a credential is not a model swap"), so freezing it would
protect nothing while blocking a credential rotation that is owed. A guard that
freezes the whole row is a defect, not a stricter guard.

Exclusivity is a default with a reachable remedy, not an enforced invariant:
the deployment runbook's restore writes purpose rows by direct ``psql`` and
passes no API check, so the shared state can exist. When it does, the escape
runs the other way — repoint the *other* purposes off the provider, which stays
permitted — and a write that leaves an existing reference alone adds no new
sharing, so it is not refused either.

This module protects the single door rather than going around it: it names the
purpose only through ``app.services.config``, which owns the purpose
vocabulary, and it never imports the judge, dispatches the purpose or calls the
ungated probe. It reads which provider the purpose row points at in order to
refuse writes to it.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_config import LLMPurposeConfigRow
from app.services.config import VERIFICATION_PURPOSE

FROZEN_FIELDS = ("base_url", "api_kind")


async def verification_provider(session: AsyncSession) -> str | None:
    """Which provider the judge's purpose resolves through, if any."""
    return (
        await session.execute(
            select(LLMPurposeConfigRow.provider_name)
            .where(LLMPurposeConfigRow.purpose == VERIFICATION_PURPOSE)
        )
    ).scalar_one_or_none()


def assert_identity_fields_unchanged(
    provider_name: str,
    current,
    incoming: dict,
    verification_provider_name: str | None,
) -> None:
    if provider_name != verification_provider_name:
        return
    for field in FROZEN_FIELDS:
        if field in incoming and incoming[field] != getattr(current, field):
            raise HTTPException(
                status_code=409,
                detail=(
                    f"{field!r} is frozen on provider {provider_name!r}: it serves "
                    f"the {VERIFICATION_PURPOSE} purpose, and this field is part of "
                    "the judge's qualification identity. The API key may still be "
                    "rotated."
                ),
            )


def assert_not_verification_provider(
    provider_name: str,
    verification_provider_name: str | None,
    purpose: str,
    current_provider_name: str | None = None,
) -> None:
    if purpose == VERIFICATION_PURPOSE or provider_name != verification_provider_name:
        return
    if provider_name == current_provider_name:
        return
    raise HTTPException(
        status_code=409,
        detail=(
            f"provider {provider_name!r} serves the {VERIFICATION_PURPOSE} purpose "
            f"and is exclusive to it; point {purpose!r} at a different provider."
        ),
    )
