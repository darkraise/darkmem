"""An evidence record gates the label, never the code (T2.95).

Darkmem puts words on data — `corroborated`, `confirmed`, `grounded` — and a
reader acts on them. Each is a claim that some measurement stands behind it,
and until that measurement exists the word is a confidence badge backed by
nothing, which is worse than no badge because it invites the trust it has not
earned.

**What this module refuses is the label, not the derivation.** The ladder still
computes, facts still promote internally, articles still synthesise and store.
What cannot happen is a promoted status reaching a reader as a promoted status
before the evidence exists. That distinction is what lets implementation run
arbitrarily far ahead of measurement without ever shipping an unbacked claim —
the whole basis of the M1 split.

**The pattern is not new here.** `VerificationJudge.judge()` has refused
unconditionally without a qualification record since T2.26, scan-enforced, and
that refusal never delayed T2.26's own construction by a day. This generalises
the same shape to the two remaining claims.

**Suppressed is not the same as candidate, and the trace must say which.** A
fact whose badge is suppressed for want of a record and a fact genuinely sitting
at `candidate` look identical on the wire unless something distinguishes them.
Collapsing them would turn a missing measurement into an apparent property of
the data — the reader would conclude the corpus is unverified when the truth is
that the *verifier* is unmeasured. So every suppressed row carries the reason.

**Fail closed, and fail closed on unreadable too.** An absent record and a
corrupt one both read as "no record". A parse error must not crash the read
path open — serving the label because the gate itself broke is the one failure
mode that would make this module worse than useless.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_RECORD_DIR = Path(__file__).resolve().parent

# G-C's evidence: the promotion-rate and false-promotion audit that certifies
# the corroboration ladder. Minted by T2.40's run, never by hand.
PROMOTION_RECORD_PATH = _RECORD_DIR / "promotion_metrics_record.json"

# **The groundedness gate is deliberately NOT in this module.** Whether an
# article may be labelled grounded is a question about the judge's
# qualification; the judge module already owns that record, and a scan enforces
# that it is the single door every consumer goes through. Importing the record
# path to re-ask the question here tripped that scan, correctly — two modules in
# the business of deciding whether the judge is qualified is exactly the drift
# it exists to prevent. The article path asks the judge directly when it is
# built (T3.02 / T3.23).
#
# Note for whoever meets that scan next: it matches the module name as **text**,
# so it fires on prose as well as imports. Writing around it is cheaper than
# loosening it, and its bluntness is why it has never been evaded.

# **Only `corroborated` is gated, and the exclusions are each a reason, not an
# oversight.**
#
# `confirmed` is **human-ratified** (doc 12 §4: the badge gains ", human-
# ratified"). Its evidence is a person who looked at the fact and said yes —
# G-C certifies the *automatic* promotion ladder, and suppressing a human's
# ratification because an automated ladder is unmeasured would withhold the one
# label in the system that never depended on the ladder at all. This module's
# first version got that wrong and the ratification test caught it.
#
# `candidate` asserts nothing. `disputed` states a two-sided conflict, which is
# honest without a promotion record; gating it would withhold an honest
# statement and leave the reader with less than the truth.
PROMOTED_STATUSES: frozenset[str] = frozenset({"corroborated"})

SUPPRESSED_STATUS = "candidate"

REASON_NO_PROMOTION_RECORD = (
    "verification_unmeasured: the corroboration ladder has no G-C evidence "
    "record, so promoted statuses are withheld and this row is served as a "
    "candidate. The status on disk is unchanged; minting the record restores "
    "the label with no code change."
)
REASON_NO_QUALIFICATION_RECORD = (
    "groundedness_unmeasured: the verification judge carries no qualification "
    "record, so no article may be served labelled grounded."
)


@dataclass(frozen=True)
class ClaimGate:
    """Whether a claim may be served, and why not when it may not."""

    open: bool
    reason: str | None = None

    def __bool__(self) -> bool:  # pragma: no cover - trivial
        return self.open


def _load_record(path: Path) -> dict | None:
    path = Path(path)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            record = json.load(fh)
    except (OSError, json.JSONDecodeError):
        logger.warning("claim-gate record %s is unreadable; treating as absent", path)
        return None
    return record if isinstance(record, dict) else None


def corroboration_gate(path: Path | None = None) -> ClaimGate:
    """Whether promoted fact statuses may reach a reader.

    Open only on a record that says it cleared its gate. A record present but
    not `gate_eligible` is a rehearsal or an interim, and an interim that opens
    the gate is the whole failure this guards — T2.26's own 0.8182 was branded
    INTERIM by its artifact and would have read as a pass to anything checking
    only for presence.
    """
    # Resolved at call time, not captured as a default: a default argument
    # binds at import, so the path could never be redirected afterwards — by an
    # operator, or by a test proving the record lights the label. A gate whose
    # own reversibility cannot be exercised is a gate nobody can verify.
    record = _load_record(PROMOTION_RECORD_PATH if path is None else path)
    if record is None or not record.get("gate_eligible"):
        return ClaimGate(False, REASON_NO_PROMOTION_RECORD)
    return ClaimGate(True)


def served_status(status: str | None, gate: ClaimGate | None = None) -> tuple[str | None, str | None]:
    """The status a reader may see, and the suppression reason if it differs.

    ``(status, None)`` when nothing was withheld — including for `candidate`
    and `disputed`, which assert nothing needing evidence. ``(candidate,
    reason)`` when a promoted status was withheld, so a consumer can tell a
    measured absence of corroboration from an unmeasured verifier.
    """
    if status not in PROMOTED_STATUSES:
        return status, None
    gate = corroboration_gate() if gate is None else gate
    if gate.open:
        return status, None
    return SUPPRESSED_STATUS, gate.reason
