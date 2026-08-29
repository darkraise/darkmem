"""Repo-hint auto-provision handoff + the SSRF allowlist gate (T1.15).

Doc 05 §2.4 gives capture exactly one job for a repository hint — validate
it and enqueue Tier C — and doc 18 §6 owns the validation. This is the one
adversarial-input surface in the capture path: a hint is caller-supplied
text arriving over the unauthenticated MCP door, so the tests below are
written as attacks rather than as happy paths.

Three properties carry the whole design and each has a test that fails if
the property is removed:

1. **Fail closed.** No allowlist means no auto-provision. Every hostile
   encoding of an internal address is refused for the same structural
   reason a typo is — it was not named — so there is no blocklist to rot.
2. **Never dereference.** The gate parses and compares; it resolves no
   name and follows no redirect, which is why a redirect chain whose final
   hop is internal cannot reach anything. Asserted structurally (call
   counters on subprocess/httpx/DNS), never by wall-clock timing.
3. **Refuse visibly, never fatally.** A refused hint journals
   `repo_hint_rejected` and the capture still succeeds.
"""
from __future__ import annotations

import socket
import subprocess
from pathlib import Path
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import func, select, text

from app.models.code import Repository
from app.models.config import Config
from app.models.memory import Memory, MemoryBuffer
from app.services.repo_allowlist import (
    REPO_ALLOWLIST_KEY,
    HintVerdict,
    evaluate_hint,
    load_allowlist,
)
from app.services.repo_provision import extract_hint

# An allowlist a real operator would plausibly write: one org on one public
# forge, plus a wildcarded private forge. Every hostile fixture below is
# tested against THIS list, not against an empty one — refusing a hostile
# hint only because nothing at all is allowed would prove nothing.
OPERATOR_ALLOWLIST = ["github.com/darkraise/*", "*.forge.internal.example"]

GOOD_HINT = "https://github.com/darkraise/darkmem.git"

# Obviously-fake placeholder credential. Real secrets never ride a fixture.
FAKE_CREDENTIAL_URL = "https://ci-bot:PLACEHOLDER-NOT-A-SECRET@github.com/darkraise/darkmem.git"


# ── The gate, as pure decisions ─────────────────────────────────────

