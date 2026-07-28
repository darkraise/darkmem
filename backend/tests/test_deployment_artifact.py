"""The shipped deployment artefacts, read as text from the repo root.

SCOPE, and it matters: everything here is an artefact-text check. In
particular the ``--no-proxy-headers`` assertions read the same files the fix
writes, so they can only ever fail because the string went missing -- they
can NEVER fail because the flag stopped suppressing uvicorn's
ProxyHeadersMiddleware. They are worth keeping because a later edit dropping
the flag is the realistic regression and this catches it for nothing, but a
green run here is not evidence that the flag works.

The proof that it works is ``test_uvicorn_proxy_headers.py``, which boots
real uvicorn both ways. The residual neither test reaches is that the
*running container* launched from the entrypoint rather than an overriding
compose ``command:``; that is verified live at execution time.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = REPO_ROOT / "entrypoint.sh"
DEV_SERVER = REPO_ROOT / "scripts" / "start_dev_server.sh"
PROD_COMPOSE = REPO_ROOT / "docker-compose.yml"
DEV_COMPOSE = REPO_ROOT / "docker-compose.dev.yml"
DOCKERFILE = REPO_ROOT / "Dockerfile"

APP_SERVICE = "darkmem-api"


def _unwrapped(path: Path) -> str:
    return path.read_text().replace("\\\n", " ")


def _uvicorn_line(path: Path) -> str:
    lines = [ln for ln in _unwrapped(path).splitlines() if "uvicorn" in ln]
    assert len(lines) == 1, f"{path.name} has {len(lines)} uvicorn lines, expected 1"
    return lines[0]


def _compose(path: Path) -> dict:
    return yaml.safe_load(path.read_text())


def _compose_command(path: Path, service: str) -> str:
    command = _compose(path)["services"][service].get("command", "")
    return " ".join(command) if isinstance(command, list) else command


LAUNCH_PATHS = {
    "entrypoint.sh": lambda: _uvicorn_line(ENTRYPOINT),
    "scripts/start_dev_server.sh": lambda: _uvicorn_line(DEV_SERVER),
    "docker-compose.dev.yml command": lambda: _compose_command(DEV_COMPOSE, APP_SERVICE),
}


# ── Layer 2: every launch path suppresses uvicorn's proxy-header rewrite ──


@pytest.mark.parametrize("name", sorted(LAUNCH_PATHS))
def test_every_launch_path_passes_no_proxy_headers(name):
    """uvicorn defaults proxy_headers to True with forwarded_allow_ips
    127.0.0.1, so without this flag any loopback client can set its own
    request.client.host -- and therefore its own rate-limit bucket -- one
    layer below the code that correctly refuses to read the header."""
    argv = LAUNCH_PATHS[name]()
    assert "uvicorn" in argv
    assert "--no-proxy-headers" in argv, name


@pytest.mark.parametrize("name", sorted(LAUNCH_PATHS))
def test_no_launch_path_re_enables_proxy_headers(name):
    argv = LAUNCH_PATHS[name]()
    assert not re.search(r"(?<!-)--proxy-headers\b", argv), name
    forwarded = re.search(r"--forwarded-allow-ips[= ]+(\S+)", argv)
    assert forwarded is None or forwarded.group(1) in ('""', "''"), name


def test_no_compose_command_re_enables_proxy_headers():
    for path in (PROD_COMPOSE, DEV_COMPOSE):
        for service, spec in _compose(path)["services"].items():
            argv = _compose_command(path, service)
            if "uvicorn" not in argv:
                continue
            assert "--no-proxy-headers" in argv, f"{path.name}:{service}"


# ── Invariant 13: one worker, always ──────────────────────────────────


def test_entrypoint_runs_a_single_worker():
    """In-process state -- the login rate limiter's failure map, the job
    registry's locks -- is per-process, so a second worker silently halves
    every limit and lets two schedulers race."""
    argv = _uvicorn_line(ENTRYPOINT)
    assert "--workers" not in argv
    assert not re.search(r"(?<![\w-])-w(?![\w-])", argv)
    assert "gunicorn" not in ENTRYPOINT.read_text()


@pytest.mark.parametrize("compose", [PROD_COMPOSE, DEV_COMPOSE], ids=["prod", "dev"])
def test_no_compose_file_sets_a_worker_count(compose):
    text = compose.read_text()
    assert "WEB_CONCURRENCY" not in text
    assert "UVICORN_WORKERS" not in text


# ── C-09: secrets are runtime-only, so rotation never needs a rebuild ──


def test_dockerfile_bakes_in_no_secret():
    """T1.54 rotates JWT_SECRET at cutover by editing .env and recreating the
    container. An ARG or ENV carrying a secret would make that a rebuild, and
    would also bake the old value into a published image layer."""
    forbidden = ("JWT_SECRET", "DB_PASSWORD", "SECRET", "PASSWORD")
    for line in DOCKERFILE.read_text().splitlines():
        stripped = line.strip()
        if not re.match(r"^(ARG|ENV)\s", stripped):
            continue
        names = re.findall(r"(?:^(?:ARG|ENV)\s+|\s)([A-Za-z_][A-Za-z0-9_]*)\s*=", stripped)
        names += re.findall(r"^ARG\s+([A-Za-z_][A-Za-z0-9_]*)\s*$", stripped)
        for name in names:
            for word in forbidden:
                assert word not in name.upper(), stripped


@pytest.mark.parametrize("secret", ["DB_PASSWORD", "JWT_SECRET"])
def test_prod_compose_requires_both_secrets_at_runtime(secret):
    environment = _compose(PROD_COMPOSE)["services"][APP_SERVICE]["environment"]
    entry = next(e for e in environment if e.startswith(f"{secret}="))
    assert f"${{{secret}:?" in entry, entry


# ── The compose surface doc 19 section 5 fixes ────────────────────────


def test_prod_compose_defines_exactly_the_app_and_postgres():
    """No darkmem-ui: the app serves the SPA itself and nothing binds :80."""
    assert set(_compose(PROD_COMPOSE)["services"]) == {APP_SERVICE, "postgres"}


def test_prod_app_service_keeps_host_networking_and_its_repo_volume():
    service = _compose(PROD_COMPOSE)["services"][APP_SERVICE]
    assert service["network_mode"] == "host"
    assert any(v.startswith("repo_data:") for v in service["volumes"]), service["volumes"]


def test_prod_postgres_keeps_its_shared_memory_sizing():
    assert _compose(PROD_COMPOSE)["services"]["postgres"]["shm_size"] == "256mb"


def test_dev_compose_builds_the_root_context():
    build = _compose(DEV_COMPOSE)["services"][APP_SERVICE]["build"]
    assert build["context"] == "."
    assert build["dockerfile"] == "Dockerfile"


def test_the_entrypoint_lives_beside_the_dockerfile_and_stays_lf():
    assert ENTRYPOINT.exists()
    assert not (REPO_ROOT / "backend" / "entrypoint.sh").exists()
    assert b"\r\n" not in ENTRYPOINT.read_bytes()
    assert "entrypoint.sh text eol=lf" in (REPO_ROOT / ".gitattributes").read_text()
