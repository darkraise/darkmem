"""REST surface conformance (T1.42b, docs/api-rest-conventions.md, doc 12 §2).

Three things are asserted, each **per route** rather than once for the whole
surface, per the controller's ruling that a single spot-check does not make a
shape "uniform":

1. Every Phase-1 route's default status code matches the convention — driven
   off a full enumeration of ``app.routes`` so a new route that doesn't fit
   the table fails loudly instead of silently drifting (Done-when box 1).
2. The error envelope (``app.main``'s exception handlers, T1.42a) is what a
   caller actually gets back on a representative failure from each of many
   routers, not just one 404 (Done-when box 2, ruling 4).
3. The paginated list surfaces that accept both ``limit`` and ``offset``
   agree on ``items`` + ``total`` + ``limit`` + ``offset`` (Done-when box 2).

``POST /memories`` and ``POST /memories/batch`` set their status dynamically
(201 vs 202 depending on whether the row settled inline) and so carry no
decorator-level ``status_code`` for the static table to check; they are
verified live instead, in the same spirit.
"""
from __future__ import annotations

import uuid

import pytest
from fastapi.routing import APIRoute

from app.main import app
from app.schemas.envelope import ENVELOPE_SCHEMA_VERSION
from app.services.pipeline_failures import RETRY_HANDLERS, PipelineFailureService, retry_locks

pytestmark = pytest.mark.asyncio


# ── 1. Status codes, asserted per route ─────────────────────────────

