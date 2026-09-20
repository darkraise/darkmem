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
import tarfile
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
ENTRYPOINT = REPO_ROOT / "entrypoint.sh"
DEV_SERVER = REPO_ROOT / "scripts" / "start_dev_server.sh"
PROD_COMPOSE = REPO_ROOT / "docker-compose.yml"
DEV_COMPOSE = REPO_ROOT / "docker-compose.dev.yml"
WORKER_COMPOSE = REPO_ROOT / "docker-compose.worker.yml"
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


def _service_env(path: Path, service: str) -> dict[str, str]:
    """The service's environment as a dict, whatever list/mapping form it uses."""
    raw = _compose(path)["services"][service].get("environment", [])
    if isinstance(raw, dict):
        return {k: str(v) for k, v in raw.items()}
    out: dict[str, str] = {}
    for entry in raw:
        key, _, value = str(entry).partition("=")
        out[key] = value
    return out


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
    for path in (PROD_COMPOSE, DEV_COMPOSE, WORKER_COMPOSE):
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


# The worker is a launch path like any other: same app, same in-process
# scheduler, limiter and WebSocket fan-out. A compose file nothing checks is
# exactly where a second worker gets added later "just for the viewer".
@pytest.mark.parametrize(
    "compose",
    [PROD_COMPOSE, DEV_COMPOSE, WORKER_COMPOSE],
    ids=["prod", "dev", "worker"],
)
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


def _invoke_restore(tmp_path: Path, dump_path: Path, db: str, stub: Path) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(
        COMPOSE_CMD=str(stub),
        POSTGRES_SERVICE="postgres",
        POSTGRES_DB=db,
        POSTGRES_USER="darkmem",
    )
    return subprocess.run(
        ["bash", str(RESTORE), str(dump_path)],
        input="y\n",
        capture_output=True,
        text=True,
        env=env,
        timeout=30,
    )


def _run_restore(tmp_path: Path, dump_path: Path, db: str) -> tuple[subprocess.CompletedProcess, Path]:
    log_path = tmp_path / "invocations.log"
    log_path.touch()
    stub = _write_stub(tmp_path, log_path)
    result = _invoke_restore(tmp_path, dump_path, db, stub)
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

    # The replay is the one command a corrupt dump reaches, so it is the one
    # command that must abort on the corrupt statement rather than pressing on
    # into a partially-loaded temp database that then gets swapped in whole.
    assert _arg_after(records[idx_replay], "-v") == "ON_ERROR_STOP=1", records[idx_replay]


# ── The cleanup STAGE machine (scripts/restore.sh:40-68) tells an operator
# which of three recoverable states a failed run left them in. Proven here by
# injecting a failure at each stage boundary through the same recording stub,
# never by pinning the script's line structure. ─────────────────────────────

_FAIL_ON_MARKER_STUB_TEMPLATE = """#!/usr/bin/env bash
{
  for a in "$@"; do
    printf '%s\x1f' "$a"
  done
  printf '\n'
} >> "__LOG_PATH__"
cat >/dev/null

for a in "$@"; do
  case "$a" in
    *"__MARKER__"*) exit 1 ;;
  esac
done
exit 0
"""

_FAIL_ON_REPLAY_STUB_TEMPLATE = """#!/usr/bin/env bash
{
  for a in "$@"; do
    printf '%s\x1f' "$a"
  done
  printf '\n'
} >> "__LOG_PATH__"
cat >/dev/null

has_c=0
is_replay_target=0
prev=""
for a in "$@"; do
  if [ "$a" = "-c" ]; then has_c=1; fi
  if [ "$prev" = "-d" ] && [[ "$a" == __TEMP_MARKER__* ]]; then is_replay_target=1; fi
  prev="$a"
done

if [ "$is_replay_target" = "1" ] && [ "$has_c" = "0" ]; then
  exit 1
fi
exit 0
"""


def _write_marker_failure_stub(tmp_path: Path, log_path: Path, marker: str) -> Path:
    """A compose stub that fails only the invocation carrying ``marker`` in
    one of its arguments, and logs+succeeds on every other invocation."""
    stub = tmp_path / "compose_stub.sh"
    script = _FAIL_ON_MARKER_STUB_TEMPLATE.replace("__LOG_PATH__", str(log_path))
    script = script.replace("__MARKER__", marker)
    stub.write_text(script)
    stub.chmod(0o755)
    return stub


