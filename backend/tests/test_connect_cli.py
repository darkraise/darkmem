"""T3.13 — `darkmem connect <tool>` (doc 15 §5).

Three done-whens, and the middle one is a rule rather than a behaviour:

1. Handshake verification runs and reports the **concrete** failure.
2. A foreign-Host ``421`` is reported as "extend ``MCP_ALLOWED_HOSTS``" —
   **never worked around, never by disabling the protection** (invariant 20).
3. Re-running is idempotent and does not duplicate config entries.

The second is tested as a scan as well as a behaviour: a suggestion to turn
the allowlist off is the kind of thing that gets added later "just for LAN
debugging", and the moment a tool prints it, someone does it.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from app.services import client_connect as cc
from app.services.client_connect import (
    DEFAULT_MCP_URL,
    SERVER_KEY,
    HandshakeFailed,
    diagnose,
    merge_json_config,
    merge_toml_config,
    verify_handshake,
)

pytestmark = pytest.mark.asyncio


# ─────────────── clause 3: re-running is idempotent ───────────────


class TestIdempotence:
    async def test_writing_twice_leaves_one_entry(self):
        once = merge_json_config("")
        twice = merge_json_config(once)

        assert once == twice
        assert list(json.loads(twice)["mcpServers"]) == [SERVER_KEY]

    async def test_a_re_run_updates_the_url_in_place(self):
        """Not two entries under different keys: a config whose effective
        server depends on which entry the tool reads first is worse than one
        that is simply wrong."""
        first = merge_json_config("", url="http://localhost:8000/mcp/")
        second = merge_json_config(first, url="http://192.168.0.5:8000/mcp/")

        servers = json.loads(second)["mcpServers"]
        assert list(servers) == [SERVER_KEY]
        assert servers[SERVER_KEY]["url"] == "http://192.168.0.5:8000/mcp/"

    async def test_another_tool_s_servers_are_left_alone(self):
        """This edits a file the human also owns."""
        existing = json.dumps({
            "mcpServers": {"someone-else": {"command": "their-server"}},
            "unrelatedTopLevelKey": {"keep": True},
        })

        merged = json.loads(merge_json_config(existing))

        assert merged["mcpServers"]["someone-else"] == {"command": "their-server"}
        assert merged["unrelatedTopLevelKey"] == {"keep": True}

    async def test_a_malformed_config_raises_rather_than_being_replaced(self):
        """The one case where "just make it work" destroys data the tool does
        not own: overwriting a hand-edited file that happens to be invalid."""
        with pytest.raises(ValueError, match="not valid JSON"):
            merge_json_config("{ this is not json")

    async def test_the_toml_writer_is_idempotent_too(self):
        once = merge_toml_config("")
        twice = merge_toml_config(once)

        assert once == twice
        assert once.count(f"[mcp_servers.{SERVER_KEY}]") == 1

    async def test_the_toml_writer_preserves_comments_and_other_tables(self):
        """Python ships a TOML reader and no writer, so a parse-and-dump would
        re-emit a hand-maintained file and lose its comments. Only our own
        table is replaced."""
        existing = (
            "# my codex config\n"
            "model = \"gpt-5\"\n\n"
            "[mcp_servers.other]\n"
            "url = \"http://elsewhere\"\n"
        )

        merged = merge_toml_config(existing)

        assert "# my codex config" in merged
        assert '[mcp_servers.other]' in merged
        assert 'url = "http://elsewhere"' in merged
        assert f"[mcp_servers.{SERVER_KEY}]" in merged

    async def test_a_re_run_replaces_the_toml_table_rather_than_appending(self):
        first = merge_toml_config("", url="http://localhost:8000/mcp/")
        second = merge_toml_config(first, url="http://192.168.0.5:8000/mcp/")

        assert second.count(f"[mcp_servers.{SERVER_KEY}]") == 1
        assert "192.168.0.5" in second
        assert "localhost" not in second


# ─────────────── clause 1: the handshake, and what it reports ───────────────


class TestTheHandshake:
    async def test_it_drives_the_real_sequence(self):
        """A reachable port proves neither that the endpoint speaks MCP nor
        that it will answer this client's Host, which is why doc 15 §5 asks
        for the handshake rather than a ping."""
        seen: list[str] = []

        async def call(method, params):
            seen.append(method)
            if method == "tools/list":
                return {"tools": [{"name": "memory_search"}, {"name": "memory_add"}]}
            return {}

        tools = await verify_handshake(call)

        assert seen == ["initialize", "notifications/initialized", "tools/list"]
        assert tools == ["memory_search", "memory_add"]

    async def test_a_server_that_lists_no_tools_is_not_connected(self):
        """The failure this catches: something answers at the URL and speaks
        the protocol, but it is not darkmem's MCP surface."""
        async def call(method, params):
            return {"tools": []} if method == "tools/list" else {}

        with pytest.raises(HandshakeFailed, match="listed no tools"):
            await verify_handshake(call)

    async def test_the_transport_error_reaches_the_caller(self):
        async def call(method, params):
            raise ConnectionRefusedError("connection refused")

        with pytest.raises(ConnectionRefusedError):
            await verify_handshake(call)