# expected value is either an int (the decorator's declared default success
# status) or the literal "dynamic" for a route whose status is chosen inside
# the handler body and therefore verified by a live call below.
EXPECTED_STATUS = {
    ("GET", "/api/v1/analytics/overview"): 200,
    ("GET", "/api/v1/analytics/pipeline-logs"): 200,
    ("POST", "/api/v1/analytics/reprocess"): 200,
    ("POST", "/api/v1/analytics/reprocess/stream"): 200,
    ("GET", "/api/v1/analytics/stats"): 200,
    # TH1.16's horizon surface. All reads plus one POST that reads: the Q&A
    # door creates nothing, so 200 rather than 201 — the convention's 201 is
    # for a resource that now exists, and a grounded answer is not stored.
    ("GET", "/api/v1/documents"): 200,
    ("GET", "/api/v1/documents/{document_id}/summary"): 200,
    ("GET", "/api/v1/documents/{document_id}/connections"): 200,
    ("GET", "/api/v1/documents/{document_id}/outline"): 200,
    ("GET", "/api/v1/documents/{document_id}"): 200,
    ("POST", "/api/v1/documents/qa"): 200,
    ("POST", "/api/v1/documents"): 201,
    ("DELETE", "/api/v1/documents/{document_id}"): 204,
    ("POST", "/api/v1/documents/search"): 200,
    # The by-uri half of the three document-keyed verbs: one handler each,
    # two paths, so the statuses are the id form's by construction.
    ("GET", "/api/v1/documents/by-uri/outline"): 200,
    ("GET", "/api/v1/documents/by-uri"): 200,
    ("DELETE", "/api/v1/documents/by-uri"): 204,
    ("POST", "/api/v1/api-keys"): 201,
    ("GET", "/api/v1/api-keys"): 200,
    # 204 and a revocation rather than a row removal: `events.api_key_id`
    # takes no foreign key, so deleting the row would orphan the history of
    # every call the key made. The verb and the status still match the
    # convention -- the resource stops being usable, which is what DELETE
    # means to a caller.
    ("DELETE", "/api/v1/api-keys/{key_id}"): 204,
    ("GET", "/api/v1/auth/audit"): 200,
    ("POST", "/api/v1/auth/change-password"): 200,
    ("POST", "/api/v1/auth/login"): 200,
    ("POST", "/api/v1/auth/logout"): 200,
    ("GET", "/api/v1/auth/me"): 200,
    ("POST", "/api/v1/auth/refresh"): 200,
    ("GET", "/api/v1/auth/security-posture"): 200,
    ("POST", "/api/v1/chat/completions"): 200,
    ("GET", "/api/v1/chat/conversations"): 200,
    ("POST", "/api/v1/chat/conversations"): 201,
    ("GET", "/api/v1/chat/conversations/{conversation_id}"): 200,
    ("PATCH", "/api/v1/chat/conversations/{conversation_id}"): 200,
    ("DELETE", "/api/v1/chat/conversations/{conversation_id}"): 204,
    ("POST", "/api/v1/code/blast-radius"): 200,
    ("GET", "/api/v1/code/files/{repo_id}"): 200,
    ("GET", "/api/v1/code/graph/{repo_id}"): 200,
    ("POST", "/api/v1/code/search"): 200,
    ("GET", "/api/v1/code/symbols"): 200,
    ("GET", "/api/v1/code/symbols/lookup"): 200,
    ("GET", "/api/v1/code/symbols/{symbol_id}"): 200,
    ("GET", "/api/v1/code/wiki/{repo_id}"): 200,
    ("GET", "/api/v1/config/classification-areas"): 200,
    ("GET", "/api/v1/config/feature-flags"): 200,
    ("PUT", "/api/v1/config/feature-flags"): 200,
    ("GET", "/api/v1/config/llm"): 200,
    # Documented deviation (api-rest-conventions.md "Known deviations"): an
    # idempotent full-replace that should be PUT for symmetry with its
    # siblings, left as POST because fixing it breaks the frontend.
    ("POST", "/api/v1/config/llm"): 200,
    ("GET", "/api/v1/git-accounts"): 200,
    ("POST", "/api/v1/git-accounts"): 201,
    # Checks a token at the forge and returns the identity; it stores nothing,
    # so it is a 200 read-shaped POST, not a 201 create.
    ("POST", "/api/v1/git-accounts/verify"): 200,
    ("PUT", "/api/v1/git-accounts/{account_id}"): 200,
    ("DELETE", "/api/v1/git-accounts/{account_id}"): 204,
    ("GET", "/api/v1/config/llm-providers"): 200,
    ("POST", "/api/v1/config/llm-providers"): 201,
    ("PUT", "/api/v1/config/llm-providers/{name}"): 200,
    ("DELETE", "/api/v1/config/llm-providers/{name}"): 204,
    # Both probes report a vendor failure as 200 with `error` set, never a
    # raise -- a probe failure is information about the vendor, not the
    # darkmem request, matching the wizard probe's existing contract.
    ("POST", "/api/v1/config/llm-providers/probe-models"): 200,
    ("POST", "/api/v1/config/llm-providers/{name}/probe-models"): 200,
    ("GET", "/api/v1/config/verification-ladder"): 200,
    ("PUT", "/api/v1/config/verification-ladder"): 200,
    ("GET", "/api/v1/config/repo-allowlist"): 200,
    # T3.28: the auto_research operator surface. A PUT that updates a
    # config row in place, so 200 rather than 201 — nothing is created.
    ("GET", "/api/v1/config/auto-research"): 200,
    ("PUT", "/api/v1/config/auto-research"): 200,
    ("GET", "/api/v1/config/auto-research/runs"): 200,
    # Not 201: a re-derivation creates no resource. It recomputes what
    # existing rows imply, so 200-with-a-report is the honest code, and
    # it matches the sibling `POST /analytics/reprocess`.
    ("POST", "/api/v1/config/auto-research/runs/{event_id}/rerun"): 200,
    ("PUT", "/api/v1/config/repo-allowlist"): 200,
    ("GET", "/api/v1/config/repos-path"): 200,
    ("PUT", "/api/v1/config/repos-path"): 200,
    ("GET", "/api/v1/config/system-prompts"): 200,
    ("PUT", "/api/v1/config/system-prompts"): 200,
    ("GET", "/api/v1/config/theme"): 200,
    ("PUT", "/api/v1/config/theme"): 200,
    ("GET", "/api/v1/events"): 200,
    ("GET", "/api/v1/events/calendar"): 200,
    ("GET", "/api/v1/events/timeline"): 200,
    ("GET", "/api/v1/graph/entities"): 200,
    ("GET", "/api/v1/graph/entities/{entity_id}/neighbors"): 200,
    ("GET", "/api/v1/graph/full"): 200,
    ("GET", "/api/v1/graph/memory-context/{memory_id}"): 200,
    # T3.16. 201 rather than the capture doors' 202: the checkpoint write is
    # synchronous and complete when the response is written, so there is no
    # queued work an ack would describe.
    ("POST", "/api/v1/checkpoints"): 201,
    ("GET", "/api/v1/checkpoints/latest"): 200,
    ("GET", "/api/v1/distribution"): 200,
    # 200 rather than 204: the curb is here, and a human turning push off
    # needs to see the state now in force.
    ("PUT", "/api/v1/distribution/policy"): 200,
    ("GET", "/api/v1/graph/unified"): 200,
    ("GET", "/api/v1/config/notifications"): 200,
    ("PUT", "/api/v1/config/notifications"): 200,
    ("POST", "/api/v1/config/notifications/test"): 200,
    ("GET", "/api/v1/jobs"): 200,
    ("GET", "/api/v1/jobs/{key}/runs"): 200,
    ("PUT", "/api/v1/jobs/{key}"): 200,
    ("PUT", "/api/v1/jobs/{key}/config"): 200,
    # Synchronous by design (jobs.py): the manual "Run" awaits the job and
    # returns its result, so there is nothing left queued to accept.
    ("POST", "/api/v1/jobs/{key}/trigger"): 200,
    ("POST", "/api/v1/memories"): "dynamic",
    ("POST", "/api/v1/memories/batch"): "dynamic",
    ("POST", "/api/v1/memories/delete"): 200,
    ("POST", "/api/v1/memories/reason"): 200,
    ("POST", "/api/v1/memories/search"): 200,
    ("POST", "/api/v1/memories/search/paginated"): 200,
    ("GET", "/api/v1/memories/{memory_id}"): 200,
    ("PUT", "/api/v1/memories/{memory_id}"): 200,
    ("DELETE", "/api/v1/memories/{memory_id}"): 204,
    ("GET", "/api/v1/memories/{memory_id}/duplicates"): 200,
    ("POST", "/api/v1/memories/{memory_id}/merge"): 200,
    ("GET", "/api/v1/memory-buffer"): 200,
    ("GET", "/api/v1/memory-buffer/stats"): 200,
    ("DELETE", "/api/v1/memory-buffer/{buffer_id}"): 204,
    ("POST", "/api/v1/memory-buffer/{buffer_id}/requeue"): 200,
    ("GET", "/api/v1/pipeline"): 200,
    ("GET", "/api/v1/pipeline-failures"): 200,
    ("GET", "/api/v1/pipeline-failures/counts"): 200,
    ("POST", "/api/v1/pipeline-failures/retry-all"): 202,
    ("GET", "/api/v1/pipeline-failures/{failure_id}"): 200,
    ("DELETE", "/api/v1/pipeline-failures/{failure_id}"): 204,
    ("POST", "/api/v1/pipeline-failures/{failure_id}/retry"): 202,
    ("GET", "/api/v1/pipeline/metrics"): 200,
    ("GET", "/api/v1/usage/overview"): 200,
    ("GET", "/api/v1/usage/series"): 200,
    ("GET", "/api/v1/usage/by-subject/{subject_type}/{subject_id}"): 200,
    ("GET", "/api/v1/usage/top"): 200,
    # A computation with a complex body, the same shape as POST .../search.
    ("POST", "/api/v1/usage/subject-totals"): 200,
    ("GET", "/api/v1/usage/by-job"): 200,
    ("GET", "/api/v1/usage/prices"): 200,
    # Full-replace of a config singleton, the same shape as /feature-flags.
    ("PUT", "/api/v1/usage/prices"): 200,
    ("POST", "/api/v1/reembed/all"): 202,
    ("POST", "/api/v1/reembed/code-chunks"): 202,
    ("POST", "/api/v1/reembed/entities"): 202,
    ("POST", "/api/v1/reembed/memories"): 202,
    ("GET", "/api/v1/reembed/obsolete-counts"): 200,
    ("GET", "/api/v1/reembed/obsolete/code-chunks"): 200,
    ("GET", "/api/v1/reembed/obsolete/entities"): 200,
    ("GET", "/api/v1/reembed/obsolete/memories"): 200,
    ("POST", "/api/v1/reembed/prune-cache"): 200,
    ("POST", "/api/v1/repos"): 201,
    ("GET", "/api/v1/repos"): 200,
    ("GET", "/api/v1/repos/stats"): 200,
    ("GET", "/api/v1/repos/{repo_id}"): 200,
    ("PUT", "/api/v1/repos/{repo_id}"): 200,
    ("DELETE", "/api/v1/repos/{repo_id}"): 204,
    ("POST", "/api/v1/repos/{repo_id}/reindex"): 202,
    ("POST", "/api/v1/repos/{repo_id}/reindex-files"): 202,
    ("POST", "/api/v1/repos/{repo_id}/webhook"): 202,
    ("GET", "/api/v1/repos/{repo_id}/tasks"): 200,
    # Documented deviation: a cancel, not a true delete — 200 with a body is
    # correct today; DELETE-as-cancel is the thing left for a coordinated
    # client update, not the status code.
    ("DELETE", "/api/v1/repos/{repo_id}/tasks/{task_id}"): 200,
    # T2.13. Both undo doors are 200-with-a-body rather than 204: the digest
    # re-renders from the response, and a 204 would leave the UI nothing to
    # mark the undone actions with.
    ("GET", "/api/v1/dream-digest/cycles"): 200,
    ("GET", "/api/v1/dream-digest/cycles/{cycle_id}"): 200,
    ("POST", "/api/v1/dream-digest/actions/{event_id}/undo"): 200,
    ("POST", "/api/v1/dream-digest/cycles/{cycle_id}/undo"): 200,
    ("GET", "/api/v1/knowledge/facts"): 200,
    ("GET", "/api/v1/knowledge/facts/{fact_id}"): 200,
    ("GET", "/api/v1/knowledge/articles"): 200,
    ("GET", "/api/v1/knowledge/articles/{article_id}"): 200,
    # A human adjudication verb, the same shape as review-queue's reject: 204,
    # so the verb serves no memory-derived content and never becomes a content
    # surface. 201 would claim a resource was minted at a new location and
    # oblige a Location header pointing at one.
    ("POST", "/api/v1/knowledge/facts/{fact_id}/ratify"): 204,
    ("GET", "/api/v1/knowledge/overview"): 200,
    ("GET", "/api/v1/knowledge/topics"): 200,
    ("GET", "/api/v1/knowledge/topics/{label}"): 200,
    ("GET", "/api/v1/knowledge/topics/pin-suggestions"): 200,
    # Accept/dismiss are adjudication verbs, the same shape as ratify/reject:
    # 204, no memory-derived content on the response.
    ("POST", "/api/v1/knowledge/topics/pin-suggestions/accept"): 204,
    ("POST", "/api/v1/knowledge/topics/pin-suggestions/dismiss"): 204,
    # The composed read: a computation over a complex body, which the
    # conventions doc puts on POST .../search and answers 200. It mints
    # nothing, so 201 would be a lie about a resource; the query is too rich
    # for a GET query string, which is the whole reason the pattern exists.
    ("POST", "/api/v1/knowledge/search"): 200,
    ("GET", "/api/v1/review-queue/articles"): 200,
    ("GET", "/api/v1/review-queue/counts"): 200,
    ("GET", "/api/v1/review-queue/facts"): 200,
    ("POST", "/api/v1/review-queue/facts/{fact_id}/reject"): 204,
    # 204 for `/reject`'s reason: the dismissal moves no served state, so
    # there is no post-state worth echoing (T2.112).
    ("POST", "/api/v1/review-queue/facts/{fact_id}/dismiss-suspicion"): 204,
    # T2.23. Bulk actions are 200-with-a-body for the same reason the T2.13
    # undo doors are: every item's own outcome (including a refusal) is the
    # point of the response, and a 204 would give the caller nothing to act on.
    ("GET", "/api/v1/hygiene-queue/duplicates"): 200,
    ("GET", "/api/v1/hygiene-queue/low-confidence"): 200,
    ("GET", "/api/v1/hygiene-queue/expiring-soon"): 200,
    ("GET", "/api/v1/hygiene-queue/superseded"): 200,
    ("GET", "/api/v1/hygiene-queue/counts"): 200,
    ("POST", "/api/v1/hygiene-queue/bulk/supersede"): 200,
    ("POST", "/api/v1/hygiene-queue/bulk/prune"): 200,
    ("POST", "/api/v1/hygiene-queue/bulk/confirm-dedup"): 200,
    ("POST", "/api/v1/setup"): 200,
    ("GET", "/api/v1/setup/fs/list"): 200,
    ("GET", "/api/v1/setup/fs/roots"): 200,
    ("POST", "/api/v1/setup/probe-models"): 200,
    ("GET", "/api/v1/setup/status"): 200,
    ("GET", "/api/v1/system/fs/list"): 200,
    ("GET", "/api/v1/system/fs/roots"): 200,
    ("GET", "/api/v1/projects"): 200,
    ("GET", "/api/v1/tags"): 200,
    ("GET", "/api/v1/vectors/projection"): 200,
    ("GET", "/health"): 200,
}


