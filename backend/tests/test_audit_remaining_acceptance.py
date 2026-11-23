"""Acceptance tests for the audit-remaining spec, written from its acceptance text."""
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
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


# ------------------------------------------------------------------ A17


@pytest.mark.asyncio
async def test_a17_memory_graph_predicates_plan_as_gin_index_scans(session):
    from sqlalchemy import event, text

    from app.repositories.graph import PostgresGraphRepository

    captured: list[tuple[str, tuple]] = []

    def grab(conn, cursor, statement, parameters, context, executemany):
        if "memory_ids" in statement and statement.lstrip().upper().startswith(("UPDATE ENTITIES", "UPDATE ENTITY_RELATIONS")):
            captured.append((statement, tuple(parameters) if not isinstance(parameters, dict) else parameters))

    from tests.conftest import test_engine

    event.listen(test_engine.sync_engine, "before_cursor_execute", grab)
    try:
        await PostgresGraphRepository(session).delete_by_memory_id(str(uuid.uuid4()))
    finally:
        event.remove(test_engine.sync_engine, "before_cursor_execute", grab)
    assert captured, "delete_by_memory_id issued no memory_ids statement"

    # With sequential scans disabled the planner can only avoid one when the
    # predicate matches the GIN index; the `:mid = ANY(memory_ids)` form cannot.
    await session.execute(text("SET LOCAL enable_seqscan = off"))
    raw = await session.connection()
    for statement, params in captured:
        rows = (await raw.exec_driver_sql("EXPLAIN " + statement, params)).all()
        plan = "\n".join(r[0] for r in rows)
        assert "Seq Scan" not in plan, plan
        assert re.search(r"(Bitmap Index Scan|Index Scan).*memory_ids", plan), plan

    # control: the old shape cannot use the index, so the assertion above discriminates
    rows = (
        await raw.exec_driver_sql(
            "EXPLAIN SELECT id FROM entities WHERE CAST('00000000-0000-4000-8000-000000000001' AS uuid) = ANY(memory_ids)"
        )
    ).all()
    assert "Seq Scan" in "\n".join(r[0] for r in rows)


# ------------------------------------------------------------------ A15


@pytest.mark.asyncio
async def test_a15_two_concurrent_supersessions_of_one_candidate_leave_one_pointer_and_one_event(setup_database):
    from datetime import timedelta

    from sqlalchemy import text
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from tests.conftest import test_engine
    from tests.test_supersession import _detect, _mem

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    now = datetime.now(timezone.utc)
    project = f"qa15-{uuid.uuid4().hex[:8]}"
    candidate = _mem(project=project, created_at=now - timedelta(days=1))
    first = _mem(project=project, technologies=[], created_at=now)
    second = _mem(project=project, technologies=[], created_at=now)
    async with factory() as seed:
        seed.add_all([candidate, first, second])
        await seed.commit()
    try:
        async def one(new):
            async with factory() as s:
                await _detect(s, new, now=now)
                await s.commit()

        await asyncio.wait_for(asyncio.gather(one(first), one(second)), 20)
        async with factory() as check:
            row = (
                await check.execute(
                    text("SELECT status, superseded_by FROM memories WHERE id = CAST(:i AS uuid)"), {"i": str(candidate.id)}
                )
            ).one()
            n = (
                await check.execute(
                    text("SELECT count(*) FROM events WHERE event_type='superseded' AND object_id = CAST(:i AS uuid)"),
                    {"i": str(candidate.id)},
                )
            ).scalar_one()
        assert row[0] == "superseded"
        assert row[1] in (first.id, second.id)
        assert n == 1
    finally:
        async with factory() as cleanup:
            await cleanup.execute(
                text("DELETE FROM memories WHERE id = ANY(CAST(:ids AS uuid[]))"),
                {"ids": [str(candidate.id), str(first.id), str(second.id)]},
            )
            await cleanup.commit()


# ------------------------------------------------------------------ A30


@pytest.fixture
def _qa30_cleanup():
    yield


async def _qa30_registry(factory, key, *, min_interval, runner):
    from app.services.job_registry import Job, JobRegistry

    registry = JobRegistry(factory)
    registry.register(
        Job(key=key, display_name=key, description="", default_cron="0 3 * * *", min_interval_seconds=min_interval, runner=runner)
    )
    return registry


@pytest.mark.asyncio
async def test_a30_a_raised_min_interval_in_code_applies_to_an_existing_install(setup_database):
    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.models.config import Config
    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    key = f"qa30-floor-{uuid.uuid4().hex[:6]}"
    async with factory() as s:
        s.add(Config(key=f"job:{key}", value={"enabled": True, "cron": "* * * * *", "min_interval_seconds": 30, "config": {}}))
        await s.commit()
    try:
        async def runner():
            return None

        registry = await _qa30_registry(factory, key, min_interval=600, runner=runner)
        cfg = await registry.load_config(key)
        assert cfg.min_interval_seconds == 600
        assert cfg.cron == "* * * * *"
    finally:
        async with factory() as s:
            await s.execute(delete(Config).where(Config.key == f"job:{key}"))
            await s.commit()


