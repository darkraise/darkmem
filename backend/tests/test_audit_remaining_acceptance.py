"""Acceptance tests for the audit-remaining spec, written from its acceptance text."""
from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[2]
BACKEND = REPO / "backend"


def _git_ls(*pathspecs: str) -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", *pathspecs], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout.split("\n")
    return [REPO / p for p in out if p]


def _read(p: Path) -> str:
    try:
        return p.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return ""


# ------------------------------------------------------------------ A6


def _fork_expr_value(event_name: str, head_repo: str, repo: str = "darkraise/darkmem") -> bool:
    wf = yaml.safe_load((REPO / ".github/workflows/ci.yml").read_text())
    expr = wf["jobs"]["pick-runner"]["steps"][1]["env"]["FORK_PULL_REQUEST"]
    inner = expr.strip()[3:-2].strip()
    py = (
        inner.replace("github.event_name", repr(event_name))
        .replace("github.event.pull_request.head.repo.full_name", repr(head_repo))
        .replace("github.repository", repr(repo))
        .replace("!=", " <> ")
        .replace("!", " not ")
        .replace("<>", "!=")
        .replace("||", " or ")
        .replace("&&", " and ")
    )
    return bool(eval(py, {"__builtins__": {}}))  # noqa: S307 - literal expression from our own workflow


def test_a6_fork_pull_request_never_routed_to_self_hosted():
    import importlib.util

    spec = importlib.util.spec_from_file_location("pick_runner", REPO / "scripts/pick_runner.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    idle = {
        "total_count": 1,
        "runners": [
            {"status": "online", "busy": False, "labels": [{"name": "self-hosted"}, {"name": "darkmem-linux"}]}
        ],
    }
    for requested in ("fallback", "auto", "self-hosted", "hosted"):
        out: list[str] = []

        class _Env(dict):
            pass

        import os
        import tempfile

        with tempfile.NamedTemporaryFile("r+", delete=False) as gh_out:
            env = {
                "REQUESTED": requested,
                "GH_TOKEN": "x",
                "GITHUB_REPOSITORY": "darkraise/darkmem",
                "FORK_PULL_REQUEST": "true",
                "GITHUB_OUTPUT": gh_out.name,
            }
            rc = mod.main(env=env, fetch=lambda url, token: idle, sleep=lambda s: None)
            gh_out.seek(0)
            text = gh_out.read()
        os.unlink(gh_out.name)
        assert rc == 0
        assert 'runs-on="ubuntu-latest"' in text, (requested, text)
        assert "self-hosted" not in text.split("\n")[0]

    # the workflow computes FORK_PULL_REQUEST true for a foreign head repo, false otherwise
    assert _fork_expr_value("pull_request", "someone/darkmem") is True
    assert _fork_expr_value("pull_request", "darkraise/darkmem") is False
    assert _fork_expr_value("push", "") is False

    # every job that targets the self-hosted runner is skipped for a foreign PR
    wf = yaml.safe_load((REPO / ".github/workflows/ci.yml").read_text())
    for name, job in wf["jobs"].items():
        runs_on = job.get("runs-on")
        if isinstance(runs_on, list) and "darkmem-linux" in runs_on:
            cond = str(job.get("if", ""))
            assert "head.repo.full_name == github.repository" in cond, name
            assert "github.event_name != 'pull_request'" in cond, name


# ------------------------------------------------------------------ A8


@pytest.mark.asyncio
async def test_a8_credentialed_localhost_3000_gets_no_cors_header_when_unset(client, auth_headers, monkeypatch):
    from app.config import settings

    assert settings.cors_origins == []
    r = await client.get(
        "/api/v1/auth/me", headers={**auth_headers, "Origin": "http://localhost:3000"}
    )
    assert "access-control-allow-origin" not in r.headers
    pre = await client.options(
        "/api/v1/auth/me",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert "access-control-allow-origin" not in pre.headers


# ------------------------------------------------------------------ A9 / A10

_SSH = {
    "name": "nas",
    "kind": "ssh",
    "enabled": True,
    "retention_keep": 30,
    "age_recipient": "age1qqqqexamplerecipient",
    "ssh": {
        "host": "192.0.2.10",
        "port": 22,
        "user": "backup",
        "remote_dir": "/srv/darkmem",
        "host_key": "192.0.2.10 ssh-ed25519 AAAAC3NzaC1lZDI1NTE5examplekey",
        "private_key": "-----BEGIN OPENSSH PRIVATE KEY-----\nexample\n",
    },
}


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value",
    [
        ("user", "-oProxyCommand=evil"),
        ("host", "-oProxyCommand=evil"),
        ("remote_dir", "/srv/a\nb"),
        ("remote_dir", "/srv/a\rb"),
    ],
)
async def test_a9_hostile_ssh_destination_is_refused_at_save(client, auth_headers, field, value):
    body = {"destinations": [{**_SSH, "ssh": {**_SSH["ssh"], field: value}}]}
    r = await client.put("/api/v1/config/backup-destinations", json=body, headers=auth_headers)
    assert r.status_code == 422, r.text
    got = await client.get("/api/v1/config/backup-destinations", headers=auth_headers)
    assert got.json()["destinations"] == []


