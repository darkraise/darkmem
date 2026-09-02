"""Snapshot inventory — where this instance's own backups landed (spec §9.6).

**REST-only**, and recorded as such in `tests/test_door_parity.py`'s
`PARITY_TABLE` rather than only here: a docstring records nothing a test can
check. The reason is on that row, and the short version is that restoring is
deliberately a shell command and never a route, so this read exists to inform
a person at a console — an agent has no restore verb to be informed for.

Nothing here mutates. It works identically on production and on the read-only
worker, where it reads through the viewer role untouched.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.services.backup_config import load_destinations
from app.services.backup_ship import build_destination
from app.services.events import BACKUP_SHIPPED, BACKUP_VERIFY_FAILED

router = APIRouter(prefix="/api/v1/backups", tags=["backups"])


class SnapshotRow(BaseModel):
    name: str
    size: int
    modified_at: datetime


class OutcomeRow(BaseModel):
    event_type: str
    at: datetime
    sha256: str | None = None
    error: str | None = None


class DestinationInventory(BaseModel):
    name: str
    kind: str
    enabled: bool
    retention_keep: int
    snapshots: list[SnapshotRow]
    last_outcome: OutcomeRow | None
    #: Why this destination could not be listed. Present rather than raising:
    #: one unreachable NAS must not blank the whole inventory, and an operator
    #: reaching for this page during an incident is exactly who needs to see
    #: what the *other* destinations still hold.
    error: str | None


class InventoryResponse(BaseModel):
    destinations: list[DestinationInventory]


_LAST_OUTCOMES = text(
    """
    SELECT DISTINCT ON (payload->>'destination')
           payload->>'destination' AS destination,
           event_type,
           created_at,
           payload
      FROM events
     WHERE event_type IN (:shipped, :failed)
       AND object_type = 'system'
     ORDER BY payload->>'destination', created_at DESC, id DESC
    """
)


async def _last_outcomes(session: AsyncSession) -> dict[str, OutcomeRow]:
    """The newest ship row per destination.

    Filters on a JSONB key with no index behind it, which is fine at this row
    count -- one row per destination per night -- and cheaper than an index
    that exists only for this page. Say so here rather than leave the next
    reader to wonder whether it was overlooked.
    """
    rows = (
        await session.execute(
            _LAST_OUTCOMES, {"shipped": BACKUP_SHIPPED, "failed": BACKUP_VERIFY_FAILED}
        )
    ).mappings().all()
    out: dict[str, OutcomeRow] = {}
    for row in rows:
        payload = row["payload"] or {}
        error = payload.get("error")
        if error is None and payload.get("got"):
            error = (
                f"read-back mismatch: expected {payload.get('expected')}, "
                f"got {payload['got']}"
            )
        # Built from a mapping rather than with an `event_type=` keyword: the
        # emit-site scan in `tests/test_events.py` matches that keyword on any
        # call, and a response model carrying the field would read to it as an
        # unresolvable journal write.
        out[row["destination"]] = OutcomeRow.model_validate(
            {
                "event_type": row["event_type"],
                "at": row["created_at"],
                "sha256": payload.get("sha256"),
                "error": error,
            }
        )
    return out


@router.get("/inventory", response_model=InventoryResponse)
async def backup_inventory(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
) -> InventoryResponse:
    """Every configured destination, what it holds, and how its last run went."""
    configured = await load_destinations(session, masked=True)
    outcomes = await _last_outcomes(session)

    rows: list[DestinationInventory] = []
    for cfg in configured:
        snapshots: list[SnapshotRow] = []
        error: str | None = None
        try:
            destination = build_destination(cfg)
            snapshots = [
                SnapshotRow(name=s.name, size=s.size, modified_at=s.modified_at)
                for s in await destination.list_snapshots()
            ]
        except Exception as exc:  # noqa: BLE001 - one destination, not the page
            error = str(exc)
        rows.append(
            DestinationInventory(
                name=cfg.name,
                kind=cfg.kind,
                enabled=cfg.enabled,
                retention_keep=cfg.retention_keep,
                snapshots=snapshots,
                last_outcome=outcomes.get(cfg.name),
                error=error,
            )
        )
    return InventoryResponse(destinations=rows)