@pytest.mark.asyncio
async def test_a30_disabling_a_job_answers_while_the_job_runs(setup_database):
    from sqlalchemy import delete
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.models.config import Config
    from app.models.job_run import JobRun
    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    key = f"qa30-run-{uuid.uuid4().hex[:6]}"
    started = asyncio.Event()
    release = asyncio.Event()

    async def runner():
        started.set()
        await release.wait()

    registry = await _qa30_registry(factory, key, min_interval=60, runner=runner)
    task = asyncio.create_task(registry.trigger(key))
    try:
        await asyncio.wait_for(started.wait(), 5)
        cfg = await asyncio.wait_for(registry.update_config(key, enabled=False), 5)
        assert cfg.enabled is False
        again = await asyncio.wait_for(registry.load_config(key), 5)
        assert again.enabled is False
    finally:
        release.set()
        await asyncio.wait_for(task, 10)
        async with factory() as s:
            await s.execute(delete(Config).where(Config.key == f"job:{key}"))
            await s.execute(delete(JobRun).where(JobRun.job_key == key))
            await s.commit()


@pytest.mark.asyncio
async def test_a30_a_job_whose_only_run_is_older_than_5000_newer_runs_still_shows_its_last_run(setup_database):
    from sqlalchemy import delete, text
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.models.job_run import JobRun
    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    old_key = f"qa30-old-{uuid.uuid4().hex[:6]}"
    other = f"qa30-busy-{uuid.uuid4().hex[:6]}"

    async def runner():
        return None

    registry = await _qa30_registry(factory, old_key, min_interval=60, runner=runner)
    async with factory() as s:
        await s.execute(
            text(
                "INSERT INTO job_runs (job_key, outcome, started_at, duration_seconds) "
                "VALUES (:k, 'ok', now() - interval '30 days', 1.0)"
            ),
            {"k": old_key},
        )
        await s.execute(
            text(
                "INSERT INTO job_runs (job_key, outcome, started_at, duration_seconds) "
                "SELECT :o, 'ok', now() - make_interval(secs => g), 1.0 FROM generate_series(1, 5200) g"
            ),
            {"o": other},
        )
        await s.commit()
    try:
        cfg = await registry.load_config(old_key)
        assert cfg.last_status == "ok"
        assert cfg.last_run_at is not None
        listed = {r["key"]: r for r in await registry.list_with_config()}
        row = listed[old_key]
        assert row["last_status"] == "ok"
        assert row["last_run_at"] is not None
    finally:
        async with factory() as s:
            await s.execute(delete(JobRun).where(JobRun.job_key.in_([old_key, other])))
            await s.commit()


# ------------------------------------------------------------------ A29


async def _asgi(app, method, path, body, headers):
    """Call the ASGI app directly, running `on_start` when the response head is sent."""
    raw = json.dumps(body).encode()
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1", "method": method, "path": path,
        "raw_path": path.encode(), "query_string": b"", "scheme": "http", "server": ("test", 80),
        "client": ("127.0.0.1", 1234), "root_path": "",
        "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(raw)).encode())]
        + [(k.lower().encode(), v.encode()) for k, v in headers.items()],
    }
    sent_body = False
    events = []

    async def receive():
        nonlocal sent_body
        if not sent_body:
            sent_body = True
            return {"type": "http.request", "body": raw, "more_body": False}
        await asyncio.sleep(3600)

    status = {}

    async def send(message):
        if message["type"] == "http.response.start":
            status["code"] = message["status"]
            await _asgi.on_start()
        events.append(message["type"])

    await app(scope, receive, send)
    return status["code"]


@pytest.mark.asyncio
async def test_a29_change_password_and_a_config_save_are_durable_before_the_response_is_sent(setup_database):
    from sqlalchemy import delete, select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.api.auth import create_access_token, hash_password, verify_password
    from app.main import app
    from app.models.config import Config
    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as s:
        before = (await s.execute(select(Config).where(Config.key == "admin_password_hash"))).scalar_one_or_none()
        saved_before = dict(before.value) if before else None
        flags_before = (await s.execute(select(Config).where(Config.key == "feature_flags"))).scalar_one_or_none()
        flags_saved = dict(flags_before.value) if flags_before else None
        if before is None:
            s.add(Config(key="admin_password_hash", value={"hash": hash_password("old-pass-123456")}))
        else:
            before.value = {"hash": hash_password("old-pass-123456")}
        await s.commit()
    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}
    try:
        seen = {}

        async def probe_password():
            async with factory() as s:
                row = (await s.execute(select(Config).where(Config.key == "admin_password_hash"))).scalar_one()
            seen["pw"] = verify_password("new-pass-123456", row.value["hash"])

        _asgi.on_start = probe_password
        code = await _asgi(app, "POST", "/api/v1/auth/change-password",
                           {"current_password": "old-pass-123456", "new_password": "new-pass-123456"}, headers)
        assert code == 200
        assert seen["pw"] is True, "the new password was not committed when the response head was sent"

        headers = {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}

        async def probe_flags():
            async with factory() as s:
                row = (await s.execute(select(Config).where(Config.key == "feature_flags"))).scalar_one_or_none()
            seen["flag"] = row.value.get("confidence_rank_gamma") if row else None

        _asgi.on_start = probe_flags
        code = await _asgi(app, "PUT", "/api/v1/config/feature-flags", {"confidence_rank_gamma": 0.123}, headers)
        assert code == 200
        assert seen["flag"] == 0.123, "the config save was not committed when the response head was sent"
    finally:
        async with factory() as s:
            await s.execute(delete(Config).where(Config.key.in_(["admin_password_hash", "admin_password_changed_at", "feature_flags"])))
            if saved_before is not None:
                s.add(Config(key="admin_password_hash", value=saved_before))
            if flags_saved is not None:
                s.add(Config(key="feature_flags", value=flags_saved))
            await s.commit()