@pytest.mark.asyncio
async def test_a9_a_clean_ssh_destination_is_still_saved(client, auth_headers):
    r = await client.put(
        "/api/v1/config/backup-destinations", json={"destinations": [_SSH]}, headers=auth_headers
    )
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_a10_masked_secret_with_changed_host_is_refused_until_reentered(client, auth_headers):
    ok = await client.put(
        "/api/v1/config/backup-destinations", json={"destinations": [_SSH]}, headers=auth_headers
    )
    assert ok.status_code == 200
    moved = {**_SSH, "ssh": {**_SSH["ssh"], "host": "203.0.113.9", "private_key": "***"}}
    r = await client.put(
        "/api/v1/config/backup-destinations", json={"destinations": [moved]}, headers=auth_headers
    )
    assert r.status_code == 422
    assert "private_key" in r.text
    again = {**_SSH, "ssh": {**_SSH["ssh"], "host": "203.0.113.9"}}
    r2 = await client.put(
        "/api/v1/config/backup-destinations", json={"destinations": [again]}, headers=auth_headers
    )
    assert r2.status_code == 200


@pytest.mark.asyncio
async def test_a10_masked_provider_key_with_changed_url_is_refused_until_reentered(client, auth_headers):
    base = {"api_kind": "openai", "base_url": "http://a.example/v1"}
    c = await client.post(
        "/api/v1/config/llm-providers",
        json={"name": "qa-prov", **base, "api_key": "secret-1"},
        headers=auth_headers,
    )
    assert c.status_code in (200, 201), c.text
    r = await client.put(
        "/api/v1/config/llm-providers/qa-prov",
        json={**base, "base_url": "http://b.example/v1", "api_key": "***"},
        headers=auth_headers,
    )
    assert r.status_code == 422
    assert "api_key" in r.text
    r2 = await client.put(
        "/api/v1/config/llm-providers/qa-prov",
        json={**base, "base_url": "http://b.example/v1", "api_key": "secret-2"},
        headers=auth_headers,
    )
    assert r2.status_code == 200, r2.text


# ------------------------------------------------------------------ A44


def test_a44_distribution_has_no_policy_surface():
    tab = (REPO / "frontend/src/features/settings/components/distribution-tab.tsx").read_text()
    tab = re.sub(r"/\*.*?\*/", "", tab, flags=re.S)
    tab = re.sub(r"(?m)^\s*//.*$", "", tab)
    for token in ("token_budget", "watch_enabled", "token budget", "watch", "policy", "switch", "number-input", "toggle", "slider", "checkbox"):
        assert token not in tab.lower(), token
    assert "Curb" not in tab and "curbed:" not in tab
    for mod in ("inject_watch", "inject_fill", "inject_block", "inject_journal"):
        assert not (BACKEND / "app/services" / f"{mod}.py").exists(), mod
        for f in _git_ls("backend/app", "backend/scripts"):
            if f.suffix == ".py":
                assert not re.search(rf"\b(import|from)\s+[\w.]*{mod}\b", _read(f)), (mod, f)
    from app.main import app

    for route in app.routes:
        path = getattr(route, "path", "")
        if path.startswith("/api/v1/distribution"):
            assert "policy" not in path, path
            assert "PUT" not in (getattr(route, "methods", set()) or set()), path


@pytest.mark.asyncio
async def test_a44_distribution_policy_route_is_gone_and_get_has_no_policy(client, auth_headers):
    put = await client.put("/api/v1/distribution/policy", json={"token_budget": 1}, headers=auth_headers)
    assert put.status_code in (404, 405)
    got = await client.get("/api/v1/distribution", headers=auth_headers)
    assert got.status_code == 200
    for key in ("policy", "watched", "refresh"):
        assert key not in got.json()


@pytest.mark.asyncio
async def test_a44_connect_script_still_resolves_an_adapter(session):
    from app.services.inject_adapters import resolve_adapter

    adapter = await resolve_adapter(session, "claude-code")
    assert adapter is not None


# ------------------------------------------------------------------ A45


def test_a45_context_boost_names_are_gone_from_code_benchlib_demo_and_ui():
    names = ("w_context_boost", "community_injection_enabled", "by_context_conflict")
    roots = ("backend/app", "backend/scripts", "frontend/src", "extension", "sdks")
    for f in _git_ls(*roots):
        if f.suffix not in {".py", ".ts", ".tsx", ".js", ".json", ".md", ".sh"}:
            continue
        if "acceptance" in f.name:
            continue
        text = _read(f)
        for n in names:
            assert n not in text, (n, str(f.relative_to(REPO)))


@pytest.mark.asyncio
async def test_a45_served_flags_carry_none_even_when_stored(client, auth_headers, session):
    from app.models.config import Config
    from sqlalchemy import select

    row = (await session.execute(select(Config).where(Config.key == "feature_flags"))).scalar_one_or_none()
    stored = {"w_context_boost": 0.5, "community_injection_enabled": True, "by_context_conflict": True}
    if row is None:
        session.add(Config(key="feature_flags", value=stored))
    else:
        row.value = {**(row.value or {}), **stored}
    await session.flush()
    from app.services.feature_flags import get_feature_flags_dict

    flags = await get_feature_flags_dict(session)
    for n in stored:
        assert n not in flags
    r = await client.get("/api/v1/config/feature-flags", headers=auth_headers)
    if r.status_code == 200:
        for n in stored:
            assert n not in r.text


