"""Watch mode — re-inject as the working context shifts (T4.06, doc 15 §3.5).

v1's cadence is session-start: one read and one idempotent file write per
session. Watch re-runs that same write when the project switches, a file opens,
or the declared context changes. Doc 15 §3.5 defers it "behind a measured need,
gated by a ``config`` flag", and the deferral is the design: a continuous
cadence adds a client-side loop and many more inject events, and the block
contract does not change to accommodate it because the write is
strip-before-rewrite idempotent already (§3.2).

**Watch is a cadence, not a second inject path.** It is
:func:`app.services.inject_fill.fill` under the operator's own
``token_budget``, exactly as session-start is. A refresh that computed its own
budget would exceed the operator's on every swap, and only on the installs that
turned watch on — the hardest shape to notice.

**Three refusals, and each one is the feature.** Off by default, so an install
that never asked for watch cannot be watched. Curbed wins, read fresh on every
refresh, because "the curb takes effect immediately" is precisely the claim
that a flag flipped between two swaps stops the second. An unknown trigger is
refused rather than recorded, because the journal is what a human reads to
explain a swap and a free-form cause is one nobody can search for.

**Nothing here writes a file.** The server does not know the client's
filesystem and must not appear to (T3.09's boundary): this returns the block's
items and the record of the push, and the client writes them into the path the
adapter names.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.services.inject_adapters import REFRESH_SESSION_START, resolve_adapter
from app.services.inject_fill import FillResult, fill
from app.services.inject_journal import record_inject
from app.services.layer_composition import ComposedResult

__all__ = [
    "REFRESH_SESSION_START",
    "REFRESH_WATCH",
    "WATCH_TRIGGERS",
    "PushCurbed",
    "WatchDisabled",
    "watch_refresh",
    "watch_enabled",
]

REFRESH_WATCH = "watch"

# The closed set of causes a re-inject may report. Closed for the same reason
# `EVENT_TYPES` is: these values land in a journal a human queries, and one
# misspelling is a swap that no search for its cause will ever return.
WATCH_TRIGGERS = frozenset({"project_changed", "file_opened", "context_changed"})

# The policy row the distribution door writes (`api/routes/distribution.py`).
# Read here rather than imported to avoid a service importing a route module;
# the key is asserted equal across the two by test.
DISTRIBUTION_CONFIG_KEY = "distribution_policy"

DEFAULT_TOKEN_BUDGET = 2000


class WatchDisabled(RuntimeError):
    """Watch is off for this install, which is the default.

    Raised rather than returning an empty block: an empty block is a real
    outcome — the budget admitted nothing — and a caller that could not tell
    the two apart would rewrite the managed block to nothing on an install
    that never enabled the mode.
    """


class PushCurbed(RuntimeError):
    """A human has stopped push, and this refresh stops with it."""


async def _policy(session: AsyncSession) -> dict[str, Any]:
    row = (
        await session.execute(
            select(Config).where(Config.key == DISTRIBUTION_CONFIG_KEY)
        )
    ).scalar_one_or_none()
    return row.value if row is not None and isinstance(row.value, dict) else {}


async def watch_enabled(session: AsyncSession) -> bool:
    """Whether this install has turned watch on. Default False.

    Its second reader is `inject_adapters.resolve_adapter`, which refuses the
    `watch` cadence while this is False. One flag read at two doors rather than
    two flags: a registry that kept refusing after the mode went on would make
    it enabled and unreachable, and one that accepted while off would make the
    flag decoration.
    """
    return bool((await _policy(session)).get("watch_enabled", False))


async def watch_refresh(
    session: AsyncSession,
    *,
    tool: str,
    trigger: str,
    result: ComposedResult,
    project: str = "default",
    actor: str | None = None,
) -> FillResult:
    """One watch re-inject: refuse, fill, journal. Does not commit.

    The order is load-bearing. Every refusal happens before the journal write,
    so a refused refresh leaves no record of a push that did not happen — the
    stream counts swaps the client actually received.
    """
    if trigger not in WATCH_TRIGGERS:
        raise ValueError(
            f"unknown watch trigger {trigger!r}; the recorded causes are "
            f"{sorted(WATCH_TRIGGERS)}. A free-form cause in the journal is a "
            f"swap no human can search for afterwards."
        )

    policy = await _policy(session)
    if not policy.get("watch_enabled", False):
        raise WatchDisabled(
            "watch mode is off for this install (doc 15 §3.5 gates it behind "
            f"`watch_enabled` in the {DISTRIBUTION_CONFIG_KEY} config row). "
            "v1 refreshes at session start only."
        )
    # Read here, on every refresh, rather than once per watch session: the curb
    # is a stop control, and one cached at the start of a watch loop would keep
    # pushing until whatever the client considers the next session.
    if policy.get("curbed", False):
        raise PushCurbed(
            "push is curbed; every target stops at once until a human releases it"
        )

    # Refuses an unknown tool, and refuses the cadence unless the flag is on —
    # the same flag this function already read, checked again at the door that
    # owns the transport facts.
    adapter = await resolve_adapter(session, tool, cadence=REFRESH_WATCH)

    budget = int(policy.get("token_budget", DEFAULT_TOKEN_BUDGET))
    out = fill(result, token_budget=budget)

    await record_inject(
        session,
        tool=adapter.tool,
        context_file=adapter.context_file,
        memory_ids=_ids_of(result, out, "memory"),
        fact_ids=_ids_of(result, out, "fact"),
        article_ids=_ids_of(result, out, "article"),
        budget_tokens=budget,
        tokens_used=out.tokens_used,
        project=project,
        actor=actor,
        trigger=trigger,
        cadence=REFRESH_WATCH,
    )
    return out


def _ids_of(result: ComposedResult, out: FillResult, id_kind: str) -> list[str]:
    """The ids of one layer that actually landed in the block.

    Derived from the fill's own item count per layer rather than from the
    composed rows: the budget is what decides which rows were pushed, and
    journalling the candidates rather than the survivors would record context
    the agent never received.
    """
    admitted = out.per_layer.get(_LAYER_OF[id_kind], 0)
    rows = [row for row in result.rows if row.id_kind == id_kind]
    return [str(row.id) for row in rows[:admitted]]


# `fill` counts per layer label, while a row names its kind; the two
# vocabularies meet here and nowhere else.
_LAYER_OF = {"fact": "L2", "article": "L3", "memory": "L0"}