@pytest.mark.asyncio
async def test_a29_two_concurrent_saves_of_one_config_row_both_survive(setup_database):
    from sqlalchemy import delete, select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.models.config import Config
    from app.services.config import patch_config_row
    from tests.conftest import test_engine

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    key = f"qa29-{uuid.uuid4().hex[:6]}"
    try:
        async def save(name):
            async with factory() as s:
                await patch_config_row(s, key, lambda cur: {**cur, name: True})

        await asyncio.wait_for(asyncio.gather(*(save(f"k{i}") for i in range(8))), 20)
        async with factory() as s:
            row = (await s.execute(select(Config).where(Config.key == key))).scalar_one()
        assert set(row.value) == {f"k{i}" for i in range(8)}
    finally:
        async with factory() as s:
            await s.execute(delete(Config).where(Config.key == key))
            await s.commit()


def test_a29_only_the_two_streaming_routes_use_request_scoped_twins_and_no_other_route_does():
    from fastapi.routing import APIRoute
    from starlette.responses import StreamingResponse
    import inspect

    from app.main import app

    def walk(dep):
        for d in dep.dependencies:
            yield d.call
            yield from walk(d)

    scoped = set()
    for route in app.routes:
        if not isinstance(route, APIRoute):
            continue
        names = {getattr(c, "__name__", "") for c in walk(route.dependant)} | {getattr(route.endpoint, "__name__", "")}
        if any(n.endswith("_for_stream") for n in names if n != getattr(route.endpoint, "__name__", "")):
            for m in route.methods:
                scoped.add((m, route.path))
    assert scoped == {("POST", "/api/v1/chat/completions"), ("POST", "/api/v1/analytics/reprocess/stream")}
    # every handler annotated as returning a streaming body is one of the two
    for route in app.routes:
        if isinstance(route, APIRoute):
            ann = inspect.signature(route.endpoint).return_annotation
            if ann is StreamingResponse or "StreamingResponse" in str(ann) or route.response_class is StreamingResponse:
                assert ("POST", route.path) in scoped, route.path


# ------------------------------------------------------------------ A25


class _FailingEmbedder:
    def __init__(self, fingerprint):
        self.fingerprint = fingerprint

    async def embed_batch_chunked(self, texts, chunk_size, concurrency):
        raise RuntimeError("embedder is down")

    async def embed(self, value):
        raise RuntimeError("embedder is down")

    def llm_fingerprint(self):
        return self.fingerprint


@pytest.mark.asyncio
async def test_a25_a_block_edit_whose_embed_fails_answers_success_with_zero_embedded_and_no_stale_vector(
    client, auth_headers, session, _stub_embedder_for_documents
):
    from sqlalchemy import text

    from app.main import app
    from app.services.embedder_registry import child_table
    from tests.test_document_door import FINGERPRINT

    doc = await _put_doc(client, auth_headers, "# T\n\nalpha paragraph\n", uri="qa25/a.md")
    got = await client.get(f"/api/v1/documents/{doc}", headers=auth_headers)
    para = next(b for b in got.json()["blocks"] if b["text"] == "alpha paragraph")
    table = child_table("block_embeddings", FINGERPRINT)

    async def vector_count():
        return (
            await session.execute(
                text(f"SELECT count(*) FROM {table} WHERE block_id = CAST(:b AS uuid)"), {"b": para["block_id"]}
            )
        ).scalar_one()

    assert await vector_count() == 1
    good = app.state.llm
    app.state.llm = _FailingEmbedder(FINGERPRINT)
    try:
        r = await client.patch(
            f"/api/v1/documents/{doc}/blocks/{para['block_id']}", json={"text": "beta paragraph"}, headers=auth_headers
        )
    finally:
        app.state.llm = good
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["blocks_embedded"] == 0
    assert await vector_count() == 0, "the edited block still has the vector of its old text"


# ------------------------------------------------------------------ A28


@pytest.mark.asyncio
async def test_a28_unchanged_repush_makes_no_embed_call_and_a_refile_embeds_only_changed_blocks(
    client, auth_headers, session
):
    from app.main import app
    from app.services.embedder_registry import embedder_registry
    from tests.test_document_door import FINGERPRINT, StubEmbedder

    class Counting(StubEmbedder):
        def __init__(self):
            super().__init__()
            self.single = 0

        async def embed(self, value):
            self.single += 1
            return await super().embed(value)

    embedder_registry.forget(FINGERPRINT)
    llm = Counting()
    previous = getattr(app.state, "llm", None)
    app.state.llm = llm
    try:
        v1 = "# Title\n\nFirst paragraph here.\n\nSecond paragraph here.\n"
        await _put_doc(client, auth_headers, v1, uri="qa28/a.md")
        embedded_first = sorted(t for batch in llm.batches for t in batch)
        assert embedded_first, "the first filing embedded nothing"

        before_batches, before_single = len(llm.batches), llm.single
        await _put_doc(client, auth_headers, v1, uri="qa28/a.md")
        assert len(llm.batches) == before_batches
        assert llm.single == before_single, "an unchanged re-push spent an embed call"

        v2 = "# Title\n\nFirst paragraph here.\n\nSecond paragraph CHANGED.\n"
        await _put_doc(client, auth_headers, v2, uri="qa28/a.md")
        new_texts = [t for batch in llm.batches[before_batches:] for t in batch]
        assert new_texts == ["Second paragraph CHANGED."] or all("CHANGED" in t for t in new_texts), new_texts
        assert new_texts
    finally:
        app.state.llm = previous
        embedder_registry.forget(FINGERPRINT)


