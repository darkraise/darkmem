"""T4.01 — the bearer credential shape and the closed scope set (doc 18 §5).

The four Done-when properties, and where each is proven here:

* format parsed and verified in constant time — ``TestCredentialShape`` and
  ``TestConstantCost``;
* the scope set is closed and an unknown scope is rejected at issue time —
  ``TestScopeVocabulary`` and ``TestIssue``;
* no code path can grant or check a ``ratify`` scope — ``TestRatifyIsNeverAScope``,
  which asserts it four ways and then plants the violation to prove the scan is
  awake;
* secrets stored hashed, plaintext shown once — ``TestIssue`` and
  ``TestManagementSurface``.

Several tests below are written as **drills**: they implement the lax
alternative alongside the shipped guard and assert the two disagree. A guard
whose weaker twin passes the same test has not been tested, and this repo has
already shipped one ``bool("false")`` master switch on exactly that reasoning.
"""

from __future__ import annotations

import ast
import asyncio
import contextlib
import re
import types
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest
import pytest_asyncio
from fastapi import Depends, FastAPI
from fastapi.dependencies.utils import get_dependant
from fastapi.routing import APIRoute
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select

from app.api.auth import Principal, require_scope
from app.database import get_session
from app.models.api_key import ApiKey
from app.services import api_key_scopes as scopes_mod
from app.services import api_keys as keys_mod
from app.services.api_key_scopes import (
    API_KEY_SCOPES,
    FORBIDDEN_SCOPES,
    ScopeRejected,
    assert_no_forbidden_scope,
    has_scope,
    parse_scopes,
    read_scopes,
)
from app.services.api_keys import (
    KEY_ID_LENGTH,
    KEY_PREFIX,
    SECRET_LENGTH,
    authenticate,
    issue_key,
    mint_credential,
    parse_credential,
    revoke_key,
    verify_secret,
)
from app.services.events import API_KEY_CREATED, API_KEY_REVOKED, EVENT_TYPES

APP_ROOT = Path(__file__).resolve().parents[1] / "app"


# --------------------------------------------------------------------------
# The closed vocabulary
# --------------------------------------------------------------------------


class TestScopeVocabulary:
    def test_the_set_is_pinned_by_value(self):
        # Doc 18 §5's three coarse scopes. A fourth is a design change that
        # must move this line, doc 18 §5 and doc 18 §11's stance together.
        assert API_KEY_SCOPES == ("capture", "read", "admin")
        assert len(API_KEY_SCOPES) == 3

    def test_the_vocabulary_cannot_be_mutated_at_runtime(self):
        # A list would make `API_KEY_SCOPES.append("ratify")` a one-line
        # privilege escalation that the import-time guard cannot see.
        assert isinstance(API_KEY_SCOPES, tuple)
        with pytest.raises(AttributeError):
            API_KEY_SCOPES.append("ratify")  # type: ignore[attr-defined]

    def test_write_is_not_a_scope(self):
        # The model's old default was `["read", "write"]`. `write` names no
        # scope in the design; `capture` is the write half.
        assert "write" not in API_KEY_SCOPES

    @pytest.mark.parametrize("bad", ["write", "ratify", "", "rea", "readx", "read admin"])
    def test_parse_rejects_anything_outside_the_set(self, bad):
        with pytest.raises(ScopeRejected):
            parse_scopes([bad])

    def test_parse_rejects_a_bare_string(self):
        # THE hazard. A string is iterable and substring-testable, so a lax
        # reader grants `admin` for the stored value `"admin"`.
        with pytest.raises(ScopeRejected):
            parse_scopes("admin")

    @pytest.mark.parametrize("bad", [None, 5, {"read": True}, object()])
    def test_parse_rejects_a_non_sequence(self, bad):
        with pytest.raises(ScopeRejected):
            parse_scopes(bad)

    def test_parse_rejects_a_non_string_member(self):
        with pytest.raises(ScopeRejected):
            parse_scopes(["read", 1])

    def test_parse_rejects_an_empty_grant(self):
        with pytest.raises(ScopeRejected):
            parse_scopes([])

    def test_parse_canonicalises_order_and_duplicates(self):
        # Two issues of one grant must store byte-identical jsonb.
        assert parse_scopes(["admin", "read", "read"]) == ("read", "admin")
        assert parse_scopes(["read", "admin"]) == parse_scopes(["admin", "read"])

    def test_parse_folds_case_and_whitespace(self):
        assert parse_scopes([" Read ", "ADMIN"]) == ("read", "admin")

    def test_the_error_names_the_offending_value_and_the_closed_set(self):
        with pytest.raises(ScopeRejected) as exc:
            parse_scopes(["telemetry"])
        message = str(exc.value)
        assert "telemetry" in message
        for scope in API_KEY_SCOPES:
            assert scope in message


class TestStoredScopesAreUntrusted:
    """`api_keys.scopes` is jsonb any psql prompt can edit, so the read side
    is as strict as the write side. Each test here pairs the shipped reader
    with the lax one it replaces and asserts they disagree."""

    def test_a_bare_string_column_grants_nothing(self):
        stored = "admin"

        def lax(granted, required):
            return required in granted

        assert lax(stored, "admin") is True, "the lax reader grants — that is the bug"
        assert has_scope(stored, "admin") is False
        assert read_scopes(stored) == frozenset()

    def test_a_substring_does_not_grant(self):
        stored = "unread"

        def lax(granted, required):
            return required in granted

        assert lax(stored, "read") is True, "the lax reader grants on a substring"
        assert has_scope(stored, "read") is False

    @pytest.mark.parametrize("stored", [None, 5, {"read": True}, "read"])
    def test_a_malformed_column_denies_rather_than_raising(self, stored):
        assert read_scopes(stored) == frozenset()
        assert has_scope(stored, "read") is False

    def test_unknown_members_are_dropped_not_kept(self):
        assert read_scopes(["read", "ratify", "write", 7]) == frozenset({"read"})

    def test_a_generous_row_still_cannot_grant_ratify(self):
        assert has_scope(["read", "admin", "ratify"], "ratify") is False

    def test_an_already_parsed_set_is_not_a_stored_value(self):
        # `has_scope` reads the raw jsonb. `KeyPrincipal.scopes` is a frozenset
        # that has already been through `read_scopes`, so passing one here is a
        # caller error, and the strict reader answers it by denying rather than
        # by appearing to work.
        assert has_scope(frozenset({"read"}), "read") is False

    def test_scopes_do_not_imply_one_another(self):
        # `admin` is config/jobs/repos, not a superset. An implication ladder
        # is a privilege-escalation design this module declines to invent.
        assert has_scope(["admin"], "read") is False
        assert has_scope(["admin"], "capture") is False