HOSTILE_HINTS: list[tuple[str, str, str]] = [
    # An internal address is refused in every encoding, and all of them fail
    # for the SAME reason: nothing named them. That is the allowlist working
    # rather than an encoding-specific blocklist entry.
    ("dotted link-local", "https://169.254.169.254/latest/meta-data", "not_allowlisted"),
    ("decimal-encoded IPv4", "https://2852039166/darkraise/darkmem.git", "not_allowlisted"),
    ("octal-ish IPv4", "https://0177.0.0.1/darkraise/darkmem.git", "not_allowlisted"),
    ("all-zeros", "https://0.0.0.0/darkraise/darkmem.git", "not_allowlisted"),
    ("loopback by name", "https://localhost/darkraise/darkmem.git", "not_allowlisted"),
    ("private RFC1918", "https://10.0.0.7/darkraise/darkmem.git", "not_allowlisted"),
    # A name that resolves into private space is refused for the same reason,
    # and the gate never learns where it resolves — see the no-DNS test.
    ("resolves-to-private name", "https://intranet.example/darkraise/darkmem.git", "not_allowlisted"),
    # The final hop of a redirect chain is irrelevant because the gate never
    # follows one; only the named host is compared.
    ("redirect chain entry point", "https://redirector.example/to/169.254.169.254", "not_allowlisted"),
    # IPv6-mapped IPv4 does not even reach the allowlist: it is not a hostname.
    ("IPv6-mapped IPv4", "https://[::ffff:169.254.169.254]/darkraise/x.git", "illegal_host"),
    # Credentials never ride memory metadata — refused even though the host
    # and path prefix are allowlisted.
    ("credential-bearing URL", FAKE_CREDENTIAL_URL, "credentials_in_url"),
    # Userinfo used to disguise the real host.
    ("userinfo host confusion", "https://github.com@169.254.169.254/darkraise/x.git", "userinfo_not_allowed"),
    ("bare userinfo on https", "https://git@github.com/darkraise/darkmem.git", "userinfo_not_allowed"),
    # Schemes with no legitimate auto-provision use.
    ("cleartext http", "http://github.com/darkraise/darkmem.git", "scheme_not_allowed"),
    ("git protocol", "git://github.com/darkraise/darkmem.git", "scheme_not_allowed"),
    ("local file", "file:///etc/passwd", "scheme_not_allowed"),
    ("schemeless", "github.com/darkraise/darkmem.git", "scheme_not_allowed"),
    ("git ext transport", "ext::sh -c 'curl 169.254.169.254'", "unparsable"),
    # Suffix and prefix confusion against an allowlisted host.
    ("suffix confusion", "https://github.com.evil.example/darkraise/x.git", "not_allowlisted"),
    ("prefix confusion", "https://notgithub.com/darkraise/x.git", "not_allowlisted"),
    ("wildcard must not match the bare domain",
     "https://forge.internal.example/team/svc.git", "not_allowlisted"),
    # A port swap reaches a service on the allowlisted host that the operator
    # never named, and the pattern language cannot express a port.
    ("port swap on an allowlisted host", "https://github.com:8443/darkraise/x.git", "explicit_port"),
    # Path tricks that would escape an allowlisted org prefix.
    ("path traversal", "https://github.com/darkraise/../../evil/x.git", "path_traversal"),
    ("encoded traversal", "https://github.com/darkraise/%2e%2e/%2e%2e/evil", "illegal_path"),
    ("query smuggling", "https://github.com/darkraise/x.git?upload-pack=evil", "illegal_path"),
    ("wrong org on an allowlisted forge", "https://github.com/attacker/x.git", "not_allowlisted"),
    ("forge root, no repo", "https://github.com/", "missing_repo_path"),
    # Shapes that are not a hint at all.
    ("empty", "   ", "unparsable"),
    ("newline injection", "https://github.com/darkraise/x.git\n--upload-pack=evil", "unparsable"),
]


@pytest.mark.parametrize(
    "label,hint,reason", HOSTILE_HINTS, ids=[c[0] for c in HOSTILE_HINTS]
)
def test_hostile_hint_is_refused(label, hint, reason):
    verdict = evaluate_hint(hint, OPERATOR_ALLOWLIST)
    assert not verdict.allowed, f"{label} was allowed through the gate"
    assert verdict.reason == reason


ACCEPTED_HINTS = [
    ("https on the allowlisted org", GOOD_HINT, "https://github.com/darkraise/darkmem.git"),
    ("ssh url form", "ssh://git@github.com/darkraise/darkmem.git",
     "ssh://git@github.com/darkraise/darkmem.git"),
    ("scp-like form normalises to ssh", "git@github.com:darkraise/darkmem.git",
     "ssh://git@github.com/darkraise/darkmem.git"),
    ("host case is folded", "https://GitHub.COM/darkraise/darkmem.git",
     "https://github.com/darkraise/darkmem.git"),
    ("trailing root dot is stripped", "https://github.com./darkraise/darkmem.git",
     "https://github.com/darkraise/darkmem.git"),
    ("wildcard subdomain", "https://build.forge.internal.example/team/svc.git",
     "https://build.forge.internal.example/team/svc.git"),
]


@pytest.mark.parametrize(
    "label,hint,remote", ACCEPTED_HINTS, ids=[c[0] for c in ACCEPTED_HINTS]
)
def test_allowlisted_hint_is_accepted_and_rebuilt(label, hint, remote):
    verdict = evaluate_hint(hint, OPERATOR_ALLOWLIST)
    assert verdict.allowed, f"{label} was refused"
    # The remote is rebuilt from validated parts, so what eventually reaches a
    # git argv is never the caller's raw string.
    assert verdict.remote == remote


@pytest.mark.parametrize(
    "patterns",
    [[], None, {}, "github.com", ["", "  ", "https://github.com", "a b", "*"]],
    ids=["empty", "absent", "wrong-type", "string-not-list", "unusable-patterns"],
)
def test_gate_fails_closed(patterns):
    """No usable pattern means no auto-provision — including for a hint that
    would be perfectly legitimate under a configured allowlist. Flip this to
    default-open and every hostile case above becomes reachable."""
    assert not evaluate_hint(GOOD_HINT, patterns).allowed
    assert evaluate_hint(GOOD_HINT, patterns).reason == "not_allowlisted"


