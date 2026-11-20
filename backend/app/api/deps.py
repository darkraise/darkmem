from contextlib import nullcontext

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.database import SessionDep, async_session_factory, get_session
from app.repositories.graph import PostgresGraphRepository
from app.repositories.relational import PostgresTagRepository
from app.repositories.vector import PostgresVectorRepository
from app.services.analytics import AnalyticsService
from app.services.chat import ChatService
from app.services.code_pipeline import CodePipeline
from app.services.graph import GraphService
from app.services.memory import MemoryService
from app.services.pipeline import ProcessingPipeline
from app.services.llm import lease_llm
from app.services.repo_manager import RepoManager


async def get_memory_service(request: Request, session: AsyncSession = SessionDep) -> MemoryService:
    pipeline = getattr(request.app.state, "pipeline", None)
    with pipeline._pinned() if isinstance(pipeline, ProcessingPipeline) else nullcontext(pipeline) as pinned:
        yield MemoryService(session, pipeline=pinned)


# LLM-dependent dependency policy:
#   - get_chat_service raises 503 when app.state.llm is None — chat cannot do
#     anything useful without the orchestrator, so fail fast at the boundary.
#   - get_graph_service and get_code_pipeline intentionally pass llm=None
#     through. They back read-only endpoints (graph reads, wiki/symbol reads)
#     that work without the LLM; the LLM-requiring paths inside those services
#     guard llm themselves and surface their own 503. Do not add a blanket
#     503 here without auditing every read path those services serve.
def _chat_llm(request: Request):
    llm = getattr(request.app.state, "llm", None)
    if not llm:
        raise HTTPException(status_code=503, detail="LLM service unavailable")
    return llm


async def get_chat_service(request: Request, session: AsyncSession = SessionDep) -> ChatService:
    llm = _chat_llm(request)
    with lease_llm(llm):
        yield ChatService(session, llm, PostgresGraphRepository(session))


async def get_analytics_service(request: Request, session: AsyncSession = SessionDep) -> AnalyticsService:
    pipeline = getattr(request.app.state, "pipeline", None)
    graph_repo = PostgresGraphRepository(session)
    with pipeline._pinned() if isinstance(pipeline, ProcessingPipeline) else nullcontext(pipeline) as pinned:
        yield AnalyticsService(session, pinned, graph_repo)


# The streaming routes' twins: request-scoped, so the session and the LLM lease
# outlive the handler and last until the body has streamed or the client left.
# A route using one commits its own writes as it streams.
async def get_chat_service_for_stream(
    request: Request, session: AsyncSession = Depends(get_session, scope="request"),
) -> ChatService:
    llm = _chat_llm(request)
    with lease_llm(llm):
        yield ChatService(session, llm, PostgresGraphRepository(session))


async def get_analytics_service_for_stream(
    request: Request, session: AsyncSession = Depends(get_session, scope="request"),
) -> AnalyticsService:
    pipeline = getattr(request.app.state, "pipeline", None)
    graph_repo = PostgresGraphRepository(session)
    with pipeline._pinned() if isinstance(pipeline, ProcessingPipeline) else nullcontext(pipeline) as pinned:
        yield AnalyticsService(session, pinned, graph_repo)


async def get_llm(request: Request):
    """The orchestrator, or a 503 (TH1.16).

    Fail fast at the boundary rather than pass `None` through: grounded Q&A is
    a generative read and there is no useful degraded answer — a flow that
    retrieved blocks and then had no model would have to return something
    shaped like an answer with nothing in it, which is worse than saying the
    orchestrator is unavailable.
    """
    llm = getattr(request.app.state, "llm", None)
    if not llm:
        from fastapi import HTTPException  # noqa: PLC0415

        raise HTTPException(status_code=503, detail="LLM orchestrator is not configured")
    with lease_llm(llm):
        yield llm


async def get_graph_service(request: Request, session: AsyncSession = SessionDep) -> GraphService:
    llm = getattr(request.app.state, "llm", None)
    vector_repo = PostgresVectorRepository(session)
    graph_repo = PostgresGraphRepository(session)
    with lease_llm(llm):
        yield GraphService(session, vector_repo, graph_repo, llm)


async def get_code_pipeline(request: Request, session: AsyncSession = SessionDep) -> CodePipeline:
    llm = getattr(request.app.state, "llm", None)
    vector_repo = PostgresVectorRepository(session, "code_chunks")
    repo_manager = RepoManager(session)
    with lease_llm(llm):
        yield CodePipeline(session=session, llm=llm, vector_repo=vector_repo, repo_manager=repo_manager)


# Function scope for every provider holding the session or an LLM lease: its
# teardown runs before the response is sent (see `SessionDep`).
MemoryServiceDep = Depends(get_memory_service, scope="function")
ChatServiceDep = Depends(get_chat_service, scope="function")
AnalyticsServiceDep = Depends(get_analytics_service, scope="function")
LlmDep = Depends(get_llm, scope="function")
GraphServiceDep = Depends(get_graph_service, scope="function")
CodePipelineDep = Depends(get_code_pipeline, scope="function")


async def get_repo_manager(session: AsyncSession = SessionDep) -> RepoManager:
    return RepoManager(session)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """The sessionmaker a detached background task opens its own session
    from — never the request's ``session`` above, which closes when the
    handler returns. A dependency (not a hardcoded import) so a test can
    substitute a factory bound to its own engine."""
    return async_session_factory


async def get_tag_repository(session: AsyncSession = SessionDep) -> PostgresTagRepository:
    return PostgresTagRepository(session)


READ_ONLY_REASON = (
    "read-only instance: this needs an external service or writes "
    "a file, and a backup worker is for viewing and backup/restore only"
)


class ReadOnlyRefused(HTTPException):
    error_code = "read_only"

    def __init__(self) -> None:
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=READ_ONLY_REASON)


def refuse_when_read_only() -> None:
    """Refuse a door that needs an external service or writes a file (owner ruling 2026-09-03).

    A backup worker is for viewing and backup/restore only, so nothing on it
    may depend on a third machine being reachable -- a host whose job is
    surviving another machine's failure is the worst place to add an outbound
    dependency.

    Declared as a dependency rather than written at the top of each handler,
    and placed BEFORE the service dependencies that build an orchestrator, so
    the refusal lands before anything is constructed or called. That ordering
    is the point on every door this guards: each one dispatches an LLM, an
    embedder or a git fetch, or writes a file, *first* and writes a row
    *second*, so the SELECT-only viewer role would stop them only after the
    spend, the connection or the file had already happened.

    This is deliberately NOT the per-route allowlist review B1 rejected for
    *writes* -- those are caught generically by the SQLSTATE 42501 handler,
    which needs no list. This list exists because an external call is not a
    write the database sees, and neither is a file written to disk before any
    row: a page attachment upload lands its bytes first, so the viewer role
    would refuse it only after the file existed.
    """
    if settings.read_only:
        raise ReadOnlyRefused()
