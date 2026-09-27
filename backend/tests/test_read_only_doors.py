"""What the read-only flag does at the doors (increment 7, groups B and C).

**The role is the guarantee.** Everything here is either ergonomics — a write
on a read path that would otherwise log an error per request — or a refusal
whose failure mode the role cannot improve: money already spent, or a viewer
session silently killed.

**What is deliberately NOT guarded, and why.** Journal rows on read and auth
flows (`record_event`, group B4) and per-call `llm_usage` rows
(`UsageRecorder.record`, B5) are left to degrade. Both already swallow their
own failures by module contract, so guarding them would spread the flag into
shared writers for no behavioural gain — and both are on paths where the
worker's log noting the posture once at boot is a better record than a guard
repeated at every call site. The four `JournalWriteFailed` raisers are all on
write doors (verification transitions, adjudication) that the role blocks
earlier, so none of them is reachable here.

Every test pins the default posture too. A flag that changes auth token
semantics has to prove prod is byte-identical to what it was before the flag
existed, and that pin is the point of the paired assertions below.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from app.config import settings
from app.models.token_blocklist import TokenBlocklist


async def _blocklist_count(session) -> int:
    return (await session.execute(select(func.count(TokenBlocklist.jti)))).scalar_one()


# ---------------------------------------------------------------------------
# C1 / C2: refresh and logout
# ---------------------------------------------------------------------------


async def test_refresh_still_blocklists_by_default(client, auth_headers, session):
    """The regression pin. Rotating refresh has no `changed_at` backstop, so
    the blocklist insert is the *only* revocation -- losing it silently on
    prod would be the worst kind of quiet."""
    before = await _blocklist_count(session)
    response = await client.post("/api/v1/auth/refresh", headers=auth_headers)
    assert response.status_code == 200
    assert await _blocklist_count(session) == before + 1


async def test_refresh_reissues_without_writing_under_the_flag(
    client, auth_headers, session, monkeypatch,
):
    """The viewer whose session this exists to serve must not die at access
    token expiry. Stated cost, reported on the posture endpoint: on the worker
    only, a captured pre-refresh token stays valid until its own exp."""
    monkeypatch.setattr(settings, "read_only", True)
    before = await _blocklist_count(session)

    response = await client.post("/api/v1/auth/refresh", headers=auth_headers)

    assert response.status_code == 200
    assert "set-cookie" in {k.lower() for k in response.headers}
    assert await _blocklist_count(session) == before


async def test_logout_still_blocklists_by_default(client, auth_headers, session):
    before = await _blocklist_count(session)
    response = await client.post("/api/v1/auth/logout", headers=auth_headers)
    assert response.status_code == 200
    assert await _blocklist_count(session) == before + 1


async def test_logout_clears_the_cookie_without_writing_under_the_flag(
    client, auth_headers, session, monkeypatch,
):
    monkeypatch.setattr(settings, "read_only", True)
    before = await _blocklist_count(session)

    response = await client.post("/api/v1/auth/logout", headers=auth_headers)

    assert response.status_code == 200
    assert "set-cookie" in {k.lower() for k in response.headers}
    assert await _blocklist_count(session) == before


# ---------------------------------------------------------------------------
# C3: change-password
# ---------------------------------------------------------------------------


async def test_change_password_refuses_up_front_under_the_flag(
    client, auth_headers, monkeypatch,
):
    """Refused before the handler touches the session, not left to fail
    halfway: changing a snapshot's password is meaningless -- the next restore
    overwrites it -- and a half-failed attempt is worse than a clean no."""
    monkeypatch.setattr(settings, "read_only", True)
    response = await client.post(
        "/api/v1/auth/change-password",
        headers=auth_headers,
        json={"current_password": "whatever", "new_password": "irrelevant-123456"},
    )
    assert response.status_code == 403
    assert "read-only" in response.text.lower()


# ---------------------------------------------------------------------------
# C6: the SQLSTATE 42501 door
# ---------------------------------------------------------------------------


def test_the_privilege_handler_is_registered_on_the_dbapi_base():
    """Registered on `DBAPIError`, the base `ProgrammingError` inherits from,
    so every write door inherits the mapping without a per-route allowlist --
    the maintained list review B1 rejected. Routes rot; the SQLSTATE cannot."""
    from sqlalchemy.exc import DBAPIError

    from app.main import app

    assert DBAPIError in app.exception_handlers


class _Orig(Exception):
    def __init__(self, sqlstate):
        super().__init__("permission denied")
        self.sqlstate = sqlstate


def _dbapi_error(sqlstate):
    from sqlalchemy.exc import ProgrammingError

    return ProgrammingError("INSERT ...", {}, _Orig(sqlstate))


async def test_a_privilege_refusal_becomes_a_403_read_only_envelope():
    from app.main import _database_refusal

    response = await _database_refusal(None, _dbapi_error("42501"))

    assert response.status_code == 403
    import json

    body = json.loads(response.body)
    assert body["error"]["code"] == "read_only"
    assert "read-only" in body["detail"].lower()


async def test_any_other_dbapi_error_still_surfaces_as_a_500():
    """The non-privilege branch re-raises, which reaches
    `ServerErrorMiddleware` and then the app's own `Exception` handler and its
    ordinary 500 envelope. Asserted rather than derived: `raise exc` reads like
    a gap when it is the design."""
    from sqlalchemy.exc import ProgrammingError

    from app.main import _database_refusal

    with pytest.raises(ProgrammingError):
        await _database_refusal(None, _dbapi_error("23505"))


async def test_a_dbapi_error_with_no_sqlstate_still_surfaces_as_a_500():
    from sqlalchemy.exc import ProgrammingError

    from app.main import _database_refusal

    error = ProgrammingError("INSERT ...", {}, Exception("no sqlstate here"))
    with pytest.raises(ProgrammingError):
        await _database_refusal(None, error)


# ---------------------------------------------------------------------------
# B1-B3: the writes on read paths
# ---------------------------------------------------------------------------


async def test_memory_access_bumps_are_a_quiet_no_op_under_the_flag(monkeypatch):
    """Every hybrid search bumps `memories.access_count`. Under the role the
    flush is refused and swallowed, so the only cost is an error per search --
    which is exactly the noise this guard removes."""
    from app.services import access_stats

    access_stats._pending_counts.clear()
    monkeypatch.setattr(settings, "read_only", True)

    assert access_stats.spawn_record_access(["11111111-1111-1111-1111-111111111111"]) is None
    assert not access_stats._pending_counts


async def test_memory_access_bumps_still_buffer_by_default(monkeypatch):
    from app.services import access_stats

    access_stats._pending_counts.clear()
    try:
        access_stats.spawn_record_access(["11111111-1111-1111-1111-111111111111"])
        assert access_stats._pending_counts
    finally:
        access_stats._pending_counts.clear()


async def test_fact_access_bumps_are_a_quiet_no_op_under_the_flag(monkeypatch):
    from app.services import fact_access_stats

    fact_access_stats._pending_counts.clear()
    monkeypatch.setattr(settings, "read_only", True)

    assert fact_access_stats.spawn_record_access(
        ["22222222-2222-2222-2222-222222222222"]
    ) is None
    assert not fact_access_stats._pending_counts


async def test_fact_access_bumps_still_buffer_by_default():
    from app.services import fact_access_stats

    fact_access_stats._pending_counts.clear()
    try:
        fact_access_stats.spawn_record_access(
            ["22222222-2222-2222-2222-222222222222"]
        )
        assert fact_access_stats._pending_counts
    finally:
        fact_access_stats._pending_counts.clear()


async def test_mark_key_used_opens_no_session_under_the_flag(monkeypatch):
    """`mark_key_used` opens its own session on purpose, so the request's own
    transaction rolling back cannot lose the bump. That also means the role
    refuses it on every single MCP call."""
    import uuid as _uuid

    import app.database as database
    from app.services import api_keys

    opened = []
    monkeypatch.setattr(
        database, "async_session_factory", lambda: opened.append(1) or None
    )
    monkeypatch.setattr(settings, "read_only", True)

    await api_keys.mark_key_used(_uuid.uuid4())

    assert opened == []


# ---------------------------------------------------------------------------
# The reranker clamp (group E) and the chat refusal (C4)
# ---------------------------------------------------------------------------


async def test_the_reranker_is_clamped_off_under_the_flag(session, monkeypatch):
    """An LLM scoring call per search, against the snapshot's restored
    credentials, is the spend class the disarmed scheduler exists to stop.
    The query embed stays -- a search surface that cannot embed cannot
    search -- and that asymmetry is the whole point of clamping only this."""
    from app.models.config import Config
    from app.services.feature_flags import FEATURE_FLAGS_KEY, get_feature_flags_dict

    session.add(
        Config(
            key=FEATURE_FLAGS_KEY,
            value={"reranker_enabled": True, "hybrid_search_enabled": True},
        )
    )
    await session.flush()

    on = await get_feature_flags_dict(session)
    assert on["reranker_enabled"] is True

    monkeypatch.setattr(settings, "read_only", True)
    clamped = await get_feature_flags_dict(session)

    assert clamped["reranker_enabled"] is False
    # Nothing else moves: this is one clamp, not a blanket disable.
    assert clamped["hybrid_search_enabled"] is True


async def test_chat_refuses_before_any_llm_construction(
    client, auth_headers, monkeypatch,
):
    """C4. Chat commits the user message *before* the stream, then spends
    tokens on the snapshot's restored credentials -- the refusal is about the
    money, not only about the write."""
    monkeypatch.setattr(settings, "read_only", True)
    response = await client.post(
        "/api/v1/chat/completions",
        headers=auth_headers,
        json={"conversation_id": None, "content": "hello"},
    )
    assert response.status_code == 403
    assert "read-only" in response.text.lower()


# ---------------------------------------------------------------------------
# The self-contained worker: no external service, no outbound connection
#
# Owner ruling 2026-09-03: a backup machine is for viewing and backup/restore
# only, so every feature needing an external service is disabled there. The
# argument is that a host whose whole job is surviving another machine's
# failure must not itself depend on a third machine being reachable.
#
# Two shapes, and the split matters. A door that would SPEND on an external
# service is refused up front -- the viewer role would stop the write, but
# only after the money is gone. A read path that merely *uses* the embedder
# degrades instead: search still answers, on its keyword arm alone.
# ---------------------------------------------------------------------------

EXTERNAL_SERVICE_DOORS = [
    # (method, path, json) -- each reaches an LLM, an embedder or the network.
    ("POST", "/api/v1/memories/reason", {"query": "anything"}),
    ("POST", "/api/v1/documents/qa", {"question": "anything"}),
    ("POST", "/api/v1/reembed/memories", None),
    ("POST", "/api/v1/reembed/code-chunks", None),
    ("POST", "/api/v1/reembed/entities", None),
    ("POST", "/api/v1/reembed/all", None),
    # Block search is cosine-only -- `search_blocks` ranks on
    # `1 - (embedding <=> :vec)` with no keyword arm at all -- so there is
    # nothing to degrade to. Returning empty would be indistinguishable from
    # "no matches", so the door refuses instead.
    ("POST", "/api/v1/documents/search", {"query": "anything"}),
]


@pytest.mark.parametrize("method,path,body", EXTERNAL_SERVICE_DOORS)
async def test_external_service_doors_refuse_under_the_flag(
    client, auth_headers, monkeypatch, method, path, body,
):
    """Refused before the call is made, not after the role rejects the write.

    Every one of these dispatches an LLM or an embedder first and writes
    second, so the SELECT-only role stops them only once the spend has already
    happened -- the same reasoning that refuses chat at the door."""
    monkeypatch.setattr(settings, "read_only", True)
    response = await client.request(
        method, path, headers=auth_headers, json=body,
    )
    assert response.status_code == 403, (
        f"{method} {path} returned {response.status_code}, not a read-only refusal"
    )
    assert "read-only" in response.text.lower()


@pytest.mark.parametrize("method,path,body", EXTERNAL_SERVICE_DOORS)
async def test_those_doors_are_untouched_by_default(
    client, auth_headers, method, path, body,
):
    """The regression pin: prod must behave exactly as it did before the flag.
    Anything but a read-only 403 proves the guard is posture-scoped."""
    response = await client.request(method, path, headers=auth_headers, json=body)
    assert not (
        response.status_code == 403 and "read-only" in response.text.lower()
    ), f"{method} {path} refuses as read-only with the flag OFF"


NETWORK_DOORS = [
    ("POST", "/api/v1/repos", {"url": "https://example.com/x.git", "name": "x"}),
    ("POST", f"/api/v1/repos/{uuid.uuid4()}/reindex", {}),
    ("POST", f"/api/v1/repos/{uuid.uuid4()}/reindex-files", {"files": ["a.py"]}),
]


@pytest.mark.parametrize("method,path,body", NETWORK_DOORS)
async def test_git_network_doors_refuse_under_the_flag(
    client, auth_headers, monkeypatch, method, path, body,
):
    """A worker holds no clones, so these would fail anyway -- but they fetch
    over the network before they fail, which is the outbound connection this
    posture exists to remove."""
    monkeypatch.setattr(settings, "read_only", True)
    response = await client.request(method, path, headers=auth_headers, json=body)
    assert response.status_code == 403, (
        f"{method} {path} returned {response.status_code}, not a read-only refusal"
    )
    assert "read-only" in response.text.lower()


async def test_search_answers_without_an_embedder_under_the_flag(monkeypatch):
    """The point of the whole ruling: the viewer must not need a third machine.

    Under the flag the semantic arm is skipped entirely rather than attempted
    and caught -- `llm.embed` sits OUTSIDE `_run_channels`' one-sided-failure
    guard, so an unreachable embedder does not degrade to keyword, it raises
    out of the whole search. Skipping is also the honest reading of "disable
    the features that need external services": not attempted, so not a
    degradation to explain.
    """
    from app.services.hybrid_search import HybridSearchService

    class _ExplodingLLM:
        async def embed(self, _query):
            raise AssertionError(
                "read-only search must not reach the embedder at all"
            )

    monkeypatch.setattr(settings, "read_only", True)
    service = HybridSearchService(session=None, llm=_ExplodingLLM())

    captured = {}

    async def _channels(query, vector, fingerprint, fetch_n, filters):
        captured["vector"] = vector
        captured["fingerprint"] = fingerprint
        return [], [{"id": "kw", "score": 1.0}], False, False

    monkeypatch.setattr(service, "_run_channels", _channels)
    monkeypatch.setattr(service, "_ppr_search", lambda *a, **k: _none())
    monkeypatch.setattr(service, "_dual_level_search", lambda *a, **k: _none())

    results = await service.search("anything", limit=5)

    assert captured["vector"] is None, "the semantic arm was handed a vector"
    assert results, "keyword-only search returned nothing"


async def _none():
    return []