def _write_replay_failure_stub(tmp_path: Path, log_path: Path, temp_marker: str) -> Path:
    """A compose stub that fails exactly the replay invocation: the one whose
    args carry ``-d <temp database>`` and no ``-c`` (every other invocation in
    restore.sh is a ``-c ...`` psql command against ``postgres`` or names the
    temp database via CREATE/RENAME rather than ``-d``)."""
    stub = tmp_path / "compose_stub.sh"
    script = _FAIL_ON_REPLAY_STUB_TEMPLATE.replace("__LOG_PATH__", str(log_path))
    script = script.replace("__TEMP_MARKER__", temp_marker)
    stub.write_text(script)
    stub.chmod(0o755)
    return stub


def test_restore_never_drops_the_original_when_the_replay_fails(tmp_path):
    """The central safety property, pinned against regression: a replay that
    aborts partway through (a corrupt or truncated dump body, a rejected
    statement) must never let the script proceed to drop '$DB'. Before this
    test, a stub that always exits 0 could not distinguish a script that
    checks the replay's exit status from one that does not."""
    db = "restore_replay_failure_test"
    temp_marker = f"{db}_restore_"
    log_path = tmp_path / "invocations.log"
    log_path.touch()
    stub = _write_replay_failure_stub(tmp_path, log_path, temp_marker)
    result = _invoke_restore(tmp_path, _complete_dump(tmp_path), db, stub)

    assert result.returncode != 0, result.stdout

    records = [_record_fields(ln) for ln in log_path.read_text().splitlines() if ln]
    drops_original = [
        fields for fields in records
        if any("DROP DATABASE" in x and temp_marker not in x and db in x for x in fields)
    ]
    assert drops_original == [], (
        "a failed replay must never reach the DROP DATABASE that removes "
        f"the original: {drops_original}"
    )

    # STAGE was "temp_created" when the trap fired: the create-temp command
    # committed (it is not the failing invocation) but the replay never
    # finished, so the operator is told the original is untouched and only
    # the leftover temp database needs cleaning up.
    assert "Original database" in result.stderr and "is untouched" in result.stderr
    assert "Drop the leftover restore copy" in result.stderr
    assert temp_marker in result.stderr


def test_restore_reports_nothing_to_clean_up_when_temp_creation_fails(tmp_path):
    """STAGE stays 'none' when the very first compose command -- creating the
    temp database -- is what fails, since the trap was armed but nothing had
    happened yet."""
    db = "restore_create_failure_test"
    log_path = tmp_path / "invocations.log"
    log_path.touch()
    stub = _write_marker_failure_stub(tmp_path, log_path, "CREATE DATABASE")
    result = _invoke_restore(tmp_path, _complete_dump(tmp_path), db, stub)

    assert result.returncode != 0, result.stdout
    assert "Original database" in result.stderr and "is untouched" in result.stderr
    assert "Nothing else to clean up" in result.stderr


def test_restore_explains_the_hand_finish_when_rename_fails(tmp_path):
    """STAGE is 'original_dropped' when only the final RENAME fails: '$DB'
    has already been dropped, so the operator needs the exact recovery
    command, not just a status line."""
    db = "restore_rename_failure_test"
    temp_marker = f"{db}_restore_"
    log_path = tmp_path / "invocations.log"
    log_path.touch()
    stub = _write_marker_failure_stub(tmp_path, log_path, "RENAME TO")
    result = _invoke_restore(tmp_path, _complete_dump(tmp_path), db, stub)

    assert result.returncode != 0, result.stdout

    records = [_record_fields(ln) for ln in log_path.read_text().splitlines() if ln]
    assert any(
        "DROP DATABASE" in x and temp_marker not in x and db in x
        for fields in records for x in fields
    ), "the rename-failure scenario must have reached the original's DROP"

    assert "was DROPPED" in result.stderr
    assert "does not currently exist" in result.stderr
    assert temp_marker in result.stderr
    assert "Finish the restore by hand" in result.stderr
    assert "RENAME TO" in result.stderr


def test_runtime_stage_installs_git():
    """Code indexing shells out to the git binary; the runtime image shipped
    without one until 2026-08-26.

    Nothing announces the omission. The image boots, migrations run, /health
    answers 200 and the healthcheck passes -- and every repository operation
    fails with "git: not found", so indexing simply never works. It went
    unnoticed because this deployment held zero repositories.

    Asserted against the *runtime* stage alone: the builder installs its own
    packages and its layers never ship, so a git that only exists there would
    satisfy a whole-file grep while leaving the artifact exactly as broken.
    """
    runtime = _unwrapped(DOCKERFILE).split("AS runtime", 1)
    assert len(runtime) == 2, "Dockerfile no longer has a stage named 'runtime'"
    installs = [
        line for line in runtime[1].splitlines()
        if re.match(r"^\s*RUN\s", line) and "apt-get install" in line
    ]
    assert any(re.search(r"\bgit\b", line) for line in installs), (
        "the runtime stage installs no git; RepoManager._run_git shells out to "
        "the binary and no pure-Python git is in the lockfile"
    )