async def test_absent_config_row_yields_no_patterns(session):
    assert await load_allowlist(session) == []


async def test_allowlist_reads_the_config_row(session):
    session.add(Config(key=REPO_ALLOWLIST_KEY, value=OPERATOR_ALLOWLIST))
    await session.flush()
    assert await load_allowlist(session) == OPERATOR_ALLOWLIST


def test_extract_hint_ignores_everything_that_is_not_one():
    assert extract_hint(None) is None
    assert extract_hint({}) is None
    assert extract_hint({"repo_hint": ""}) is None
    assert extract_hint({"repo_hint": 169254169254}) is None
    assert extract_hint({"repository": GOOD_HINT}) is None
    assert extract_hint({"repo_hint": GOOD_HINT}) == GOOD_HINT


# ── The handoff, through the real capture door ──────────────────────


async def _set_allowlist(session, patterns) -> None:
    session.add(Config(key=REPO_ALLOWLIST_KEY, value=patterns))
    await session.flush()


async def _capture(client, auth_headers, hint, *, project="default", content="hinted"):
    return await client.post(
        "/api/v1/memories",
        json={"content": content, "project": project, "metadata": {"repo_hint": hint}},
        headers=auth_headers,
    )


async def _events(session, event_type: str) -> list[dict]:
    rows = await session.execute(
        text(
            "SELECT project, source, payload FROM events "
            "WHERE event_type = :t ORDER BY created_at, id"
        ),
        {"t": event_type},
    )
    return [dict(r) for r in rows.mappings().all()]


async def _repos(session) -> list[Repository]:
    return list((await session.execute(select(Repository))).scalars().all())


async def _associations(session) -> list[dict]:
    rows = await session.execute(
        text("SELECT project, repo_id, added_from, opt_out FROM project_repositories")
    )
    return [dict(r) for r in rows.mappings().all()]


async def test_allowlisted_hint_registers_the_repo_and_the_association(
    client, auth_headers, session
):
    await _set_allowlist(session, OPERATOR_ALLOWLIST)
    response = await _capture(client, auth_headers, GOOD_HINT, project="darkmem")
    assert response.status_code == 202

    repos = await _repos(session)
    assert len(repos) == 1
    repo = repos[0]
    assert repo.url == "https://github.com/darkraise/darkmem.git"
    assert repo.name == "darkmem"
    # Tier C's queue: `repo_sync` drains fetch/index-armed repos at its own
    # cadence.
    assert repo.fetch_enabled is True
    assert repo.index_on_commit_enabled is True
    assert repo.status == "queued"
    assert repo.last_indexed_commit is None

    assoc = await _associations(session)
    assert assoc == [
        {"project": "darkmem", "repo_id": repo.id, "added_from": "memory_hint",
         "opt_out": False},
    ]

    registered = await _events(session, "repo_registered")
    assert len(registered) == 1
    assert registered[0]["payload"]["remote"] == repo.url
    assert registered[0]["payload"]["queued_for"] == "tier_c"
    assert registered[0]["project"] == "darkmem"


async def test_rejected_hint_journals_and_the_capture_still_succeeds(
    client, auth_headers, session
):
    """Doc 18 §6 rule 4: the memory is the caller's content and must not hinge
    on a provisioning convenience that looked hostile."""
    await _set_allowlist(session, OPERATOR_ALLOWLIST)
    response = await _capture(
        client, auth_headers, "https://169.254.169.254/latest/meta-data",
        project="darkmem", content="summary of some untrusted page",
    )
    assert response.status_code == 202
    ack_id = UUID(response.json()["id"])

    buffered = (await session.execute(select(MemoryBuffer))).scalars().all()
    assert len(buffered) == 1
    assert buffered[0].content == "summary of some untrusted page"

    assert await _repos(session) == []
    assert await _associations(session) == []

    rejected = await _events(session, "repo_hint_rejected")
    assert len(rejected) == 1
    payload = rejected[0]["payload"]
    assert payload["reason"] == "not_allowlisted"
    assert payload["verdict"] == "matched_nothing"
    assert payload["hint"] == "https://169.254.169.254/latest/meta-data"
    assert payload["memory_id"] == str(ack_id)
    assert rejected[0]["project"] == "darkmem"


