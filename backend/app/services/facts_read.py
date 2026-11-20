"""The facts read surface — doc 13 §5.1's Facts tab, served (T2.36a).

Until this module the only read over ``knowledge_triples`` was the review
queue's own membership list; ``review_queue``'s docstring said so in as many
words. A browsing tab had nothing to call, so the tab was demo data and the
badge it was told to render "verbatim from the backend" had no backend to
render from.

**A door, not a ranking.** The list is arrival-ordered and unfiltered by
verification status: a candidate, a disputed and a corroborated fact are all
listed, each carrying its own label. Doc 08 §6's "never a gate on the read
path" is the rule, and this surface is the first place a gate could have been
introduced by accident — a default ``verification_status='corroborated'``
filter would have made the vault look empty and honest at the same time.

**Cold start is a real state, not a failure.** Doc 13 §5.1 fixes its meaning:
a fresh install has no corroborated facts for months, so an empty list is an
empty vault and the surface says nothing more than that. The one thing it must
not do is imply a fault, and the one thing a caller must not do is read
``total: 0`` as a degraded read.

**The caution overlay is carried, not derivable.** ``demotion_pending_since``
rides the wire item because doc 13 §5.3's ``under-sourced`` overlay renders on
this tab, and the only other way to reach it from here is elimination —
``corroborated`` plus ``review_state='open'`` — which is the derivation T2.62
rejected for the review queue and which stops being sound the moment a second
condition opens the queue.

The sources module is the badge's audit: ``fact_sources`` grouped by
``origin_key`` so a reader can count the groups and get the ``origin_count``
the claim asserts. The two numbers come from one grouping expression in
``fact_sources`` (see ``sources_by_origin``), so agreeing is structural rather
than tested-into-place — the test that pins them together is a regression
guard, not the mechanism.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.fact_sources import FactSourceRepository, OriginGroup
from app.repositories.knowledge_triples import KnowledgeTripleRepository
from app.services.claim_gates import gated_journal_payload, raw_statuses_for_served
from app.services.events import object_timeline
from app.services.fact_badge import badges_for_facts, row_labels
from app.services.layer_composition import dispute_label
from app.services.verified_evidence import latest_verified_evidence

FACT_ID_KIND = "fact"

# The detail page's ladder history, bounded the same as `GET /events/timeline`
# itself — a per-fact ladder is a handful of transitions, never a growing feed,
# so this is a safety cap rather than a page size a reader is meant to exhaust.
LADDER_LIMIT = 50


def applies_when_labels(applies_when: Mapping[str, Any] | None) -> list[dict[str, str]]:
    """``applies_when`` as the labels doc 13 §5.1 renders, axes and values
    trimmed and lowercased, empty ones dropped."""
    axes = {
        str(axis).strip().lower(): str(value).strip().lower()
        for axis, value in (applies_when or {}).items()
        if value is not None and str(value).strip()
    }
    return [{"axis": axis, "value": value} for axis, value in sorted(axes.items())]


def _belief_window(row: Mapping[str, Any]) -> dict[str, Any]:
    """The bi-temporal axis, kept as its own block.

    Separate from the verification fields because the two axes are
    independent (doc 08 §3) — a fact can be expired and confirmed — and a flat
    payload invites a renderer to treat ``expired_at`` as a verification
    outcome.
    """
    return {
        "valid_at": row["valid_at"],
        "invalid_at": row["invalid_at"],
        "expired_at": row["expired_at"],
    }


def _base_item(row: Mapping[str, Any], badge) -> dict[str, Any]:
    item = {
        "id": str(row["id"]),
        "id_kind": FACT_ID_KIND,
        "subject_name": row["subject_name"],
        "object_name": row["object_name"],
        "rel_type": row["rel_type"],
        "fact": row["fact"],
        "project": row["project"],
        "confidence": row["confidence"],
        "review_state": row["review_state"],
        "demotion_pending_since": row["demotion_pending_since"],
        "belief_window": _belief_window(row),
        "applies_when": row["applies_when"],
        "applies_when_labels": applies_when_labels(row["applies_when"]),
        "created_at": row["created_at"],
    }
    item.update(
        row_labels(
            id_kind=FACT_ID_KIND,
            verification_status=row["verification_status"],
            badge=badge,
        )
    )
    return item


def _source_group(group: OriginGroup) -> dict[str, Any]:
    return {
        "origin_key": group.origin_key,
        "unknown_origin": group.is_unknown,
        # Served rather than filtered: a stale origin is retained evidence that
        # stopped corroborating, and the flag is what lets a reader reconcile
        # the group list against the badge's origin count.
        "stale": group.is_stale,
        "source_kinds": list(group.source_kinds),
        "first_seen": group.first_seen,
        "last_seen": group.last_seen,
        "sources": [
            {
                "id": source["id"],
                "source_kind": source["source_kind"],
                "source_ref": source["source_ref"],
                "detail": source["detail"],
                "created_at": source["created_at"],
            }
            for source in group.sources
        ],
    }


async def list_facts(
    session: AsyncSession,
    *,
    project: str | None = None,
    subject_name: str | None = None,
    rel_type: str | None = None,
    object_name: str | None = None,
    served_status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[dict], int]:
    """A page of badged facts, filtered on the status a reader is *served*.

    The filter and the field answer the same question, so they read the same
    value. Keying the filter on the column instead inverts the claim gate: with
    the gate closed, asking for the promoted rung returns exactly the rows
    whose label was withheld and asking for the suppressed rung returns none of
    them, which recovers per fact the rung the label refuses to say. The label
    would still never appear in a response body, and the reader would still
    have it.
    """
    repo = KnowledgeTripleRepository(session)
    rows, total = await repo.list_live(
        project=project,
        subject_name=subject_name,
        rel_type=rel_type,
        object_name=object_name,
        verification_statuses=(
            None
            if served_status is None
            else raw_statuses_for_served(served_status, id_kind=FACT_ID_KIND)
        ),
        limit=limit,
        offset=offset,
    )
    badges = await badges_for_facts(session, rows)
    return [_base_item(row, badges[str(row["id"])]) for row in rows], total


async def get_fact(session: AsyncSession, fact_id: UUID | str) -> dict | None:
    repo = KnowledgeTripleRepository(session)
    row = await repo.get(fact_id)
    if row is None:
        return None
    fid = str(row["id"])
    evidence = await latest_verified_evidence(session, [fid])
    badges = await badges_for_facts(session, [row], evidence=evidence)
    item = _base_item(row, badges[fid])

    groups = await FactSourceRepository(session).sources_by_origin(row["id"])
    item["sources"] = [_source_group(group) for group in groups]
    item["triple_key"] = row["triple_key"]
    item["learned_in"] = row["learned_in"]
    item["source_file"] = row["source_file"]
    item["reference_time"] = row["reference_time"]

    item["dispute"] = dispute_label(row, evidence.get(fid))

    # `newest_first=True`: a fact's ladder is read to understand how it got
    # to its present state, so a truncated ladder must drop from the old end,
    # not the new one — the newest transitions are exactly the ones that
    # explain the badge the page displays. Reversed back to oldest-to-newest
    # for chronological rendering; `total` rides the wire separately so a
    # capped ladder is never presented as the complete history (invariant 14).
    ladder_items, ladder_total = await object_timeline(
        session,
        object_type=FACT_ID_KIND,
        object_id=UUID(fid),
        limit=LADDER_LIMIT,
        newest_first=True,
    )
    # The ladder is journal rows embedded in a claim surface, so it is served
    # through the gate rather than verbatim: this body states the fact's
    # status, and a rung suppressed two keys above may not reappear here.
    item["ladder"] = gated_journal_payload(
        list(reversed(ladder_items)), id_kind=FACT_ID_KIND
    )
    item["ladder_total"] = ladder_total
    return item
