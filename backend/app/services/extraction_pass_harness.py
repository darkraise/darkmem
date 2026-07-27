"""Ordered-pass harness for the deterministic extraction post-processor.

The post-processor is a fixed sequence of pure passes, not a bag of
filters: several orderings are load-bearing (doc 06 §4), so the sequence
is declared as data and its constraints are checked at import time rather
than left to convention.
"""

from __future__ import annotations

from collections.abc import Callable, Collection, Iterable, Sequence
from dataclasses import dataclass, field, replace

__all__ = [
    "CleanState",
    "Pass",
    "RunsBefore",
    "StraddlesPivot",
    "OrderingConstraint",
    "RegistryContractError",
    "apply_pass",
    "run_passes",
    "validate_registry",
    "indices_of",
    "index_of",
    "without",
]


class RegistryContractError(RuntimeError):
    """A pass registry violates its declared shape or ordering contract."""


@dataclass(frozen=True)
class CleanState:
    """Everything the passes read or write, threaded through the sequence.

    Frozen so a pass cannot smuggle state forward: each one returns a new
    state built from its declared writes.
    """

    content: str = ""
    entities: list[dict] = field(default_factory=list)
    relationships: list[dict] = field(default_factory=list)
    # The entity list exactly as the model emitted it. ``_build_name_remap``
    # needs the pre-shaping names to map an edge endpoint onto its survivor.
    raw_entities: list[dict] = field(default_factory=list)
    negated_names: Collection[str] = ()
    relation_rescue: bool = True


_STATE_FIELDS: frozenset[str] = frozenset(CleanState.__dataclass_fields__)


@dataclass(frozen=True)
class Pass:
    """One deterministic step: a pure function plus its state bindings.

    ``reads`` names the ``CleanState`` fields passed as positional
    arguments, ``writes`` the fields the return value lands in (a tuple
    return when there is more than one). ``gate``, when set, names a
    boolean state field that must be true for the pass to run.
    """

    name: str
    stage: str
    fn: Callable[..., object]
    reads: tuple[str, ...]
    writes: tuple[str, ...]
    gate: str | None = None


@dataclass(frozen=True)
class RunsBefore:
    earlier: str
    later: str
    why: str


@dataclass(frozen=True)
class StraddlesPivot:
    name: str
    pivot: str
    why: str


OrderingConstraint = RunsBefore | StraddlesPivot


def indices_of(registry: Sequence[Pass], name: str) -> list[int]:
    return [i for i, p in enumerate(registry) if p.name == name]


def index_of(registry: Sequence[Pass], name: str) -> int:
    found = indices_of(registry, name)
    if not found:
        raise KeyError(name)
    return found[0]


def without(registry: Sequence[Pass], *names: str) -> tuple[Pass, ...]:
    """The same sequence minus every occurrence of ``names``.

    Makes a single pass individually reversible: drop it, re-run the
    chain, measure the delta.
    """
    dropped = set(names)
    return tuple(p for p in registry if p.name not in dropped)


def validate_registry(
    registry: Sequence[Pass],
    constraints: Iterable[OrderingConstraint] = (),
) -> None:
    """Raise ``RegistryContractError`` unless the sequence holds its contract."""
    for p in registry:
        if not p.reads:
            raise RegistryContractError(f"pass {p.name!r} declares no reads")
        if not p.writes:
            raise RegistryContractError(f"pass {p.name!r} declares no writes")
        for kind, names in (("reads", p.reads), ("writes", p.writes)):
            unknown = [n for n in names if n not in _STATE_FIELDS]
            if unknown:
                raise RegistryContractError(
                    f"pass {p.name!r} {kind} unknown state field(s): {unknown}"
                )
        if p.gate is not None and p.gate not in _STATE_FIELDS:
            raise RegistryContractError(
                f"pass {p.name!r} gates on unknown state field {p.gate!r}"
            )

    for c in constraints:
        if isinstance(c, RunsBefore):
            earlier = indices_of(registry, c.earlier)
            later = indices_of(registry, c.later)
            if not earlier or not later:
                raise RegistryContractError(
                    f"ordering constraint names a missing pass: "
                    f"{c.earlier!r} before {c.later!r}"
                )
            if max(earlier) >= min(later):
                raise RegistryContractError(
                    f"{c.earlier!r} must run before {c.later!r}: {c.why}"
                )
        else:
            spots = indices_of(registry, c.name)
            pivot = indices_of(registry, c.pivot)
            if not spots or not pivot:
                raise RegistryContractError(
                    f"ordering constraint names a missing pass: "
                    f"{c.name!r} straddling {c.pivot!r}"
                )
            if not (min(spots) < min(pivot) and max(spots) > max(pivot)):
                raise RegistryContractError(
                    f"{c.name!r} must run both before and after {c.pivot!r}: {c.why}"
                )


def apply_pass(p: Pass, state: CleanState) -> CleanState:
    if p.gate is not None and not getattr(state, p.gate):
        return state
    result = p.fn(*(getattr(state, name) for name in p.reads))
    if len(p.writes) == 1:
        updates: dict[str, object] = {p.writes[0]: result}
    else:
        if not isinstance(result, tuple) or len(result) != len(p.writes):
            raise RegistryContractError(
                f"pass {p.name!r} must return a {len(p.writes)}-tuple "
                f"for writes {p.writes}"
            )
        updates = dict(zip(p.writes, result, strict=True))
    return replace(state, **updates)


def run_passes(registry: Sequence[Pass], state: CleanState) -> CleanState:
    for p in registry:
        state = apply_pass(p, state)
    return state