def test_runtime_stage_installs_the_backup_toolchain():
    """The backup_ship job dumps over the stack network and encrypts with
    age; the ssh destination shells out to scp/rsync. None are in the base
    image, and an image missing them boots green while every nightly ship
    fails -- the process-boundary lesson applied to its own fix."""
    runtime = _unwrapped(DOCKERFILE)
    for package in ("postgresql-client", "age", "openssh-client", "rsync"):
        assert package in runtime, f"runtime stage does not install {package}"


def test_prod_app_service_mounts_a_writable_dump_directory():
    """The container runs as the unprivileged `app` user (USER app), and a
    host bind mount is NOT chowned by Docker the way a fresh named volume is.
    A default under /root -- mode 0700 -- is a directory the job can neither
    traverse nor write, so every ship would fail on its first `.part` open
    while the image reported healthy."""
    service = _compose(PROD_COMPOSE)["services"][APP_SERVICE]
    mount = next((v for v in service["volumes"] if "/dumps" in v), None)
    assert mount and "DARKMEM_DUMP_DIR" in mount, service["volumes"]
    assert "/root" not in mount, (
        "the dump mount's default must be reachable by the image's "
        f"unprivileged user; /root is 0700 -- got {mount!r}"
    )


# ── The backup worker stack (increment 7, spec §9.5) ──────────────────


def test_worker_app_runs_read_only_as_the_viewer_role():
    """Two settings, and neither is the other's substitute. `DB_USER` is the
    enforcement -- the SELECT-only role beneath every code path -- and
    `DARKMEM_READ_ONLY` is ergonomics on top of it. A worker connecting as the
    owner role would be a writable instance with a flag set."""
    env = _service_env(WORKER_COMPOSE, APP_SERVICE)
    assert env["DARKMEM_READ_ONLY"] == "true"
    assert env["DB_USER"] == "darkmem_viewer", (
        "the worker app must connect as the SELECT-only role, never the owner"
    )


def test_worker_app_never_runs_the_entrypoint():
    """`entrypoint.sh` runs `alembic upgrade head` and stamps `schema_guard`,
    which are writes -- and the restore loop already does both, privileged,
    against the side database while the app still serves the previous one.
    Overriding `command:` is what keeps the app out of that business, the same
    way the dev compose does."""
    command = _compose_command(WORKER_COMPOSE, APP_SERVICE)
    assert "uvicorn" in command
    assert "entrypoint" not in command
    assert "alembic" not in command


def test_worker_receiver_is_a_separate_service_running_its_own_module():
    """The one write door is a different process. A receiver started as
    `app.main` would be the read-only app with an upload route bolted on,
    which is the contradiction review B1 rejected."""
    services = _compose(WORKER_COMPOSE)["services"]
    assert "receiver" in services
    command = _compose_command(WORKER_COMPOSE, "receiver")
    assert "app.worker_receiver:app" in command
    assert "app.main" not in command


def test_only_the_receiver_mounts_the_dump_directory():
    """The app neither reads nor writes snapshots. Giving it the mount would
    make "the receiver is the only write door" a convention rather than a
    shape."""
    services = _compose(WORKER_COMPOSE)["services"]
    app_volumes = " ".join(services[APP_SERVICE].get("volumes", []) or [])
    receiver_volumes = " ".join(services["receiver"].get("volumes", []) or [])
    assert "/dumps" not in app_volumes
    assert "/dumps" in receiver_volumes
    # Review B-1's twin: a bind mount under /root is unreachable to the
    # image's unprivileged user, and Docker does not chown one.
    assert "DARKMEM_DUMP_DIR" in receiver_volumes
    assert "/root" not in receiver_volumes


def test_the_worker_stack_has_its_own_project_name():
    """Both other compose files learned this the hard way: an unnamed project
    defaults to the directory, so a worker brought up from this repo would
    recreate the prod stack's containers."""
    name = _compose(WORKER_COMPOSE).get("name")
    assert name and name not in {"darkmem-prod", "darkmem"}


def test_the_worker_stack_is_healthchecked_end_to_end():
    for service in ("darkmem", "receiver", "postgres"):
        assert "healthcheck" in _compose(WORKER_COMPOSE)["services"][service], service


# ── The worker's restore loop (increment 7 Task 9) ────────────────────
#
# Driven through the same stub-compose harness the restore.sh tests use: no
# real database is touched, and every compose invocation is recorded so the
# ORDER can be asserted. Order is the whole design here -- verify, then swap --
# so a test that only checked "it ran" would prove nothing worth proving.