# --------------------------------------------------------------------------
# ratify is never a scope — four independent guards, then the drill
# --------------------------------------------------------------------------


def _require_scope_arguments() -> list[tuple[str, ast.expr]]:
    """Every `require_scope(...)` argument node under `backend/app`."""
    found: list[tuple[str, ast.expr]] = []
    sources = sorted(APP_ROOT.rglob("*.py"))
    assert len(sources) > 100, "the source glob broke; the scan would pass vacuously"
    for path in sources:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        rel = str(path.relative_to(APP_ROOT))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "require_scope"
                and node.args
            ):
                found.append((rel, node.args[0]))
    return found


def _routes_source_files() -> list[tuple[str, str]]:
    """`(relative_path, source_text)` for every module under app/api/routes."""
    routes = APP_ROOT / "api" / "routes"
    return [
        (str(path.relative_to(APP_ROOT)), path.read_text(encoding="utf-8"))
        for path in sorted(routes.rglob("*.py"))
    ]


def _require_scope_call_sites(files: list[tuple[str, str]]) -> list[tuple[str, int]]:
    """How many `require_scope(...)` call sites each file has -- binding
    granularity, not a substring match on the file text, so a second call
    site added to an already-offending file still moves the count."""
    sites: list[tuple[str, int]] = []
    for rel, text in files:
        tree = ast.parse(text, filename=rel)
        calls = [
            node for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "require_scope"
        ]
        if calls:
            sites.append((rel, len(calls)))
    return sites


def _offending_scope_arguments(arguments) -> list[str]:
    offenders = []
    for rel, node in arguments:
        if not (isinstance(node, ast.Constant) and isinstance(node.value, str)):
            # A non-literal argument is an offence in itself: the scan cannot
            # see through it, so a scope assembled at runtime would silently
            # leave this guard's reach.
            offenders.append(f"{rel}:{node.lineno}: non-literal scope argument")
        elif node.value not in API_KEY_SCOPES or node.value in FORBIDDEN_SCOPES:
            offenders.append(f"{rel}:{node.lineno}: scope {node.value!r}")
    return offenders


class TestRatifyIsNeverAScope:
    def test_it_is_absent_from_the_closed_set(self):
        assert "ratify" not in API_KEY_SCOPES

    def test_it_is_named_as_forbidden_rather_than_merely_omitted(self):
        # Omission alone is indistinguishable from an oversight. Naming it as
        # data is what lets the import guard and `has_scope` both refuse it.
        assert FORBIDDEN_SCOPES == frozenset({"ratify"})

    def test_widening_the_vocabulary_to_include_it_fails_at_import(self):
        # The drill for the module-level guard: the shipped call passes, the
        # widened one raises.
        assert_no_forbidden_scope(API_KEY_SCOPES)
        with pytest.raises(RuntimeError, match="ratify"):
            assert_no_forbidden_scope(("read", "ratify"))

    def test_it_cannot_be_granted_at_issue_time(self):
        with pytest.raises(ScopeRejected, match="ratify"):
            parse_scopes(["read", "ratify"])

    def test_it_cannot_be_checked_even_against_a_row_that_carries_it(self):
        assert has_scope(["ratify"], "ratify") is False

    def test_a_dependency_cannot_be_built_for_it(self):
        with pytest.raises(ValueError, match="ratify"):
            require_scope("ratify")

    def test_no_route_in_the_tree_names_a_scope_outside_the_set(self):
        assert _offending_scope_arguments(_require_scope_arguments()) == []

    def test_the_ratification_route_declares_no_scope_at_all(self):
        # `ratification.py` carries the instruction in its own docstring:
        # "this route must not grow a scope for it".
        source = (APP_ROOT / "api" / "routes" / "ratification.py").read_text()
        tree = ast.parse(source)
        names = {
            node.id for node in ast.walk(tree) if isinstance(node, ast.Name)
        } | {
            alias.name
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom)
            for alias in node.names
        }
        assert "require_scope" not in names
        assert "Principal" not in names

    def test_the_scan_flags_a_planted_scope(self):
        """The drill. A scan that flags nothing on a deliberately broken input
        has stopped working, and would read exactly like a passing one."""
        planted = ast.parse(
            "from app.api.auth import require_scope\n"
            "dep = require_scope('ratify')\n"
            "other = require_scope('write')\n"
            "sneaky = require_scope(SOME_NAME)\n"
        )
        arguments = [
            ("planted.py", node.args[0])
            for node in ast.walk(planted)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Name)
            and node.func.id == "require_scope"
            and node.args
        ]
        offenders = _offending_scope_arguments(arguments)
        assert len(offenders) == 3
        assert any("ratify" in o for o in offenders)
        assert any("write" in o for o in offenders)
        assert any("non-literal" in o for o in offenders)


# --------------------------------------------------------------------------
# The credential shape
# --------------------------------------------------------------------------

CREDENTIAL_RE = re.compile(r"^dmk_[a-z2-7]{16}_[a-z2-7]{32}$")


