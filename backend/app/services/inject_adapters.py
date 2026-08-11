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
from pathlib import PurePosixPath as Path

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
    "get_registry",
    "reject_reason",
    "resolve_adapter",
]

INJECT_ADAPTERS_CONFIG_KEY = "inject_adapters"

# The fields an entry may carry. A row naming anything else is a typo, and a
# typo that is silently ignored is a config the operator believes took effect.
_ADAPTER_FIELDS = frozenset({"context_file", "mcp_config", "refresh"})

# Every v1 context file is Markdown, which is what makes one marker style
# serve all four. Enforced on config rows too, not just on the defaults.
MARKDOWN_SUFFIXES = frozenset({".md", ".mdc", ".markdown"})

# The cadence every install implements. `watch` (T4.06) is the second, and it
# is reachable only while `watch_enabled` is on: a parameter accepted but
# unimplemented is worse than one refused, because the caller believes it took.
REFRESH_SESSION_START = "session_start"
REFRESH_WATCH = "watch"


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
    """A refresh cadence this install does not serve (doc 15 §3.3).

    Two shapes reach it. A cadence this build has no implementation for is
    refused outright; `watch` is implemented (T4.06) but refused while the
    install has not enabled it, so a client cannot obtain a watch-cadence
    adapter for an install that never asked to be watched.
    """


def reject_reason(context_file: str | None) -> str | None:
    """Why this ``context_file`` cannot be an adapter target, or ``None``.

    One predicate with two readers — the registry below and
    :func:`get_registry`, whose second return value the distribution surface
    renders. A second copy of these rules would be the drift that lets the
    screen say a row was kept while the writer dropped it.
    """
    if not context_file:
        return "no context_file — an adapter with no file cannot say where the block goes"
    if (
        context_file.startswith("/")
        or context_file.startswith("~")
        or ".." in Path(context_file).parts
        or (len(context_file) > 1 and context_file[1] == ":")
    ):
        return (
            f"{context_file!r} is not a project-relative path — it is resolved "
            "against the client's workspace and an absolute one escapes it"
        )
    return None


async def _resolve(
    session: AsyncSession,
) -> tuple[dict[str, Adapter], dict[str, str]]:
    """The registry and the rows it refused, from one pass.

    Split out so ``get_adapters`` keeps its shape for every existing caller
    while the surface can still ask what was dropped. Re-deriving the
    rejections from a second pass would mean a second copy of the merge.
    """
    result = await session.execute(
        select(Config).where(Config.key == INJECT_ADAPTERS_CONFIG_KEY)
    )
    row = result.scalar_one_or_none()
    raw = row.value if row is not None and isinstance(row.value, dict) else {}

    merged: dict[str, dict[str, str]] = {k: dict(v) for k, v in DEFAULT_ADAPTERS.items()}
    rejected: dict[str, str] = {}
    for tool, entry in raw.items():
        if not isinstance(entry, dict):
            # Served, not merely logged: an operator whose entry is a string
            # rather than an object watches their row vanish exactly as one
            # with a bad `context_file` did, and the reason has the same right
            # to reach the screen. The sentence is finished after the merge —
            # a *non-dict* override of a shipped tool leaves that tool served
            # at its default, and calling that "no block is written" would be
            # the screen asserting something not in force.
            #
            # **This branch only.** The comment used to say "a malformed
            # override", which is false one branch down (branch review M-8):
            # a well-typed-but-invalid override — `{"context_file":
            # "/etc/passwd"}`, or an empty one — *replaces* the default's
            # field in `merged`, so `reject_reason` below drops the tool from
            # `adapters` entirely and the default is **not** in force. The
            # wire stays honest either way (the tool is simply absent from
            # `targets`); what was wrong was the general claim, on the one
            # surface whose fix round was about the screen not asserting what
            # is not in force.
            rejected[tool] = (
                f"the entry is {type(entry).__name__}, not an object — an "
                "adapter is a mapping of context_file / mcp_config / refresh"
            )
            logger.warning(
                "%s: entry for %r is %s, not an object; ignoring",
                INJECT_ADAPTERS_CONFIG_KEY, tool, type(entry).__name__,
            )
            continue
        # Every discarded field is logged. The first version filtered silently,
        # so a non-string value or a mistyped key left the shipped default in
        # place while the operator believed they had moved a tool's file --
        # blocks keep landing in the old one, with nothing said. That directly
        # contradicted this module's own "degrade loudly" contract.
        usable: dict[str, str] = {}
        for field, value in entry.items():
            if field not in _ADAPTER_FIELDS:
                logger.warning(
                    "%s: entry for %r has unknown field %r; ignoring. Known "
                    "fields: %s",
                    INJECT_ADAPTERS_CONFIG_KEY, tool, field, sorted(_ADAPTER_FIELDS),
                )
                continue
            if not isinstance(value, str):
                logger.warning(
                    "%s: entry for %r has %s = %r, which is not a string; "
                    "ignoring that field and keeping the default",
                    INJECT_ADAPTERS_CONFIG_KEY, tool, field, value,
                )
                continue
            usable[field] = value
        merged.setdefault(tool, {}).update(usable)

    adapters: dict[str, Adapter] = {}
    for tool, entry in merged.items():
        context_file = entry.get("context_file")
        # The invariants the docstring states, enforced at the door a config
        # row comes through rather than only over the committed defaults.
        # `Path(workspace) / "/etc/passwd"` **is** `/etc/passwd`, so an
        # absolute path is not a cosmetic violation.
        rejection = reject_reason(context_file)
        if rejection is not None and context_file:
            rejected[tool] = rejection
            logger.warning(
                "%s: entry for %r has context_file %r, which is not a "
                "project-relative path; dropping it — this path is resolved "
                "against the client's workspace and an absolute one escapes it",
                INJECT_ADAPTERS_CONFIG_KEY, tool, context_file,
            )
            continue
        suffix = Path(context_file).suffix if context_file else ""
        if context_file and suffix and suffix not in MARKDOWN_SUFFIXES:
            # **Warned, not dropped**, and the difference is the config row's
            # whole purpose: doc 15 §3.3 makes this operator-configurable so a
            # tool changing its convention is an edit rather than a release,
            # and refusing an unfamiliar suffix would put the operator back
            # behind a deploy. An extensionless name is not warned at all --
            # `.cursorrules` is a documented legacy target and the dotfile
            # convention is normal here.
            logger.warning(
                "%s: entry for %r targets %r, whose suffix is not Markdown. "
                "The managed block's markers are HTML comments and may render "
                "literally there; parameterising them is the recorded seam "
                "(T3.11) if this target is here to stay",
                INJECT_ADAPTERS_CONFIG_KEY, tool, context_file,
            )
        if not context_file:
            rejected[tool] = reject_reason(context_file) or ""
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

    # A rejected entry for a tool that still resolves is an override that did
    # not take effect, not a target that vanished. Every other rejection path
    # leaves its tool absent from `adapters`; this is the one that does not.
    for tool in rejected:
        if tool in adapters:
            rejected[tool] += (
                f" — the shipped default is still in force, so {tool} is still "
                "served at its committed path"
            )
    return adapters, rejected


