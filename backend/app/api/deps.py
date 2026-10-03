from contextlib import nullcontext

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.database import async_session_factory, get_session
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


async def get_memory_service(request: Request, session: AsyncSession = Depends(get_session)) -> MemoryService:
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
async def get_chat_service(request: Request, session: AsyncSession = Depends(get_session)) -> ChatService:
    llm = getattr(request.app.state, "llm", None)
    if not llm:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail="LLM service unavailable")
    graph_repo = PostgresGraphRepository(session)
    with lease_llm(llm):
        yield ChatService(session, llm, graph_repo)


async def get_analytics_service(request: Request, session: AsyncSession = Depends(get_session)) -> AnalyticsService:
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


async def get_graph_service(request: Request, session: AsyncSession = Depends(get_session)) -> GraphService:
    llm = getattr(request.app.state, "llm", None)
    vector_repo = PostgresVectorRepository(session)
    graph_repo = PostgresGraphRepository(session)
    with lease_llm(llm):
        yield GraphService(session, vector_repo, graph_repo, llm)


async def get_code_pipeline(request: Request, session: AsyncSession = Depends(get_session)) -> CodePipeline:
    llm = getattr(request.app.state, "llm", None)
    vector_repo = PostgresVectorRepository(session, "code_chunks")
    repo_manager = RepoManager(session)
    with lease_llm(llm):
        yield CodePipeline(session=session, llm=llm, vector_repo=vector_repo, repo_manager=repo_manager)


async def get_repo_manager(session: AsyncSession = Depends(get_session)) -> RepoManager:
    return RepoManager(session)


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    """The sessionmaker a detached background task opens its own session
    from — never the request-scoped ``session`` above, which closes when the
    request returns. A dependency (not a hardcoded import) so a test can
    substitute a factory bound to its own engine."""
    return async_session_factory


async def get_tag_repository(session: AsyncSession = Depends(get_session)) -> PostgresTagRepository:
    return PostgresTagRepository(session)


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
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "read-only instance: this needs an external service or writes "
                "a file, and a backup worker is for viewing and backup/restore only"
            ),
        )