class TestCredentialShape:
    def test_a_minted_credential_matches_the_documented_shape(self):
        token = mint_credential().token
        assert CREDENTIAL_RE.match(token), token
        assert token.startswith(f"{KEY_PREFIX}_")

    def test_the_alphabet_excludes_the_delimiter_and_the_ambiguous_digits(self):
        # Base32 keeps `o` and `l` and drops `0`, `1`, `8`, `9`, so exactly one
        # member of each homoglyph pair can occur and a hand-copied key cannot
        # land on a different valid character. `_`, `+`, `/` and `=` would each
        # make the credential ambiguous to split or to put in a URL.
        joined = "".join(mint_credential().token for _ in range(50))
        body = joined.replace("dmk_", "").replace("_", "")
        for banned in "0189+/=":
            assert banned not in body, f"{banned!r} weakens hand-copying"
        assert set(body) <= set("abcdefghijklmnopqrstuvwxyz234567")

    def test_the_plaintext_is_absent_from_the_repr(self):
        # An accidental log line or a traceback frame must not publish the one
        # copy of the secret that will ever exist.
        credential = mint_credential()
        assert credential.secret not in repr(credential)
        assert credential.key_id in repr(credential)

    def test_credentials_do_not_repeat(self):
        minted = [mint_credential() for _ in range(200)]
        assert len({c.key_id for c in minted}) == 200
        assert len({c.secret for c in minted}) == 200

    def test_parsing_round_trips(self):
        credential = mint_credential()
        assert parse_credential(credential.token) == (
            credential.key_id,
            credential.secret,
        )

    @pytest.mark.parametrize(
        "bad",
        [
            None,
            "",
            b"dmk_aaaaaaaaaaaaaaaa_" + b"a" * 32,
            "dmk_" + "a" * 16,
            "dmk_" + "a" * 16 + "_" + "a" * 32 + "_extra",
            "dmx_" + "a" * 16 + "_" + "a" * 32,
            "DMK_" + "a" * 16 + "_" + "a" * 32,
            "dmk_" + "a" * 15 + "_" + "a" * 32,
            "dmk_" + "a" * 16 + "_" + "a" * 31,
            "dmk_" + "A" * 16 + "_" + "a" * 32,
            "dmk_" + "1" * 16 + "_" + "a" * 32,
            "dmk_" + "a" * 16 + "_" + "0" * 32,
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.e30.abc",
        ],
    )
    def test_parsing_refuses_everything_else(self, bad):
        assert parse_credential(bad) is None

    def test_the_lengths_are_the_ones_the_regex_pins(self):
        assert (KEY_ID_LENGTH, SECRET_LENGTH) == (16, 32)


class TestConstantCost:
    def test_a_lookup_miss_still_pays_a_bcrypt_verify(self, monkeypatch):
        """Otherwise a miss answers in microseconds where a hit pays the full
        key-stretching cost, which tells a prober that a guessed key_id
        exists."""
        calls = []
        real = keys_mod.bcrypt.checkpw

        def counting(secret, hashed):
            calls.append(1)
            return real(secret, hashed)

        monkeypatch.setattr(keys_mod.bcrypt, "checkpw", counting)

        assert verify_secret("a" * 32, None) is False
        assert len(calls) == 1, "a miss skipped the verify"

        calls.clear()
        assert verify_secret("a" * 32, keys_mod.hash_secret("a" * 32)) is True
        assert len(calls) == 1

    def test_an_unusable_stored_hash_denies_rather_than_raising(self):
        assert verify_secret("a" * 32, "not-a-bcrypt-hash") is False

    def test_the_secret_compare_is_not_a_python_equality(self):
        # `bcrypt.checkpw` is the constant-time compare. A `==` on the digest
        # would short-circuit on the first differing byte.
        source = Path(keys_mod.__file__).read_text()
        tree = ast.parse(source)
        function = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.FunctionDef) and node.name == "verify_secret"
        )
        compares = [n for n in ast.walk(function) if isinstance(n, ast.Compare)]
        assert not compares, "verify_secret must delegate the compare to bcrypt"
        assert any(
            isinstance(n, ast.Call)
            and isinstance(n.func, ast.Attribute)
            and n.func.attr == "checkpw"
            for n in ast.walk(function)
        )


# --------------------------------------------------------------------------
# Storage, issue and authentication
# --------------------------------------------------------------------------


class TestIssue:
    async def test_only_a_hash_is_stored(self, session):
        row, token = await issue_key(session, name="ci", scopes=["read"])
        _, _, secret = token.split("_")

        stored = (
            await session.execute(select(ApiKey).where(ApiKey.id == row.id))
        ).scalar_one()
        assert stored.key_hash != secret
        assert secret not in stored.key_hash
        # Nothing on the row carries the plaintext, under any column.
        for column in ApiKey.__table__.columns:
            value = getattr(stored, column.name)
            assert secret not in str(value)

    async def test_an_unknown_scope_leaves_no_row_behind(self, session):
        before = len((await session.execute(select(ApiKey))).scalars().all())
        with pytest.raises(ScopeRejected):
            await issue_key(session, name="bad", scopes=["ratify"])
        after = len((await session.execute(select(ApiKey))).scalars().all())
        assert after == before

    async def test_scopes_are_stored_canonically(self, session):
        row, _ = await issue_key(session, name="ci", scopes=["admin", "read"])
        assert row.scopes == ["read", "admin"]

    async def test_issue_journals_its_own_event(self, session):
        row, _ = await issue_key(session, name="ci", scopes=["read"], actor="admin")
        journal = await _events_for(session, row.id)
        assert [e["event_type"] for e in journal] == [API_KEY_CREATED]
        assert journal[0]["object_type"] == "system"
        assert journal[0]["actor"] == "admin"
        # The mint is made by a human session, not by a key: stamping
        # `api_key_id` would attribute a credential's creation to itself.
        assert journal[0]["api_key_id"] is None

    async def test_the_journal_payload_carries_no_secret(self, session):
        row, token = await issue_key(session, name="ci", scopes=["read"])
        _, _, secret = token.split("_")
        journal = await _events_for(session, row.id)
        assert secret not in str(journal)

    def test_both_lifecycle_types_are_in_the_closed_vocabulary(self):
        assert API_KEY_CREATED in EVENT_TYPES
        assert API_KEY_REVOKED in EVENT_TYPES