# ------------------------------------------------------------------ A47


def test_a47_stated_expiry_and_last_commit_sha_have_no_readers_or_writers():
    allowed_expiry = {"backend/app/services/stated_expiry.py", "backend/app/services/pipeline.py"}
    for f in _git_ls("backend/app", "backend/scripts", "frontend/src"):
        rel = str(f.relative_to(REPO))
        if f.suffix not in {".py", ".ts", ".tsx"} or "migrations" in rel or "acceptance" in rel:
            continue
        text = _read(f)
        assert "last_commit_sha" not in text, rel
        if re.search(r"\bstated_expiry\b", text) and rel not in allowed_expiry:
            pytest.fail(f"stated_expiry referenced in {rel}")


@pytest.mark.asyncio
async def test_a47_columns_still_exist(session):
    from sqlalchemy import text

    rows = (
        await session.execute(
            text(
                "SELECT table_name, column_name FROM information_schema.columns "
                "WHERE (table_name='knowledge_triples' AND column_name='stated_expiry') "
                "OR (table_name='code_files' AND column_name='last_commit_sha')"
            )
        )
    ).all()
    assert sorted(tuple(r) for r in rows) == [
        ("code_files", "last_commit_sha"),
        ("knowledge_triples", "stated_expiry"),
    ]


def test_a47_expires_at_still_derived_from_a_stated_expiry():
    from datetime import datetime, timezone

    from app.services.stated_expiry import derive_stated_expiry

    ref = datetime(2026, 1, 1, tzinfo=timezone.utc)
    got = derive_stated_expiry("This reminder expires on 2026-03-15.", reference_time=ref)
    assert got is not None and (got.year, got.month) == (2026, 3) and got.day in (15, 16)


# ------------------------------------------------------------------ A48


def test_a48_lock_holds_no_pdf_library():
    lock = _read(BACKEND / "requirements.lock").lower()
    pyproject = _read(BACKEND / "pyproject.toml").lower()
    for lib in ("pdfplumber", "pdfminer", "pypdfium2"):
        assert lib not in lock, lib
        assert lib not in pyproject, lib


@pytest.mark.asyncio
async def test_a48_pdf_filing_answers_422(client, auth_headers):
    from app.main import app
    from tests.test_document_door import StubEmbedder

    previous = getattr(app.state, "llm", None)
    app.state.llm = StubEmbedder()
    try:
        r = await _put_pdf(client, auth_headers)
    finally:
        app.state.llm = previous
    assert r.status_code == 422, r.text


async def _put_pdf(client, auth_headers):
    r = await client.post(
        "/api/v1/documents",
        json={"project": "qa", "uri": "x/a.pdf", "content": "%PDF-1.4\n%binary", "title": "a"},
        headers=auth_headers,
    )
    return r


# ------------------------------------------------------------------ A50


def test_a50_ci_runs_extension_and_both_sdk_suites_and_numpy_is_declared():
    wf = yaml.safe_load((REPO / ".github/workflows/ci.yml").read_text())
    runs = []
    for job in wf["jobs"].values():
        for step in job.get("steps", []):
            if "run" in step:
                runs.append((step.get("working-directory", ""), step["run"]))
    assert any(wd == "extension" and "npm test" in r for wd, r in runs)
    assert any(wd == "sdks/python" and "pytest" in r for wd, r in runs)
    assert any(wd == "sdks/ts" and "npm test" in r for wd, r in runs)
    pyproject = _read(BACKEND / "pyproject.toml")
    assert re.search(r'"numpy[>=~<!]', pyproject)


# ------------------------------------------------------------------ A52


def test_a52_every_register_row_is_done_or_deferred_with_reason():
    path = REPO / "docs/dforge/registers/2026-11-20-audit-remaining.md"
    rows = [l for l in path.read_text().splitlines() if re.match(r"\|\s*\d+\s*\|", l)]
    assert len(rows) >= 200
    bad = []
    for line in rows:
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        n, state, note = cells[0], cells[4], "|".join(cells[5:]).strip()
        if state not in {"done", "deferred"} or not note:
            bad.append((n, state, note))
        elif state == "done":
            ok = re.search(r"\b[0-9a-f]{7,40}\b", note) or note.lower().startswith("not reproduced:")
            if not ok:
                bad.append((n, state, note))
    assert not bad, bad


# ------------------------------------------------------------------ A7

import asyncio
import threading


class _OneRowSession:
    def __init__(self, row):
        self._row = row

    async def execute(self, _stmt):
        await asyncio.sleep(0.01)

        class _R:
            def __init__(self, row):
                self._row = row

            def scalar_one_or_none(self):
                return self._row

        return _R(self._row)