RESTORE_CYCLE = REPO_ROOT / "scripts" / "worker" / "restore-cycle.sh"

_AGE_STUB = """#!/usr/bin/env bash
# Stand-in for `age -d -i IDENTITY [-o OUT] IN`: copies IN to OUT, or to
# stdout when no -o is given, which is how the attachment unpack reads it.
out=""; last=""
while [ "$#" -gt 0 ]; do
  case "$1" in
    -o) out="$2"; shift 2 ;;
    -d|-i) shift; [ "$1" != "" ] && [ "${1#-}" = "$1" ] && shift ;;
    *) last="$1"; shift ;;
  esac
done
if [ -n "$out" ]; then cp "$last" "$out"; else cat "$last"; fi
"""


def _write_age_stub(tmp_path: Path) -> Path:
    stub = tmp_path / "age"
    stub.write_text(_AGE_STUB)
    stub.chmod(0o755)
    return stub


def _write_tarball(tmp_path: Path, dumps: Path, stamp: str, marker: str) -> None:
    """A real gzipped tar whose one member names the generation, so a test can
    read back *which* set was unpacked rather than only that something was."""
    source = tmp_path / f"src-{stamp}"
    (source / "ab").mkdir(parents=True, exist_ok=True)
    (source / "ab" / "marker").write_text(marker)
    target = dumps / f"darkmem-app-attachments-{stamp}.tar.gz.age"
    with tarfile.open(target, "w:gz") as archive:
        archive.add(source, arcname=".")


def _run_cycle(
    tmp_path: Path, *, snapshot: str | None, complete: bool = True,
    migrate_ok: bool = True, attachments: tuple[tuple[str, str], ...] = (),
) -> tuple[subprocess.CompletedProcess, list[list[str]], Path]:
    dumps = tmp_path / "dumps"
    dumps.mkdir(exist_ok=True)
    for stamp, marker in attachments:
        _write_tarball(tmp_path, dumps, stamp, marker)
    if snapshot:
        source = _complete_dump(tmp_path) if complete else _incomplete_dump(tmp_path)
        (dumps / snapshot).write_bytes(source.read_bytes())

    log_path = tmp_path / "invocations.log"
    # Truncated, not touched: the second call in a re-run test shares tmp_path,
    # and a `touch` would leave the first run's records in place and make the
    # idempotence assertion pass for the wrong reason.
    log_path.write_text("")
    stub = _write_stub(tmp_path, log_path)
    if not migrate_ok:
        # The stub exits 0 for everything; a `run` that must fail needs its own.
        failing = tmp_path / "compose_failing.sh"
        failing.write_text(
            _STUB_TEMPLATE.replace("__LOG_PATH__", str(log_path)).replace(
                "exit 0",
                'for a in "$@"; do [ "$a" = "run" ] && exit 3; done\nexit 0',
            )
        )
        failing.chmod(0o755)
        stub = failing

    age_stub = _write_age_stub(tmp_path)
    state = tmp_path / "state"
    identity = tmp_path / "identity.txt"
    identity.write_text("AGE-SECRET-KEY-STUB")

    env = dict(os.environ)
    env.update(
        PATH=f"{tmp_path}:{env['PATH']}",
        COMPOSE_CMD=str(stub),
        WORKER_COMPOSE=str(REPO_ROOT / "docker-compose.worker.yml"),
        DUMP_DIR=str(dumps),
        STATE_FILE=str(state),
        AGE_IDENTITY=str(identity),
        OWNER_PASSWORD="owner-pw",
        VIEWER_PASSWORD="viewer-pw",
        DB_NAME="darkmem",
        GRANTS=str(REPO_ROOT / "scripts" / "worker" / "viewer-grants.sql"),
        ATTACHMENT_STORE=str(tmp_path / "attachments"),
    )
    result = subprocess.run(
        ["bash", str(RESTORE_CYCLE)],
        capture_output=True, text=True, env=env, timeout=60,
    )
    records = [_record_fields(ln) for ln in log_path.read_text().splitlines() if ln]
    return result, records, state


SNAPSHOT = "darkmem-app-20260101-000000.sql.gz.age"


def _index_of(records, predicate) -> int:
    hits = [i for i, fields in enumerate(records) if predicate(fields)]
    assert len(hits) == 1, (hits, records)
    return hits[0]


def test_restore_cycle_is_a_no_op_when_there_is_nothing_to_restore(tmp_path):
    result, records, _ = _run_cycle(tmp_path, snapshot=None)
    assert result.returncode == 0, result.stderr
    assert records == [], "a compose command ran with no snapshot present"