class TestAuthenticate:
    async def test_a_valid_credential_resolves_to_its_scopes(self, session):
        row, token = await issue_key(session, name="ci", scopes=["read", "capture"])
        principal = await authenticate(session, token)
        assert principal is not None
        assert principal.api_key_id == row.id
        assert principal.name == "ci"
        assert principal.scopes == frozenset({"read", "capture"})

    async def test_a_wrong_secret_is_refused(self, session):
        _, token = await issue_key(session, name="ci", scopes=["read"])
        prefix, key_id, secret = token.split("_")
        forged = f"{prefix}_{key_id}_{'a' * SECRET_LENGTH}"
        assert forged != token
        assert await authenticate(session, forged) is None

    async def test_an_unknown_key_id_is_refused(self, session):
        await issue_key(session, name="ci", scopes=["read"])
        assert await authenticate(session, mint_credential().token) is None

    async def test_a_revoked_key_is_refused(self, session):
        row, token = await issue_key(session, name="ci", scopes=["read"])
        assert await authenticate(session, token) is not None
        await revoke_key(session, row.id)
        assert await authenticate(session, token) is None

    async def test_an_expired_key_is_refused(self, session):
        past = datetime.now(timezone.utc) - timedelta(seconds=1)
        _, token = await issue_key(
            session, name="ci", scopes=["read"], expires_at=past
        )
        assert await authenticate(session, token) is None

    async def test_expiry_is_exclusive_at_the_instant(self, session):
        moment = datetime.now(timezone.utc) + timedelta(hours=1)
        _, token = await issue_key(
            session, name="ci", scopes=["read"], expires_at=moment
        )
        assert await authenticate(session, token, now=moment) is None
        assert (
            await authenticate(session, token, now=moment - timedelta(seconds=1))
            is not None
        )

    async def test_a_revoked_key_is_indistinguishable_from_a_forged_one(
        self, session
    ):
        """The secret is verified before revocation is consulted, so holding a
        revoked key's id without its secret reveals nothing."""
        row, token = await issue_key(session, name="ci", scopes=["read"])
        await revoke_key(session, row.id)
        prefix, key_id, _ = token.split("_")
        forged = f"{prefix}_{key_id}_{'a' * SECRET_LENGTH}"
        assert await authenticate(session, token) is None
        assert await authenticate(session, forged) is None

    async def test_every_refusal_costs_the_same_one_verify(
        self, session, monkeypatch
    ):
        """Uniform cost is the point: a revoked or expired key that
        short-circuited before the verify would answer faster than a forged
        one, which is a live-key oracle for anyone holding a stolen key_id."""
        row, token = await issue_key(session, name="ci", scopes=["read"])
        await revoke_key(session, row.id)
        _, expired_token = await issue_key(
            session,
            name="old",
            scopes=["read"],
            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        )

        calls: list[int] = []
        real = keys_mod.bcrypt.checkpw

        def counting(secret, hashed):
            calls.append(1)
            return real(secret, hashed)

        monkeypatch.setattr(keys_mod.bcrypt, "checkpw", counting)

        for presented in (token, expired_token, mint_credential().token):
            calls.clear()
            assert await authenticate(session, presented) is None
            assert len(calls) == 1, "a refusal path skipped the verify"

    async def test_a_hand_edited_scope_column_authenticates_with_nothing(
        self, session
    ):
        row, token = await issue_key(session, name="ci", scopes=["read"])
        row.scopes = "admin"
        await session.flush()
        principal = await authenticate(session, token)
        assert principal is not None
        assert principal.scopes == frozenset()

    @pytest.mark.parametrize("bad", [None, "", "not-a-key", 7])
    async def test_a_malformed_presentation_never_touches_the_database(
        self, session, bad
    ):
        assert await authenticate(session, bad) is None


# --------------------------------------------------------------------------
# Task 6b — bcrypt off the event loop, no connection held across it
# --------------------------------------------------------------------------


class TestEventLoopNotBlocked:
    """Single uvicorn worker (invariant 13): a synchronous ~167ms bcrypt call
    on the event loop stalls the whole process, not just this request. These
    tests fail against the pre-6b code, where ``verify_secret`` runs inline,
    and pass once it is offloaded via ``asyncio.to_thread``.
    """

    async def test_authenticate_does_not_stall_the_loop_during_verify(
        self, session
    ):
        _, token = await issue_key(session, name="ci", scopes=["read"])

        ticks = 0

        async def ticker() -> None:
            nonlocal ticks
            while True:
                await asyncio.sleep(0.005)
                ticks += 1

        tick_task = asyncio.create_task(ticker())
        try:
            principal = await authenticate(session, token)
        finally:
            tick_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tick_task

        assert principal is not None
        # A loop blocked by an inline bcrypt call never gives the ticker a
        # turn: it stays at 0 for the whole ~167ms the verify takes. Free,
        # the loop advances it several times over that window. 3 is well
        # below what a healthy run measures (~30) and well above what a
        # blocked loop can ever produce.
        assert ticks >= 3, (
            f"only {ticks} ticks advanced during authenticate() -- "
            "the event loop looks blocked"
        )

    async def test_a_lookup_miss_also_does_not_stall_the_loop(self, session):
        """The sentinel burn on an unknown key_id is the same cost and must
        be offloaded the same way -- otherwise a client hammering invented
        key_ids stalls the process exactly as effectively as a real key
        would."""
        ticks = 0

        async def ticker() -> None:
            nonlocal ticks
            while True:
                await asyncio.sleep(0.005)
                ticks += 1

        tick_task = asyncio.create_task(ticker())
        try:
            result = await authenticate(session, mint_credential().token)
        finally:
            tick_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await tick_task

        assert result is None
        assert ticks >= 3, f"only {ticks} ticks advanced during a lookup miss"


