"""Blind-adjudication tooling for the entailment gold (T2.54, Ruling 3).

The instrument is independence: two separately-dispatched labellers
three-way-verdict every live pair against LABELLING.md, with no access to
the recorded labels or to each other. This module owns the two mechanical
halves -- the stripped export a blind pass labels from, and the merge rule
that turns two passes into flipped ``label_source`` values plus an
escalation queue for the owner.

Merge rule (Layer 2, stated before any pass ran): both passes agree with
the recorded verdict -> ``label_source`` flips to ``adjudicated``; any
disagreement -- between the passes, or with the recorded label -- leaves
the pair untouched and puts it in the escalation queue. The queue is the
owner's Step-6 work list; nothing here ever rewrites a verdict, because a
verdict change is retire-and-replace, a human decision.

No judge is called from here and none can be: the module is pure functions
over parsed JSON, with no model client, no database and no network.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from benchlib.entailment_gold import VERDICTS

# The ONLY fields a blind labeller sees. verdict, rationale, slice_tags,
# provenance and label_source are all withheld: a slice tag alone constrains
# the lawful verdict set (SLICE_VERDICTS), so exporting it would leak the
# answer for five of the eight slices.
BLIND_FIELDS = ("id", "premise", "hypothesis")


def strip_for_blind(gold_doc: dict) -> list[dict]:
    """Live pairs only, id/premise/hypothesis only, file order preserved."""
    return [
        {field: pair[field] for field in BLIND_FIELDS}
        for pair in gold_doc["pairs"]
        if not pair.get("retired")
    ]


def load_pass(path: str | Path) -> dict[str, dict]:
    """Parse one blind pass file: a list of ``{id, verdict, rule}`` entries,
    returned keyed by pair id. Refuses untabled verdicts and duplicate ids
    -- a pass that cannot state its verdicts in the closed vocabulary did
    not follow LABELLING.md."""
    with open(path, encoding="utf-8") as fh:
        entries = json.load(fh)
    verdicts: dict[str, dict] = {}
    for entry in entries:
        pid = entry["id"]
        if pid in verdicts:
            raise ValueError(f"blind pass {path}: duplicate id {pid!r}")
        if entry.get("verdict") not in VERDICTS:
            raise ValueError(
                f"blind pass {path}: pair {pid!r} verdict "
                f"{entry.get('verdict')!r} is not in {sorted(VERDICTS)}"
            )
        verdicts[pid] = {"verdict": entry["verdict"], "rule": entry.get("rule", "")}
    return verdicts


@dataclass(frozen=True)
class MergeOutcome:
    doc: dict
    escalations: list[dict]
    adjudicated: int
    n_live: int
    agreement_a: float
    agreement_b: float
    agreement_ab: float


def merge_blind_passes(
    gold_doc: dict, pass_a: dict[str, dict], pass_b: dict[str, dict],
) -> MergeOutcome:
    """Apply the merge rule to a deep copy of ``gold_doc``.

    Both passes must cover exactly the live pair ids -- a missing verdict is
    not an implicit agreement, and a surplus id means a pass labelled a pair
    that does not exist. Agreement rates are raw fractions over live pairs:
    each pass against the recorded verdicts, and the two passes against
    each other (the inter-labeller number LABELLING.md's history records).
    """
    doc = json.loads(json.dumps(gold_doc))
    live = [p for p in doc["pairs"] if not p.get("retired")]
    live_ids = [p["id"] for p in live]

    for name, blind in (("A", pass_a), ("B", pass_b)):
        missing = set(live_ids) - set(blind)
        surplus = set(blind) - set(live_ids)
        if missing or surplus:
            raise ValueError(
                f"blind pass {name} does not cover exactly the live pairs: "
                f"missing={sorted(missing)} surplus={sorted(surplus)}"
            )

    escalations: list[dict] = []
    adjudicated = agree_a = agree_b = agree_ab = 0
    for pair in live:
        pid = pair["id"]
        recorded = pair["verdict"]
        a = pass_a[pid]
        b = pass_b[pid]
        agree_a += a["verdict"] == recorded
        agree_b += b["verdict"] == recorded
        agree_ab += a["verdict"] == b["verdict"]
        if a["verdict"] == recorded and b["verdict"] == recorded:
            pair["label_source"] = "adjudicated"
            adjudicated += 1
        else:
            escalations.append({
                "id": pid,
                "premise": pair["premise"],
                "hypothesis": pair["hypothesis"],
                "slice": pair["slice_tags"][0],
                "recorded_verdict": recorded,
                "recorded_rationale": pair["rationale"],
                "pass_a": a,
                "pass_b": b,
            })

    n_live = len(live)
    return MergeOutcome(
        doc=doc,
        escalations=escalations,
        adjudicated=adjudicated,
        n_live=n_live,
        agreement_a=agree_a / n_live if n_live else 0.0,
        agreement_b=agree_b / n_live if n_live else 0.0,
        agreement_ab=agree_ab / n_live if n_live else 0.0,
    )
