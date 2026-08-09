"""The per-tool adapter registry (doc 15 §3.3) — T3.11.

Each target tool reads a project-root context file at session start, and that
uniformity is why the managed file block is v1's push transport: it needs no
per-tool push machinery. What differs per tool is *which file*, so this module
answers exactly one question — given a tool name, which file does its block
live in — and nothing else.

**The mapping is a ``config`` row, not code constants, and doc 15 §3.3 says
why:** each tool's context-file convention can change with that tool's own
releases, so treating the mapping as configuration keeps such a change a config
edit rather than a release. :data:`DEFAULT_ADAPTERS` is the committed starting
point the row merges over — the same shape ``feature_flags`` and the ranking
config use, so an operator adding a tool never has to wait for a deploy.

**An unknown tool is refused, never guessed.** There is no plausible default
path: writing a block into a file a tool does not read is silent failure (the
human sees nothing and nothing reports why), and writing into a *wrong* file
that some tool does read is worse. The refusal names the tools that are known,
because the caller's next move is either to pick one or to add a row.

**One marker style serves all four**, and that is a fact about the target set
rather than a simplification: every v1 context file is Markdown, so
``inject_block``'s HTML-comment sentinels are valid in all of them. A tool with
a different comment syntax needs the marker parameterised — recorded here as
the seam rather than built, since no such target exists (invariant 23).

**Cadence is session start only.** ``watch`` mode is Phase 4's (T4.06), so this
module declares the cadence it supports and refuses any other, rather than
accepting a parameter it has no implementation for. Nothing in this tree
schedules an inject; a test asserts that, because a cadence nobody enforces is
a comment.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config

logger = logging.getLogger(__name__)

__all__ = [
    "INJECT_ADAPTERS_CONFIG_KEY",
    "REFRESH_SESSION_START",
    "Adapter",
    "UnknownTool",
    "UnsupportedCadence",
    "get_adapters",
    "resolve_adapter",
]

INJECT_ADAPTERS_CONFIG_KEY = "inject_adapters"

# The only cadence v1 implements. `watch` is T4.06's, and a parameter accepted
# but unimplemented is worse than one refused: the caller believes it took.
REFRESH_SESSION_START = "session_start"


@dataclass(frozen=True)
class Adapter:
    """One tool's transport facts.

    ``context_file`` is a **project-relative** path the client resolves against
    its own workspace. It is never absolute and never resolved here: the server
    does not know the client's filesystem and must not appear to (T3.09's
    boundary), so this is a name the client interprets, not a location this
    process could open.
    """

    tool: str
    context_file: str
    mcp_config: str
    refresh: str = REFRESH_SESSION_START


# Doc 15 §3.3's matrix, verbatim. Legacy paths are recorded in the comment
# rather than as alternates: an adapter that could resolve to two files makes
# "which file did the block land in" unanswerable without looking.
DEFAULT_ADAPTERS: dict[str, dict[str, str]] = {
    "claude-code": {
        "context_file": "CLAUDE.md",
        "mcp_config": ".mcp.json",
    },
    # Legacy `.cursorrules` predates the rules directory; a workspace still on
    # it points this row at that path rather than having the adapter guess.
    "cursor": {
        "context_file": ".cursor/rules/darkmem.mdc",
        "mcp_config": ".cursor/mcp.json",
    },
    "codex": {
        "context_file": "AGENTS.md",
        "mcp_config": "~/.codex/config.toml",
    },
    "cline": {
        "context_file": ".clinerules/darkmem.md",
        "mcp_config": "cline_mcp_settings.json",
    },
}


class UnknownTool(LookupError):
    """No adapter for that tool, and no guess offered.

    Doc 15 §3.3's matrix has an explicit *unlisted tool* row served by the shim
    fallback, not by this registry inventing a path. Guessing writes a managed
    block into a file the tool may not read — silent failure — or into one
    another tool does, which is worse.
    """


class UnsupportedCadence(ValueError):
    """A refresh cadence v1 does not implement (doc 15 §3.3; T4.06 owns watch)."""


async def get_adapters(session: AsyncSession) -> dict[str, Adapter]:
    """The effective registry: the ``config`` row merged over the defaults.

    A row may override a shipped tool's path or add one this build never heard
    of — that is the point of it being configuration. Malformed entries degrade
    loudly and are dropped rather than raising: one bad row must not take the
    whole registry down, and a dropped entry surfaces as ``UnknownTool`` at the
    door, which names what *is* known.
    """
    result = await session.execute(
        select(Config).where(Config.key == INJECT_ADAPTERS_CONFIG_KEY)
    )
    row = result.scalar_one_or_none()
    raw = row.value if row is not None and isinstance(row.value, dict) else {}

    merged: dict[str, dict[str, str]] = {k: dict(v) for k, v in DEFAULT_ADAPTERS.items()}
    for tool, entry in raw.items():
        if not isinstance(entry, dict):
            logger.warning(
                "%s: entry for %r is %s, not an object; ignoring",
                INJECT_ADAPTERS_CONFIG_KEY, tool, type(entry).__name__,
            )
            continue
        merged.setdefault(tool, {}).update(
            {k: v for k, v in entry.items() if isinstance(v, str)}
        )

    adapters: dict[str, Adapter] = {}
    for tool, entry in merged.items():
        context_file = entry.get("context_file")
        if not context_file:
            logger.warning(
                "%s: entry for %r has no context_file; dropping it — an adapter "
                "with no file cannot say where the block goes",
                INJECT_ADAPTERS_CONFIG_KEY, tool,
            )
            continue
        adapters[tool] = Adapter(
            tool=tool,
            context_file=context_file,
            mcp_config=entry.get("mcp_config", ""),
            refresh=entry.get("refresh", REFRESH_SESSION_START),
        )
    return adapters


async def resolve_adapter(
    session: AsyncSession, tool: str, *, cadence: str = REFRESH_SESSION_START
) -> Adapter:
    """The adapter for ``tool``, or a refusal naming what is known."""
    if cadence != REFRESH_SESSION_START:
        raise UnsupportedCadence(
            f"refresh cadence {cadence!r} is not implemented; v1 refreshes at "
            f"{REFRESH_SESSION_START!r} only, and watch mode is T4.06's. A "
            f"cadence accepted here and unimplemented below would report a "
            f"push that never happens."
        )

    adapters = await get_adapters(session)
    adapter = adapters.get(tool)
    if adapter is None:
        raise UnknownTool(
            f"no inject adapter for {tool!r}; known tools are "
            f"{sorted(adapters)}. Add a row to the {INJECT_ADAPTERS_CONFIG_KEY} "
            f"config entry rather than guessing a path — a block written into a "
            f"file the tool does not read fails silently."
        )
    if adapter.refresh != REFRESH_SESSION_START:
        raise UnsupportedCadence(
            f"adapter {tool!r} declares refresh {adapter.refresh!r}, which v1 "
            f"does not implement"
        )
    return adapter