class TestConnectionReleasedBeforeVerify:
    async def test_the_fetch_transaction_is_released_before_bcrypt_runs(
        self, session, monkeypatch
    ):
        """Part B: the row is fetched and the session committed before the
        ~167ms verify runs, so that time does not also pin a pooled
        connection idle. Proven by inspecting the session's own transaction
        state from inside the (monkeypatched) bcrypt call."""
        _, token = await issue_key(session, name="ci", scopes=["read"])

        observed: dict[str, bool] = {}
        real = keys_mod.bcrypt.checkpw

        def spy(secret, hashed):
            observed["in_transaction"] = session.in_transaction()
            return real(secret, hashed)

        monkeypatch.setattr(keys_mod.bcrypt, "checkpw", spy)

        principal = await authenticate(session, token)

        assert principal is not None
        assert observed.get("in_transaction") is False, (
            "verify_secret ran while the fetch transaction was still open"
        )

    async def test_a_lookup_miss_also_releases_before_the_sentinel_burn(
        self, session, monkeypatch
    ):
        observed: dict[str, bool] = {}
        real = keys_mod.bcrypt.checkpw

        def spy(secret, hashed):
            observed["in_transaction"] = session.in_transaction()
            return real(secret, hashed)

        monkeypatch.setattr(keys_mod.bcrypt, "checkpw", spy)

        result = await authenticate(session, mint_credential().token)

        assert result is None
        assert observed.get("in_transaction") is False


class TestRevoke:
    async def test_revocation_keeps_the_row(self, session):
        row, _ = await issue_key(session, name="ci", scopes=["read"])
        assert await revoke_key(session, row.id, actor="admin") is True
        stored = (
            await session.execute(select(ApiKey).where(ApiKey.id == row.id))
        ).scalar_one_or_none()
        assert stored is not None, "history of the key's calls must survive"
        assert stored.revoked_at is not None

    async def test_revoking_twice_is_not_a_second_event(self, session):
        row, _ = await issue_key(session, name="ci", scopes=["read"])
        assert await revoke_key(session, row.id) is True
        assert await revoke_key(session, row.id) is False
        journal = await _events_for(session, row.id)
        assert [e["event_type"] for e in journal] == [API_KEY_CREATED, API_KEY_REVOKED]

    async def test_revoking_an_unknown_key_reports_nothing_to_do(self, session):
        assert await revoke_key(session, uuid.uuid4()) is False


async def _events_for(session, object_id) -> list[dict]:
    from sqlalchemy import text

    rows = await session.execute(
        text(
            "SELECT event_type, object_type, actor, api_key_id, payload "
            "FROM events WHERE object_id = CAST(:oid AS uuid) ORDER BY id"
        ),
        {"oid": str(object_id)},
    )
    return [dict(r) for r in rows.mappings().all()]


# --------------------------------------------------------------------------
# require_scope — the dependency, exercised on a throwaway route
# --------------------------------------------------------------------------


@pytest_asyncio.fixture
async def scoped_client(session):
    """A minimal app carrying one route behind `require_scope("read")`.

    Deliberately not a production route: T4.01 assigns no scope to the shipped
    surface (that is T4.03's), so the dependency is exercised here rather than
    by silently making some real route keyed.
    """
    probe = FastAPI()

    async def override():
        yield session

    probe.dependency_overrides[get_session] = override

    @probe.get("/probe")
    async def _probe(principal: Principal = Depends(require_scope("read"))):
        return {
            "actor": principal.actor,
            "is_human": principal.is_human,
            "api_key_id": str(principal.api_key_id) if principal.api_key_id else None,
        }

    async with AsyncClient(
        transport=ASGITransport(app=probe), base_url="http://probe"
    ) as c:
        yield c


