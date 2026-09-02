import asyncio
import logging
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request as FastAPIRequest, status
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.auth import require_auth, require_scope
from app.api.deps import refuse_when_read_only, get_code_pipeline, get_repo_manager, get_session_factory
from app.database import get_session
from app.models.code import CodeFile, CodeSymbol, Repository
from app.schemas.code import (
    IndexDebtStatus, ReindexFilesRequest, ReindexFilesResponse, ReindexRequest,
    RepoCreate, RepoResponse, RepoUpdate,
)
from app.services import index_debt
from app.services.code_pipeline import CodePipeline
from app.services.events import record_event
from app.services.job_runners import forget_repo_due
from app.services.reindex_request import ReindexRefused, journal_reindex_outcome, prepare_reindex
from app.services.repo_manager import RepoManager
from app.services.usage_recorder import UsageSubject, subject_scope
from app.services.task_registry import TaskRegistry

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/repos", tags=["repos"])

# Doc 18 §5 groups repository control under the `admin` scope. Bound once at
# module scope, not inside the route, so a test can override this exact
# dependency object via `app.dependency_overrides` (a `require_scope(...)`
# call builds a fresh closure each time, so overriding one built inline in
# the decorator would silently miss the one actually wired to the route).
_require_repo_admin = require_scope("admin")


def _sync_loop_fields(repo: Repository) -> tuple:
    """The fields `make_repo_sync_runner` schedules and gates a repo on."""
    return (
        repo.fetch_enabled,
        repo.fetch_interval_seconds,
        repo.index_on_commit_enabled,
        repo.commit_poll_seconds,
        repo.index_uncommitted,
    )


def _to_response(
    repo: Repository,
    file_count: int = 0,
    symbol_count: int = 0,
    account_labels: dict[UUID, str] | None = None,
) -> RepoResponse:
    return RepoResponse(
        id=repo.id,
        name=repo.name,
        url=repo.url,
        local_path=repo.local_path,
        provider=repo.provider,
        default_branch=repo.default_branch,
        last_indexed_commit=repo.last_indexed_commit,
        last_indexed_at=repo.last_indexed_at,
        status=repo.status,
        status_message=repo.status_message,
        fetch_enabled=repo.fetch_enabled,
        fetch_interval_seconds=repo.fetch_interval_seconds,
        index_on_commit_enabled=repo.index_on_commit_enabled,
        commit_poll_seconds=repo.commit_poll_seconds,
        index_uncommitted=repo.index_uncommitted,
        git_account_id=repo.git_account_id,
        git_account_label=(account_labels or {}).get(repo.git_account_id)
        if repo.git_account_id
        else None,
        has_custom_token=bool(repo.auth_token_ref),
        index_debt=IndexDebtStatus(**index_debt.summarize(repo.index_debt)),
        file_count=file_count,
        symbol_count=symbol_count,
        created_at=repo.created_at,
        updated_at=repo.updated_at,
    )