def test_restore_cycle_refuses_an_incomplete_dump_before_touching_compose(tmp_path):
    """Same marker check as restore.sh, and for the same reason: gzip of a
    truncated stream is valid gzip, so integrity proves nothing."""
    result, records, _ = _run_cycle(tmp_path, snapshot=SNAPSHOT, complete=False)
    assert result.returncode == 1
    assert records == [], "a command reached compose before the dump was validated"


def test_restore_cycle_verifies_before_it_swaps(tmp_path):
    """The order IS the design (B1's last bullet). Replay, migrate, stamp and
    grant all happen against the side database while the app is still serving
    the previous one; only then does anything stop."""
    result, records, state = _run_cycle(tmp_path, snapshot=SNAPSHOT)
    assert result.returncode == 0, result.stderr

    def has(fields, *needles):
        joined = " ".join(fields)
        return all(n in joined for n in needles)

    idx_create = _index_of(records, lambda f: has(f, "CREATE DATABASE", "_restore_"))
    idx_migrate = _index_of(records, lambda f: "run" in f and has(f, "alembic"))
    idx_grants = _index_of(records, lambda f: has(f, "viewer_password"))
    idx_stop = _index_of(records, lambda f: "stop" in f)
    idx_drop = _index_of(
        records, lambda f: has(f, "DROP DATABASE") and "_restore_" not in " ".join(f)
    )
    idx_rename = _index_of(records, lambda f: has(f, "ALTER DATABASE", "RENAME TO"))
    idx_start = _index_of(records, lambda f: "start" in f)

    assert idx_create < idx_migrate < idx_grants < idx_stop < idx_drop < idx_rename < idx_start
    assert state.read_text().strip() == SNAPSHOT


def test_restore_cycle_records_what_it_serves_so_a_re_run_is_a_no_op(tmp_path):
    _run_cycle(tmp_path, snapshot=SNAPSHOT)
    result, records, _ = _run_cycle(tmp_path, snapshot=SNAPSHOT)
    assert result.returncode == 0
    assert records == [], "the second run restored the snapshot it was already serving"


def test_a_snapshot_that_fails_the_schema_guard_never_stops_the_app(tmp_path):
    """B1's schema-mismatch answer. A snapshot from an older baseline fails
    schema_guard against the SIDE database, so the viewer keeps serving what it
    had -- it must not go down for exactly the snapshots one most wants to
    inspect. Exits 0, loudly: this is an expected outcome, not a broken run."""
    result, records, state = _run_cycle(tmp_path, snapshot=SNAPSHOT, migrate_ok=False)

    assert result.returncode == 0, result.stderr
    assert "REJECTED" in result.stdout + result.stderr
    assert not any("stop" in fields for fields in records), (
        "the app was stopped despite the snapshot failing verification"
    )
    assert not any(
        "ALTER DATABASE" in " ".join(fields) for fields in records
    ), "the swap happened despite the snapshot failing verification"
    # The side database is cleaned up rather than left as debris.
    assert any(
        "DROP DATABASE" in " ".join(f) and "_restore_" in " ".join(f) for f in records
    )
    assert not state.exists(), "a rejected snapshot was recorded as being served"


DUMP_0102 = "darkmem-app-20260102-000000.sql.gz.age"


def _store(tmp_path: Path) -> Path:
    return tmp_path / "attachments"


def test_the_cycle_unpacks_the_tarball_paired_with_the_dump(tmp_path):
    result, records, _ = _run_cycle(
        tmp_path,
        snapshot=DUMP_0102,
        attachments=(
            ("20260101-000000", "older-set"),
            ("20260103-000000", "newer-than-the-dump"),
        ),
    )
    assert result.returncode == 0, result.stderr

    store = _store(tmp_path)
    assert os.readlink(store / "current") == "gen-20260101-000000"
    assert (store / "current" / "ab" / "marker").read_text() == "older-set"


def test_a_missing_tarball_still_restores_the_database(tmp_path):
    result, records, state = _run_cycle(tmp_path, snapshot=SNAPSHOT)

    assert result.returncode == 0, result.stderr
    assert state.read_text().strip() == SNAPSHOT
    assert not (_store(tmp_path) / "current").exists()
    assert _index_of(records, lambda f: "ALTER" in " ".join(f)) >= 0