class TestRequireScope:
    @pytest.mark.parametrize("bad", ["ratify", "write", "", "READ", "admin "])
    def test_a_bad_scope_literal_fails_at_decoration(self, bad):
        # A typo must stop the process at import, not become a route that
        # quietly admits nobody.
        with pytest.raises(ValueError):
            require_scope(bad)

    def test_every_member_of_the_closed_set_builds(self):
        for scope in API_KEY_SCOPES:
            assert require_scope(scope) is not None

    async def test_no_credential_is_refused(self, scoped_client):
        assert (await scoped_client.get("/probe")).status_code == 401

    async def test_a_key_holding_the_scope_is_admitted(self, session, scoped_client):
        row, token = await issue_key(session, name="ci", scopes=["read"])
        response = await scoped_client.get(
            "/probe", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 200
        body = response.json()
        assert body["is_human"] is False
        assert body["actor"] == "ci"
        assert body["api_key_id"] == str(row.id)

    async def test_a_key_lacking_the_scope_is_forbidden_not_unauthorised(
        self, session, scoped_client
    ):
        _, token = await issue_key(session, name="ci", scopes=["capture"])
        response = await scoped_client.get(
            "/probe", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 403

    async def test_a_revoked_key_is_refused(self, session, scoped_client):
        row, token = await issue_key(session, name="ci", scopes=["read"])
        await revoke_key(session, row.id)
        response = await scoped_client.get(
            "/probe", headers={"Authorization": f"Bearer {token}"}
        )
        assert response.status_code == 401

    async def test_a_forged_credential_is_refused(self, scoped_client):
        response = await scoped_client.get(
            "/probe", headers={"Authorization": f"Bearer {mint_credential().token}"}
        )
        assert response.status_code == 401

    async def test_a_human_session_is_admitted_and_carries_no_key_id(
        self, scoped_client, auth_headers
    ):
        response = await scoped_client.get("/probe", headers=auth_headers)
        assert response.status_code == 200
        body = response.json()
        assert body["is_human"] is True
        assert body["api_key_id"] is None

    async def test_a_jwt_bearer_is_not_mistaken_for_a_key(
        self, scoped_client, auth_headers
    ):
        # Both credentials share the Authorization header. The `dmk_` prefix
        # is what routes them, so a JWT must still reach the JWT verifier.
        assert not auth_headers["Authorization"].startswith("Bearer dmk_")
        assert (await scoped_client.get("/probe", headers=auth_headers)).status_code == 200


# --------------------------------------------------------------------------
# The management surface
# --------------------------------------------------------------------------


class TestManagementSurface:
    async def test_issue_returns_the_plaintext_once_and_never_again(
        self, client, auth_headers, session
    ):
        client.cookies.clear()
        created = await client.post(
            "/api/v1/api-keys",
            json={"name": "ci", "scopes": ["read"]},
            headers=auth_headers,
        )
        assert created.status_code == 201, created.text
        token = created.json()["token"]
        assert CREDENTIAL_RE.match(token)

        listed = await client.get("/api/v1/api-keys", headers=auth_headers)
        assert listed.status_code == 200
        body = listed.text
        assert token not in body
        _, key_id, secret = token.split("_")
        assert secret not in body
        assert "key_hash" not in body

        # The listed handle must be the public key_id and nothing else. Naming
        # the absent field is not enough on its own: serving `key_hash`'s value
        # under the `key_id` name passes every assertion above while publishing
        # the stored bcrypt hash of every key.
        row = next(r for r in listed.json() if r["key_id"] == key_id)
        assert re.fullmatch(r"[a-z2-7]{16}", row["key_id"])
        assert "$2b$" not in body

    async def test_the_surface_requires_a_session(self, client):
        client.cookies.clear()
        assert (await client.get("/api/v1/api-keys")).status_code == 401
        assert (
            await client.post("/api/v1/api-keys", json={"name": "x", "scopes": ["read"]})
        ).status_code == 401

    @pytest.mark.parametrize("bad", [["ratify"], ["write"], ["read", "ratify"]])
    async def test_an_unknown_scope_is_rejected_at_the_door(
        self, client, auth_headers, bad
    ):
        client.cookies.clear()
        response = await client.post(
            "/api/v1/api-keys",
            json={"name": "ci", "scopes": bad},
            headers=auth_headers,
        )
        assert response.status_code == 422
        assert "scope" in response.text.lower()

    async def test_a_key_can_never_manage_keys(self, client, auth_headers, session):
        """Doc 18 §5: a credential mint is confirmed-grade power, so the
        management surface stays behind the human door — including for a key
        holding `admin`."""
        client.cookies.clear()
        _, token = await issue_key(session, name="ci", scopes=["admin"])
        await session.commit()
        key_headers = {"Authorization": f"Bearer {token}"}

        assert (await client.get("/api/v1/api-keys", headers=key_headers)).status_code == 401
        assert (
            await client.post(
                "/api/v1/api-keys",
                json={"name": "x", "scopes": ["read"]},
                headers=key_headers,
            )
        ).status_code == 401
        assert (
            await client.delete(f"/api/v1/api-keys/{uuid.uuid4()}", headers=key_headers)
        ).status_code == 401

    async def test_revoke_returns_204_and_keeps_the_row(
        self, client, auth_headers, session
    ):
        client.cookies.clear()
        created = await client.post(
            "/api/v1/api-keys",
            json={"name": "ci", "scopes": ["read"]},
            headers=auth_headers,
        )
        key_row_id = created.json()["id"]

        deleted = await client.delete(
            f"/api/v1/api-keys/{key_row_id}", headers=auth_headers
        )
        assert deleted.status_code == 204

        listed = await client.get("/api/v1/api-keys", headers=auth_headers)
        rows = [r for r in listed.json() if r["id"] == key_row_id]
        assert len(rows) == 1, "a revoked key must remain listed"
        assert rows[0]["revoked_at"] is not None

    async def test_revoking_an_unknown_key_is_404(self, client, auth_headers):
        client.cookies.clear()
        response = await client.delete(
            f"/api/v1/api-keys/{uuid.uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404


# --------------------------------------------------------------------------
# Posture the activation must not have changed
# --------------------------------------------------------------------------


class TestPostureIsUnchanged:
    def test_require_auth_still_decodes_a_jwt_and_nothing_else(self):
        """The fail-closed half of the activation: keys reach only routes that
        opt in, so widening `require_auth` would have made every route in the
        tree keyed at once."""
        source = Path(scopes_mod.__file__).parent.parent / "api" / "auth.py"
        tree = ast.parse(source.read_text())
        function = next(
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.AsyncFunctionDef) and node.name == "require_auth"
        )
        called = {
            node.func.id
            for node in ast.walk(function)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        assert "authenticate" not in called
        assert "looks_like_credential" not in called

    def test_key_reach_is_pinned_to_the_call_sites_that_were_argued_for(self):
        """T4.01 landed the mechanism; T4.05's push-webhook receiver was the
        one sanctioned exception; T4.21 assigned the two scopes that had been
        grantable and reached nothing.

        Pinned to the exact call sites rather than to file membership: a
        file-level check would pass unchanged if a second, unargued
        `require_scope` call landed anywhere in a file already on the list
        (see the drills below). The number is the point — widening key reach
        must be a diff someone has to justify, not a line that slips in."""
        sites = _require_scope_call_sites(_routes_source_files())
        assert sites == [
            ("api/routes/memories.py", 2),
            ("api/routes/repos.py", 1),
        ]

        repos_source = (APP_ROOT / "api" / "routes" / "repos.py").read_text(encoding="utf-8")
        assert '_require_repo_admin = require_scope("admin")' in repos_source
        memories_source = (APP_ROOT / "api" / "routes" / "memories.py").read_text(encoding="utf-8")
        assert '_require_capture = require_scope("capture")' in memories_source
        assert '_require_read = require_scope("read")' in memories_source

    def test_the_scan_flags_a_call_site_planted_in_another_route(self):
        """The fail-closed direction: a require_scope call anywhere else in
        the tree still fails the positive assertion above, even though it is
        no longer a bare file-membership check."""
        files = _routes_source_files() + [
            (
                "api/routes/tags.py",
                "from app.api.auth import require_scope\n_x = require_scope('admin')\n",
            ),
        ]
        sites = _require_scope_call_sites(files)
        assert ("api/routes/tags.py", 1) in sites

    def test_the_scan_flags_a_second_call_site_in_repos_py_itself(self):
        """What file-granularity membership would have missed: a second
        require_scope call added to repos.py -- a DELETE route quietly
        gaining a scope nobody argued for, say -- leaves the file list
        unchanged but must move the call count."""
        patched = [
            (rel, text + "\n_extra = require_scope('read')\n") if rel == "api/routes/repos.py" else (rel, text)
            for rel, text in _routes_source_files()
        ]
        sites = _require_scope_call_sites(patched)
        assert ("api/routes/repos.py", 2) in sites
        assert ("api/routes/repos.py", 1) not in sites

    def test_the_mcp_door_gained_no_bearer_requirement(self):
        # Doc 18 §11's stance: the MCP bearer is a second, independent flip.
        source = (APP_ROOT / "api" / "mcp" / "server.py").read_text(encoding="utf-8")
        assert "require_scope" not in source
        assert "api_keys" not in source


# --------------------------------------------------------------------------
# Which route the one sanctioned require_scope binding actually reaches
# --------------------------------------------------------------------------
#
# `TestPostureIsUnchanged` above proves there is exactly one `require_scope`
# *call site*. It says nothing about which route the closure that call built
# is wired to -- a reviewer can repoint a second route at the same
# `_require_repo_admin` object (`Depends(_require_repo_admin)` on
# `delete_repo` instead of `Depends(require_auth)`) without adding a call
# site or changing the binding string, and every JWT-based test on the
# mutated route stays green because `require_scope`'s fallthrough accepts a
# session too (`auth.py:208-213`). The tests below walk the dependency
# closure FastAPI itself resolves for every route, so they see that
# mutation -- and any alias or indirect call reaching the same closure --
# regardless of how the source text spells it.


def _require_scope_dependency_code() -> types.CodeType:
    """The code object shared by every closure `require_scope(...)` builds.

    A nested function's code object is compiled once per source location,
    not once per call of the enclosing factory, so identity against this
    object survives an alias (`rs = require_scope; rs("read")`), an
    indirect call (`TABLE[0](repo)`), and binding reuse (a second route
    pointed at the same already-built closure) -- none of which a
    source-text scan can see.
    """
    return next(
        const
        for const in require_scope.__code__.co_consts
        if isinstance(const, types.CodeType) and const.co_name == "_require_scope"
    )


def _iter_api_routes(routes):
    """Recurse through the app's route tree down to concrete `APIRoute`
    objects, including FastAPI's lazy `_IncludedRouter` wrappers around each
    `include_router` call."""
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        elif hasattr(route, "original_router"):
            yield from _iter_api_routes(route.original_router.routes)
        elif hasattr(route, "routes"):
            yield from _iter_api_routes(route.routes)


def _iter_dependant_calls(dependant, seen=None):
    """Walk one route's full dependency closure -- the tree FastAPI itself
    resolves at request time, sub-dependencies included -- not just the
    `Depends(...)` arguments named directly in the route signature."""
    if seen is None:
        seen = set()
    if id(dependant) in seen:
        return
    seen.add(id(dependant))
    if dependant.call is not None:
        yield dependant.call
    for sub in dependant.dependencies:
        yield from _iter_dependant_calls(sub, seen)


def _routes_gated_by_require_scope(app) -> set[tuple[str, str]]:
    """Every `(method, path)` whose runtime dependency closure contains a
    require_scope-built dependency."""
    target_code = _require_scope_dependency_code()
    gated: set[tuple[str, str]] = set()
    for route in _iter_api_routes(app.router.routes):
        for call in _iter_dependant_calls(route.dependant):
            if getattr(call, "__code__", None) is target_code:
                for method in route.methods or ():
                    gated.add((method, route.path))
                break
    return gated


class TestRuntimeScopeGatedRoutes:
    """Important 3, fix round 2 (`docs/planning/briefs/2026-08-16-t4.05-fix-round-2.md`)."""

    def test_exactly_the_intended_routes_are_scope_gated(self):
        """The set is pinned, not bounded, so widening key reach is a visible
        diff rather than a side effect.

        T4.21 added the three memory doors: the boundary is the surface the
        minimal client speaks (`sdks/generate.py` binds `capture` to
        POST /memories and `search` to POST /memories/search/paginated), plus
        `/batch` because doc 18 §5 defines `capture` as "write memories" and a
        key that may write one but not many is an arbitrary line. Widening
        `read` to the vault or the code surface is a decision about what a
        leaked key can exfiltrate, and it is demand-gated rather than taken
        because the word fits.
        """
        from app.main import app

        assert _routes_gated_by_require_scope(app) == {
            ("POST", "/api/v1/repos/{repo_id}/webhook"),
            ("POST", "/api/v1/repos/{repo_id}/reindex-files"),
            ("POST", "/api/v1/memories"),
            ("POST", "/api/v1/memories/batch"),
            ("POST", "/api/v1/memories/search/paginated"),
        }

    def test_no_scope_in_the_closed_set_gates_nothing(self):
        """Doc 18 §5's set is closed, and a scope that reaches no route is a
        credential the UI can mint and the server refuses everywhere — which is
        what `capture` and `read` were until T4.21, advertised on the settings
        card the whole time."""
        from app.api.routes import memories as memories_module
        from app.api.routes import repos as repos_module
        from app.services.api_key_scopes import API_KEY_SCOPES

        bound = {
            "capture": memories_module._require_capture,
            "read": memories_module._require_read,
            "admin": repos_module._require_repo_admin,
        }
        assert set(bound) == set(API_KEY_SCOPES), (
            "a scope gained or lost its binding — every member of the closed "
            "set must gate at least one route, or leave the set"
        )

    def test_the_assertion_catches_delete_repo_reusing_the_binding(self):
        """The drill: reproduce the reviewer's exact mutation -- `delete_repo`
        repointed at the already-built `_require_repo_admin` closure, no new
        call site -- against the real app's route table, and confirm the
        runtime assertion goes red, then green again once restored.

        Reconstructing the dependant with `get_dependant` (the same analysis
        FastAPI runs when it processes `Depends(...)` on a route signature)
        and swapping it onto the live `delete_repo` route object is what
        makes this the reviewer's mutation and not a synthetic stand-in --
        the walk below sees exactly what FastAPI would have resolved had
        `repos.py` actually been edited this way.
        """
        from app.api.routes.repos import _require_repo_admin
        from app.main import app

        async def mutated_delete_repo(repo_id: uuid.UUID, _principal=Depends(_require_repo_admin)):
            ...

        mutated_dependant = get_dependant(
            path="/api/v1/repos/{repo_id}", call=mutated_delete_repo
        )

        target = next(
            route
            for route in _iter_api_routes(app.router.routes)
            if route.path == "/api/v1/repos/{repo_id}" and "DELETE" in (route.methods or ())
        )
        expected = {
            ("POST", "/api/v1/repos/{repo_id}/webhook"),
            ("POST", "/api/v1/repos/{repo_id}/reindex-files"),
            ("POST", "/api/v1/memories"),
            ("POST", "/api/v1/memories/batch"),
            ("POST", "/api/v1/memories/search/paginated"),
        }
        original_dependant = target.dependant
        target.dependant = mutated_dependant
        try:
            assert _routes_gated_by_require_scope(app) == expected | {
                ("DELETE", "/api/v1/repos/{repo_id}"),
            }, "the mutant must be caught -- the delete route now carries the binding"
        finally:
            target.dependant = original_dependant

        assert _routes_gated_by_require_scope(app) == expected, (
            "restoring the original dependant must clear the finding again"
        )

# --------------------------------------------------------------------------
# T4.21 — the two scopes now reach the client surface, and only it
# --------------------------------------------------------------------------


@pytest.mark.asyncio
class TestScopeAssignment:
    """`capture` and `read` were grantable, advertised, and gated nothing.

    The boundary chosen is the surface the minimal client speaks. These tests
    drive the **real** routes rather than a throwaway app, because what T4.21
    decides is which shipped doors a credential reaches — a throwaway app can
    prove the mechanism and says nothing about that.
    """

    async def _key(self, session, scopes):
        _row, token = await issue_key(session, name=f"t421-{'-'.join(scopes)}", scopes=scopes)
        return {"Authorization": f"Bearer {token}"}

    async def test_a_capture_key_writes_but_cannot_search(self, client, session):
        headers = await self._key(session, ["capture"])

        wrote = await client.post(
            "/api/v1/memories", json={"content": "keyed capture"}, headers=headers
        )
        assert wrote.status_code in (200, 201, 202), wrote.text

        searched = await client.post(
            "/api/v1/memories/search/paginated", json={"query": "keyed"}, headers=headers
        )
        assert searched.status_code == 403, "a capture key must not read the corpus"

    async def test_a_read_key_searches_but_cannot_write(self, client, session):
        headers = await self._key(session, ["read"])

        searched = await client.post(
            "/api/v1/memories/search/paginated", json={"query": "keyed"}, headers=headers
        )
        assert searched.status_code == 200, searched.text

        wrote = await client.post(
            "/api/v1/memories", json={"content": "should not land"}, headers=headers
        )
        assert wrote.status_code == 403, "a read key must not write to the corpus"

    async def test_batch_is_capture_not_read(self, client, session):
        read_headers = await self._key(session, ["read"])
        capture_headers = await self._key(session, ["capture"])

        refused = await client.post(
            "/api/v1/memories/batch", json={"entries": [{"content": "x"}]},
            headers=read_headers,
        )
        assert refused.status_code == 403

        allowed = await client.post(
            "/api/v1/memories/batch", json={"entries": [{"content": "x"}]},
            headers=capture_headers,
        )
        assert allowed.status_code in (200, 201, 202), allowed.text

    async def test_the_human_session_still_reaches_all_three(self, client, auth_headers):
        """The fallthrough that makes this change additive rather than a
        migration: `require_scope` accepts a cookie session, so the SPA is
        untouched. Without this the change could gate the UI out of its own
        capture door and every keyed test above would still pass."""
        wrote = await client.post(
            "/api/v1/memories", json={"content": "human capture"}, headers=auth_headers
        )
        assert wrote.status_code in (200, 201, 202), wrote.text

        searched = await client.post(
            "/api/v1/memories/search/paginated", json={"query": "human"}, headers=auth_headers
        )
        assert searched.status_code == 200, searched.text

        batched = await client.post(
            "/api/v1/memories/batch", json={"entries": [{"content": "human batch"}]},
            headers=auth_headers,
        )
        assert batched.status_code in (200, 201, 202), batched.text

    async def test_a_keyed_capture_stamps_its_key_on_the_journal(self, client, session):
        """Found by a drill that passed when it should not have: removing the
        stamp left every test green, because nothing asserted the door doc 18
        §5 convention 8 is actually about. A keyed door that journals
        `api_key_id=None` is the same defect the epic review's C1 named on the
        webhook, one route over."""
        from sqlalchemy import text as sql_text

        row, token = await issue_key(session, name="t421-stamp", scopes=["capture"])
        response = await client.post(
            "/api/v1/memories",
            json={"content": "stamped capture"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code in (200, 201, 202), response.text

        stamped = (await session.execute(
            sql_text(
                "SELECT actor FROM events WHERE api_key_id = CAST(:kid AS uuid)"
            ),
            {"kid": str(row.id)},
        )).scalars().all()
        assert stamped, "the keyed capture journalled no row naming its key"
        assert "t421-stamp" in stamped

    async def test_a_human_capture_stamps_no_key(self, client, session, auth_headers):
        """The counterpart: the stamp must be the caller's identity, not a
        constant that happens to be non-null."""
        from sqlalchemy import text as sql_text

        before = (await session.execute(
            sql_text("SELECT count(*) FROM events WHERE api_key_id IS NOT NULL")
        )).scalar_one()

        response = await client.post(
            "/api/v1/memories", json={"content": "human capture"}, headers=auth_headers
        )
        assert response.status_code in (200, 201, 202), response.text

        after = (await session.execute(
            sql_text("SELECT count(*) FROM events WHERE api_key_id IS NOT NULL")
        )).scalar_one()
        assert after == before, "a human capture must stamp no key"

    async def test_an_unkeyed_unauthenticated_call_is_still_refused(self, client):
        response = await client.post("/api/v1/memories", json={"content": "anonymous"})
        assert response.status_code == 401