def _iter_api_routes():
    """Flatten FastAPI's (lazily-included) router tree into APIRoute leaves.

    Recent FastAPI wraps ``include_router`` targets in ``_IncludedRouter``
    rather than eagerly flattening ``app.routes``, so a plain iteration over
    ``app.routes`` sees wrapper objects, not the leaf routes this test needs.
    """
    def walk(routes):
        for r in routes:
            original = getattr(r, "original_router", None)
            if original is not None:
                yield from walk(original.routes)
            elif isinstance(r, APIRoute):
                yield r

    yield from walk(app.routes)


async def test_every_route_status_code_matches_the_convention():
    seen = set()
    for route in _iter_api_routes():
        for method in sorted(route.methods - {"HEAD"}):
            key = (method, route.path)
            seen.add(key)
            assert key in EXPECTED_STATUS, (
                f"{method} {route.path} has no conformance entry in "
                "EXPECTED_STATUS — classify it against "
                "docs/api-rest-conventions.md before adding it"
            )
            expected = EXPECTED_STATUS[key]
            if expected == "dynamic":
                continue
            actual = route.status_code if route.status_code is not None else 200
            assert actual == expected, (
                f"{method} {route.path} answers {actual}, "
                f"convention expects {expected}"
            )
    # The table must not silently grow stale entries for routes that no
    # longer exist — every table row was seen on this pass.
    stale = set(EXPECTED_STATUS) - seen
    assert not stale, f"EXPECTED_STATUS has entries for removed routes: {stale}"