# ------------------------------------------------------------------ A22


@pytest.mark.asyncio
async def test_a22_a_hygiene_action_whose_journal_write_fails_commits_nothing(client, auth_headers, session, monkeypatch):
    from sqlalchemy import text

    from app.models.memory import Memory
    from app.services import hygiene_queue

    project = f"qa22-{uuid.uuid4().hex[:6]}"
    now = datetime.now(timezone.utc)
    older = Memory(id=uuid.uuid4(), content="old truth", source="test", project=project, status="active", importance=0.5,
                   metadata_={}, created_at=now - timedelta(days=2))
    newer = Memory(id=uuid.uuid4(), content="new truth", source="test", project=project, status="active", importance=0.5,
                   metadata_={}, created_at=now - timedelta(days=1))
    session.add_all([older, newer])
    await session.flush()

    async def refuse(*a, **k):
        return False

    control = await client.post(
        "/api/v1/hygiene-queue/bulk/supersede",
        json={"items": [{"memory_id": str(uuid.uuid4()), "superseded_by": str(newer.id)}]},
        headers=auth_headers,
    )
    assert control.status_code == 200 and control.json()["results"][0]["reason"] == "not_found"
    monkeypatch.setattr(hygiene_queue, "record_event", refuse)
    r = await client.post(
        "/api/v1/hygiene-queue/bulk/supersede",
        json={"items": [{"memory_id": str(older.id), "superseded_by": str(newer.id)}]},
        headers=auth_headers,
    )
    assert r.status_code == 200, r.text
    result = r.json()["results"][0]
    assert result["applied"] is False
    assert result["reason"] == "journal_failed"
    row = (
        await session.execute(
            text("SELECT status, superseded_by FROM memories WHERE id = CAST(:i AS uuid)"), {"i": str(older.id)}
        )
    ).one()
    assert row[0] == "active" and row[1] is None, "the supersession committed without its journal row"
    n = (
        await session.execute(
            text("SELECT count(*) FROM events WHERE object_id = CAST(:i AS uuid) AND event_type IN ('superseded','consolidated')"),
            {"i": str(older.id)},
        )
    ).scalar_one()
    assert n == 0


# ------------------------------------------------------------------ A36


def _qa_git(cwd, *args):
    return subprocess.run(
        ["git", "-c", "user.email=t@t", "-c", "user.name=t", *args], cwd=cwd, check=True, capture_output=True, text=True
    ).stdout.strip()


def _qa_upstream(root):
    up = root / "upstream"
    up.mkdir()
    _qa_git(up, "init", "-q", "-b", "main")
    (up / "a.py").write_text("x = 1\n")
    _qa_git(up, "add", "a.py")
    _qa_git(up, "commit", "-qm", "init")
    return up


@pytest.mark.asyncio
async def test_a36_a_failed_fetch_never_deletes_a_healthy_clone(session, tmp_path, monkeypatch):
    import app.services.repo_manager as rm
    from app.services.repo_manager import RepoManager

    base = tmp_path / "clones"
    base.mkdir()
    monkeypatch.setattr(rm, "REPOS_BASE_DIR", base)
    up = _qa_upstream(tmp_path)
    repo = Repository(
        name=f"qa36-{uuid.uuid4().hex[:6]}", url="https://example.invalid/o/r.git", default_branch="main",
        provider="github", status="ready",
    )
    session.add(repo)
    await session.flush()
    clone = base / str(repo.id)
    _qa_git(tmp_path, "clone", "-q", str(up), str(clone))
    marker = clone / "local-only.txt"
    marker.write_text("untracked work")
    _qa_git(clone, "remote", "set-url", "origin", str(tmp_path / "does-not-exist"))
    head = _qa_git(clone, "rev-parse", "HEAD")

    with pytest.raises(Exception):
        await RepoManager(session).pull_repo(repo, take_claim=True)

    assert (clone / ".git").is_dir()
    assert marker.read_text() == "untracked work"
    assert _qa_git(clone, "rev-parse", "HEAD") == head


