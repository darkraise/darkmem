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

# **The groundedness record is deliberately NOT read in this module.** Whether
# an article may be labelled grounded is a question about the judge's
# qualification; the judge module already owns that record, and a scan enforces
# that it is the single door every consumer goes through. Importing the record
# path to re-ask the question here tripped that scan, correctly — two modules in
# the business of deciding whether the judge is qualified is exactly the drift
# it exists to prevent. The article path asks the judge directly when it is
# built (T3.02 / T3.23).
#
# What lives here instead is the *refusal*: an article's promoted status is
# withheld unconditionally, because this module cannot ask the only question
# that could release it. That is strictly stronger than the fact gate and
# cannot be wrong in the unsafe direction — the failure mode it removes is the
# one the review measured by inference: without keying on `id_kind`, minting
# G-C's *fact* record would light an article's label with the article evidence
# still absent (doc 08 §4.3 and doc 09 §4.3 keep the two records distinct).
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

FACT_ID_KIND = "fact"
ARTICLE_ID_KIND = "article"

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
    # ValueError rather than JSONDecodeError alone: a record with invalid
    # UTF-8 raises UnicodeDecodeError out of the *read*, not the parse, and an
    # uncaught one here took the whole fact read path down with it — every
    # row, candidate rows included, 500ing because the gate file was corrupt.
    except (OSError, ValueError):
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
    # `is True`, not truthiness: a record whose artifact brands eligibility as
    # a *string* — "INTERIM", or even "false" — is truthy, and truthiness
    # would read the exact branding this gate exists to refuse as a pass.
    if record is None or record.get("gate_eligible") is not True:
        return ClaimGate(False, REASON_NO_PROMOTION_RECORD)
    return ClaimGate(True)


def groundedness_gate() -> ClaimGate:
    """Whether a promoted article status may reach a reader. It may not.

    Closed unconditionally, and the closure is the honest answer rather than a
    placeholder: an article's claim is certified by G-D's judge qualification,
    the judge module owns that record and is scan-enforced as its single door,
    and this module may not ask it. A gate that cannot ask its question refuses.

    Opening it is the judge's own door to open when the article channel is
    built (T3.02 / T3.23), not a second reader of the qualification record
    here.
    """
    return ClaimGate(False, REASON_NO_QUALIFICATION_RECORD)


# The claim decides its own evidence. A fact's promoted rung is certified by
# G-C's promotion audit and an article's by G-D's judge qualification, so one
# gate serving both would let either record light the other's label.
_GATE_BY_ID_KIND = {
    FACT_ID_KIND: corroboration_gate,
    ARTICLE_ID_KIND: groundedness_gate,
}


def served_status(
    status: str | None, *, id_kind: str, gate: ClaimGate | None = None
) -> tuple[str | None, str | None]:
    """The status a reader may see, and the suppression reason if it differs.

    ``(status, None)`` when nothing was withheld — including for `candidate`
    and `disputed`, which assert nothing needing evidence. ``(candidate,
    reason)`` when a promoted status was withheld, so a consumer can tell a
    measured absence of corroboration from an unmeasured verifier.

    ``id_kind`` is required rather than defaulted: the default would have to
    name one claim, and every caller that forgot it would silently gate its
    rows against the *other* claim's evidence. An unknown kind raises, so a new
    labelled surface fails loud instead of ungated.
    """
    if status not in PROMOTED_STATUSES:
        return status, None
    if gate is None:
        try:
            resolve = _GATE_BY_ID_KIND[id_kind]
        except (KeyError, TypeError):
            raise ValueError(
                f"no claim gate is defined for id_kind {id_kind!r}; the "
                f"evidence records are per claim ({sorted(_GATE_BY_ID_KIND)}) "
                "and serving a promoted status under an unrecognised one "
                "would be gating it against nothing"
            ) from None
        gate = resolve()
    if gate.open:
        return status, None
    return SUPPRESSED_STATUS, gate.reason


def ungated_status(status: str | None) -> str | None:
    """The raw status, declared at its site as something no reader is served.

    A verification status legitimately appears outside a served label — in a
    journal payload recording which rung a transition moved off, in a candidate
    row handed to the ranking that doc 12 lets consume promoted statuses
    internally, in an operational return value a route discards. The scan in
    ``tests/test_claim_serving_gates.py`` quantifies over *every*
    ``verification_status`` emission in ``app/`` rather than enumerating the
    ones it knows, so those sites need a way to say which side of the gate they
    are on.

    This is that way, and it is a call rather than a comment on purpose: the
    scan reads the parsed tree, so prose can neither claim the exemption nor
    trip the guard. Wrapping a value here is a claim that the value reaches no
    reader as a label. A serving path that wraps itself to quiet the scan has
    written that claim down falsely, which is a reviewable act; writing a raw
    dict entry was not.
    """
    return status