@router.post("", response_model=RepoResponse, status_code=status.HTTP_201_CREATED)
async def create_repo(
    body: RepoCreate,
    _read_only=Depends(refuse_when_read_only),
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
    pipeline: CodePipeline = Depends(get_code_pipeline),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
):
    def _index_after_clone(repo_id: UUID) -> None:
        # `on_ready` runs synchronously from inside `_clone_in_background`'s
        # task, but claiming is async -- schedule a child task rather than
        # awaiting here, and never mock this closure's shape without also
        # mocking the claim.
        async def _claim_and_spawn() -> None:
            async with session_factory() as claim_session:
                claimed = await RepoManager(claim_session).claim_for_indexing(
                    repo_id, message="Queued for indexing...",
                )
            if not claimed:
                logger.error(
                    "Repository %s already indexing after clone; skipping initial index",
                    repo_id,
                )
                return
            try:
                _spawn_repo_index(
                    repo_id, pipeline, session_factory, kind="initial", pull=False,
                )
            except Exception as e:
                # The row exists and the Reindex button is one click away;
                # failing the create over a scheduling error would be worse.
                logger.error(
                    "Failed to schedule initial index for %s after clone: %s", repo_id, e,
                )

        # A bare `asyncio.create_task` here keeps no strong reference of its
        # own; CPython is free to garbage-collect it before it runs, which
        # would silently reproduce Finding 2 (a "ready" URL repo that is
        # never indexed) as an intermittent bug instead of the deterministic
        # one it used to be. `TaskRegistry` is what the clone task and every
        # `_spawn_repo_index` task on either side of this one already lean
        # on for exactly that -- register here too rather than inventing a
        # second convention.
        task = asyncio.create_task(_claim_and_spawn())
        TaskRegistry.register(repo_id, "initial-claim", task, "Queued for indexing...")

    try:
        repo = await manager.create(body, on_ready=_index_after_clone)
    except IntegrityError:
        raise HTTPException(status_code=409, detail=f"Repository '{body.name}' already exists")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # A URL repo is still cloning; `on_ready` (above) indexes it once the
    # clone lands. Only a local_path repo has a tree to read right now, so
    # only that branch claims and spawns immediately.
    if not body.url:
        claimed = await manager.claim_for_indexing(repo.id, message="Queued for indexing...")
        # claim_for_indexing's UPDATE has a `.notin_()` predicate, which
        # synchronize_session cannot "evaluate" in Python and falls back to
        # "fetch" for -- that path expires the matched ORM object outright
        # rather than patching its attributes in place. Every other caller
        # of this method returns a plain dict, so this route is the first
        # to serialize the same `repo` object afterward; without this
        # refresh, `_to_response` below hits an implicit lazy-load with no
        # greenlet to run it in and crashes.
        await manager.session.refresh(repo)
        if claimed:
            try:
                _spawn_repo_index(
                    repo.id, pipeline, session_factory, kind="initial", pull=False,
                )
            except Exception as e:
                logger.error("Failed to schedule initial index for %s: %s", repo.id, e)
        else:
            # Not reachable in practice -- nothing else has this id yet -- but
            # a lost claim must never spawn an unclaimed index.
            logger.error(
                "Repository %s already indexing at creation; skipping initial index", repo.id,
            )

    return _to_response(repo, account_labels=await manager.account_labels())


@router.get("", response_model=list[RepoResponse])
async def list_repos(
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
):
    entries = await manager.list_all()
    labels = await manager.account_labels()
    return [
        _to_response(e["repo"], e["file_count"], e["symbol_count"], labels)
        for e in entries
    ]


@router.get("/stats")
async def repo_stats(
    _user=Depends(require_auth),
    session: AsyncSession = Depends(get_session),
):
    total_repos = (await session.execute(select(func.count()).select_from(Repository))).scalar() or 0
    total_files = (await session.execute(select(func.count()).select_from(CodeFile))).scalar() or 0
    total_symbols = (await session.execute(select(func.count()).select_from(CodeSymbol))).scalar() or 0
    pending = (await session.execute(
        select(func.count()).select_from(CodeSymbol).where(CodeSymbol.enrichment_status == "pending")
    )).scalar() or 0
    completed = (await session.execute(
        select(func.count()).select_from(CodeSymbol).where(CodeSymbol.enrichment_status == "completed")
    )).scalar() or 0
    return {
        "total_repos": total_repos,
        "total_files": total_files,
        "total_symbols": total_symbols,
        "enrichment_pending": pending,
        "enrichment_completed": completed,
    }