@pytest.mark.asyncio
async def test_a36_the_fetch_lane_never_fast_forwards_a_branch_other_than_the_default(session, tmp_path):
    from app.services.repo_manager import RepoManager

    up = _qa_upstream(tmp_path)
    work = tmp_path / "work"
    _qa_git(tmp_path, "clone", "-q", str(up), str(work))
    _qa_git(work, "checkout", "-q", "-b", "topic")
    topic_head = _qa_git(work, "rev-parse", "HEAD")
    (up / "a.py").write_text("x = 2\n")
    _qa_git(up, "commit", "-qam", "upstream moves")
    up_head = _qa_git(up, "rev-parse", "HEAD")
    repo = Repository(
        name=f"qa36b-{uuid.uuid4().hex[:6]}", local_path=str(work), default_branch="main", provider="local", status="ready"
    )
    session.add(repo)
    await session.flush()
    mgr = RepoManager(session)

    await mgr.pull_repo(repo)
    assert _qa_git(work, "rev-parse", "HEAD") == topic_head
    assert _qa_git(work, "rev-parse", "topic") == topic_head

    _qa_git(work, "checkout", "-q", "main")
    await mgr.pull_repo(repo)
    assert _qa_git(work, "rev-parse", "main") == up_head


# ------------------------------------------------------------------ A20

from tests.test_dream_undo import (  # noqa: E402,F401 - fixtures and helpers
    committing,
    memory_row,
    produce_refine,
    project,
    undo_ids,
)


@pytest.mark.asyncio
async def test_a20_a_new_refine_changes_the_summary_and_never_the_tags(committing, project):
    from app.services import memory_dream as dream
    from app.utils.ids import new_id

    verdict = dream.parse_refine(json.dumps({"summary": "a crisp summary", "tags": ["invented", "project/other"]}))
    assert verdict.summary == "a crisp summary"
    assert not hasattr(verdict, "tags") or not getattr(verdict, "tags")

    memory, _event = await produce_refine(committing, project, cycle_id=str(new_id()), prior_tags=("t213-original", "project/t213-keep"))
    row = await memory_row(committing, memory)
    assert row["summary"] == "a refined summary"
    assert sorted(row["tag_names"]) == ["project/t213-keep", "t213-original"]


@pytest.mark.asyncio
async def test_a20_undoing_a_refine_journalled_with_tags_still_restores_them(committing, project):
    from app.utils.ids import new_id

    memory, event_id = await produce_refine(
        committing, project, cycle_id=str(new_id()), tags=("t213-changed",), prior_tags=("t213-original", "project/t213-keep")
    )
    changed = await memory_row(committing, memory)
    assert sorted(changed["tag_names"]) == ["t213-changed"]
    await undo_ids(committing, event_id)
    row = await memory_row(committing, memory)
    assert row["summary"] == "the old summary"
    assert sorted(row["tag_names"]) == ["project/t213-keep", "t213-original"]


# ------------------------------------------------------------------ A21


@pytest.mark.asyncio
async def test_a21_the_digest_marks_an_associate_undoable_exactly_when_its_undo_succeeds(committing, project):
    from app.services import dream_digest as digest
    from app.services import dream_undo as undo
    from app.services import memory_dream as dream
    from app.utils.ids import new_id
    from tests.test_dream_digest import _derived_edge, edges, journal

    cycle = str(new_id())
    untouched = await _derived_edge(committing, project, cycle_id=cycle, label="qa21-keep")
    rewritten = await _derived_edge(committing, project, cycle_id=cycle, label="qa21-moved")
    signal = dream.SIGNAL_EMBEDDING_PROXIMITY
    async with committing() as session:
        await edges.upsert_edge(
            session, source_memory_id=rewritten[0], target_memory_id=rewritten[1], rel_type=rewritten[2],
            project=project, pass_key=journal.DERIVATION_PASS,
            block=dream.derived_block(signal=signal, scores={signal: 0.33}, derived_at="a later pass"),
        )
        await session.commit()

    async with committing() as session:
        views = await digest.annotate_undoability(session, await digest.read_cycle_actions(session, cycle))
    by_source = {v.object_id: v for v in views}
    assert by_source[untouched[0]].undoable is True
    assert by_source[rewritten[0]].undoable is False

    await undo_ids(committing, by_source[untouched[0]].event_id)
    with pytest.raises(undo.UndoRefused):
        await undo_ids(committing, by_source[rewritten[0]].event_id)


# ------------------------------------------------------------------ A23

from tests.test_article_synthesis import factory  # noqa: E402,F401 - fixture


@pytest.mark.asyncio
async def test_a23_two_subjects_with_one_name_and_different_types_get_articles_from_their_own_facts(session, factory):
    from sqlalchemy import text

    from app.services import article_synthesis as asyn
    from tests.test_article_synthesis import _CitingLLM, _fact, _selection_config

    project = f"qa23-{uuid.uuid4().hex[:6]}"
    own = {}
    for etype in ("tool", "concept"):
        ent = uuid.uuid4()
        await session.execute(
            text("INSERT INTO entities (id, name, entity_type, memory_ids) VALUES (CAST(:i AS uuid), 'saturn', CAST(:t AS text), '{}'::uuid[])"),
            {"i": str(ent), "t": etype},
        )
        own[etype] = {str(await _fact(session, subject_name="saturn", subject_id=ent, project=project)) for _ in range(3)}
    await _selection_config(session, {"synthesis_budget": 5, "min_verified_facts": 3})
    await session.commit()

    llm = _CitingLLM()
    await asyn.run_article_synthesis(factory, lambda: llm, batch_size=50)

    prompted = {frozenset(p) for p in llm.prompted}
    assert prompted == {frozenset(own["tool"]), frozenset(own["concept"])}
    rows = (
        await session.execute(
            text("SELECT subject_key FROM knowledge_articles WHERE project = CAST(:p AS text) ORDER BY subject_key"), {"p": project}
        )
    ).scalars().all()
    assert rows == ["saturn::concept", "saturn::tool"]


