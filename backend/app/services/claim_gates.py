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

**Two declarations, because "ungated" was one word for two facts (T2.100).**
A site that keeps a raw rung says which: :func:`unserved_status` claims no
reader receives the value, :func:`journalled_status` claims a reader receives
it as a record of what the ladder computed rather than as an assertion about
the fact. The single marker they replace promised the first at sites that did
the second, and a false declaration is worse than an undeclared one — the scan
trusts it and so does the next reader. What the second marker permits is scoped
to the audit door: a journalled payload embedded in a claim surface is served
through :func:`gated_journal_payload`, because the reasoning that accepts the
raw rung on ``/events`` is about which door was opened, not about the bytes.

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


def _resolve_gate(id_kind: str) -> ClaimGate:
    try:
        resolve = _GATE_BY_ID_KIND[id_kind]
    except (KeyError, TypeError):
        raise ValueError(
            f"no claim gate is defined for id_kind {id_kind!r}; the "
            f"evidence records are per claim ({sorted(_GATE_BY_ID_KIND)}) "
            "and serving a promoted status under an unrecognised one "
            "would be gating it against nothing"
        ) from None
    return resolve()


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
        gate = _resolve_gate(id_kind)
    if gate.open:
        return status, None
    return SUPPRESSED_STATUS, gate.reason


def raw_statuses_for_served(
    served: str, *, id_kind: str, gate: ClaimGate | None = None
) -> frozenset[str]:
    """The stored statuses a reader sees as ``served`` — `served_status` inverted.

    A surface that lets a reader *filter* by verification status must filter on
    the value it serves, not on the column. With the gate closed the two
    disagree, and the disagreement is readable: asking for the promoted rung
    returns exactly the rows whose label was withheld, and asking for the
    suppressed rung returns them not at all, so two requests recover per fact
    the rung the label refuses to say. The label stays unserved and the leak
    happens anyway, because membership of a filtered set is an answer.

    Empty is a real result, not a missing filter: with the gate closed nothing
    is served as ``corroborated``, so the honest page is no rows. Callers must
    not read it as "no filter".

    Derived from :func:`served_status` rather than written beside it, so the
    filter and the field cannot drift into two answers to one question. The
    preimage is complete because ``served_status`` rewrites only values in
    ``PROMOTED_STATUSES``: every other status is served as itself, so anything
    serving as ``served`` is either ``served`` or promoted.
    """
    if gate is None:
        gate = _resolve_gate(id_kind)
    return frozenset(
        raw
        for raw in {served} | set(PROMOTED_STATUSES)
        if served_status(raw, id_kind=id_kind, gate=gate)[0] == served
    )


JOURNAL_STATUS_KEY = "verification_status"
JOURNAL_SUPPRESSION_KEY = "label_suppressed"


def gated_journal_payload(value, *, id_kind: str, gate: ClaimGate | None = None):
    """A journal record embedded in a claim surface, mapped through the gate.

    **An accepted residue is scoped to the surface it was accepted on**
    (T2.100 fix round, ruled 2026-08-06). ``/events`` may serve the raw rung
    because a reader of that door is reading a computation log by construction
    of the door they opened — an argument about the door, not about the bytes.
    It evaporates the moment the same payload is embedded in a response whose
    purpose is to state a fact's status: a body that suppresses the rung in
    ``verification_status`` and hands it back two keys later in ``ladder`` has
    not gated anything, it has moved the answer.

    So every ``verification_status`` anywhere in the structure is served
    through :func:`served_status`, and a withheld one gains a
    ``label_suppressed`` sibling in the same object. Rewriting it silently
    would be the worse failure: the trace would record a movement to
    ``candidate`` that the ladder never made, and a suppressed transition
    would read as a genuine one.

    What the marker discloses is exactly what the row's own served labels
    already disclose on the same body — that a promoted rung was withheld here
    — and no more; the rung itself is never in the response. Dropping the
    marker to close that last inch is the one thing the ruling forbids.

    Takes any JSON-shaped value, so a caller hands over a whole page and the
    gate resolves **once** for it. Resolving per row would let a record minted
    mid-response serve half a page gated and half not.
    """
    if gate is None:
        gate = _resolve_gate(id_kind)
    if isinstance(value, dict):
        out: dict = {}
        withheld: str | None = None
        for key, item in value.items():
            if key == JOURNAL_STATUS_KEY and (item is None or isinstance(item, str)):
                out[key], withheld = served_status(item, id_kind=id_kind, gate=gate)
                continue
            out[key] = gated_journal_payload(item, id_kind=id_kind, gate=gate)
        # After the loop, so a payload that already carried the key cannot
        # overwrite the marker with a stale one.
        if withheld is not None:
            out[JOURNAL_SUPPRESSION_KEY] = withheld
        return out
    if isinstance(value, list):
        return [gated_journal_payload(item, id_kind=id_kind, gate=gate) for item in value]
    return value