@pytest.mark.asyncio
async def test_a7_twenty_concurrent_wrong_logins_verify_at_most_five_off_the_loop(monkeypatch):
    import bcrypt
    from httpx import ASGITransport, AsyncClient

    from app.api.auth import hash_password
    from app.database import get_session
    from app.main import app
    from app.models.config import Config

    loop_thread = threading.get_ident()
    seen: list[int] = []
    real = bcrypt.checkpw

    def counting(pw, hashed):
        seen.append(threading.get_ident())
        return real(pw, hashed)

    monkeypatch.setattr(bcrypt, "checkpw", counting)
    row = Config(key="admin_password_hash", value={"hash": hash_password("the-right-one")})

    async def stub():
        yield _OneRowSession(row)

    app.dependency_overrides[get_session] = stub
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            rs = await asyncio.gather(
                *(c.post("/api/v1/auth/login", json={"password": "wrong"}) for _ in range(20))
            )
    finally:
        app.dependency_overrides.clear()
    codes = [r.status_code for r in rs]
    assert 1 <= len(seen) <= 5, len(seen)
    assert all(t != loop_thread for t in seen)
    assert codes.count(401) == len(seen)
    assert codes.count(429) == 20 - len(seen)


# ------------------------------------------------------------------ A11

from datetime import datetime, timedelta, timezone

from tests.test_mcp_auth import door, mint_key  # noqa: F401,E402 - fixtures


async def _tools_list(client, credential):
    return await client.post(
        "/",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
        headers={"Authorization": f"Bearer {credential}"},
    )


@pytest.mark.asyncio
async def test_a11_second_keyed_call_verifies_no_bcrypt_and_a_revoked_key_is_refused(door, mint_key, monkeypatch):
    import bcrypt
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    from app.api.auth import create_access_token
    from app.database import get_session
    from app.main import app
    from tests.conftest import test_engine

    n = {"c": 0}
    real = bcrypt.checkpw

    def counting(pw, hashed):
        n["c"] += 1
        return real(pw, hashed)

    monkeypatch.setattr(bcrypt, "checkpw", counting)
    row_id, cred = await mint_key(scopes=["read"])
    assert (await _tools_list(door, cred)).status_code == 200
    assert n["c"] == 1
    assert (await _tools_list(door, cred)).status_code == 200
    assert n["c"] == 1, "second call within 60s must not run bcrypt"

    factory = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)

    async def real_session():
        async with factory() as s:
            yield s

    app.dependency_overrides[get_session] = real_session
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            r = await c.delete(
                f"/api/v1/api-keys/{row_id}",
                headers={"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"},
            )
    finally:
        app.dependency_overrides.clear()
    assert r.status_code == 204
    assert (await _tools_list(door, cred)).status_code == 401


@pytest.mark.asyncio
async def test_a11_an_expired_key_is_refused_on_its_next_call(door, mint_key):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.services import api_keys
    from tests.conftest import test_engine

    _id, cred = await mint_key(scopes=["read"], expires_at=datetime.now(timezone.utc) + timedelta(seconds=30))
    assert (await _tools_list(door, cred)).status_code == 200
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as s:
        assert await api_keys.authenticate(s, cred, now=datetime.now(timezone.utc) + timedelta(seconds=45)) is None


# ------------------------------------------------------------------ A12

_FAILURE = "00000000-0000-4000-8000-0000000000bb"


class _SpyLLM:
    def __init__(self):
        self.calls = []

    async def embed(self, *a, **k):
        self.calls.append("embed")
        return [[0.0]], "spy|1"

    async def chat_completion(self, *a, **k):
        self.calls.append("chat")
        return "{}"


@pytest.mark.asyncio
async def test_a12_read_only_refuses_reprocess_retry_and_three_mcp_tools_before_any_provider_call(
    client, auth_headers, monkeypatch
):
    from types import SimpleNamespace

    from app.api.mcp import server as mcp_server
    from app.config import settings
    from app.main import app

    spy = _SpyLLM()
    monkeypatch.setattr(app.state, "pipeline", SimpleNamespace(llm=spy), raising=False)
    monkeypatch.setattr(app.state, "llm", spy, raising=False)
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=spy))
    monkeypatch.setattr(settings, "read_only", True)

    for path in (
        "/api/v1/analytics/reprocess",
        "/api/v1/analytics/reprocess/stream",
        f"/api/v1/pipeline-failures/{_FAILURE}/retry",
        "/api/v1/pipeline-failures/retry-all",
    ):
        r = await client.post(path, headers=auth_headers)
        assert r.status_code == 403, (path, r.status_code)
        assert r.json()["error"]["code"] == "read_only", path

    calls = {
        "memory_reason": {"question": "anything"},
        "memory_overview": {"project": "default"},
        "document_search": {"query": "anything", "project": "default"},
    }
    for tool, args in calls.items():
        payload = json.loads(await getattr(mcp_server, tool)(**args))
        assert payload["status"] == "read_only", (tool, payload)
    assert spy.calls == []


@pytest.mark.asyncio
async def test_a12_the_same_routes_are_not_refused_outside_read_only(client, auth_headers):
    r = await client.post("/api/v1/pipeline-failures/retry-all", headers=auth_headers)
    assert r.status_code != 403 or r.json()["error"]["code"] != "read_only"


# ------------------------------------------------------------------ A19