# ------------------------------------------------------------------ A33 / A34

from tests.test_code_pipeline_incremental import (  # noqa: E402,F401 - fixtures and helpers
    _chunk_files,
    _commit,
    _index,
    _repo,
    _symbols,
    embedder,
)


@pytest.mark.asyncio
async def test_a33_a_file_whose_embed_failed_is_embedded_by_the_next_run(session, tmp_path, embedder):
    repo = await _repo(session, tmp_path, {"one.py": "def first():\n    return 1\n", "two.py": "def second():\n    return 1\n"})
    await _index(session, repo, embedder)
    assert await _chunk_files(session, repo.id, embedder.fingerprint) == {"one.py", "two.py"}

    embedder.fail_marker = "BREAKS_EMBED"
    _commit(tmp_path, {"one.py": "def first():\n    return 'BREAKS_EMBED'\n"})
    await _index(session, repo, embedder)
    assert "one.py" not in await _chunk_files(session, repo.id, embedder.fingerprint)

    embedder.fail_marker = None
    _commit(tmp_path, {"two.py": "def second():\n    return 2\n"})
    await _index(session, repo, embedder)
    assert await _chunk_files(session, repo.id, embedder.fingerprint) == {"one.py", "two.py"}


@pytest.mark.asyncio
async def test_a33_an_unchanged_dependent_is_not_re_embedded(session, tmp_path, embedder):
    repo = await _repo(
        session,
        tmp_path,
        {
            "lib.py": "def helper():\n    return 'LIB_V1'\n",
            "user.py": "from lib import helper\n\ndef use_it():\n    return helper() + 'DEPENDENT_BODY'\n",
        },
    )
    await _index(session, repo, embedder)
    embedder.texts.clear()
    _commit(tmp_path, {"lib.py": "def helper():\n    return 'LIB_V2'\n"})
    await _index(session, repo, embedder)
    assert any("LIB_V2" in t for t in embedder.texts)
    assert not any("DEPENDENT_BODY" in t for t in embedder.texts)


@pytest.mark.asyncio
async def test_a34_an_incremental_run_handles_a_changed_non_ascii_path(session, tmp_path):
    path = "src/é.py"
    repo = await _repo(session, tmp_path, {path: "def before_change():\n    return 1\n"})
    await _index(session, repo)
    assert await _symbols(session, repo.id, path) == {"before_change"}
    _commit(tmp_path, {path: "def after_change():\n    return 2\n"})
    await _index(session, repo)
    assert await _symbols(session, repo.id, path) == {"after_change"}


@pytest.mark.asyncio
async def test_a34_a_subclass_of_a_base_in_an_unchanged_file_keeps_its_extends_edge(session, tmp_path):
    from sqlalchemy import text

    repo = await _repo(
        session,
        tmp_path,
        {
            "parent.py": "class Parent:\n    def run(self):\n        return 1\n",
            "child.py": "from parent import Parent\n\nclass Child(Parent):\n    pass\n",
        },
    )
    await _index(session, repo)
    _commit(tmp_path, {"child.py": "from parent import Parent\n\nclass Child(Parent):\n    def more(self):\n        return 2\n"})
    await _index(session, repo)
    targets = set(
        (
            await session.execute(
                text("SELECT target_key FROM code_edges WHERE repo_id = :r AND edge_type='extends' AND source_key='Child::child.py'"),
                {"r": repo.id},
            )
        ).scalars().all()
    )
    assert targets == {"Parent::parent.py"}


# ------------------------------------------------------------------ A26


