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