async def test_bare_memory_create_status_is_201_or_202_by_wait_process(
    client, auth_headers,
):
    accepted = await client.post(
        "/api/v1/memories", json={"content": "dynamic status, buffered"},
        headers=auth_headers,
    )
    assert accepted.status_code == 202

    settled = await client.post(
        "/api/v1/memories?wait_process=true",
        json={"content": "dynamic status, inline"},
        headers=auth_headers,
    )
    assert settled.status_code == 201


async def test_batch_memory_create_status_is_201_or_202_by_wait_process(
    client, auth_headers,
):
    accepted = await client.post(
        "/api/v1/memories/batch",
        json={"entries": [{"content": "batch buffered"}]},
        headers=auth_headers,
    )
    assert accepted.status_code == 202

    settled = await client.post(
        "/api/v1/memories/batch?wait_process=true",
        json={"entries": [{"content": "batch inline"}]},
        headers=auth_headers,
    )
    assert settled.status_code == 201


# ── 2. Error shape, asserted per case rather than once ──────────────


def _assert_uniform_error_envelope(body: dict) -> None:
    assert body["schema_version"] == ENVELOPE_SCHEMA_VERSION
    error = body["error"]
    assert isinstance(error["code"], str) and error["code"]
    assert isinstance(error["message"], str) and error["message"]
    # `detail` is a string mirror of `error.message` on every shape — the
    # frontend interpolates `detail` straight into an `Error` (app/main.py).
    assert body["detail"] == error["message"]