@pytest.mark.asyncio
async def test_a26_an_upload_in_progress_does_not_block_a_page_write_in_another_project(setup_database, monkeypatch, tmp_path):
    from httpx import ASGITransport, AsyncClient
    from sqlalchemy import delete, select
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.api.auth import create_access_token, hash_password
    from app.config import settings
    from app.main import app
    from app.models.config import Config
    from tests.conftest import test_engine

    monkeypatch.setattr(settings, "attachments_dir", str(tmp_path / "att"))
    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    async with factory() as s:
        had = (await s.execute(select(Config).where(Config.key == "admin_password_hash"))).scalar_one_or_none()
        saved = dict(had.value) if had else None
        if had is None:
            s.add(Config(key="admin_password_hash", value={"hash": hash_password("qa26-pass-123456")}))
        await s.commit()
    headers = {"Authorization": f"Bearer {create_access_token({'sub': 'admin'})}"}
    proj_a, proj_b = f"qa26a-{uuid.uuid4().hex[:6]}", f"qa26b-{uuid.uuid4().hex[:6]}"
    previous_llm = getattr(app.state, "llm", None)
    from tests.test_document_door import StubEmbedder

    app.state.llm = StubEmbedder()
    try:
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
            page_a = (await c.post("/api/v1/pages", json={"project": proj_a, "title": "A"}, headers=headers)).json()["id"]

            release = asyncio.Event()
            first_chunk_sent = asyncio.Event()

            async def slow_body():
                yield b"\x89PNG\r\n\x1a\n" + b"0" * (1024 * 1024)
                first_chunk_sent.set()
                await release.wait()
                yield b"0" * 1024

            upload = asyncio.create_task(
                c.post(
                    f"/api/v1/pages/{page_a}/attachments",
                    content=slow_body(),
                    headers={**headers, "X-Filename": "big.png", "Content-Type": "application/octet-stream"},
                )
            )
            await asyncio.wait_for(first_chunk_sent.wait(), 10)
            await asyncio.sleep(0.3)
            assert not upload.done()
            write = await asyncio.wait_for(
                c.post("/api/v1/pages", json={"project": proj_b, "title": "B"}, headers=headers), 10
            )
            assert write.status_code == 201, write.text
            assert not upload.done(), "the upload finished before the page write: the test proved nothing"
            release.set()
            done = await asyncio.wait_for(upload, 30)
            assert done.status_code in (200, 201), done.text
    finally:
        app.state.llm = previous_llm
        async with factory() as s:
            from sqlalchemy import text

            await s.execute(
                text("DELETE FROM page_attachments WHERE project IN (:a, :b)"), {"a": proj_a, "b": proj_b}
            )
            await s.execute(text("DELETE FROM pages WHERE project IN (:a, :b)"), {"a": proj_a, "b": proj_b})
            if saved is None:
                await s.execute(delete(Config).where(Config.key == "admin_password_hash"))
            await s.commit()


# ------------------------------------------------------------------ A16


@pytest.mark.asyncio
async def test_a16_two_concurrent_phase5_writes_sharing_entities_both_commit_without_a_deadlock(setup_database, monkeypatch):
    import contextlib

    from app.repositories.graph import PostgresGraphRepository
    from tests.test_pipeline_savepoints import VECTOR, savepoint_bed

    names = ("qa16-red", "qa16-blue", "qa16-green")

    def extraction(order):
        return {
            "entities": [{"name": n, "type": "tool"} for n in order],
            "relationships": [
                {"source": names[0], "target": names[1], "type": "USES", "weight": 0.5},
                {"source": names[1], "target": names[2], "type": "USES", "weight": 0.5},
            ],
            "memory_type": "fact",
        }

    async with savepoint_bed(["writer one", "writer two"], "qa16|4", entity_names=names) as bed:
        first = {m: asyncio.Event() for m in bed.memory_ids}
        real = PostgresGraphRepository.create_entity

        async def create_then_wait(self, name, entity_type, properties, memory_id):
            created = await real(self, name, entity_type, properties, memory_id)
            mine = first[memory_id]
            if not mine.is_set():
                mine.set()
                other = next(e for m, e in first.items() if m != memory_id)
                with contextlib.suppress(asyncio.TimeoutError):
                    await asyncio.wait_for(other.wait(), 3)
            return created

        monkeypatch.setattr(PostgresGraphRepository, "create_entity", create_then_wait)
        statuses = await asyncio.wait_for(
            asyncio.gather(
                *[
                    bed.pipe._write_memory(bed.entry(i), VECTOR, bed.fingerprint, bed.fingerprint, extraction(order), None, {}, {})
                    for i, order in enumerate((names, tuple(reversed(names))))
                ]
            ),
            60,
        )
        assert [s["graph"] for s in statuses] == ["ok", "ok"], statuses
        for i in range(2):
            assert await bed.entity_names(i) == set(names)


# ------------------------------------------------------------------ A18

from tests.test_wait_process import _pipeline as _qa18_pipeline  # noqa: E402


@pytest.mark.asyncio
async def test_a18_a_wait_process_capture_past_its_deadline_answers_the_ack_and_its_flush_finishes(
    client, auth_headers, session, monkeypatch
):
    import app.services.memory as memory_module
    from sqlalchemy import select, text

    from app.main import app
    from app.models.memory import MemoryBuffer
    from app.services import wait_process
    from app.services.embedder_registry import child_table
    from app.services.pipeline import ProcessingPipeline, _flag_cache_reset
    from tests.test_buffer_flush import EXTRACTION
    from tests.test_pipeline_phase1 import FakeEmbedder
    from app.services.buffer_flush import as_session_factory

    gate = asyncio.Event()

    class SlowLLM:
        async def chat_completion(self, purpose, **kwargs):
            await gate.wait()
            return json.dumps(EXTRACTION)

    fp = "qa18-deadline|4"
    _flag_cache_reset()
    pipeline = ProcessingPipeline(FakeEmbedder([fp]), as_session_factory(session))
    pipeline.extraction.llm = SlowLLM()
    monkeypatch.setattr(memory_module, "BUFFER_WAIT_TIMEOUT_SECONDS", 0.4)
    app.state.pipeline = pipeline
    try:
        r = await client.post("/api/v1/memories?wait_process=true", json={"content": "slow inline capture qa18"}, headers=auth_headers)
    finally:
        app.state.pipeline = None
    assert r.status_code == 202
    assert r.json()["status"] == "accepted"
    memory_id = r.json()["id"]
    gate.set()
    await asyncio.gather(*wait_process.continuing_flushes())
    row = (
        await session.execute(
            select(MemoryBuffer).where(MemoryBuffer.metadata_["memory_id"].astext == memory_id).execution_options(populate_existing=True)
        )
    ).scalar_one()
    assert row.status == "done"
    n = (
        await session.execute(
            text(f"SELECT count(*) FROM {child_table('memory_embeddings', fp)} WHERE memory_id = CAST(:m AS uuid)"), {"m": memory_id}
        )
    ).scalar_one()
    assert n == 1