@pytest.mark.asyncio
async def test_a19_saving_local_without_torch_is_422(client, auth_headers, session):
    from app.models.llm_config import LLMPurposeConfigRow
    from app.models.llm_provider import LLMProviderRow

    session.add(LLMProviderRow(name="qa-cls", api_kind="openai", base_url="https://api.example.invalid/v1"))
    await session.flush()
    session.add(LLMPurposeConfigRow(purpose="classification", model="m", provider_name="qa-cls"))
    await session.flush()
    r = await client.post(
        "/api/v1/config/llm", headers=auth_headers, json={"classification": {"classifier_kind": "local"}}
    )
    assert r.status_code == 422, r.text
    assert "torch" in r.text


@pytest.mark.asyncio
async def test_a19_health_flags_a_stored_local_row_without_torch(client, setup_database):
    from app.main import app
    from tests.test_classifier_kind import _clear_classification_row, _factory, _set_classifier_kind

    factory = _factory()
    previous = getattr(app.state, "llm", None)
    app.state.llm = None
    try:
        await _set_classifier_kind(factory, "local")
        h = await client.get("/health")
        assert h.status_code == 200
        assert h.json()["classifier_unavailable"] is True
        await _set_classifier_kind(factory, "llm")
        assert (await client.get("/health")).json()["classifier_unavailable"] is False
    finally:
        app.state.llm = previous
        await _clear_classification_row(factory)


# ------------------------------------------------------------------ A24


@pytest.mark.asyncio
async def test_a24_unqualified_contradiction_role_scan_tick_drains_nothing_and_journals_nothing(session):
    from sqlalchemy import text

    from tests.test_contradiction_scan import StubLLM, _enqueue, _fact, _run, _source

    for i in range(3):
        fid = await _fact(session, subject=f"qa-svc-{i}", obj="postgres", fact=f"qa-svc-{i} stores data in postgres")
        await _source(session, fid, f"qa-sess-{i}")
        for _ in range(3):
            await _enqueue(session, fid)

    async def counts():
        pending = (await session.execute(text("SELECT count(*) FROM events WHERE event_type='sources_changed'"))).scalar_one()
        total = (await session.execute(text("SELECT count(*) FROM events"))).scalar_one()
        cfg = (await session.execute(text("SELECT count(*) FROM config WHERE key='contradiction_scan_state'"))).scalar_one()
        return pending, total, cfg

    before = await counts()
    llm = StubLLM([])
    outcome = await _run(session, llm)
    after = await counts()
    assert after == before, "the tick changed events or the watermark row"
    assert llm.calls == []
    assert outcome.events_scanned == 0
    assert outcome.watermark_advanced is False
    scanned = (await session.execute(text("SELECT count(*) FROM events WHERE event_type='contradiction_scanned'"))).scalar_one()
    assert scanned == 0


# ------------------------------------------------------------------ A27

import uuid


@pytest.fixture
def _stub_embedder_for_documents():
    from app.main import app
    from tests.test_document_door import FINGERPRINT, StubEmbedder
    from app.services.embedder_registry import embedder_registry

    embedder_registry.forget(FINGERPRINT)
    previous = getattr(app.state, "llm", None)
    app.state.llm = StubEmbedder()
    yield
    app.state.llm = previous
    embedder_registry.forget(FINGERPRINT)


