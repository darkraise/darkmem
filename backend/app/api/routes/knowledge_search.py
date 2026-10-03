"""The vault's composed read over REST — doc 12 §2's twin for ``knowledge_search``.

``POST /api/v1/knowledge/search`` (T2.80). The cross-layer *ranked* question was
the only ranked retrieval in the system reachable from one door: ``memory.search``
and ``code.search`` are both two-door, so a composed answer is a capability by
this repo's own precedent rather than an agent-shaped projection.

**This route owns no shaping and no ranking.** It resolves the three axes the
twin resolves — including ``fuse``, doc 07 §5's channel-topology choice
(T2.56) — calls ``LayerCompositionService.search`` and hands the result to
``knowledge_search_response`` — the serialiser T2.72 placed outside the tool for
exactly this. ``code_search`` and ``code_blast_radius`` shared a service and
still answered differently because each door reshaped the result itself, and a
door that reshapes is a door that can rank. ``fuse`` never reaches the
composition call: both of doc 07 §5's shapes present the identical order, so
the choice belongs to the serialiser alone.

**The three outcomes are three status codes, and the middle one is the point.**
200 with an empty result — ``rows: []`` fused, every section empty sectioned —
is a vault that holds nothing for this query; 503 is every channel down,
carrying the composition's own channel record; and a defect inside the
composition — the grouping fixpoint, a reranker returning the wrong window —
is neither, so it propagates as a 500. Collapsing the third into the second is
the failed-versus-empty conflation T2.66 removed from the memory surface, and
it is what serving ``RuntimeError`` as unavailability would reintroduce.

**Authenticated, while the twin is not** (invariant 20's trust posture, not a
gap). Every two-door read on this table already pairs an unauthenticated tool
with an authenticated route, so posture does not decide door count — but it does
mean the two doors can be pointed at different row sets by an operator, and the
ranking parity ``tests/test_knowledge_search.py`` asserts is a parity *within an
equal row set*.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import lease_llm
from app.api.auth import require_auth
from app.database import get_session
from app.schemas.envelope import ErrorDetail, ErrorEnvelope
from app.schemas.knowledge import (
    KnowledgeSearchRequest,
    KnowledgeSearchResponse,
    knowledge_search_response,
    knowledge_search_unavailable,
)
from app.services.layer_composition import (
    CompositionUnavailable,
    LayerCompositionService,
)

router = APIRouter(prefix="/api/v1/knowledge", tags=["knowledge"])


@router.post(
    "/search",
    response_model=KnowledgeSearchResponse,
    responses={503: {"model": ErrorEnvelope}},
)
async def search_knowledge(
    body: KnowledgeSearchRequest,
    request: Request,
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    # Whatever the app holds, including None, exactly as the twin passes
    # whatever the pipeline holds. A 503 here on a missing orchestrator would
    # answer a request the other door answers: the memory channel's semantic
    # arm is the only part that needs one, and its failure is a one-sided
    # outage the envelope already reports as partial.
    llm = getattr(request.app.state, "llm", None)
    with lease_llm(llm):
        service = LayerCompositionService(llm, session)
        try:
            result = await service.search(
                body.query, project=body.project, limit=body.limit,
            )
        except CompositionUnavailable as exc:
            # Answered here rather than through ``HTTPException`` because that
            # handler keeps a string message or a list of details and never both:
            # a dict ``detail`` is dropped to "Request failed", which would leave
            # this door naming neither the outage nor the channels behind it while
            # its twin names both. The body is the app's own error envelope —
            # ``error.code`` is 503's ``unavailable``, the same word the tool's
            # ``status`` carries — with the shared unavailability object under
            # ``details``, so the composition's channel record survives the wrap.
            unavailable = knowledge_search_unavailable(exc)
            return JSONResponse(
                status_code=503,
                content=ErrorEnvelope(
                    error=ErrorDetail(
                        code="unavailable",
                        message=unavailable.reason,
                        details=[unavailable.model_dump(mode="json")],
                    ),
                    detail=unavailable.reason,
                ).model_dump(),
            )
        return knowledge_search_response(result, fuse=body.fuse)