def test_the_attachments_only_path_leaves_the_database_alone(tmp_path):
    _run_cycle(
        tmp_path, snapshot=DUMP_0102, attachments=(("20260101-000000", "first"),)
    )
    # The database is current; only a newer attachment set arrived.
    result, records, _ = _run_cycle(
        tmp_path,
        snapshot=DUMP_0102,
        attachments=(
            ("20260101-000000", "first"),
            ("20260102-000000", "second"),
        ),
    )

    assert result.returncode == 0, result.stderr
    assert os.readlink(_store(tmp_path) / "current") == "gen-20260102-000000"
    assert not any("stop" in " ".join(fields) for fields in records)
    assert not any("ALTER" in " ".join(fields) for fields in records)


def test_the_cycle_removes_the_generations_it_replaced(tmp_path):
    _run_cycle(
        tmp_path, snapshot=DUMP_0102, attachments=(("20260101-000000", "first"),)
    )
    _run_cycle(
        tmp_path,
        snapshot=DUMP_0102,
        attachments=(
            ("20260101-000000", "first"),
            ("20260102-000000", "second"),
        ),
    )

    generations = sorted(p.name for p in _store(tmp_path).glob("gen-*"))
    assert generations == ["gen-20260102-000000"]


def test_a_leftover_current_tmp_does_not_break_the_swap(tmp_path):
    """A cycle killed between `ln -s` and `mv -T` leaves current.tmp behind,
    and the next `ln -s` would fail under errexit -- inside the window where
    the database has already been renamed."""
    store = _store(tmp_path)
    store.mkdir(parents=True)
    (store / "current.tmp").symlink_to("gen-does-not-exist")

    result, _, _ = _run_cycle(
        tmp_path, snapshot=DUMP_0102, attachments=(("20260101-000000", "first"),)
    )

    assert result.returncode == 0, result.stderr
    assert os.readlink(store / "current") == "gen-20260101-000000"


def test_a_torn_tarball_is_never_swapped_to(tmp_path):
    """A half-shipped set unpacks to a partial tree. Swapping to it would point
    the viewer's ATTACHMENTS_DIR at files that are not all there, which reads as
    rows whose attachment is missing rather than as a failed restore."""
    dumps = tmp_path / "dumps"
    dumps.mkdir()
    (dumps / "darkmem-app-attachments-20260101-000000.tar.gz.age").write_bytes(
        b"\x1f\x8b not a tarball"
    )

    result, records, state = _run_cycle(tmp_path, snapshot=DUMP_0102)

    assert result.returncode == 0, result.stderr
    assert "Could not unpack" in result.stderr
    assert not (_store(tmp_path) / "current").exists()
    assert list(_store(tmp_path).glob("gen-*")) == []
    # The database half still restored: a bad tarball is not a reason to keep
    # serving a stale snapshot.
    assert state.read_text().strip() == DUMP_0102
    assert _index_of(records, lambda f: "ALTER" in " ".join(f)) >= 0


def test_both_halves_current_is_a_no_op(tmp_path):
    args = dict(snapshot=DUMP_0102, attachments=(("20260101-000000", "first"),))
    _run_cycle(tmp_path, **args)
    result, records, _ = _run_cycle(tmp_path, **args)

    assert result.returncode == 0, result.stderr
    assert records == []


def test_the_restore_cycle_never_writes_from_the_serving_process():
    """The loop is a host-side script on purpose: it drops and renames the
    database the app is connected to, so the app process must never own the
    operation that destroys its own connection target."""
    body = RESTORE_CYCLE.read_text()
    assert "DARKMEM_READ_ONLY" not in body, (
        "the restore loop runs privileged and outside the app; it has no "
        "business reading the app's posture flag"
    )
    assert "alembic upgrade head" in body and "app.schema_guard" in body


# ── restore.sh --from (increment 7 Task 10) ───────────────────────────


def _invoke_restore_from(
    tmp_path: Path, stub: Path, *, args: list[str], pulled: Path, identity: Path | None = None,
) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update(
        COMPOSE_CMD=str(stub),
        POSTGRES_SERVICE="postgres",
        POSTGRES_DB="restore_from_test",
        POSTGRES_USER="darkmem",
        DARKMEM_DUMP_DIR=str(pulled.parent),
        PATH=f"{tmp_path}:{env['PATH']}",
    )
    env.pop("AGE_IDENTITY", None)
    if identity is not None:
        env["AGE_IDENTITY"] = str(identity)
    return subprocess.run(
        ["bash", str(RESTORE), *args],
        input="y\n", capture_output=True, text=True, env=env, timeout=60,
    )


_PULL_STUB = """#!/usr/bin/env bash
{
  printf 'ARGS\\x1f'
  for a in "$@"; do
    printf '%s\\x1f' "$a"
  done
  printf '\\n'
} >> "__LOG_PATH__"
for a in "$@"; do
  if [ "$a" = "backup_pull" ] || [ "$a" = "app.services.backup_pull" ]; then
    echo "some client library chatter on stdout"
    echo "/dumps/__PULLED__"
    exit 0
  fi
done
cat >/dev/null
exit 0
"""