async def test_credential_bearing_hint_is_refused_at_the_door(
    client, auth_headers, session
):
    """Host and path prefix both match the allowlist; the embedded credential
    is what refuses it."""
    await _set_allowlist(session, OPERATOR_ALLOWLIST)
    response = await _capture(client, auth_headers, FAKE_CREDENTIAL_URL)
    assert response.status_code == 202
    assert await _repos(session) == []
    rejected = await _events(session, "repo_hint_rejected")
    assert [r["payload"]["reason"] for r in rejected] == ["credentials_in_url"]


async def test_default_deployment_provisions_nothing(client, auth_headers, session):
    """No `repo_allowlist` config row at all — the shipped default. Auto-
    provision is inert, and the refusal is still journaled rather than silent."""
    response = await _capture(client, auth_headers, GOOD_HINT)
    assert response.status_code == 202
    assert await _repos(session) == []
    assert await _associations(session) == []
    rejected = await _events(session, "repo_hint_rejected")
    assert [r["payload"]["reason"] for r in rejected] == ["not_allowlisted"]


async def test_two_projects_share_one_repository_row(client, auth_headers, session):
    """Doc 04 §8.7: two projects naming the same remote own the SAME repo and
    its one code graph, not private copies."""
    await _set_allowlist(session, OPERATOR_ALLOWLIST)
    for project in ("alpha", "beta", "alpha"):
        assert (
            await _capture(client, auth_headers, GOOD_HINT, project=project)
        ).status_code == 202

    repos = await _repos(session)
    assert len(repos) == 1
    assoc = await _associations(session)
    assert sorted(a["project"] for a in assoc) == ["alpha", "beta"]
    assert {a["repo_id"] for a in assoc} == {repos[0].id}


async def test_scp_and_https_forms_of_one_remote_stay_distinct_rows(
    client, auth_headers, session
):
    """Normalisation is per-scheme: an ssh remote and an https remote are two
    different clone targets even for the same repo, so they are two rows."""
    await _set_allowlist(session, OPERATOR_ALLOWLIST)
    await _capture(client, auth_headers, GOOD_HINT)
    await _capture(client, auth_headers, "git@github.com:darkraise/darkmem.git")
    urls = sorted(r.url for r in await _repos(session))
    assert urls == [
        "https://github.com/darkraise/darkmem.git",
        "ssh://git@github.com/darkraise/darkmem.git",
    ]


async def test_project_opt_out_blocks_the_association(client, auth_headers, session):
    """`project_repositories.opt_out` is the per-project escape hatch."""
    await _set_allowlist(session, OPERATOR_ALLOWLIST)
    repo = Repository(
        id=uuid4(), name="darkmem", url="https://github.com/darkraise/darkmem.git",
        provider="git", default_branch="main", status="ready",
    )
    session.add(repo)
    await session.flush()
    await session.execute(
        text(
            "INSERT INTO project_repositories (project, repo_id, added_from, opt_out) "
            "VALUES (:p, CAST(:r AS uuid), 'manual', true)"
        ),
        {"p": "darkmem", "r": str(repo.id)},
    )

    assert (
        await _capture(client, auth_headers, GOOD_HINT, project="darkmem")
    ).status_code == 202
    assoc = await _associations(session)
    assert [a["added_from"] for a in assoc] == ["manual"]
    assert await _events(session, "repo_registered") == []


async def test_capture_without_a_hint_touches_nothing(client, auth_headers, session):
    await _set_allowlist(session, OPERATOR_ALLOWLIST)
    response = await client.post(
        "/api/v1/memories", json={"content": "no hint here"}, headers=auth_headers,
    )
    assert response.status_code == 202
    assert await _repos(session) == []
    assert await _events(session, "repo_hint_rejected") == []


