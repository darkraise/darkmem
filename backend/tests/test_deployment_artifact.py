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

import gzip
import os
import re
import subprocess
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = REPO_ROOT / "entrypoint.sh"
DEV_SERVER = REPO_ROOT / "scripts" / "start_dev_server.sh"
PROD_COMPOSE = REPO_ROOT / "docker-compose.yml"
DEV_COMPOSE = REPO_ROOT / "docker-compose.dev.yml"
DOCKERFILE = REPO_ROOT / "Dockerfile"
RESTORE = REPO_ROOT / "scripts" / "restore.sh"

APP_SERVICE = "darkmem"


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
    """No second UI service: one image carries the API and the built SPA
    together -- which is why it is `darkraise/darkmem`, not `-api` -- the app
    serves the SPA itself, and nothing binds :80."""
    assert set(_compose(PROD_COMPOSE)["services"]) == {APP_SERVICE, "postgres"}


def test_prod_app_service_publishes_its_port_and_keeps_its_repo_volume():
    service = _compose(PROD_COMPOSE)["services"][APP_SERVICE]
    assert "8000:8000" in service["ports"], service["ports"]
    assert any(v.startswith("repo_data:") for v in service["volumes"]), service["volumes"]


@pytest.mark.parametrize("service", [APP_SERVICE, "postgres"])
def test_prod_compose_uses_bridge_networking(service):
    """Host networking was replaced by an explicit bridge network on
    2026-08-18. `network_mode: host` ignores every `ports:` mapping silently,
    so a reintroduction would not fail to start -- it would quietly un-publish
    the ports below and put Postgres back on the host namespace."""
    spec = _compose(PROD_COMPOSE)["services"][service]
    assert "network_mode" not in spec, spec.get("network_mode")
    assert "darkmem" in spec["networks"], spec.get("networks")
    assert _compose(PROD_COMPOSE)["networks"]["darkmem"]["driver"] == "bridge"


def test_prod_postgres_publishes_on_the_host_loopback_only():
    """The database must not become LAN-reachable as a side effect of leaving
    host networking: an unqualified "5432:5432" binds 0.0.0.0."""
    ports = _compose(PROD_COMPOSE)["services"]["postgres"]["ports"]
    assert ports == ["127.0.0.1:5432:5432"], ports


def test_prod_postgres_listens_beyond_loopback():
    """The counterpart of the mapping above. Under bridge networking the API
    connects across the stack network, so the host-networking-era
    `listen_addresses=127.0.0.1` would refuse every application connection."""
    command = " ".join(_compose(PROD_COMPOSE)["services"]["postgres"]["command"])
    assert "listen_addresses=127.0.0.1" not in command, command


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


# ── The restore path replays into an empty database, never over a live one ──


def _restore_lines() -> list[str]:
    """Comment-free, so a comment naming a statement cannot be read as one."""
    return [
        ln for ln in _unwrapped(RESTORE).splitlines()
        if not ln.lstrip().startswith("#")
    ]


def _one(lines: list[str], predicate) -> int:
    hits = [i for i, ln in enumerate(lines) if predicate(ln)]
    assert len(hits) == 1, hits
    return hits[0]


def test_restore_still_stops_on_the_first_error_it_meets():
    lines = _restore_lines()
    replay = lines[_one(lines, lambda ln: "gunzip -c" in ln and "psql" in ln)]
    assert "-v ON_ERROR_STOP=1" in replay, replay


def test_restore_stays_lf_and_executable():
    assert RESTORE.exists()
    assert b"\r\n" not in RESTORE.read_bytes()
    assert os.access(RESTORE, os.X_OK)
    assert "*.sh text eol=lf" in (REPO_ROOT / ".gitattributes").read_text()


# ── Behavioural: restore.sh drives docker compose, so its real safety
# properties are proved by running it against a recording stub rather than
# by pinning strings, which would pass on a script that greps for a marker
# and ignores the result. No database is touched; COMPOSE_CMD points at a
# throwaway shell script that logs its argv and exits 0. ──────────────────

_STUB_TEMPLATE = """#!/usr/bin/env bash
{
  for a in "$@"; do
    printf '%s\x1f' "$a"
  done
  printf '\n'
} >> "__LOG_PATH__"
cat >/dev/null
exit 0
"""


def _write_stub(tmp_path: Path, log_path: Path) -> Path:
    stub = tmp_path / "compose_stub.sh"
    stub.write_text(_STUB_TEMPLATE.replace("__LOG_PATH__", str(log_path)))
    stub.chmod(0o755)
    return stub


def _run_restore(tmp_path: Path, dump_path: Path, db: str) -> tuple[subprocess.CompletedProcess, Path]:
    log_path = tmp_path / "invocations.log"
    log_path.touch()
    stub = _write_stub(tmp_path, log_path)
    env = dict(os.environ)
    env.update(
        COMPOSE_CMD=str(stub),
        POSTGRES_SERVICE="postgres",
        POSTGRES_DB=db,
        POSTGRES_USER="darkmem",
    )
    result = subprocess.run(
        ["bash", str(RESTORE), str(dump_path)],
        input="y\n",
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )
    return result, log_path


def _incomplete_dump(tmp_path: Path) -> Path:
    path = tmp_path / "empty.sql.gz"
    with gzip.open(path, "wb"):
        pass
    return path


def _complete_dump(tmp_path: Path) -> Path:
    path = tmp_path / "good.sql.gz"
    with gzip.open(path, "wt") as fh:
        fh.write("SELECT 1;\n--\nPostgreSQL database dump complete\n--\n")
    return path


def _record_fields(record: str) -> list[str]:
    # Each record is argv joined by \x1f with a trailing separator, so
    # splitting leaves one empty element to drop.
    return record.split("\x1f")[:-1]


def _arg_after(fields: list[str], flag: str) -> str | None:
    try:
        i = fields.index(flag)
    except ValueError:
        return None
    return fields[i + 1] if i + 1 < len(fields) else None


def test_restore_refuses_an_incomplete_dump_before_issuing_any_command(tmp_path):
    result, log_path = _run_restore(tmp_path, _incomplete_dump(tmp_path), db="restore_refusal_test")
    assert result.returncode == 1, result.stderr
    assert log_path.read_text() == "", "a command reached compose before the dump was validated"


def test_restore_orders_create_temp_then_replay_then_drop_then_rename(tmp_path):
    db = "restore_order_test"
    result, log_path = _run_restore(tmp_path, _complete_dump(tmp_path), db=db)
    assert result.returncode == 0, result.stderr

    records = [_record_fields(ln) for ln in log_path.read_text().splitlines() if ln]
    temp_marker = f"{db}_restore_"

    def index_of(predicate) -> int:
        hits = [i for i, fields in enumerate(records) if predicate(fields)]
        assert len(hits) == 1, (hits, records)
        return hits[0]

    idx_create = index_of(
        lambda f: any("CREATE DATABASE" in x and temp_marker in x for x in f)
    )
    idx_replay = index_of(
        lambda f: "-c" not in f and (_arg_after(f, "-d") or "").startswith(temp_marker)
    )
    idx_drop = index_of(
        lambda f: any("DROP DATABASE" in x and temp_marker not in x and db in x for x in f)
    )
    idx_rename = index_of(
        lambda f: any("ALTER DATABASE" in x and "RENAME TO" in x and temp_marker in x for x in f)
    )
    assert idx_create < idx_replay < idx_drop < idx_rename, records