async def test_error_shape_is_uniform_across_the_surface(
    client, auth_headers, session,
):
    missing = uuid.uuid4()

    cases: list[tuple[str, str, dict | None, int]] = [
        ("GET", f"/api/v1/memories/{missing}", None, 404),
        ("GET", f"/api/v1/repos/{missing}", None, 404),
        # Not /chat/conversations/{id}: ChatService's dependency raises a
        # blanket 503 whenever app.state.llm is unset (app/api/deps.py) —
        # true in this bare test app for every id, not just a missing one —
        # so it would not exercise the 404 path this case is after.
        ("GET", f"/api/v1/code/symbols/{missing}", None, 404),
        ("GET", f"/api/v1/pipeline-failures/{missing}", None, 404),
        ("DELETE", f"/api/v1/memory-buffer/{missing}", None, 404),
        ("PUT", "/api/v1/jobs/no-such-job", {}, 404),
        ("POST", "/api/v1/jobs/no-such-job/trigger", None, 404),
        ("GET", f"/api/v1/graph/entities/{missing}/neighbors", None, 404),
    ]

    for method, path, json_body, expected_status in cases:
        kwargs = {"headers": auth_headers}
        if json_body is not None:
            kwargs["json"] = json_body
        response = await client.request(method, path, **kwargs)
        assert response.status_code == expected_status, (
            f"{method} {path} answered {response.status_code}, expected "
            f"{expected_status}"
        )
        _assert_uniform_error_envelope(response.json())

    # 401 — no credentials at all.
    unauthorized = await client.get(f"/api/v1/memories/{missing}")
    assert unauthorized.status_code == 401
    _assert_uniform_error_envelope(unauthorized.json())

    # 422 — validation failure (FastAPI's own list-shaped errors path).
    invalid_body = await client.post(
        "/api/v1/memories", json={}, headers=auth_headers,
    )
    assert invalid_body.status_code == 422
    _assert_uniform_error_envelope(invalid_body.json())

    invalid_pattern = await client.put(
        "/api/v1/config/repo-allowlist",
        json={"patterns": ["has space"]},
        headers=auth_headers,
    )
    assert invalid_pattern.status_code == 422
    _assert_uniform_error_envelope(invalid_pattern.json())

    # 409 — a buffered row that is not a poison row cannot be requeued.
    from tests.test_api.test_buffer import seed as seed_buffer_row

    pending_id = await seed_buffer_row(session, status="pending")
    conflict = await client.post(
        f"/api/v1/memory-buffer/{pending_id}/requeue", headers=auth_headers,
    )
    assert conflict.status_code == 409
    _assert_uniform_error_envelope(conflict.json())

    # 503 — no pipeline/LLM wired up in the test app, the reembed doors'
    # own precondition check.
    unavailable = await client.post(
        "/api/v1/reembed/memories", headers=auth_headers,
    )
    assert unavailable.status_code == 503
    _assert_uniform_error_envelope(unavailable.json())