@pytest.mark.asyncio
async def test_a18_a_hard_failed_replay_never_answers_201_with_an_unprocessed_memory(client, auth_headers, session):
    from app.main import app

    pipeline = _qa18_pipeline(session, fail=True)
    app.state.pipeline = pipeline
    try:
        r = await client.post("/api/v1/memories?wait_process=true", json={"content": "replay that hard-fails qa18"}, headers=auth_headers)
    finally:
        app.state.pipeline = None
    assert r.status_code == 202, r.text
    assert r.json()["status"] == "accepted"


# ------------------------------------------------------------------ A13

from tests.test_chat_retrieval_parity import (  # noqa: E402,F401
    FLIPPED_FLAGS as _QA13_FLAGS,
    PROJECT as _QA13_PROJECT,
    QUERY as _QA13_QUERY,
    RERANK_ORDER as _QA13_RERANK,
    _FakeLLM as _QA13_LLM,
    _chat_ids,
    _flag_corpus,
    _knowledge_ids,
    _search_surface_ids,
)


@pytest.mark.asyncio
@pytest.mark.parametrize("case", ["hybrid_off", "reranker_on", "confidence_gamma"])
async def test_a13_chat_knowledge_search_and_memory_search_return_one_memory_order_with_each_flag_flipped(
    session, client, auth_headers, monkeypatch, case
):
    from contextlib import asynccontextmanager
    from types import SimpleNamespace

    from app.api.mcp import server as mcp_server
    from app.main import app
    from app.models.config import Config
    from app.services.reranker import RerankerService

    notes = await _flag_corpus(session)

    async def fixed_rerank(self, query, documents, top_k=None, **_kw):
        key = lambda row: _QA13_RERANK.index(notes[str(row.get("memory_id") or row.get("id"))])
        ranked = sorted(documents, key=key)
        return ranked[:top_k] if top_k else ranked

    @asynccontextmanager
    async def same_session():
        yield session

    monkeypatch.setattr(RerankerService, "rerank", fixed_rerank)
    monkeypatch.setattr(mcp_server, "async_session_factory", same_session)
    monkeypatch.setattr(mcp_server, "_pipeline", SimpleNamespace(llm=_QA13_LLM()))
    monkeypatch.setattr(app.state, "llm", _QA13_LLM(), raising=False)

    before = await _search_surface_ids(session)
    session.add(Config(key="feature_flags", value=_QA13_FLAGS[case]))
    await session.flush()

    memory_search = await _search_surface_ids(session)
    chat = await _chat_ids(session)
    rest, knowledge_tool = await _knowledge_ids(client, auth_headers)

    assert memory_search != before, f"{case} must change the order on this corpus"
    assert chat == memory_search
    assert rest == memory_search
    assert knowledge_tool == memory_search


# ------------------------------------------------------------------ A1


@pytest.mark.asyncio
async def test_a1_a_lift_interleaved_with_a_re_extraction_leaves_no_source_the_new_graph_does_not_assert(setup_database):
    from sqlalchemy.ext.asyncio import async_sessionmaker

    from app.repositories.graph import PostgresGraphRepository
    from app.services.fact_lift import run_lift
    from app.services.fact_provenance import memory_source_ref
    from tests.conftest import test_engine
    from tests.test_fact_lift import facts, sources
    from tests.test_fact_lift_interleave import (
        _candidate,
        _cleanup,
        _hold_memory_row,
        _lift,
        _seed_asserting,
    )

    factory = async_sessionmaker(test_engine, expire_on_commit=False)
    project = f"qa1-{uuid.uuid4()}"
    keeper = await _seed_asserting(factory, project, "qa1-keeper")
    async with factory() as seed:
        await run_lift(seed)
        await seed.commit()
    moved = await _seed_asserting(factory, project, "qa1-moved")

    task = None
    async with factory() as reextracting, factory() as lifting, factory() as observer:
        try:
            fact_id = (await facts(observer, project))[0]["id"]
            candidate = await _candidate(lifting, project)
            # the re-extraction starts first: it locks the memory row and strips the old graph...
            await _hold_memory_row(reextracting, moved)
            await PostgresGraphRepository(reextracting).delete_by_memory_id(uuid.UUID(moved))
            # ...and the lift, started during it, must not commit a source from the stale graph
            task = asyncio.create_task(_lift(lifting, candidate))
            await asyncio.sleep(0.3)
            await reextracting.commit()
            await asyncio.wait_for(task, 10)
            await lifting.commit()
            refs = {row["source_ref"] for row in await sources(observer, fact_id)}
            assert memory_source_ref(moved) not in refs
            assert refs == {memory_source_ref(keeper)}
        finally:
            if task is not None and not task.done():
                task.cancel()
                await asyncio.gather(task, return_exceptions=True)
            await reextracting.rollback()
            await lifting.rollback()
            await observer.rollback()
            await _cleanup(factory, [project], [keeper, moved])