@router.get("/{repo_id}", response_model=RepoResponse)
async def get_repo(
    repo_id: UUID,
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
):
    repo = await manager.get(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")
    return _to_response(repo, account_labels=await manager.account_labels())


@router.put("/{repo_id}", response_model=RepoResponse)
async def update_repo(
    repo_id: UUID,
    body: RepoUpdate,
    request: FastAPIRequest,
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
):
    # Snapshot whether either recurring lane was armed BEFORE the update so
    # we can detect whether this PUT flipped the polling gate. The repo_sync
    # background job filters by ``fetch_enabled`` / ``index_on_commit_enabled``;
    # a flip from neither armed to either armed should wake the job
    # immediately so the new repo joins the next iteration without waiting
    # for the global tick.
    existing = await manager.get(repo_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Repository not found")
    prev_armed = existing.fetch_enabled or existing.index_on_commit_enabled
    # Read as scalars, not as a reference to the row: `manager.update` mutates
    # this very instance, so comparing against `existing` afterwards compares
    # the new values with themselves.
    prev_schedule = _sync_loop_fields(existing)

    repo = await manager.update(repo_id, body)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    if (repo.fetch_enabled or repo.index_on_commit_enabled) and not prev_armed:
        wakeup = getattr(request.app.state, "repo_sync_wakeup", None)
        if wakeup is not None:
            wakeup.set()

    # Waking the loop accomplishes nothing on its own: the loop's per-repo
    # due-times are derived from exactly these fields, so a tick that arrives
    # before the previous interval lapses refuses the repo it was woken for.
    if _sync_loop_fields(repo) != prev_schedule:
        forget_repo_due(repo_id)

    return _to_response(repo, account_labels=await manager.account_labels())


@router.delete("/{repo_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_repo(
    repo_id: UUID,
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
):
    if not await manager.delete(repo_id):
        raise HTTPException(status_code=404, detail="Repository not found")
    # Nothing else ever removes a repo's due-times, so without this they
    # outlive the row until the process restarts.
    forget_repo_due(repo_id)


def _spawn_repo_index(
    repo_id: UUID,
    pipeline: CodePipeline,
    session_factory: async_sessionmaker[AsyncSession],
    *,
    kind: str,
    full: bool = False,
    enrich_symbols: bool = False,
    generate_wiki: bool = False,
    union_files: list[str] | None = None,
    pull: bool = True,
) -> asyncio.Task:
    """Spawn the one background indexing path both ``reindex_repo`` and
    ``repo_push_webhook`` dispatch through -- a tracked task on a fresh
    session, never a synchronous ``pipeline.run`` inline in either route.

    ``run_kwargs`` carries a flag only when it is not the default, so a
    caller that passes nothing but ``repo_id`` (the webhook) reaches
    ``CodePipeline.run`` with the identical bare ``(repo_id)`` shape
    polling's own call site uses (``job_runners.py``), not a look-alike call
    with explicit values. ``pull`` defaults True to match every existing
    caller (reindex, reindex-files, webhook, MCP ``code_reindex``); only the
    two initial-index arms (fresh local repo, post-clone) pass ``pull=False``
    -- an initial index has nothing of its own to fetch yet, and calling
    ``pull_repo`` here would ff-advance or reset the operator's own checkout
    on the very first index.

    The background pipeline mirrors whether the *injected* ``pipeline`` was
    given a vector repo at all: production's DI-provided pipeline always
    carries one, so this only ever matters to a test that overrides
    ``get_code_pipeline`` with ``vector_repo=None`` (the established pattern
    for a deterministic run with no live embedder) -- that override has to
    reach the background closure too, not just the request-scoped object,
    or a background run silently falls back to a real
    ``PostgresVectorRepository`` regardless of what the caller asked for.
    """
    collection_name = pipeline.vector_repo.collection_name if pipeline.vector_repo else None
    has_vector_repo = pipeline.vector_repo is not None
    llm = pipeline.llm

    async def _run_index():
        # Set inside the task: the request that spawned it has returned 202
        # and its scope is gone before the first symbol is enriched.
        with subject_scope(UsageSubject(
            "maintenance", f"{kind}:{repo_id}", None,
        )):
            try:
                async with session_factory() as session:
                    fresh_vector_repo = None
                    if has_vector_repo:
                        from app.repositories.vector import PostgresVectorRepository
                        fresh_vector_repo = PostgresVectorRepository(session, collection_name)
                    idx = CodePipeline(
                        session=session,
                        llm=llm,
                        vector_repo=fresh_vector_repo,
                        repo_manager=RepoManager(session),
                    )
                    run_kwargs = {}
                    if full:
                        run_kwargs["full"] = full
                    if enrich_symbols:
                        run_kwargs["enrich_symbols"] = enrich_symbols
                    if generate_wiki:
                        run_kwargs["generate_wiki"] = generate_wiki
                    if union_files:
                        run_kwargs["union_files"] = union_files
                    if not pull:
                        run_kwargs["pull"] = pull
                    await idx.run(repo_id, **run_kwargs)
            except Exception as e:
                logger.error(f"Background {kind} failed for {repo_id}: {e}")
                from app.api.websocket import event_manager
                await event_manager.broadcast("repo.indexing_failed", {"repo_id": str(repo_id), "error": str(e)[:200]})
                try:
                    async with session_factory() as session:
                        from app.models.code import Repository
                        from sqlalchemy import select
                        r = (await session.execute(
                            select(Repository).where(Repository.id == repo_id)
                        )).scalar_one_or_none()
                        # CodePipeline.run() already set and committed its own
                        # terminal status (including "stale" when it kept a prior
                        # graph); don't stomp that back to a bare "error" here.
                        if r and r.status != "stale":
                            r.status = "error"
                            r.status_message = str(e)[:500]
                            await session.commit()
                except Exception as inner_e:
                    logger.error("Failed to set error status for repo %s: %s", repo_id, inner_e)

    task = asyncio.create_task(_run_index())
    TaskRegistry.register(repo_id, kind, task, "Indexing repository...")
    return task


@router.post("/{repo_id}/reindex", status_code=status.HTTP_202_ACCEPTED)
async def reindex_repo(
    repo_id: UUID,
    _read_only=Depends(refuse_when_read_only),
    body: ReindexRequest = ReindexRequest(),
    _user=Depends(require_auth),
    pipeline: CodePipeline = Depends(get_code_pipeline),
    manager: RepoManager = Depends(get_repo_manager),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
):
    repo = await manager.get(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    if not await manager.claim_for_indexing(repo_id, message="Queued for indexing..."):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository is already indexing",
        )

    try:
        _spawn_repo_index(
            repo_id, pipeline, session_factory,
            kind="reindex",
            full=body.full,
            enrich_symbols=body.enrich_symbols,
            generate_wiki=body.generate_wiki,
        )
    except Exception as e:
        # The 'indexing' status was already committed above; if scheduling fails
        # the repo would be stuck there with no task. Reset it so the UI isn't
        # wedged and the user can retry.
        logger.error("Failed to schedule reindex for %s: %s", repo_id, e)
        repo.status = "error"
        repo.status_message = "Failed to start indexing"
        await manager.session.commit()
        raise HTTPException(status_code=500, detail="Failed to start indexing")
    return {"status": "indexing", "repo_id": str(repo_id)}


@router.post("/{repo_id}/reindex-files", status_code=status.HTTP_202_ACCEPTED)
async def reindex_repo_files(
    repo_id: UUID,
    body: ReindexFilesRequest,
    _read_only=Depends(refuse_when_read_only),
    principal=Depends(_require_repo_admin),
    pipeline: CodePipeline = Depends(get_code_pipeline),
    manager: RepoManager = Depends(get_repo_manager),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
):
    """File-scoped, commit-verified reindex (doc: 2026-08-28 design).

    ``reindex_repo``'s shape with two additions: the caller's file list is
    unioned into the diff rather than replacing it, and an optional sha is
    verified against HEAD before anything is claimed. The verification is
    read-only -- see ``reindex_request`` for why it must not pull here.

    ``prepare_reindex`` journals only its own refusals; every path here that
    it does not already cover -- claim lost, spawn failure, or the not-found
    case it never reaches -- journals its own outcome exactly once, so one
    request produces exactly one audit row no matter which branch it takes.
    """
    repo = await manager.get(repo_id)
    if not repo:
        await journal_reindex_outcome(
            manager.session, repo_id, outcome="not_found",
            file_count=len(body.files), commit=body.commit,
            actor=principal.actor, api_key_id=principal.api_key_id,
            source="reindex_api",
        )
        await manager.session.commit()
        raise HTTPException(status_code=404, detail="Repository not found")

    try:
        accepted = await prepare_reindex(
            manager.session, repo,
            files=body.files, commit=body.commit,
            actor=principal.actor, api_key_id=principal.api_key_id,
            source="reindex_api",
        )
    except ReindexRefused as refused:
        # Returned directly, not raised as an HTTPException: main.py's
        # generic StarletteHTTPException handler keeps `details` only for a
        # list and `message` only for a string, so a dict `detail` is
        # flattened to "Request failed" (see knowledge_search.py's own note
        # on the same constraint). A caller needs `reason` and the sha pair,
        # so this bypasses that handler by never raising through it.
        return JSONResponse(
            status_code=refused.status_code,
            content={"detail": {"reason": refused.reason, **refused.detail}},
        )

    if not await manager.claim_for_indexing(repo_id, message="Queued for indexing..."):
        await journal_reindex_outcome(
            manager.session, repo_id, outcome="repo_busy",
            file_count=len(body.files), commit=accepted.commit,
            actor=principal.actor, api_key_id=principal.api_key_id,
            source="reindex_api",
        )
        await manager.session.commit()
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content={"detail": {"reason": "repo_busy"}},
        )

    try:
        _spawn_repo_index(
            repo_id, pipeline, session_factory,
            kind="reindex-files",
            enrich_symbols=body.enrich_symbols,
            union_files=accepted.union_files,
        )
    except Exception as e:
        logger.error("Failed to schedule file reindex for %s: %s", repo_id, e)
        repo.status = "error"
        repo.status_message = "Failed to start indexing"
        await journal_reindex_outcome(
            manager.session, repo_id, outcome="spawn_failed",
            file_count=len(body.files), commit=accepted.commit,
            actor=principal.actor, api_key_id=principal.api_key_id,
            source="reindex_api",
        )
        await manager.session.commit()
        raise HTTPException(status_code=500, detail="Failed to start indexing")

    await journal_reindex_outcome(
        manager.session, repo_id, outcome="indexing",
        file_count=len(body.files), commit=accepted.commit,
        actor=principal.actor, api_key_id=principal.api_key_id,
        source="reindex_api",
    )
    await manager.session.commit()

    return ReindexFilesResponse(
        status="indexing", repo_id=str(repo_id),
        commit=accepted.head, accepted=len(accepted.union_files),
    )


@router.post("/{repo_id}/webhook", status_code=status.HTTP_202_ACCEPTED)
async def repo_push_webhook(
    repo_id: UUID,
    _read_only=Depends(refuse_when_read_only),
    principal=Depends(_require_repo_admin),
    pipeline: CodePipeline = Depends(get_code_pipeline),
    manager: RepoManager = Depends(get_repo_manager),
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
):
    """Push-triggered sync for one repo (doc 10 §5, doc 15 §9).

    ``reindex_repo``'s own shape, one screen up in this file: guard, commit
    ``status='indexing'`` in the route before any work, spawn the identical
    change-gated ``CodePipeline.run`` polling's own job runner uses through
    the one shared ``_spawn_repo_index`` background path, and return 202
    with no terminal result -- never a synchronous ``pipeline.run`` inline
    here. Credential verification is the ``_require_repo_admin`` dependency,
    which FastAPI resolves before this body runs at all, so a missing,
    forged, wrong-scope or revoked credential never reaches the conflict
    check or the spawn below.

    The push payload itself is never parsed: the pipeline re-derives the
    true state with its own ``git pull`` + HEAD-sha compare inside ``run``,
    so nothing here needs to trust (or even read) what the sender claims
    changed -- exactly the "purely a latency improvement" framing doc 10 §5
    gives the webhook over polling. Committing ``status='indexing'`` here,
    before any work, is also what narrows the concurrent-delivery window to
    the route body rather than leaving it as wide as the pipeline's own
    ``git pull``.
    """
    # Journalled before the lookup, in its own committed session, so *every*
    # keyed delivery leaves a row — including the 404 probe against a repo id
    # that does not exist and the 409 against one already indexing, which are
    # precisely the deliveries a leaked credential produces and precisely the
    # ones whose request transaction never commits. This is the keyed act;
    # the `repo_indexed` row the spawned run writes is the system's own work.
    async with session_factory() as journal_session:
        await record_event(
            journal_session,
            event_type="repo_webhook_received",
            object_type="repository",
            object_id=repo_id,
            actor=principal.actor,
            api_key_id=principal.api_key_id,
            source="webhook",
            payload={"keyed": principal.api_key_id is not None},
        )
        await journal_session.commit()

    repo = await manager.get(repo_id)
    if not repo:
        raise HTTPException(status_code=404, detail="Repository not found")

    # A sync (from polling or an earlier webhook delivery) may already be in
    # flight for this repo -- the same conflict this module's own
    # `reindex_repo` guards against, and the same status code
    # docs/api-rest-conventions.md names for exactly this case. The claim is
    # one atomic UPDATE rather than a read followed by an assignment, so two
    # simultaneous deliveries cannot both observe a free repo (T4.16).
    if not await manager.claim_for_indexing(repo_id, message="Queued for indexing..."):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Repository is already indexing",
        )

    try:
        _spawn_repo_index(repo_id, pipeline, session_factory, kind="webhook")
    except Exception as e:
        logger.error("Failed to schedule webhook reindex for %s: %s", repo_id, e)
        repo.status = "error"
        repo.status_message = "Failed to start indexing"
        await manager.session.commit()
        raise HTTPException(status_code=500, detail="Failed to start indexing")
    return {"status": "indexing", "repo_id": str(repo_id)}


@router.get("/{repo_id}/tasks")
async def get_repo_tasks(
    repo_id: UUID,
    _user=Depends(require_auth),
):
    from app.services.task_registry import TaskRegistry
    return TaskRegistry.get_repo_tasks(repo_id)


@router.delete("/{repo_id}/tasks/{task_id}")
async def cancel_repo_task(
    repo_id: UUID,
    task_id: str,
    _user=Depends(require_auth),
    manager: RepoManager = Depends(get_repo_manager),
):
    from app.services.task_registry import TaskRegistry
    cancelled = TaskRegistry.cancel(task_id)
    if not cancelled:
        raise HTTPException(status_code=404, detail="Task not found or already completed")

    repo = await manager.get(repo_id)
    if repo and repo.status in ("cloning", "indexing"):
        repo.status = "cancelled"
        repo.status_message = f"Task {task_id} cancelled by user"
        await manager.session.flush()

    return {"status": "cancelled", "task_id": task_id}