def unserved_status(status: str | None) -> str | None:
    """The raw status, declared at its site as reaching no reader at all.

    The strong half of the split. Wrapping a value here claims it never leaves
    the process as data a reader receives: a candidate row handed to the
    ranking that doc 12 lets consume promoted statuses internally, an
    operational return value the door discards without echoing.

    This is a call rather than a comment on purpose: the scan reads the parsed
    tree, so prose can neither claim the exemption nor trip the guard. A
    serving path that wraps itself to quiet the scan has written that claim
    down falsely, which is a reviewable act; writing a raw dict entry was not.

    The claim is checked at the door, not taken on trust — the gate suite
    drives every door these sites feed and asserts the promoted rung appears
    nowhere in the body.
    """
    return status


def journalled_status(status: str | None) -> str | None:
    """The raw status, declared as a record of a computation, never a claim.

    The weak half, and the one this module used to have no way to say. A
    ladder transition journals the rung it moved off and the rung it moved to,
    and that payload does reach readers — a site declaring otherwise would be
    lying at exactly the point where the declaration is load-bearing.

    **Three readers, and they do not all serve it the same way.** The reach
    sentence here named only ``/events`` until the T2.100 review measured the
    other two, which is this marker's own defect class one level up: a
    declaration whose stated reach is narrower than its readers.

    - ``GET /api/v1/events`` (and the timeline and calendar over the same
      table) serves the payload **verbatim** to an authenticated reader, under
      the same ``require_auth`` as the facts door.
    - ``GET /api/v1/knowledge/facts/{id}`` embeds it in ``ladder`` — as does
      MCP's ``fact_get``, which serves the same response model — and
      ``GET /api/v1/review-queue/facts`` embeds it in ``evidence``. All go
      through :func:`gated_journal_payload`, because an accepted residue is
      scoped to the surface it was accepted on.

    **The events-door exposure is ruled acceptable, not open (T2.100,
    2026-08-06).** G-C's own false-promotion audit reads this journal, so
    narrowing the substrate to protect the gate would degrade the evidence the
    gate is measured with; T2.59 settled the analogous content-residue question
    the same way; and a journal row and a claim surface are different speech
    acts — one records what the ladder computed, the other asserts what is true
    of the fact now. Do not add filtering, redaction or gating to the events
    door to make this marker's promise smaller. **The ruling is about that
    door, so it does not travel with the bytes**: the same payload embedded in
    a body whose purpose is to state a fact's status is a claim surface's
    output and is gated as one.

    So the honest form of the M1 safety sentence is not *no serving path can
    reach a label whose evidence does not exist*. It is: **no claim surface
    serves an unbacked label; the audit journal records the ladder's own
    transitions and an authenticated operator can read them.**

    A gated copy here would be worse than the exposure: it would record a
    movement that did not happen, in a table that cannot un-write it.
    """
    return status


STATUS_DECLARATIONS = frozenset(
    {unserved_status.__name__, journalled_status.__name__}
)


def ungated_mapping(mapping):
    """A mapping copied wholesale, declared as carrying no served label.

    ``dict(row)``, ``{**row}`` and ``{k: row[k] for k in COLUMNS}`` emit a
    ``verification_status`` without ever naming one, so a scan keyed on the
    key cannot see them. The scan therefore also asks, in every module that
    serves the claim, where a wholesale copy's source came from — and a source
    it cannot see into needs the same kind of declaration as a raw status.

    Wrapping a copy here claims one of two things: the mapping carries no
    verification status at all, or the copy is internal and no reader receives
    it as a label. Same reason for being a call as :func:`unserved_status`.

    **It is deliberately not split the way the status marker is.** No site
    carrying this declaration lands in a journal payload, so a second mapping
    marker would have no sites and would state a distinction nothing
    exercises — and the gate suite fails the build if one ever does, rather
    than letting the missing half be discovered by a reader of ``/events``.
    """
    return mapping