def _write_pull_stub(tmp_path: Path, log_path: Path, pulled_name: str) -> Path:
    stub = tmp_path / "compose_pull.sh"
    stub.write_text(
        _PULL_STUB.replace("__LOG_PATH__", str(log_path)).replace(
            "__PULLED__", pulled_name
        )
    )
    stub.chmod(0o755)
    return stub


def test_restore_from_pulls_through_compose_and_replays_the_result(tmp_path):
    """`--from` fetches, then falls through to exactly the same marker check,
    confirmation and side-database replay as the plain form. The path is read
    off the LAST stdout line, which is why the stub prints noise above it."""
    dumps = tmp_path / "dumps"
    dumps.mkdir()
    pulled = dumps / "darkmem-app-20260101-000000.sql.gz"
    with gzip.open(pulled, "wt") as fh:
        fh.write("SELECT 1;\n--\nPostgreSQL database dump complete\n--\n")

    log_path = tmp_path / "invocations.log"
    log_path.write_text("")
    stub = _write_pull_stub(tmp_path, log_path, pulled.name)

    result = _invoke_restore_from(tmp_path, stub, args=["--from", "nas"], pulled=pulled)

    assert result.returncode == 0, result.stderr
    records = [_record_fields(ln) for ln in log_path.read_text().splitlines() if ln]
    assert any("app.services.backup_pull" in " ".join(f) for f in records)
    assert any("--latest" in f for f in records)
    assert any(
        "ALTER DATABASE" in " ".join(f) and "RENAME TO" in " ".join(f) for f in records
    ), "the pull ran but the restore did not"


def test_restore_from_passes_a_named_snapshot_through(tmp_path):
    dumps = tmp_path / "dumps"
    dumps.mkdir()
    pulled = dumps / "darkmem-app-20260101-000000.sql.gz"
    with gzip.open(pulled, "wt") as fh:
        fh.write("SELECT 1;\n--\nPostgreSQL database dump complete\n--\n")
    log_path = tmp_path / "invocations.log"
    log_path.write_text("")
    stub = _write_pull_stub(tmp_path, log_path, pulled.name)

    result = _invoke_restore_from(
        tmp_path, stub, args=["--from", "nas", pulled.name], pulled=pulled
    )

    assert result.returncode == 0, result.stderr
    records = [_record_fields(ln) for ln in log_path.read_text().splitlines() if ln]
    assert any("--name" in f for f in records)
    assert not any("--latest" in f for f in records)


def test_an_encrypted_snapshot_with_no_identity_is_refused(tmp_path):
    """The identity never enters the container, so it has to be supplied here
    -- and a restore that silently proceeded without decrypting would fail at
    the marker check with a confusing message instead of this one."""
    dumps = tmp_path / "dumps"
    dumps.mkdir()
    encrypted = dumps / "darkmem-app-20260101-000000.sql.gz.age"
    encrypted.write_bytes(b"ciphertext")
    log_path = tmp_path / "invocations.log"
    log_path.write_text("")
    stub = _write_pull_stub(tmp_path, log_path, encrypted.name)
    _write_age_stub(tmp_path)

    result = _invoke_restore_from(tmp_path, stub, args=["--from", "nas"], pulled=encrypted)

    assert result.returncode == 1
    assert "identity" in result.stderr.lower()
    records = [_record_fields(ln) for ln in log_path.read_text().splitlines() if ln]
    assert not any("ALTER DATABASE" in " ".join(f) for f in records)


def test_an_encrypted_snapshot_is_decrypted_on_the_host_then_replayed(tmp_path):
    dumps = tmp_path / "dumps"
    dumps.mkdir()
    plain = _complete_dump(tmp_path)
    encrypted = dumps / "darkmem-app-20260101-000000.sql.gz.age"
    encrypted.write_bytes(plain.read_bytes())  # the age stub is a copy
    identity = tmp_path / "identity.txt"
    identity.write_text("AGE-SECRET-KEY-STUB")
    log_path = tmp_path / "invocations.log"
    log_path.write_text("")
    stub = _write_pull_stub(tmp_path, log_path, encrypted.name)
    _write_age_stub(tmp_path)

    result = _invoke_restore_from(
        tmp_path, stub, args=["--from", "nas"], pulled=encrypted, identity=identity
    )

    assert result.returncode == 0, result.stderr
    records = [_record_fields(ln) for ln in log_path.read_text().splitlines() if ln]
    assert any(
        "ALTER DATABASE" in " ".join(f) and "RENAME TO" in " ".join(f) for f in records
    )