class TestTheDiagnosis:
    async def test_a_421_names_the_allowlist_and_the_server_side_fix(self):
        message = diagnose(421, host="192.168.0.195:8000")

        assert "MCP_ALLOWED_HOSTS" in message
        assert "192.168.0.195:8000" in message
        # Named as protection working, not as an error to route around.
        assert "protection" in message.lower()

    async def test_the_421_diagnosis_never_suggests_disabling_the_check(self):
        """Invariant 20's explicit anti-pattern."""
        message = diagnose(421, host="host:8000").lower()

        for forbidden in ("disable", "turn off", "mcp_allowed_hosts=*", 'set it to "*"'):
            assert forbidden not in message

    @pytest.mark.parametrize(
        "status,expected",
        [(404, "no MCP endpoint"), (401, "credential"), (403, "credential"),
         (500, "answered 500")],
    )
    async def test_each_failure_names_its_own_cause(self, status, expected):
        assert expected in diagnose(status, host="localhost:8000")

    async def test_an_unreachable_server_says_so_rather_than_blaming_the_config(self):
        message = diagnose(None, host="localhost:8000", error="connection refused")
        assert "could not reach" in message and "connection refused" in message


# ─────────────── invariant 20, as a scan ───────────────


async def test_no_module_suggests_disabling_the_host_allowlist():
    """The rule, where it can regress rather than only where it was written.

    A "just disable the allowlist" hint is exactly the thing added later for
    LAN debugging, and the moment a tool prints it, someone does it. The scan
    looks for the suggestion in prose the user could see, not for the constant
    itself — `MCP_ALLOWED_HOSTS` is named all over the codebase legitimately.
    """
    suggestion = re.compile(
        r"(disable|turn off|bypass)[^.\n]{0,40}(allowlist|host check|rebinding)",
        re.I,
    )
    offenders: list[str] = []
    for path in sorted(Path("app").rglob("*.py")):
        for number, line in enumerate(path.read_text().splitlines(), 1):
            if suggestion.search(line):
                offenders.append(f"{path}:{number}: {line.strip()}")

    assert not offenders, (
        "a LAN 421 is fixed by extending MCP_ALLOWED_HOSTS, never by "
        f"disabling the protection (invariant 20):\n  " + "\n  ".join(offenders)
    )


async def test_the_default_url_is_loopback():
    """Loopback is always allowed by the Host allowlist, so the default path
    needs no allowlist entry at all — a non-loopback host is opt-in and comes
    with the reminder that the server must permit it."""
    assert DEFAULT_MCP_URL.startswith("http://localhost:")
    assert cc.render_server_entry()["url"] == DEFAULT_MCP_URL
