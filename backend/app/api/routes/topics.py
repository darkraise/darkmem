"""The topics read surface and the pin-suggestion door (doc 09 §3, T2.39a).

Provides:
  - GET  /api/v1/knowledge/topics
  - GET  /api/v1/knowledge/topics/pin-suggestions
  - POST /api/v1/knowledge/topics/pin-suggestions/accept
  - POST /api/v1/knowledge/topics/pin-suggestions/dismiss
  - GET  /api/v1/knowledge/topics/{label}

T2.20 shipped `topic_browsing.py` and `pin_suggestions.py` — the browsing
reads, the diff, and the accept/dismiss persistence — with no caller
anywhere in `app/`. This module is the door onto that work and adds no new
semantics: every read here is one of `browse_topics` / `get_topic` /
`get_injectable_report`, and every write is `accept_pin_suggestion` /
`dismiss_pin_suggestion`. See those modules' docstrings for the design this
door does not re-litigate.

**Route order matters.** `/topics/pin-suggestions` and its `/accept` /
`/dismiss` children are registered before `/topics/{label}`, because a
catch-all path parameter registered first would swallow the literal
`pin-suggestions` segment.

**Pin-suggestion identity.** `compute_pin_suggestions` and accept/dismiss
key on the community's dominant entity's soft key (`subject_soft_key`, doc
09 §3.4) — never the community id, which is rewritten by every detection
run (`memory_communities` is delete-and-rewrite per project, doc 06 §7).
`PinDecisionRequest` therefore carries `subject_key`, never a community id,
and no route here takes one.

**No cross-run snapshot at this door.** `diff_topics` needs a pre-rewrite
snapshot to report anything beyond `new`; only the detection job holds one
mid-run (`snapshot_topics`'s own docstring). A browsing read has no such
snapshot to hand it, so `list_pin_suggestions` calls `diff_topics({},
current)` — exactly the seam `pin_suggestions.py`'s docstring names as the
caller shape a UI-driven read gets: every topic reads `new`, gating still
runs in full (pinned / dismissed / fact-floor / live-article checks), but
`grown` never surfaces from this door alone. Wiring a persisted cross-run
snapshot into the door is new mechanics this task's brief puts out of
scope; see the report's "known gaps" section.

**Read-only, no `journal_pin_suggestions` call.** That call is documented
as something "a scheduler should call ... exactly once after a detection
pass, not on every read" — a browsing GET calling it would journal a
duplicate `consolidated` row on every page view. Accept/dismiss already
journal through `accept_pin_suggestion` / `dismiss_pin_suggestion`
themselves, satisfying the journalling requirement without this door
adding a second writer.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.auth import require_auth
from app.database import get_session
from app.repositories import memory_communities as communities_repo
from app.repositories.pinned_subjects import get_subject_lists
from app.schemas.topics import (
    PinDecisionRequest,
    PinSuggestionItem,
    PinSuggestionsResponse,
    TopicDetailResponse,
    TopicDiffItem,
    TopicItem,
    TopicListResponse,
)
from app.services import pin_suggestions as pins
from app.services import topic_browsing as browsing

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


def _topic_item(project: str, view: browsing.TopicView) -> TopicItem:
    return TopicItem(
        project=project,
        label=view.label,
        dominant_entities=list(view.dominant_entities),
        impact_rating=view.impact_rating,
        member_count=view.member_count,
        report_status=view.report_status,
        report=view.report_string,
    )


@router.get("/topics", response_model=TopicListResponse)
async def list_topics(
    project: str = "default",
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    topics = await browsing.browse_topics(session, project)
    return TopicListResponse(items=[_topic_item(project, t) for t in topics])


@router.get("/topics/pin-suggestions", response_model=PinSuggestionsResponse)
async def list_pin_suggestions(
    project: str = "default",
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    current = await communities_repo.list_with_members(session, project)
    entries = pins.diff_topics({}, current)
    suggestions = await pins.compute_pin_suggestions(session, project, entries)
    pinned, dismissed = await get_subject_lists(session, project)
    return PinSuggestionsResponse(
        diff=[
            TopicDiffItem(
                project=project,
                label=entry.label,
                status=entry.status,
                dominant_name=entry.dominant_name,
                dominant_entity_type=entry.dominant_entity_type,
                member_count=entry.member_count,
                prior_member_count=entry.prior_member_count,
            )
            for entry in entries
        ],
        suggestions=[
            PinSuggestionItem(
                project=project,
                subject_key=s.subject_key,
                dominant_name=s.dominant_name,
                dominant_entity_type=s.dominant_entity_type,
                label=s.label,
                why=s.why,
                member_count=s.member_count,
                verified_fact_count=s.verified_fact_count,
            )
            for s in suggestions
        ],
        pinned_subject_keys=sorted(pinned),
        dismissed_subject_keys=sorted(dismissed),
    )


@router.post(
    "/topics/pin-suggestions/accept", status_code=status.HTTP_204_NO_CONTENT
)
async def accept_pin_suggestion(
    body: PinDecisionRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    await pins.accept_pin_suggestion(
        session, body.project, body.subject_key, label=body.label
    )
    await session.commit()


@router.post(
    "/topics/pin-suggestions/dismiss", status_code=status.HTTP_204_NO_CONTENT
)
async def dismiss_pin_suggestion(
    body: PinDecisionRequest,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    await pins.dismiss_pin_suggestion(
        session, body.project, body.subject_key, label=body.label
    )
    await session.commit()


@router.get("/topics/{label}", response_model=TopicDetailResponse)
async def get_topic(
    label: str,
    project: str = "default",
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    topic = await browsing.get_topic(session, project, label)
    if topic is None:
        raise HTTPException(status_code=404, detail="Topic not found")
    report = await browsing.get_injectable_report(session, project, label)
    return TopicDetailResponse(
        project=project,
        label=topic.label,
        dominant_entities=list(topic.dominant_entities),
        impact_rating=topic.impact_rating,
        member_count=topic.member_count,
        report_status=topic.report_status,
        report=report,
    )