async def test_batch_capture_gates_every_entry(client, auth_headers, session):
    await _set_allowlist(session, OPERATOR_ALLOWLIST)
    response = await client.post(
        "/api/v1/memories/batch",
        json={"entries": [
            {"content": "good", "project": "darkmem", "metadata": {"repo_hint": GOOD_HINT}},
            {"content": "hostile", "project": "darkmem",
             "metadata": {"repo_hint": "https://169.254.169.254/x.git"}},
            {"content": "plain", "project": "darkmem"},
        ]},
        headers=auth_headers,
    )
    assert response.status_code == 202
    assert len(await _repos(session)) == 1
    assert len(await _events(session, "repo_hint_rejected")) == 1
    assert (await session.execute(
        select(func.count()).select_from(MemoryBuffer)
    )).scalar() == 3


async def test_a_broken_handoff_never_fails_the_capture(
    client, auth_headers, session, monkeypatch
):
    """The refusal path degrades loudly; so does an unexpected one. Journaling
    and provisioning are both secondary to the capture itself."""
    import app.services.repo_provision as provision

    async def _boom(*args, **kwargs):
        raise RuntimeError("registry write exploded")

    await _set_allowlist(session, OPERATOR_ALLOWLIST)
    monkeypatch.setattr(provision, "_provision", _boom)
    response = await _capture(client, auth_headers, GOOD_HINT)
    assert response.status_code == 202
    assert (await session.execute(
        select(func.count()).select_from(MemoryBuffer)
    )).scalar() == 1
    # The verdict is the gate's decision, so a failed registry write does not
    # retract it — the handoff still reports what the gate said.
    verdict = await provision.handoff_capture_hint(
        session, metadata={"repo_hint": GOOD_HINT}, memory_id=uuid4(),
        project="darkmem", patterns=OPERATOR_ALLOWLIST,
    )
    assert verdict is not None and verdict.allowed


# ── Ruling 3: capture never clones, proven structurally ─────────────


class _CallCounter:
    """Records every attempt to leave the process."""

    def __init__(self) -> None:
        self.git: list[list[str]] = []
        self.http: list[str] = []
        self.dns: list[str] = []

    def install(self, monkeypatch) -> None:
        real_run = subprocess.run

        def _run(cmd, *args, **kwargs):
            self.git.append(list(cmd) if isinstance(cmd, (list, tuple)) else [str(cmd)])
            return real_run(cmd, *args, **kwargs)

        # The real outbound transports only. The in-process test client speaks
        # through ASGITransport, which is a different class, so counting here
        # counts requests that would actually leave the box.
        async def _async_transport(_self, request, *args, **kwargs):
            self.http.append(str(request.url))
            raise AssertionError(f"capture must issue no HTTP request ({request.url})")

        def _sync_transport(_self, request, *args, **kwargs):
            self.http.append(str(request.url))
            raise AssertionError(f"capture must issue no HTTP request ({request.url})")

        def _getaddrinfo(host, *args, **kwargs):
            self.dns.append(str(host))
            raise AssertionError(f"capture must resolve no name ({host})")

        def _create_connection(address, *args, **kwargs):
            self.dns.append(str(address))
            raise AssertionError(f"capture must open no connection ({address})")

        monkeypatch.setattr(subprocess, "run", _run)
        monkeypatch.setattr(
            httpx.AsyncHTTPTransport, "handle_async_request", _async_transport
        )
        monkeypatch.setattr(httpx.HTTPTransport, "handle_request", _sync_transport)
        monkeypatch.setattr(socket, "getaddrinfo", _getaddrinfo)
        monkeypatch.setattr(socket, "create_connection", _create_connection)

    @property
    def git_invocations(self) -> list[list[str]]:
        return [c for c in self.git if c and "git" in c[0]]