def test_the_legacy_invocation_is_byte_compatible(tmp_path):
    """The regression pin. `restore.sh FILE.sql.gz` must behave exactly as it
    did before `--from` existed -- the argument loop treats any non-flag as
    the positional, and nothing else changed on that path."""
    result, log_path = _run_restore(tmp_path, _complete_dump(tmp_path), db="legacy_pin")
    assert result.returncode == 0, result.stderr
    records = [_record_fields(ln) for ln in log_path.read_text().splitlines() if ln]
    assert not any("backup_pull" in " ".join(f) for f in records)


def test_worker_ports_are_overridable():
    """A worker rehearsed beside an existing darkmem on one host collides on
    every published port, and that rehearsal is how the runbook gets checked
    before a second machine exists. The defaults are what a dedicated worker
    wants; the variables are what makes the rehearsal possible."""
    services = _compose(WORKER_COMPOSE)["services"]
    published = " ".join(
        port
        for service in services.values()
        for port in (service.get("ports", []) or [])
    )
    for var in ("WORKER_APP_PORT", "WORKER_RECEIVER_PORT", "WORKER_DB_PORT"):
        assert var in published, f"{var} is not overridable"
    # Postgres stays bound to host loopback whatever the port is: the restore
    # loop needs it and nothing off-box does.
    assert "127.0.0.1:${WORKER_DB_PORT" in published


def test_the_receiver_healthcheck_asserts_the_bearer_guard_is_armed():
    """Two things this must get right, and the first one bit.

    `urllib.request.urlopen` RAISES `HTTPError` on 4xx rather than returning a
    response, so a check reading `.status` on an endpoint that answers 401 can
    never pass -- the container sits unhealthy while serving perfectly.

    And the right expectation is 401, not "200 or 401": an unauthenticated GET
    that succeeded would mean the bearer guard is not armed, which is the one
    failure a snapshot store must never boot into.
    """
    check = " ".join(
        _compose(WORKER_COMPOSE)["services"]["receiver"]["healthcheck"]["test"]
    )
    assert "HTTPError" in check, (
        "the healthcheck must handle urlopen raising on 401, not read .status"
    )
    assert "401" in check
    assert "200" not in check, (
        "an unauthenticated 200 means the bearer guard is not armed; the "
        "healthcheck must not accept it"
    )


def test_the_image_creates_the_attachments_dir_before_chowning_app():
    """A named volume mounted on a path the image lacks is created root-owned,
    and the unprivileged `app` user then cannot write a single attachment."""
    dockerfile = _unwrapped(DOCKERFILE)
    mkdir = dockerfile.find("/app/data/attachments")
    chown = dockerfile.find("chown -R app:app /app")
    assert mkdir != -1, "the Dockerfile never creates /app/data/attachments"
    assert chown != -1 and mkdir < chown, (
        "/app/data/attachments must exist before `chown -R app:app /app`"
    )


def test_prod_app_service_mounts_the_attachment_volume():
    service = _compose(PROD_COMPOSE)["services"][APP_SERVICE]
    assert "attachment_data:/app/data/attachments" in service["volumes"], service["volumes"]
    assert "attachment_data" in _compose(PROD_COMPOSE)["volumes"]
    env = _service_env(PROD_COMPOSE, APP_SERVICE)
    assert env["ATTACHMENTS_DIR"] == "/app/data/attachments"


def test_boot_checks_the_attachments_dir_outside_any_degrading_try():
    """The lifespan's LLM and registry setup sits in a broad try that logs and
    continues; a check inside it would let an unwritable volume boot green."""
    source = (REPO_ROOT / "backend" / "app" / "main.py").read_text()
    check = source.find("assert_attachments_dir_usable(read_only=settings.read_only)")
    first_try = source.find("from app.services.config import get_llm_config")
    assert check != -1, "lifespan never checks the attachments dir"
    assert check < first_try, "the attachments dir check must precede the lifespan's first try"


# ── The worker serves attachments from a restored generation ─────────


def test_the_worker_mounts_an_attachment_store_read_only():
    service = _compose(WORKER_COMPOSE)["services"]["darkmem"]
    mounts = [v for v in service["volumes"] if "attachment-store" in v]
    assert len(mounts) == 1, service["volumes"]
    assert mounts[0].endswith(":/app/data/attachment-store:ro"), mounts[0]


def test_the_worker_points_attachments_dir_at_the_current_generation():
    service = _compose(WORKER_COMPOSE)["services"]["darkmem"]
    assert (
        "ATTACHMENTS_DIR=/app/data/attachment-store/current" in service["environment"]
    )
