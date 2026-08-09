"""T3.11 — the per-tool adapter registry (doc 15 §3.3).

Three done-whens, and two of them are about refusing rather than doing:

1. Each adapter names the right file, and the mapping is a ``config`` row so a
   tool's convention change is an edit rather than a release.
2. An unknown tool is refused with a message, **not a best guess** — the
   failure that forbids is writing a managed block into a file the tool does
   not read (silent) or one another tool does (worse).
3. Refresh is session-start only; ``watch`` is T4.06's, and a cadence accepted
   here but unimplemented below would report a push that never happens.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest
from sqlalchemy import text

from app.services import inject_adapters as ia
from app.services.inject_adapters import (
    REFRESH_SESSION_START,
    UnknownTool,
    UnsupportedCadence,
    get_adapters,
    resolve_adapter,
)

pytestmark = pytest.mark.asyncio


async def _config(session, value: dict) -> None:
    await session.execute(
        text(
            "INSERT INTO config (key, value) VALUES (CAST(:k AS text), CAST(:v AS jsonb)) "
            "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value"
        ),
        {"k": ia.INJECT_ADAPTERS_CONFIG_KEY, "v": json.dumps(value)},
    )
    await session.flush()


# ─────────────── clause 1: the matrix, and it is configuration ───────────────


class TestTheMatrix:
    @pytest.mark.parametrize(
        "tool,context_file",
        [
            ("claude-code", "CLAUDE.md"),
            ("cursor", ".cursor/rules/darkmem.mdc"),
            ("codex", "AGENTS.md"),
            ("cline", ".clinerules/darkmem.md"),
        ],
    )
    async def test_each_v1_tool_names_doc_15_s_file(self, session, tool, context_file):
        adapter = await resolve_adapter(session, tool)
        assert adapter.context_file == context_file

    async def test_the_path_is_project_relative_never_absolute(self, session):
        """The server does not know the client's filesystem and must not appear
        to (T3.09's boundary). An absolute path here would read as one this
        process could open."""
        for adapter in (await get_adapters(session)).values():
            assert not adapter.context_file.startswith("/")

    async def test_a_config_row_can_move_a_tool_s_file(self, session):
        """Doc 15 §3.3's reason for the row: a workspace still on Cursor's
        legacy `.cursorrules` points the mapping at it rather than having the
        adapter guess between two paths."""
        await _config(session, {"cursor": {"context_file": ".cursorrules"}})

        adapter = await resolve_adapter(session, "cursor")

        assert adapter.context_file == ".cursorrules"
        # The override is per-field: nothing else about the entry is lost.
        assert adapter.mcp_config == ".cursor/mcp.json"

    async def test_a_config_row_can_add_a_tool_this_build_never_heard_of(
        self, session
    ):
        await _config(session, {"zed": {"context_file": ".zed/darkmem.md"}})

        adapter = await resolve_adapter(session, "zed")

        assert adapter.context_file == ".zed/darkmem.md"

    async def test_a_malformed_entry_is_dropped_loudly_not_raised(
        self, session, caplog
    ):
        """One bad row must not take the registry down — but a dropped entry
        must not look like a working one either, so it surfaces as UnknownTool
        at the door, which names what is known."""
        await _config(session, {"broken": {"mcp_config": "x"}, "alsobroken": "string"})

        with caplog.at_level("WARNING"):
            adapters = await get_adapters(session)

        assert "broken" not in adapters and "alsobroken" not in adapters
        assert "claude-code" in adapters, "the good entries survive"
        assert "context_file" in caplog.text

    async def test_one_marker_style_is_valid_in_every_v1_context_file(self, session):
        """Not a simplification but a fact about the target set: every v1 file
        is Markdown, so `inject_block`'s HTML-comment sentinels are valid in
        all four. A target with a different comment syntax is the seam this
        records — parameterising the marker before one exists is scaffolding.
        """
        markdownish = {".md", ".mdc", ".markdown"}
        for adapter in (await get_adapters(session)).values():
            assert Path(adapter.context_file).suffix in markdownish, adapter


# ─────────────── clause 2: an unknown tool is refused ───────────────


class TestAnUnknownToolIsRefused:
    async def test_it_raises_rather_than_returning_a_default(self, session):
        with pytest.raises(UnknownTool):
            await resolve_adapter(session, "some-editor-nobody-adapted")

    async def test_the_refusal_names_the_tools_that_are_known(self, session):
        """The caller's next move is to pick one or add a row, and they cannot
        do either from a bare failure."""
        with pytest.raises(UnknownTool) as refusal:
            await resolve_adapter(session, "unknown-tool")

        message = str(refusal.value)
        assert "claude-code" in message
        assert ia.INJECT_ADAPTERS_CONFIG_KEY in message

    async def test_no_near_miss_resolves_to_a_neighbour(self, session):
        """The specific guess this forbids: fuzzy-matching a tool name onto an
        adapter would write one tool's block into another tool's file."""
        for near in ("claude", "claude_code", "Claude-Code", "cursor-ide", ""):
            with pytest.raises(UnknownTool):
                await resolve_adapter(session, near)


# ─────────────── clause 3: session start only ───────────────


class TestTheCadence:
    async def test_watch_mode_is_refused_not_accepted_and_ignored(self, session):
        with pytest.raises(UnsupportedCadence):
            await resolve_adapter(session, "claude-code", cadence="watch")

    async def test_an_adapter_declaring_another_cadence_is_refused(self, session):
        """A config row cannot switch on an unimplemented feature either — the
        refusal belongs to the implementation's absence, not to the argument."""
        await _config(
            session, {"claude-code": {"context_file": "CLAUDE.md", "refresh": "watch"}}
        )

        with pytest.raises(UnsupportedCadence):
            await resolve_adapter(session, "claude-code")

    async def test_nothing_in_the_tree_schedules_an_inject(self):
        """The cadence claim, asserted where it can regress. `watch` being
        deferred means no job, cron or loop drives an inject; the client asks
        at session start. A scan, because a cadence nobody enforces is prose.
        """
        offenders: list[str] = []
        for path in sorted(Path("app").rglob("*.py")):
            tree = ast.parse(path.read_text())
            for node in ast.walk(tree):
                if not isinstance(node, ast.Call):
                    continue
                name = (
                    node.func.attr if isinstance(node.func, ast.Attribute)
                    else getattr(node.func, "id", "")
                )
                if name in {"register", "add_job", "schedule"}:
                    source = ast.get_source_segment(path.read_text(), node) or ""
                    if "inject" in source.lower():
                        offenders.append(f"{path}:{node.lineno}")

        assert not offenders, (
            "inject must be pulled by the client at session start, never "
            f"scheduled server-side (watch mode is T4.06's): {offenders}"
        )