async def test_capture_makes_no_network_call_and_no_git_invocation(
    client, auth_headers, session, monkeypatch
):
    """Ruling 3, structurally rather than by wall clock. A timing assertion
    flakes on a slow machine; a call counter fails the moment anyone inlines a
    clone, a fetch, or a DNS probe into the capture path — and keeps failing
    however fast the box is.

    Both an accepted and a refused hint run under the counter: the accepted
    one is the case that would clone, the refused one is the case a
    "let me just check where this resolves" fix would break.
    """
    await _set_allowlist(session, OPERATOR_ALLOWLIST)
    # Warm the pooled connection so the counter measures the capture, not the
    # fixture's first round-trip to Postgres.
    await session.execute(text("SELECT 1"))

    counter = _CallCounter()
    counter.install(monkeypatch)

    for hint in (GOOD_HINT, "https://redirector.example/to/169.254.169.254"):
        assert (await _capture(client, auth_headers, hint)).status_code == 202

    assert counter.git_invocations == []
    assert counter.git == []
    assert counter.http == []
    assert counter.dns == []

    # ...and the accepted hint still landed its registry row, so the zero
    # counts are not the trivial consequence of the handoff never running.
    assert len(await _repos(session)) == 1


async def test_the_gate_itself_resolves_no_name(monkeypatch):
    """Doc 18 §6 rule 3: the gate does no DNS-based checking at all. That is
    what makes a rebinding host and a redirect chain equally irrelevant —
    there is nothing to rebind between validate and clone, because validation
    never looked."""
    counter = _CallCounter()
    counter.install(monkeypatch)
    for _, hint, _ in HOSTILE_HINTS:
        evaluate_hint(hint, OPERATOR_ALLOWLIST)
    for _, hint, _ in ACCEPTED_HINTS:
        evaluate_hint(hint, OPERATOR_ALLOWLIST)
    assert counter.dns == []
    assert counter.http == []
    assert counter.git == []


async def test_capture_creates_no_memories_row_and_no_clone_directory(
    client, auth_headers, session
):
    """Provisioning is queued, not done: no `memories` row (that is the
    flush's) and nothing on disk (that is Tier C's)."""
    from app.services import repo_manager

    await _set_allowlist(session, OPERATOR_ALLOWLIST)
    assert (await _capture(client, auth_headers, GOOD_HINT)).status_code == 202

    repo = (await _repos(session))[0]
    assert (await session.execute(
        select(func.count()).select_from(Memory)
    )).scalar() == 0
    assert not (repo_manager.REPOS_BASE_DIR / str(repo.id)).exists()


# ── Ruling 5: safe.directory survives on local registration ─────────


async def test_local_registration_still_adds_git_safe_directory(
    session, tmp_path, monkeypatch
):
    """Without this, git refuses to operate on a tree owned by another uid —
    the normal case for a bind-mounted checkout in a container, which is
    exactly what local registration points at."""
    from app.schemas.code import RepoCreate
    from app.services import repo_manager

    calls: list[list[str]] = []

    class _Ok:
        returncode = 0
        stdout = b""
        stderr = b""

    def _fake_run(cmd, *args, **kwargs):
        calls.append(list(cmd))
        return _Ok()

    monkeypatch.setattr(subprocess, "run", _fake_run)

    local = tmp_path / "checkout"
    local.mkdir()
    manager = repo_manager.RepoManager(session)
    repo = await manager.create(
        RepoCreate(name="local", local_path=str(local), provider="local")
    )

    assert repo.local_path == str(Path(local).resolve())
    assert [
        "git", "config", "--global", "--add", "safe.directory", str(Path(local).resolve()),
    ] in calls


async def test_auto_provisioned_repo_is_remote_and_never_a_local_path(
    client, auth_headers, session
):
    """Doc 18 §6 rule 1 rejects `file://` and every non-remote scheme, so no
    caller-supplied local path can reach auto-provision — the clone
    destination is system-chosen. The local-path sandbox therefore stays a
    human-registration concern."""
    await _set_allowlist(session, OPERATOR_ALLOWLIST)
    assert (await _capture(client, auth_headers, GOOD_HINT)).status_code == 202
    repo = (await _repos(session))[0]
    assert repo.local_path is None
    assert not evaluate_hint("file:///root/.ssh", OPERATOR_ALLOWLIST).allowed


def test_verdict_reason_is_empty_exactly_when_allowed():
    allowed = evaluate_hint(GOOD_HINT, OPERATOR_ALLOWLIST)
    assert isinstance(allowed, HintVerdict)
    assert allowed.allowed and allowed.reason == ""
    refused = evaluate_hint(GOOD_HINT, [])
    assert not refused.allowed and refused.reason