async def test_pipeline_failure_retry_conflict_uses_the_error_envelope(
    client, auth_headers, session,
):
    """Regression guard for the two `return JSONResponse(...)` conflict
    bodies this task replaced with `raise HTTPException(...)` in
    pipeline_failures.py and reembed.py: before the fix, a 409/503 from these
    routes carried ``{"accepted": false, "reason": ...}`` instead of the
    uniform envelope, which is exactly what this test would have caught."""
    svc = PipelineFailureService(session)
    failure = await svc.record(
        entity_type="memory", entity_id=uuid.uuid4(),
        pipeline_name="__conformance_test_pipeline__",
        failed_step="extract", error_message="boom",
    )
    await session.commit()
    failure_id = uuid.UUID(failure["id"])

    RETRY_HANDLERS["__conformance_test_pipeline__"] = _noop_retry_handler
    try:
        assert retry_locks.try_acquire(failure_id)
        try:
            response = await client.post(
                f"/api/v1/pipeline-failures/{failure_id}/retry",
                headers=auth_headers,
            )
            assert response.status_code == 409
            _assert_uniform_error_envelope(response.json())
        finally:
            retry_locks.release(failure_id)
    finally:
        RETRY_HANDLERS.pop("__conformance_test_pipeline__", None)

    no_handler = await svc.record(
        entity_type="memory", entity_id=uuid.uuid4(),
        pipeline_name="__conformance_test_pipeline_unhandled__",
        failed_step="extract", error_message="boom",
    )
    await session.commit()
    response = await client.post(
        f"/api/v1/pipeline-failures/{no_handler['id']}/retry",
        headers=auth_headers,
    )
    assert response.status_code == 503
    _assert_uniform_error_envelope(response.json())