async def get_adapters(session: AsyncSession) -> dict[str, Adapter]:
    """The effective registry: the ``config`` row merged over the defaults.

    A row may override a shipped tool's path or add one this build never heard
    of — that is the point of it being configuration. Malformed entries degrade
    loudly and are dropped rather than raising: one bad row must not take the
    whole registry down, and a dropped entry surfaces as ``UnknownTool`` at the
    door, which names what *is* known.
    """
    adapters, _ = await _resolve(session)
    return adapters


async def get_registry(
    session: AsyncSession,
) -> tuple[dict[str, Adapter], dict[str, str]]:
    """Both halves for the one caller that needs both.

    Two entry points asking ``_resolve`` separately would be two SELECTs of the
    same ``config`` row and two merges per request. The docstring above says a
    second pass "would mean a second copy of the merge" — the copy was avoided,
    the pass was not, and this is where that is paid once.
    """
    return await _resolve(session)





async def resolve_adapter(
    session: AsyncSession, tool: str, *, cadence: str = REFRESH_SESSION_START
) -> Adapter:
    """The adapter for ``tool``, or a refusal naming what is known.

    ``watch`` passes only while the install enabled it. The flag is read here
    as well as in `inject_watch.watch_refresh` — one flag, two doors, on
    purpose: this is the door that hands out transport facts, and an adapter
    obtained at a cadence the install never enabled is a client told it may
    watch.
    """
    if cadence not in (REFRESH_SESSION_START, REFRESH_WATCH):
        raise UnsupportedCadence(
            f"refresh cadence {cadence!r} is not implemented; the cadences are "
            f"{REFRESH_SESSION_START!r} and {REFRESH_WATCH!r}. A cadence "
            f"accepted here and unimplemented below would report a push that "
            f"never happens."
        )
    watching = await _watch_enabled(session)
    if cadence == REFRESH_WATCH and not watching:
        raise UnsupportedCadence(
            f"refresh cadence {REFRESH_WATCH!r} is off for this install; doc 15 "
            f"§3.5 gates it behind `watch_enabled` on the distribution policy. "
            f"v1 refreshes at {REFRESH_SESSION_START!r} until a human turns it on."
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
    if adapter.refresh not in (REFRESH_SESSION_START, REFRESH_WATCH):
        raise UnsupportedCadence(
            f"adapter {tool!r} declares refresh {adapter.refresh!r}, which this "
            f"build does not implement"
        )
    if adapter.refresh == REFRESH_WATCH and not watching:
        # A config row must not switch on a mode the policy has off. The two
        # are different questions — "which cadence does this tool want" and
        # "may this install be watched" — and the second is the human's.
        raise UnsupportedCadence(
            f"adapter {tool!r} declares refresh {REFRESH_WATCH!r}, but watch is "
            f"off for this install. Turn it on with `watch_enabled` on the "
            f"distribution policy; an adapter row cannot enable it by itself."
        )
    return adapter


async def _watch_enabled(session: AsyncSession) -> bool:
    """The distribution policy's watch flag, imported late.

    `inject_watch` imports this module for the cadence constants, so a
    module-scope import back would be a cycle. The flag has one owner and this
    reads it there rather than growing a second copy of the default.
    """
    from app.services.inject_watch import watch_enabled

    return await watch_enabled(session)