async def _put_doc(client, auth_headers, content, uri="qa/a.md"):
    r = await client.post(
        "/api/v1/documents", json={"project": "qa27", "uri": uri, "content": content}, headers=auth_headers
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["document_id"]


async def _set_history(session, doc_id, ages):
    from sqlalchemy import text

    await session.execute(text("DELETE FROM document_revisions WHERE document_id = CAST(:d AS uuid)"), {"d": doc_id})
    ids = []
    n = len(ages)
    for pos, age in enumerate(ages):
        rid = str(uuid.uuid4())
        ids.append(rid)
        await session.execute(
            text(
                "INSERT INTO document_revisions (id, document_id, content, content_hash, created_at) "
                "VALUES (CAST(:i AS uuid), CAST(:d AS uuid), :c, md5(:c), now() - make_interval(days => :age) - make_interval(secs => :back))"
            ),
            {"i": rid, "d": doc_id, "c": f"old {pos}", "age": age, "back": n - pos},
        )
    return ids


async def _live_ids(session, doc_id):
    from sqlalchemy import text

    rows = await session.execute(
        text("SELECT CAST(id AS text) FROM document_revisions WHERE document_id = CAST(:d AS uuid) ORDER BY created_at, id"),
        {"d": doc_id},
    )
    return [r[0] for r in rows]


@pytest.mark.asyncio
async def test_a27_prune_removes_exactly_the_old_beyond_fifty_and_journals_first(
    client, auth_headers, session, _stub_embedder_for_documents
):
    from sqlalchemy import text

    doc = await _put_doc(client, auth_headers, "# A\n\nFirst.\n")
    other = await _put_doc(client, auth_headers, "# B\n\nFirst.\n", uri="qa/b.md")
    # 15 old (100d), 5 young-but-beyond-50 cannot exist without 50 newer: 15 old + 5 mid-age + 45 newest
    ages = [100] * 15 + [10] * 50
    ids = await _set_history(session, doc, ages)
    other_ids = await _set_history(session, other, [100] * 70)
    before_other = await _live_ids(session, other)

    r = await client.post(
        "/api/v1/documents", json={"project": "qa27", "uri": "qa/a.md", "content": "# A\n\nSecond.\n"}, headers=auth_headers
    )
    assert r.status_code in (200, 201)
    live = await _live_ids(session, doc)
    # the 15 old ones are beyond the newest 50 (50 young + new one => 51 newer) and older than 90 days
    assert set(ids[:15]).isdisjoint(live)
    assert set(ids[15:]) <= set(live)
    assert len(live) == 51
    assert await _live_ids(session, other) == before_other, "another document's revisions were touched"
    events = (
        await session.execute(
            text("SELECT payload FROM events WHERE event_type='document_revisions_pruned' AND object_id=CAST(:d AS uuid)"),
            {"d": doc},
        )
    ).all()
    assert [e[0] for e in events] == [{"pruned": 15}]


@pytest.mark.asyncio
async def test_a27_old_revisions_inside_the_newest_fifty_stay(client, auth_headers, session, _stub_embedder_for_documents):
    doc = await _put_doc(client, auth_headers, "# A\n\nFirst.\n")
    ids = await _set_history(session, doc, [400] * 30)
    r = await client.post(
        "/api/v1/documents", json={"project": "qa27", "uri": "qa/a.md", "content": "# A\n\nThird.\n"}, headers=auth_headers
    )
    assert r.status_code in (200, 201)
    assert set(ids) <= set(await _live_ids(session, doc))


@pytest.mark.asyncio
async def test_a27_a_prune_whose_journal_row_does_not_land_is_skipped_and_the_put_succeeds(
    client, auth_headers, session, monkeypatch, _stub_embedder_for_documents
):
    import app.services.document_ingest as ingest

    real = ingest.record_event

    async def refuse(session_, *, event_type, **kw):
        if event_type == "document_revisions_pruned":
            return False
        return await real(session_, event_type=event_type, **kw)

    monkeypatch.setattr(ingest, "record_event", refuse)
    doc = await _put_doc(client, auth_headers, "# A\n\nFirst.\n")
    await _set_history(session, doc, [100] * 15 + [10] * 50)
    r = await client.post(
        "/api/v1/documents", json={"project": "qa27", "uri": "qa/a.md", "content": "# A\n\nSecond.\n"}, headers=auth_headers
    )
    assert r.status_code in (200, 201), r.text
    assert len(await _live_ids(session, doc)) == 66


@pytest.mark.asyncio
async def test_a27_before_cursor_naming_a_pruned_revision_answers_404(
    client, auth_headers, session, _stub_embedder_for_documents
):
    doc = await _put_doc(client, auth_headers, "# A\n\nFirst.\n")
    ids = await _set_history(session, doc, [100] * 15 + [10] * 50)
    await client.post(
        "/api/v1/documents", json={"project": "qa27", "uri": "qa/a.md", "content": "# A\n\nSecond.\n"}, headers=auth_headers
    )
    assert ids[0] not in await _live_ids(session, doc)
    r = await client.get(f"/api/v1/documents/{doc}/revisions", params={"before": ids[0]}, headers=auth_headers)
    assert r.status_code == 404


# ------------------------------------------------------------------ A31 / A32


@pytest.mark.asyncio
async def test_a31_a_boot_whose_llm_setup_raises_still_reconciles_partitions_and_health_says_failed_at_boot(
    setup_database, client, monkeypatch
):
    from tests.test_boot_reconciliation import _committed_factory, _drop_far_partitions, _event_children
    from tests.test_health import initialised
    from tests.test_boot_reconciliation import booted

    factory = _committed_factory()
    months = await _drop_far_partitions(factory)
    assert not set(months) <= await _event_children(factory)
    async with initialised():
        async with booted(monkeypatch, llm_fails=True):
            r = await client.get("/health")
            assert r.status_code == 200
            assert r.json()["pipeline_state"] == "failed_at_boot"
            assert set(months) <= await _event_children(factory)


@pytest.mark.asyncio
async def test_a32_partitions_three_months_ahead_with_pipeline_failure_cleanup_disabled(setup_database):
    from sqlalchemy import delete, select

    from app.models.config import Config
    from app.services.job_registry import Job, JobConfig, JobRegistry
    from tests.test_boot_reconciliation import _committed_factory, _drop_far_partitions, _event_children

    factory = _committed_factory()
    months = await _drop_far_partitions(factory)
    slept: list[float] = []
    parked = asyncio.Event()

    async def tick(seconds):
        slept.append(seconds)
        if len(slept) > 1:
            await parked.wait()

    async def must_not_run():
        raise AssertionError("the disabled cleanup ran")

    registry = JobRegistry(factory, maintenance_sleep=tick)
    registry.register(
        Job(
            key="pipeline_failure_cleanup", display_name="c", description="", default_cron="0 * * * *",
            min_interval_seconds=60, runner=must_not_run,
        )
    )
    async with factory() as s:
        existed = (await s.execute(select(Config.key).where(Config.key == "job:pipeline_failure_cleanup"))).scalar_one_or_none() is not None
    await registry.save_config(
        "pipeline_failure_cleanup", JobConfig(enabled=False, cron="0 * * * *", min_interval_seconds=60, config={})
    )
    try:
        await registry.start_all()
        for _ in range(100):
            if set(months) <= await _event_children(factory):
                break
            await asyncio.sleep(0.05)
        assert set(months) <= await _event_children(factory)
    finally:
        await registry.stop_all()
        if not existed:
            async with factory() as s:
                await s.execute(delete(Config).where(Config.key == "job:pipeline_failure_cleanup"))
                await s.commit()


# ------------------------------------------------------------------ A49

import os
import shutil
import tempfile


def _eval_gha(expr: str, ctx: dict) -> bool:
    py = " ".join(expr.split())
    py = py.replace("always()", "True").replace("&&", " and ").replace("||", " or ")
    for key, val in ctx.items():
        py = py.replace(key, repr(val))
    py = py.replace("==", " == ")
    return bool(eval(py, {"__builtins__": {}}))  # noqa: S307 - the expression is our own workflow's


@pytest.mark.parametrize("tag_result", ["cancelled", "failure", "skipped"])
def test_a49_a_cancelled_or_failed_tag_job_on_master_creates_no_release(tag_result):
    wf = yaml.safe_load((REPO / ".github/workflows/release.yml").read_text())
    jobs = wf["jobs"]
    cond = str(jobs["github-release"]["if"])
    ctx = {
        "needs.publish.result": "success",
        "needs.tag.result": tag_result,
        "github.ref_type": "branch",
    }
    assert _eval_gha(cond, ctx) is False
    ok = {**ctx, "needs.tag.result": "success"}
    assert _eval_gha(cond, ok) is True
    # a hand-cut tag run legitimately skips the tag job
    assert _eval_gha(cond, {**ctx, "needs.tag.result": "skipped", "github.ref_type": "tag"}) is True
    # and the tag job itself is not forced by always()
    assert "always()" not in str(jobs["tag"].get("if", ""))
    assert "publish" in jobs["tag"]["needs"]


def test_a49_a_dirty_tree_is_not_tagged_with_the_head_sha(tmp_path):
    repo = tmp_path / "r"
    repo.mkdir()
    env = {**os.environ, "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t"}
    def run(*a):
        return subprocess.run(a, cwd=repo, env=env, capture_output=True, text=True, check=True).stdout
    run("git", "init", "-q")
    (repo / "f.txt").write_text("one\n")
    run("git", "add", "f.txt")
    run("git", "commit", "-q", "-m", "c")
    head = run("git", "rev-parse", "--short", "HEAD").strip()
    head_lines = "\n".join((REPO / "scripts/build-push.sh").read_text().splitlines()[:14])
    probe = tmp_path / "probe.sh"
    probe.write_text(head_lines + '\necho "SHA=$GIT_SHA"\n')

    def sha():
        out = subprocess.run(["bash", str(probe)], cwd=repo, capture_output=True, text=True, env=env).stdout
        return re.search(r"SHA=(\S+)", out).group(1)

    assert sha() == head
    (repo / "f.txt").write_text("two\n")
    assert sha() == f"{head}-dirty"


def _run_backup(tmp_path, dump_text: str, keep: int):
    dest = tmp_path / "dumps"
    dest.mkdir()
    import gzip
    import time

    old = []
    for i in range(3):
        p = dest / f"darkmem-2020010{i}-000000.sql.gz"
        with gzip.open(p, "wt") as f:
            f.write("-- old real dump\n")
        t = time.time() - 1000 * (10 - i)
        os.utime(p, (t, t))
        old.append(p)
    shim = tmp_path / "shim.sh"
    dump = tmp_path / "dump.sql"
    dump.write_text(dump_text)
    shim.write_text(f"#!/usr/bin/env bash\ncat {dump}\n")
    env = {**os.environ, "COMPOSE_CMD": f"bash {shim}", "BACKUP_KEEP": str(keep)}
    r = subprocess.run(["bash", str(REPO / "scripts/backup.sh"), str(dest)], env=env, capture_output=True, text=True, timeout=60)
    return r, dest, old


def test_a49_a_dump_of_the_wrong_database_triggers_no_prune(tmp_path):
    wrong = "-- PostgreSQL database dump\nCREATE TABLE public.other (id int);\n-- PostgreSQL database dump complete\n"
    r, dest, old = _run_backup(tmp_path, wrong, keep=1)
    assert r.returncode != 0
    assert all(p.exists() for p in old), r.stderr
    assert list(dest.glob("*.suspect"))


def test_a49_a_right_dump_still_prunes(tmp_path):
    right = (
        "-- PostgreSQL database dump\nCREATE TABLE public.memories (\n id int\n);\n"
        "COPY public.alembic_version (version_num) FROM stdin;\n0001\n\\.\n-- PostgreSQL database dump complete\n"
    )
    r, dest, old = _run_backup(tmp_path, right, keep=2)
    assert r.returncode == 0, r.stderr
    assert len(list(dest.glob("darkmem-*.sql.gz"))) == 2


def test_a49_the_restore_cycle_exits_nonzero_on_a_migrate_failure_unless_an_older_baseline():
    text = (REPO / "scripts/worker/restore-cycle.sh").read_text()
    m = re.search(
        r'if ! \$COMPOSE run .*?alembic upgrade head.*?; then\n(?P<body>.*?)\nfi\n', text, flags=re.S
    )
    assert m, "the migrate step is not guarded"
    body = m.group("body")
    cond = re.search(r'if (\[ .*? \]); then\n(?P<then>.*?)\n\s*fi\n(?P<after>.*)', body, flags=re.S)
    assert cond, body
    assert '"$STAMPED" != "$IMAGE_SHA"' in cond.group(1)
    assert re.search(r"\bexit 0\b", cond.group("then"))
    assert re.search(r"\bexit 1\b", cond.group("after"))
    assert not re.search(r"\bexit 0\b", cond.group("after"))


# ------------------------------------------------------------------ A14 / A35

from app.models.code import CodeEdge, CodeFile, CodeSymbol, Repository


async def _qa_repo(session, name):
    repo = Repository(name=name)
    session.add(repo)
    await session.flush()
    return repo


async def _qa_symbol(session, repo, path, name, *, kind="function", parent=None):
    f = (
        await session.execute(
            __import__("sqlalchemy").select(CodeFile).where(CodeFile.repo_id == repo.id, CodeFile.file_path == path)
        )
    ).scalar_one_or_none()
    if f is None:
        f = CodeFile(id=uuid.uuid4(), repo_id=repo.id, file_path=path, language="python", content_hash=f"h-{uuid.uuid4()}")
        session.add(f)
        await session.flush()
    sym = CodeSymbol(
        id=uuid.uuid4(), file_id=f.id, name=name, kind=kind, line_start=1, line_end=2,
        source_code=f"def {name}(): ...", parent_symbol_id=parent.id if parent is not None else None,
    )
    session.add(sym)
    await session.flush()
    return sym


async def _mcp(client, tool, args):
    r = await client.post(
        "/", json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": tool, "arguments": args}}
    )
    assert r.status_code == 200, r.text
    return r.json()["result"]


@pytest.mark.asyncio
async def test_a14_code_search_with_no_embedder_returns_keyword_rows_marked_degraded(mcp_http_client, session, monkeypatch):
    import app.api.mcp.server as mcp_server

    monkeypatch.setattr(mcp_server, "_pipeline", None)
    repo = await _qa_repo(session, f"qa14-{uuid.uuid4().hex[:6]}")
    await _qa_symbol(session, repo, "cfg.py", "load_settings_blob")
    result = await _mcp(mcp_http_client, "code_search", {"query": "load_settings_blob", "repo_name": repo.name})
    assert not result.get("isError"), result
    reply = json.loads(result["content"][0]["text"])
    assert reply["degraded"] is True
    assert [r["symbol_name"] for r in reply["results"]] == ["load_settings_blob"]


@pytest.mark.asyncio
async def test_a35_code_symbol_and_blast_radius_answer_and_honour_the_repository(mcp_http_client, session):
    a = await _qa_repo(session, f"qa35a-{uuid.uuid4().hex[:6]}")
    b = await _qa_repo(session, f"qa35b-{uuid.uuid4().hex[:6]}")
    await _qa_symbol(session, a, "m.py", "shared_name")
    await _qa_symbol(session, b, "m.py", "shared_name")
    await _qa_symbol(session, b, "other.py", "only_in_b")

    ra = await _mcp(mcp_http_client, "code_symbol", {"name": "shared_name", "repo_name": a.name})
    rows = json.loads(ra["content"][0]["text"])
    assert not ra.get("isError") and len(rows) == 1 and rows[0]["name"] == "shared_name"
    rb = await _mcp(mcp_http_client, "code_symbol", {"name": "only_in_b", "repo_name": a.name})
    assert rb.get("isError") is True, "a symbol of repository b must not answer under repository a"

    blast = await _mcp(mcp_http_client, "code_blast_radius", {"symbol_name": "shared_name", "repo_name": a.name})
    assert not blast.get("isError"), blast


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "tool,args",
    [("code_symbol", {"name": "h"}), ("code_file_symbols", {"file_path": "x.py"}), ("code_context", {"symbol_name": "h"}),
     ("code_dependencies", {}), ("code_processes", {}), ("code_communities", {}), ("code_blast_radius", {"symbol_name": "h"})],
)
async def test_a35_an_ambiguous_repository_name_lists_candidates(mcp_http_client, session, tool, args):
    name = f"qa35-{uuid.uuid4().hex[:6]}"
    one = await _qa_repo(session, name)
    two = await _qa_repo(session, name)
    for r in (one, two):
        await _qa_symbol(session, r, "x.py", "h")
    result = await _mcp(mcp_http_client, tool, {**args, "repo_name": name})
    assert not result.get("isError"), result
    env = json.loads(result["content"][0]["text"])
    assert env["status"] == "ambiguous"
    assert {c["id"] for c in env["candidates"]} == {str(one.id), str(two.id)}
