"""The isolation probe's metric, stated as code before any run (T1.35, doc 20 §4).

G-B's third number is "zero unlabelled cross-project or superseded rows on
every channel". This module is the whole definition of what counts, kept free
of app and database imports so the bar can be unit-tested and read on its own.

A *sighting* is one row of memory-derived data observed crossing one front
door, together with the scope the request carried and the labels the row
itself carried. Classification is per row, one verdict each:

- ``V1`` — scope breach. The request carried a scope (an explicit project or
  status parameter, a scope the service derives from the addressed row, a
  repository id, or the active-fingerprint constraint) and the row lies
  outside it. Labels never excuse a V1: a predicate that was promised in SQL
  and did not hold is a leak however self-describing the row is. Archived
  rows are always V1 — no probed surface accepts an include-archived request.
- ``V2`` — unlabelled escape. The request was legitimately wide on the
  breached axis (an operator-wide surface, or a scoped surface whose ratified
  default is every project) and the row is cross-project or non-active, but
  does not itself name the project / lifecycle state it came from. A labelled
  wide row is the ratified design (T1.29e); an unlabelled one is what the bar
  counts (the brief's Ruling 5).
- ``I1`` — id-only exposure, reported but not counted. ``memory_ids`` arrays,
  crossref lists and relation edges reveal *existence* across scope without
  content. T1.29d/e recorded these as deliberate (entities are not
  memory-scoped; trimming the array breaks the neighbour derivation) and left
  the product question open. Counting them would convert an explicitly parked
  decision into a gate failure by fiat; hiding them would bury the openness.
  They are therefore a separate reported number.
- ``I2`` — retention snapshot, reported but not counted. Content persisted at
  write time into an append-only store (the events journal, chat citation
  snippets) that outlives deletion or supersession of its memory. T1.29e
  escalated retention to the human; the serve-time scope of those stores is
  still probed normally (an events read that ignored its project parameter
  would be V1).
- ``OK`` — in scope, or wide-and-labelled.

Cross-project on a wide read is judged against the probe's observer project:
the probe reads as a single operator homed in one project, so a wide row from
another project must arrive naming that project. The bar is the count of V1
plus V2 across every surface; the gate clears only at exactly zero.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum

SENTINEL_PREFIX = "ISOPRB"

_SENTINEL_RE = re.compile(rf"{SENTINEL_PREFIX}-([a-z0-9_]+)")


def sentinel(key: str) -> str:
    """The per-fixture content marker. It leads the content string so that an
    80-char preview still carries it, and it is scanned out of raw response
    bodies so a row crossing through a field no driver enumerated still
    counts (the preview leaks of Ruling 4 were exactly that shape)."""
    if not re.fullmatch(r"[a-z0-9_]+", key):
        raise ValueError(f"sentinel key {key!r} would not survive the scan regex")
    return f"{SENTINEL_PREFIX}-{key}"


def scan_sentinels(body: str) -> set[str]:
    return set(_SENTINEL_RE.findall(body or ""))


class Verdict(str, Enum):
    OK = "OK"
    V1 = "V1"
    V2 = "V2"
    I1 = "I1"
    I2 = "I2"


COUNTED = (Verdict.V1, Verdict.V2)


@dataclass(frozen=True)
class Sighting:
    """One observed row crossing one front door."""

    surface: str
    door: str
    case: str
    row: str
    kind: str = "content"  # "content" | "preview" | "id"
    true_project: str | None = None
    true_status: str | None = None  # None = the row has no memory lifecycle
    archived: bool = False
    requested_project: str | None = None  # None = wide on the project axis
    requested_statuses: tuple[str, ...] | None = None  # None = wide on status
    label_project: bool = False  # the row itself names its true project
    label_status: bool = False  # the row itself names its true status
    retention: bool = False
    # A breach the axis model cannot express: a sentinel found in a raw
    # response body outside every row the driver enumerated, a row served
    # out of an inactive fingerprint partition, or an enumeration under an
    # absent partition. Always V1 — the probe fails loud rather than
    # letting an unmodelled crossing pass.
    forced_v1_reason: str | None = None


@dataclass(frozen=True)
class Classified:
    sighting: Sighting
    verdict: Verdict
    reasons: tuple[str, ...] = ()


def classify(s: Sighting, observer_project: str) -> Classified:
    if s.forced_v1_reason:
        return Classified(s, Verdict.V1, (s.forced_v1_reason,))
    if s.kind == "id":
        return Classified(s, Verdict.I1, ("id-only exposure",))
    if s.retention:
        return Classified(s, Verdict.I2, ("retention snapshot",))

    breaches: list[str] = []
    if s.archived:
        breaches.append("archived row returned")
    if s.requested_project is not None and s.true_project != s.requested_project:
        breaches.append(
            f"project {s.true_project!r} outside requested {s.requested_project!r}"
        )
    if (
        s.requested_statuses is not None
        and s.true_status is not None
        and s.true_status not in s.requested_statuses
    ):
        breaches.append(
            f"status {s.true_status!r} outside requested {s.requested_statuses!r}"
        )
    if breaches:
        return Classified(s, Verdict.V1, tuple(breaches))

    escapes: list[str] = []
    if (
        s.requested_project is None
        and s.true_project is not None
        and s.true_project != observer_project
        and not s.label_project
    ):
        escapes.append(f"cross-project row from {s.true_project!r} without a project label")
    if (
        s.requested_statuses is None
        and s.true_status is not None
        and s.true_status != "active"
        and not s.label_status
    ):
        escapes.append(f"{s.true_status} row without a status label")
    if escapes:
        return Classified(s, Verdict.V2, tuple(escapes))

    return Classified(s, Verdict.OK)


@dataclass
class ProbeReport:
    observer_project: str
    classified: list[Classified] = field(default_factory=list)
    surfaces_driven: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add(self, sightings: list[Sighting]) -> None:
        for s in sightings:
            self.classified.append(classify(s, self.observer_project))

    @staticmethod
    def _stable_order(c: Classified) -> tuple:
        s = c.sighting
        return (s.surface, s.door, s.case, s.row)

    def violations(self) -> list[Classified]:
        # Sorted so two runs over the same code render identically even where
        # a queue orders by near-identical timestamps.
        return sorted(
            (c for c in self.classified if c.verdict in COUNTED),
            key=self._stable_order,
        )

    def informational(self) -> list[Classified]:
        return sorted(
            (c for c in self.classified if c.verdict in (Verdict.I1, Verdict.I2)),
            key=self._stable_order,
        )

    def count(self) -> int:
        return len(self.violations())

    def per_surface(self) -> dict[str, dict[str, int]]:
        out: dict[str, dict[str, int]] = {}
        for c in self.classified:
            row = out.setdefault(
                c.sighting.surface, {v.value: 0 for v in Verdict} | {"rows": 0}
            )
            row["rows"] += 1
            row[c.verdict.value] += 1
        return out

    def render(self) -> str:
        lines = [
            "isolation probe — unlabelled cross-project / superseded rows",
            f"observer project: {self.observer_project}",
            "",
            f"{'surface':34} {'rows':>5} {'V1':>4} {'V2':>4} {'I1':>4} {'I2':>4} {'OK':>4}",
        ]
        table = self.per_surface()
        for surface_key in self.surfaces_driven:
            row = table.get(surface_key, {v.value: 0 for v in Verdict} | {"rows": 0})
            lines.append(
                f"{surface_key:34} {row['rows']:>5} {row['V1']:>4} {row['V2']:>4} "
                f"{row['I1']:>4} {row['I2']:>4} {row['OK']:>4}"
            )
        for surface_key in sorted(set(table) - set(self.surfaces_driven)):
            row = table[surface_key]
            lines.append(
                f"{surface_key:34} {row['rows']:>5} {row['V1']:>4} {row['V2']:>4} "
                f"{row['I1']:>4} {row['I2']:>4} {row['OK']:>4}"
            )
        violations = self.violations()
        if violations:
            lines.append("")
            lines.append("violations (each row is a leak):")
            for c in violations:
                lines.append(
                    f"  [{c.verdict.value}] {c.sighting.surface} via {c.sighting.door} "
                    f"({c.sighting.case}): row {c.sighting.row} — {'; '.join(c.reasons)}"
                )
        informational = self.informational()
        if informational:
            lines.append("")
            lines.append("informational (reported, not counted — see module docstring):")
            for c in informational:
                lines.append(
                    f"  [{c.verdict.value}] {c.sighting.surface} via {c.sighting.door} "
                    f"({c.sighting.case}): row {c.sighting.row}"
                )
        for note in self.notes:
            lines.append("")
            lines.append(f"note: {note}")
        lines.append("")
        lines.append(f"ISOLATION PROBE VIOLATIONS: {len(violations)}")
        return "\n".join(lines)