async def _noop_retry_handler(entity_id: uuid.UUID) -> None:
    return None


# ── 3. Pagination shape, asserted across every limit+offset list ────


async def test_paginated_list_shapes_are_uniform(client, auth_headers, session):
    """Every list surface that accepts *both* `limit` and `offset` answers
    with `items` + `total` + `limit` + `offset`, so a client can tell what
    page it was actually served without re-deriving it from the request it
    sent. Bounded-but-unpaginated reads (tags, repos, vectors/projection —
    accept at most a cap, never an offset) are out of scope by construction:
    a caller of those cannot ask for a page in the first place."""
    paginated_gets = [
        "/api/v1/memory-buffer",
        "/api/v1/pipeline-failures",
        "/api/v1/code/symbols",
        "/api/v1/auth/audit",
        "/api/v1/review-queue/facts",
        "/api/v1/review-queue/articles",
        "/api/v1/knowledge/facts",
        "/api/v1/knowledge/articles",
        "/api/v1/hygiene-queue/duplicates",
        "/api/v1/hygiene-queue/low-confidence",
        "/api/v1/hygiene-queue/expiring-soon",
        "/api/v1/hygiene-queue/superseded",
    ]
    for path in paginated_gets:
        response = await client.get(path, headers=auth_headers)
        assert response.status_code == 200, f"GET {path} -> {response.status_code}"
        body = response.json()
        for key in ("items", "total", "limit", "offset"):
            assert key in body, f"GET {path} response is missing {key!r}: {body.keys()}"
        assert isinstance(body["limit"], int)
        assert isinstance(body["offset"], int)

    # The reembed obsolete-listings need an active embedder to resolve a
    # fingerprint (app.state.pipeline.llm), unset in the bare test app; stub
    # just enough of it to exercise the pagination shape without asserting
    # anything about the embedder itself (test_reembed_absent_partition.py
    # owns the absent-partition semantics this stub deliberately triggers).
    from types import SimpleNamespace

    previous_pipeline = getattr(app.state, "pipeline", None)
    app.state.pipeline = SimpleNamespace(
        llm=SimpleNamespace(llm_fingerprint=lambda: "conformance-test-fp|4")
    )
    try:
        for path in (
            "/api/v1/reembed/obsolete/memories",
            "/api/v1/reembed/obsolete/code-chunks",
            "/api/v1/reembed/obsolete/entities",
        ):
            response = await client.get(path, headers=auth_headers)
            assert response.status_code == 200, f"GET {path} -> {response.status_code}"
            body = response.json()
            for key in ("items", "total", "limit", "offset", "partition_missing"):
                assert key in body, f"GET {path} response is missing {key!r}: {body.keys()}"
    finally:
        app.state.pipeline = previous_pipeline

    search_paginated = await client.post(
        "/api/v1/memories/search/paginated", json={"query": "x"}, headers=auth_headers,
    )
    assert search_paginated.status_code == 200
    body = search_paginated.json()
    for key in ("items", "total", "limit", "offset"):
        assert key in body, f"POST search/paginated response is missing {key!r}"
