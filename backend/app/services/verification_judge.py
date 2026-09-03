"""The one `verification`-purpose NLI judge (doc 17 §6, doc 11 §6) — T2.26.

One judge, three consumers: the fact-level contradiction veto (doc 08 §4.2),
the article claim-level entailment pass (doc 09 §4.3), and block-answer
faithfulness (doc 16 §4, horizon). The judge lives here — not in the harness —
so the qualification run measures the exact prompt, parser and call
construction every consumer will run.

**One judge identity, one qualification record per consumer role** (R1,
doc 17 §6 amended 2026-08-12, owner-ratified). A consumer is admitted for the
discrimination it actually makes: the entailment role branches on ``entailed``
and gates on the entailed pair, the contradiction role branches on
``contradicted`` and gates on the contradiction pair. One purpose and one
measurement run per role, so `judge()` takes the role the caller is asking as.
**The prompt no longer follows that "nothing splits" rule, and this sentence
said it did until 2026-09-03**: the faithfulness role is served
``SPAN_SYSTEM_PROMPT`` because its premise is a raw document span rather than a
stored fact, so it carries its own ``prompt_sha`` and therefore its own identity
hash. That is scoped to the prompt alone — still one purpose, one model, one
parser — and it is what keeps repairing one role from moving another role's
identity. The

rejected alternative in §6 is per-consumer *judges* (three purposes, three
models, drifting independently); this is not that, but the roles do now hold
qualification state independently, which is that alternative's nearest
neighbour and is why the amendment says so out loud.

The prompt encodes the task semantics from
``scripts/benchlib/entailment/LABELLING.md`` (verdict definitions,
implicature-is-not-contradiction, the evaluation-time rule, entailment's
asymmetry). Those rules are the task definition the gold was labelled under,
not the gold's answers. Any change to the prompt or the user-message template
is a judge change: both texts fold into ``prompt_sha`` and therefore into the
judge identity, so an edit — disclosed or not — changes the recorded identity
and invalidates a prior qualification mechanically.

Verdicts are the gold's own three: ``entailed`` / ``contradicted`` /
``unsupported``. The grounded/ungrounded binary is derived at scoring time in
the harness (``benchlib.entailment_gold.GROUNDED_VERDICTS``); this module
never collapses the three, because the veto consumer is qualified on the
contradiction verdict specifically.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.services.extraction_clean import _content_seed
from app.services.faithfulness_bars import (
    FAITHFULNESS_BAR_DEFAULTS as _FAITHFULNESS_DEFAULTS,
)

if TYPE_CHECKING:  # pragma: no cover - typing only
    # The runtime import stays inside article_claim_gate() below, keeping this
    # module's dependency on claim_gates one-directional at import time. The
    # annotation still has to name something, or it resolves to nothing at all.
    from app.services.claim_gates import ClaimGate


logger = logging.getLogger(__name__)

JUDGE_PROMPT_VERSION = 1

JUDGE_VERDICTS = frozenset({"entailed", "contradicted", "unsupported"})

# DELIBERATELY NOT IN prompt.py, AND NEVER UI-EDITABLE. This string and
# USER_TEMPLATE below both fold into prompt_sha (see judge_identity), so an
# edit changes the recorded judge identity and mechanically invalidates the
# minted qualification record - the entailment record of 2026-08-17 among
# them. Routing the served prompt through prompt.get() while judge_identity()
# keeps hashing this constant is worse than either alternative: the model
# would receive an overridden prompt while the record still read valid.
# Comments are safe; only the string values are hashed.
SYSTEM_PROMPT = """\
You are a strict natural-language-inference judge. Given a PREMISE (a stored
fact) and a HYPOTHESIS (a claim), return exactly one verdict:

- "entailed": the premise alone makes the hypothesis true. A hypothesis that
  is strictly weaker than the premise (less precise, a subset of what the
  premise asserts) is still entailed. Use only the premise — never outside
  knowledge or plausibility.
- "contradicted": the premise and the hypothesis cannot both be true. This
  includes: a different value in a slot the premise fills exclusively; a
  present-tense claim of a state whose validity window the premise explicitly
  closes; an explicit negation; a reversed relation when the relation is
  exclusive in direction.
- "unsupported": neither of the above. A hypothesis that adds anything the
  premise does not assert (extra hosts, versions, causes, quantifiers,
  vendors) is unsupported, not entailed — even if plausible. A hypothesis the
  premise merely implicates but does not assert is unsupported, not
  contradicted. A time-anchored premise neither entails nor contradicts an
  un-anchored "currently" claim unless the window decides it.

Judge only what the texts assert. Respond with JSON:
{"verdict": "entailed" | "contradicted" | "unsupported", "reason": "<one sentence>"}
"""

# The faithfulness role's premise is a raw document span, not a stored fact.
# A span may record something to verify, to do, or to expect without asserting
# that it holds — an unchecked checklist item, an imperative, an `Expected:`
# line — and the shared prompt's "a stored fact" framing tells the judge the
# opposite. G-F's 2026-08-17 miss was 12 such spans out of 14 false-accepts:
# docs/planning/analyses/2026-09-03-gf-premise-framing-defect.md
SPAN_SYSTEM_PROMPT = """\
You are a strict natural-language-inference judge. Given a PREMISE (text quoted
verbatim from a document) and a HYPOTHESIS (a claim about the system), return
exactly one verdict:

- "entailed": the premise alone makes the hypothesis true. A hypothesis that
  is strictly weaker than the premise (less precise, a subset of what the
  premise asserts) is still entailed. Use only the premise — never outside
  knowledge or plausibility.
- "contradicted": the premise and the hypothesis cannot both be true. This
  includes: a different value in a slot the premise fills exclusively; a
  present-tense claim of a state whose validity window the premise explicitly
  closes; an explicit negation; a reversed relation when the relation is
  exclusive in direction.
- "unsupported": neither of the above. A hypothesis that adds anything the
  premise does not assert (extra hosts, versions, causes, quantifiers,
  vendors) is unsupported, not entailed — even if plausible. A hypothesis the
  premise merely implicates but does not assert is unsupported, not
  contradicted.

The premise is quoted document text, so it does not always assert anything.
Text that records something to verify, to do, or to expect states an intention,
not a fact about the system: an unchecked checklist item ("[ ] ..."), an
imperative instruction, a step in a procedure, an "Expected:" or "Verify ..."
line. A hypothesis claiming the system exhibits the behaviour is "unsupported"
by such a premise, however exactly the words match. A checklist item that is
marked done asserts only that it was checked.

Judge only what the texts assert. Respond with JSON:
{"verdict": "entailed" | "contradicted" | "unsupported", "reason": "<one sentence>"}
"""

USER_TEMPLATE = "PREMISE:\n{premise}\n\nHYPOTHESIS:\n{hypothesis}"


def _system_prompt_for(role: str | None) -> str:
    """The system prompt a role is served.

    Role-scoped rather than shared because editing ``SYSTEM_PROMPT`` moves
    ``prompt_sha`` and therefore the judge identity, which would un-qualify
    G-D's minted entailment record (``fd39e7b2c47fa375``) as a side effect of
    repairing a different role.
    """
    return SPAN_SYSTEM_PROMPT if role == FAITHFULNESS_ROLE else SYSTEM_PROMPT


def build_messages(premise: str, hypothesis: str, *, role: str | None = None) -> list[dict]:
    return [
        {"role": "system", "content": _system_prompt_for(role)},
        {"role": "user", "content": USER_TEMPLATE.format(premise=premise, hypothesis=hypothesis)},
    ]


@dataclass(frozen=True)
class ProbeVerdict:
    verdict: str | None
    reason: str | None
    raw: str
    valid: bool


_TOKEN_RES = {v: re.compile(rf"\b{v}\b") for v in JUDGE_VERDICTS}


def parse_verdict(raw: str) -> ProbeVerdict:
    """Strict JSON first, then a bare-token fallback; anything else is
    ``invalid`` — never an exception, never a coerced verdict. An invalid
    response can never register as an acceptance, so it cannot create a
    false accept; the qualification scorer counts it as a miss for
    whatever the gold expected."""
    try:
        payload = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        payload = None

    if isinstance(payload, dict):
        verdict = payload.get("verdict")
        if verdict in JUDGE_VERDICTS:
            reason = payload.get("reason")
            return ProbeVerdict(
                verdict=verdict,
                reason=reason if isinstance(reason, str) else None,
                raw=raw,
                valid=True,
            )
        return ProbeVerdict(verdict=None, reason=None, raw=raw, valid=False)

    found = [v for v, pattern in _TOKEN_RES.items() if pattern.search(raw or "")]
    if len(found) == 1:
        return ProbeVerdict(verdict=found[0], reason=None, raw=raw, valid=True)
    return ProbeVerdict(verdict=None, reason=None, raw=raw, valid=False)


class VerificationJudge:
    def __init__(self, llm):
        self.llm = llm

    async def qualification_probe(
        self, premise: str, hypothesis: str, *, role: str | None = None,
    ) -> ProbeVerdict:
        """The ungated door, named for its only lawful caller: the
        qualification harness must be able to measure an unqualified judge.
        A source scan pins that nothing else under ``app/`` reaches it.

        ``role`` selects the system prompt, so a harness measuring one role
        measures the prompt that role is actually served."""
        raw = await self.llm.chat_completion(
            "verification",
            build_messages(premise, hypothesis, role=role),
            response_format={"type": "json_object"},
            seed=_content_seed(premise + "\n" + hypothesis),
        )
        return parse_verdict(raw)

    async def judge(
        self,
        session: AsyncSession,
        premise: str,
        hypothesis: str,
        *,
        role: str,
    ) -> ProbeVerdict:
        """The gated door — the only entry a consumer may use. Refuses with
        ``JudgeNotQualifiedError`` unless the record for ``role`` matches the
        currently resolved judge identity and clears that role's currently
        merged bars, recomputed on every call (detected, never remembered).

        ``role`` is keyword-only and has no default, so a new consumer has to
        name the discrimination it makes rather than inherit whichever record
        happens to exist. A scan re-proves each consumer passes its own.

        Deliberately takes no record path: only the canonical, minting-locked
        record can qualify a consumer call. A caller-supplied path here would
        reopen the rehearsal-record bypass one level above the writer's lock
        (a rehearsal ``--gate`` run may legitimately write a qualifying
        record to any non-default path — that record must never be loadable
        through this door). Tests point the module constant elsewhere."""
        state = await qualification_state(
            session, self.llm.config, role=role,
        )
        if not state.qualified:
            raise JudgeNotQualifiedError(
                f"the verification judge is not qualified for the {role!r} "
                "role at its current identity and bars; no consumer may ship "
                "on its verdicts (doc 17 §6). Reasons: " + "; ".join(state.reasons)
            )
        return await self.qualification_probe(premise, hypothesis, role=role)


# ── judge identity: what a qualification is recorded against ─────────────

# caching_llm._KEYED_CONFIG_FIELDS minus nothing: the same resolved-config
# fields whose change makes a cached answer stale make a qualification
# stale. api_key is deliberately absent — rotating a credential is not a
# model swap.
IDENTITY_FIELDS = ("model", "base_url", "api_kind", "dimensions", "reasoning", "params")


def judge_identity(cfg, *, role: str | None = None) -> dict:
    """The identity a qualification binds to: the resolved purpose config's
    behaviour-shaping fields plus the prompt version and the hash of ALL
    prompt text (system prompt + user-message template — both are sent on
    every call, so an edit to either is a judge change and must move the
    identity even without a version bump).

    The system prompt hashed is the one that role is actually served, so a
    role whose prompt differs gets its own identity and a record minted for
    one cannot qualify a judge serving another.
    """
    identity = {field: getattr(cfg, field, None) for field in IDENTITY_FIELDS}
    identity["prompt_version"] = JUDGE_PROMPT_VERSION
    # NUL-joined so text migrating across the system-prompt/template boundary
    # cannot keep the hash.
    identity["prompt_sha"] = hashlib.sha256(
        (_system_prompt_for(role) + "\x00" + USER_TEMPLATE).encode("utf-8")
    ).hexdigest()[:16]
    return identity


def judge_identity_hash(identity: dict) -> str:
    canonical = json.dumps(identity, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ── the qualification record and the computed state ──────────────────────

# ── the two consumer roles (R1, doc 17 §6 amended 2026-08-12) ────────────

ENTAILMENT_ROLE = "entailment"
CONTRADICTION_ROLE = "contradiction"
# The third consumer (TH1.09, doc 16 §4). Its own role rather than a reuse of
# the entailment one: the discrimination is the same word and a different
# premise distribution — raw document span text, which the claim/fact gold does
# not represent — so the entailment record qualifies articles and not this.
FAITHFULNESS_ROLE = "faithfulness"

# The judge verdict each role's consumer branches on. This is the premise the
# amendment derives from — "each consumer's gate depends on a discrimination it
# never makes" — so it is machine-checked rather than asserted: a scan in
# tests/test_verification_judge.py fails the build if either consumer module
# compares against any other judge verdict, or asks for the other role.
ROLE_VERDICTS = {
    ENTAILMENT_ROLE: "entailed",
    CONTRADICTION_ROLE: "contradicted",
    FAITHFULNESS_ROLE: "entailed",
}

# role -> the bar keys that role's discrimination is measured by. The split is
# symmetric by construction and pinned by test: the two role bar sets partition
# BAR_METRICS exactly, so no bar is orphaned into no role's gate and none is
# double-counted into both.
JUDGE_ROLES: dict[str, tuple[str, ...]] = {
    ENTAILMENT_ROLE: (
        "groundedness_gate_precision_bar",
        "groundedness_gate_recall_bar",
    ),
    CONTRADICTION_ROLE: (
        "contradiction_precision_bar",
        "contradiction_recall_bar",
    ),
    FAITHFULNESS_ROLE: (
        "faithfulness_gate_precision_bar",
        "faithfulness_gate_recall_bar",
    ),
}

# The pair sets retired from qualification use, in full. `4975c5cc…` is the gold
# T2.114 spent its final attempt on: the stopping rule fired, and the owner's
# 2026-08-12 ruling retires the pairs from qualification for **any** role —
# refusing both a fresh sitting (the frozen identity would be served warm-cache
# verdicts byte-for-byte) and the composed mint (the run recorded NOT CLEARED
# minting the redefined gate's record). A record naming one of these is inert
# here no matter what it measured, and the harness refuses to contact them at
# all. Splitting the record by role is exactly the move that could be misread as
# licensing another attempt, so the refusal is code rather than protocol.
RETIRED_PAIR_SETS = frozenset({
    "4975c5cc6d57faa97115b624cafb2982600c7c4b00bbcc6dabe4440109bb485f",
})

# The ledger and every report name these sets by their first 8 hex characters,
# so a record carrying the abbreviated form must be caught too. A collision at
# 8 hex refuses a lawful pair set rather than admitting a retired one, which is
# the direction an anti-tuning guard must fail in.
RETIRED_PREFIX_LENGTH = 8

_RETIRED_PREFIXES = frozenset(s[:RETIRED_PREFIX_LENGTH] for s in RETIRED_PAIR_SETS)


def is_retired_pair_set(value: object) -> bool:
    if not isinstance(value, str) or len(value) < RETIRED_PREFIX_LENGTH:
        return False
    return value[:RETIRED_PREFIX_LENGTH].lower() in _RETIRED_PREFIXES


# One record per role, minted only by a cleared run for that role. Both are
# absent on this branch and a test pins that: the contradiction role is
# unqualified because its bar was missed and stays missed, and the entailment
# role is unqualified because its record is owed to a fresh gold (T2.124/T2.125)
# and was NOT minted from the spent run's artifact.
QUALIFICATION_RECORD_PATHS: dict[str, Path] = {
    role: Path(__file__).resolve().parent / f"verification_qualification.{role}.json"
    for role in JUDGE_ROLES
}


def qualification_record_path(role: str) -> Path:
    try:
        return QUALIFICATION_RECORD_PATHS[role]
    except KeyError:
        raise ValueError(
            f"unknown judge role {role!r}; the roles are "
            f"{sorted(JUDGE_ROLES)} (doc 17 §6)"
        ) from None


# Bar config-row key -> the recorded metric it governs. Judge-wide: this is the
# full set of metrics anything is barred on, and ``JUDGE_ROLES`` above is what
# says which role's gate each one enters. The two stay in step by test (the
# roles partition this mapping) and at runtime (a bar in no role fails every
# role closed).
#
# **``contradiction_recall_bar`` is why this mapping exists as a separate
# thing from the defaults** (doc 17 §6's 2026-08-08 amendment, T2.109).
# Gating the contradiction verdict on precision alone was measured incoherent:
# replayed through the shipped scorer, a judge emitting ``contradicted`` on
# exactly one correct pair and ``unsupported`` everywhere else passes all three
# previously-gated bars at contradiction-recall 0.0182 — a near-mute judge
# qualified to hold a veto, while the measured 0.88-precision / 0.95-recall
# judge scores as a failure. Doc 08 §4.2's amendment turns that consumer into a
# surfacing instrument, which inverts the pair: recall is truth-critical (a
# missed contradiction never reaches a reviewer) and precision becomes a
# review-load floor.
#
# The bar's value was withheld at first, because stating it in the same breath
# as the amendment would have meant choosing it while looking at both measured
# judges' public numbers. **It has since been stated — 0.95, by derivation, on
# 2026-08-08** (see VERIFICATION_BAR_DEFAULTS below for the derivation and for
# why a fit would have landed on 0.90 instead). The fail-closed machinery it
# was withheld behind is not vestigial and must not be removed: selecting rows
# over BAR_METRICS rather than over the defaults is what lets a *future* barred
# metric be added here and refuse to resolve until someone writes its number
# down. Deleting a key from the defaults still fails the gate closed; it no
# longer silently qualifies against a number nobody chose.
BAR_METRICS = {
    "groundedness_gate_precision_bar": "entailed_precision",
    "groundedness_gate_recall_bar": "entailed_recall",
    "contradiction_precision_bar": "contradiction_precision",
    "contradiction_recall_bar": "contradiction_recall",
    # TH1.09 lands the faithfulness role, so its two keys join here rather than
    # living alone in `faithfulness_bars` — a bar orphaned into no role's gate
    # is what the partition test forbids. The values are **imported** from that
    # module below, never restated: the numbers TH1.01 stated and the numbers
    # enforced here cannot be allowed to become two values.
    "faithfulness_gate_precision_bar": "entailed_precision",
    "faithfulness_gate_recall_bar": "entailed_recall",
}


class JudgeNotQualifiedError(RuntimeError):
    pass


@dataclass(frozen=True)
class QualificationState:
    qualified: bool
    reasons: tuple[str, ...]
    record: dict | None


def load_qualification_record(path: Path) -> dict | None:
    """Absent or unreadable both read as "no record" — the enforcement path
    must fail closed, never crash open or closed."""
    path = Path(path)
    if not path.exists():
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            record = json.load(fh)
    except (OSError, json.JSONDecodeError):
        logger.warning("qualification record %s is unreadable; treating as absent", path)
        return None
    return record if isinstance(record, dict) else None


async def article_claim_gate(
    session: AsyncSession,
    llm_config: dict,
    record_path: Path | None = None,
) -> "ClaimGate":
    """Whether a promoted **article** status may reach a reader (T3.02).

    Asks the **entailment** role, because that is the discrimination the
    article path makes: a claim is grounded or it is not, and `contradicted`
    and `unsupported` are one bucket to it. Since R1 that means an article
    surface can open while the contradiction role stays unqualified — a real
    weakening, named as a cost in doc 17 §6's amendment rather than left for a
    reader to discover.

    The judge's door, deliberately — ``claim_gates.groundedness_gate()`` is
    unconditionally closed because that module may not read this record, and
    two modules deciding whether the judge is qualified is the drift this
    module's single-door scan exists to prevent. So the question is answered
    here and the answer is handed out.

    **This is the T2.95 principle applied to L3: an evidence record gates the
    label, never the code.** Before this existed, opening the article gate
    needed a code change — which is a code-gated label wearing a gate's name.
    Now minting a cleared qualification record opens it with no edit anywhere,
    exactly as minting the promotion record lights a fact's.

    It lands **inert**, by two independent constructions: no qualification
    record exists (G-D is not cleared), and even with one, T3.02 writes only
    `candidate` articles — the only path that could raise one is T3.03's
    coverage routing, itself behind G-E.
    """
    from app.services.claim_gates import ClaimGate, REASON_NO_QUALIFICATION_RECORD

    state = await qualification_state(
        session, llm_config, role=ENTAILMENT_ROLE, record_path=record_path,
    )
    if state.qualified:
        return ClaimGate(True, None)
    reason = "; ".join(state.reasons) if state.reasons else REASON_NO_QUALIFICATION_RECORD
    return ClaimGate(False, reason)


# The field an entailment-role record must carry to be honoured: how many
# contradicted pairs the judge called entailed.
#
# **It is required because R1 removed the only bound on that cell.** Under one
# bundled record, contradiction-recall >= 0.95 bounded every contradicted miss
# at 5%, including the ones judged `entailed` — which are exactly the ones that
# ship contradicted material as grounded. After the split, that leak is priced
# only by entailed precision at the pooled base rate, where a handful of
# contradicted-judged-entailed pairs barely move the number while corrupting a
# large fraction of the contradicted material. Nothing bounds it now, so the
# record must at minimum *state* it: an undisclosed leak fails the role closed
# rather than passing on a number the reader cannot see.
LEAK_DISCLOSURE_METRIC = "contradicted_judged_entailed"
# The claim/span analogue, owed by a faithfulness-role record (TH1.01's spec
# §3). Same shape, different premise distribution: the cell that matters is a
# span that does *not* support the sentence being judged as if it did, because
# that is the one that serves a hallucination under the grounded badge.
SPAN_LEAK_DISCLOSURE_METRIC = "unsupported_judged_entailed"

ROLE_REQUIRED_DISCLOSURES: dict[str, tuple[str, ...]] = {
    ENTAILMENT_ROLE: (LEAK_DISCLOSURE_METRIC,),
    CONTRADICTION_ROLE: (),
    FAITHFULNESS_ROLE: (SPAN_LEAK_DISCLOSURE_METRIC,),
}


async def qualification_state(
    session: AsyncSession,
    llm_config: dict,
    *,
    role: str,
    record_path: Path | None = None,
) -> QualificationState:
    """Whether the judge is qualified **for one consumer role**.

    Every check below is per-role by construction: which record is read, which
    bars are compared, and which disclosures the record owes. What is not
    per-role is bar *resolution* — an unstated or unreadable bar anywhere in
    ``BAR_METRICS`` fails every role closed, because a bar nobody has stated a
    number for is a question about the instrument, not about one consumer.
    """
    if role not in JUDGE_ROLES:
        raise ValueError(
            f"unknown judge role {role!r}; the roles are "
            f"{sorted(JUDGE_ROLES)} (doc 17 §6)"
        )
    if record_path is None:
        record_path = qualification_record_path(role)

    record = load_qualification_record(record_path)
    if record is None:
        return QualificationState(
            False, (f"no qualification record for the {role!r} role",), None,
        )

    reasons: list[str] = []

    # A record qualifies the role it was minted for and no other. Without this
    # the split is cosmetic: copying one role's file onto the other's path, or
    # keeping a pre-R1 bundled record that names no role at all, would qualify a
    # consumer on a discrimination nobody measured it for.
    recorded_role = record.get("role")
    if recorded_role != role:
        reasons.append(
            f"the record names role {recorded_role!r}, not {role!r} — a "
            "qualification is per-role since doc 17 §6's 2026-08-12 amendment, "
            "and a record without a role is a pre-amendment bundle that "
            "qualifies nothing"
        )

    # Which pairs produced the number. A record that does not say cannot be
    # checked against the retired sets, and unverifiable provenance on the one
    # artifact that opens a gate fails closed.
    pairs_sha = record.get("gold_pairs_sha256")
    if not isinstance(pairs_sha, str) or not pairs_sha:
        reasons.append(
            "the record carries no gold_pairs_sha256 — the pair set behind a "
            "qualification must be nameable to be checkable (doc 17 §6)"
        )
    elif is_retired_pair_set(pairs_sha):
        reasons.append(
            f"the record was measured on retired pair set {pairs_sha[:8]} — "
            "the T2.114 stopping rule retires it from qualification for every "
            "role, and the 2026-08-12 ruling refused minting from it"
        )

    for metric_key in ROLE_REQUIRED_DISCLOSURES.get(role, ()):
        value = (record.get("metrics") or {}).get(metric_key)
        if not isinstance(value, int) or isinstance(value, bool):
            reasons.append(
                f"the {role!r} record does not disclose {metric_key} — the "
                "split left this confusion cell unbounded, so a record that "
                "does not state it fails closed"
            )

    if not record.get("gate_eligible"):
        reasons.append("the record is not gate_eligible (interim or rehearsal output)")

    cfg = llm_config.get("verification") if llm_config else None
    if cfg is None:
        reasons.append("no verification purpose in the resolved LLM config")
    else:
        current_hash = judge_identity_hash(judge_identity(cfg, role=role))
        recorded = record.get("judge_identity") or {}
        recorded_hash = recorded.get("identity_hash")
        if recorded_hash != current_hash:
            reasons.append(
                f"judge identity mismatch: recorded {recorded_hash!r}, current "
                f"{current_hash!r} — a model, param or prompt change requires "
                "re-qualification (doc 17 §11)"
            )

    try:
        bars = await get_verification_bars(session)
    except (ValueError, OverflowError) as exc:
        # `OverflowError` is not a `ValueError`, and jsonb accepts numerics
        # far outside float range (`1e400` round-trips as a 401-digit int), so
        # `float()` on one raised straight through this catch and crashed the
        # consumer instead of failing closed with a reason. Found in review.
        reasons.append(f"bars unreadable — failing closed: {exc}")
        return QualificationState(False, tuple(reasons), record)

    # The runtime half of the partition pin. A barred metric assigned to no
    # role gates nothing at all, which is a silently weaker gate than the one
    # before the split — so it fails every role closed, exactly as an unstated
    # bar does, rather than quietly dropping out of the comparison.
    unassigned = sorted(
        set(BAR_METRICS) - {key for keys in JUDGE_ROLES.values() for key in keys}
    )
    if unassigned:
        reasons.append(
            f"barred metric(s) {', '.join(unassigned)} belong to no judge role "
            "— failing closed rather than gating on a subset nobody chose"
        )

    metrics = record.get("metrics") or {}
    for bar_key in JUDGE_ROLES[role]:
        # Total rather than indexed: this is the enforcement path, and a role
        # naming a bar the judge does not declare must fail closed rather than
        # raise out of a consumer's call.
        if bar_key not in BAR_METRICS or bar_key not in bars:
            reasons.append(
                f"the {role!r} role names bar {bar_key} which the judge does "
                "not declare — failing closed"
            )
            continue
        metric_key = BAR_METRICS[bar_key]
        value = metrics.get(metric_key)
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            reasons.append(
                f"recorded metric {metric_key} is missing or null — failing closed"
            )
        elif value < bars[bar_key]:
            reasons.append(
                f"recorded {metric_key}={value} is below {bar_key}={bars[bar_key]}"
            )

    return QualificationState(not reasons, tuple(reasons), record)


# ── the bars (doc 17 §6): config rows over stated defaults ───────────────

# Deliberately a subset of BAR_METRICS: a barred metric with no entry here is
# one whose number nobody has stated, and it fails closed rather than
# defaulting. See the BAR_METRICS block for why contradiction_recall_bar is the
# one such bar today.
# ``contradiction_recall_bar`` is stated here as of 2026-08-08, by derivation
# rather than by measurement, which is what makes it lawful to state at all.
#
# Doc 17 §6's rule predates every judge run: the **truth-critical** metric of
# this judge is barred at 0.95, the other at 0.90. The 2026-08-08 amendment
# moved the LLM arm from deciding to surfacing, and for a surfacing instrument
# recall is the truth-critical metric — a contradiction it misses reaches no
# reviewer, and the fact stays corroborated and citable. So recall takes 0.95
# by the same rule that gave entailed-precision 0.95, not by anything observed.
#
# The check that this is a derivation and not a fit: **the measured judge does
# not clear it.** gpt-5.5 scored contradiction-recall 0.945 on the retired
# gold. A bar chosen to launder that result would sit at 0.90.
#
# Precision moves 0.95 -> 0.70 because its consumer changed, not because it was
# missed. It is now a review-load floor: a false flag costs a reviewer a
# minute, not a wrong belief, so the only thing it must guarantee is a queue a
# human will actually work - noise a clear minority, under one flag in three.
# Holding it at 0.95 would keep pricing precision as truth after the amendment
# said it is not, and would block the gate for a reason unrelated to being
# right. A *lower* bar here is the honest consequence of the redesign.
#
# Both are the owner's to move with a recorded argument. Neither may be moved
# to make a run pass.
VERIFICATION_BAR_DEFAULTS: dict[str, float] = {
    "contradiction_recall_bar": 0.95,
    "groundedness_gate_precision_bar": 0.95,
    "groundedness_gate_recall_bar": 0.90,
    "contradiction_precision_bar": 0.70,
    # Imported, never restated (TH1.01's spec §3 is explicit about this): the
    # bars stated when the metric was defined and the bars enforced when the
    # role landed must not be able to become two values.
    **{
        key: _FAITHFULNESS_DEFAULTS[key]
        for key in ("faithfulness_gate_precision_bar", "faithfulness_gate_recall_bar")
    },
}

# T2.126, owner-ruled 2026-08-13: the shipped defaults above are **floors**, on
# the verification ladder's shape (`verification_ladder.LADDER_FLOORS`).
# Tightening is free; a config row below a floor is honoured only against a
# licence naming that parameter, and otherwise clamps back with a warning
# rather than raising — a bad row degrades to the conservative bar instead of
# taking the enforcement path down. The floors are `VERIFICATION_BAR_DEFAULTS`
# itself rather than a second mapping, so "what ships" and "what may not be
# gone below" stay one statement.
#
# **What this row can assert, and what it cannot.** The ladder ties a loosening
# to a recorded G-C measurement; a judge bar's licence is the owner's recorded
# argument in the gate ledger, and code cannot read a paragraph, let alone
# judge one. So the row asserts only three mechanical things — which parameter
# (by name, never blanket), how far (the lowest value the argument is claimed
# to support, so the licence *bounds* the loosening), and where the argument is
# recorded (a citation checked for presence and never for truth). Bounding it
# is the part that keeps this from being the bar row licensing itself: a row
# that unlocked "whatever the bar row says" would be a ratchet — one write,
# then any number. What it cannot do is stop an operator who writes both rows;
# nothing in-process can, and the ladder's row has the same limit. What it buys
# is that a loosening is no longer a single number edit that leaves no trace.
VERIFICATION_BAR_LICENCES_KEY = "verification_bar_licences"


async def get_verification_bar_licences(session: AsyncSession) -> dict[str, float]:
    """Which bars carry a licence to sit below their floor, and how far down.

    Shape, mirroring ``get_ladder_measurements``' posture — a ``config`` row
    nothing in this codebase writes, empty by default, degrading rather than
    raising::

        {"licensed": {"<bar key>": {"value": 0.90,
                                    "argument": "gate-ledger.md#<section>"}}}

    Permission is **per parameter and per value**: an entry unlocks its own
    parameter down to its own stated value and nothing else. A malformed entry
    licenses nothing and says which field it is missing, because the operator
    whose value was ignored is the one who needs to read that line.
    """
    row = (await session.execute(
        select(Config).where(Config.key == VERIFICATION_BAR_LICENCES_KEY)
    )).scalar_one_or_none()
    if row is None:
        return {}

    licensed = row.value.get("licensed") if isinstance(row.value, dict) else None
    if not isinstance(licensed, dict):
        logger.warning(
            "%s config row is %r, not {\"licensed\": {<bar key>: {\"value\": x, "
            "\"argument\": \"<where the argument is recorded>\"}}}; licensing "
            "nothing, so every bar holds at its floor",
            VERIFICATION_BAR_LICENCES_KEY,
            row.value,
        )
        return {}

    out: dict[str, float] = {}
    for key, entry in licensed.items():
        if key not in VERIFICATION_BAR_DEFAULTS:
            logger.warning(
                "%s licenses %r, which is not a barred metric with a floor; "
                "ignoring. Licensable parameters: %s",
                VERIFICATION_BAR_LICENCES_KEY,
                key,
                sorted(VERIFICATION_BAR_DEFAULTS),
            )
            continue
        if not isinstance(entry, dict):
            logger.warning(
                "%s licence for %s is %r, not an object carrying value and "
                "argument; licensing nothing for it",
                VERIFICATION_BAR_LICENCES_KEY,
                key,
                entry,
            )
            continue
        value = entry.get("value")
        # bool is an int subclass, and False would read as a licence down to 0.
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            logger.warning(
                "%s licence for %s states value %r, not a number; licensing "
                "nothing for it. A licence must say how far down the recorded "
                "argument reaches, or it bounds nothing",
                VERIFICATION_BAR_LICENCES_KEY,
                key,
                value,
            )
            continue
        # The bound must itself be a coherent bar value. Without this, a
        # licence of 0 (or a negative) unlocks its parameter wholesale and
        # *silently*, because no candidate can ever fall below it and the
        # out-of-bound warning therefore never fires — a bound that bounds
        # nothing, which is the one thing this shape exists not to be. Found
        # in review; `1.0` is admitted and inert, since a licence at the
        # ceiling licenses no loosening any floor would refuse.
        try:
            bound = float(value)
        except (ValueError, OverflowError):
            bound = float("nan")
        if not 0.0 < bound <= 1.0:
            logger.warning(
                "%s licence for %s states value %r, which is not a bar value "
                "in (0, 1]; licensing nothing for it. A licence at or below "
                "zero would unlock the parameter outright and no candidate "
                "could ever trip its own bound",
                VERIFICATION_BAR_LICENCES_KEY,
                key,
                value,
            )
            continue
        argument = entry.get("argument")
        if not isinstance(argument, str) or not argument.strip():
            logger.warning(
                "%s licence for %s states no argument citation; licensing "
                "nothing for it. The citation is what a reviewer checks the "
                "loosening against — its presence is all this code can verify, "
                "and its absence is all it takes to refuse",
                VERIFICATION_BAR_LICENCES_KEY,
                key,
            )
            continue
        out[key] = bound
    return out


def _clamp_to_floor(key: str, candidate: float, licensed: dict[str, float]) -> float:
    floor = VERIFICATION_BAR_DEFAULTS.get(key)
    if floor is None or candidate >= floor:
        return candidate

    allowed = licensed.get(key)
    if allowed is None:
        logger.warning(
            "%s=%s is below its floor %s and the %s row licenses no loosening "
            "for it; clamping to %s. Lowering a judge bar takes a licence "
            "naming this parameter, the lowest value its recorded argument "
            "supports, and where that argument is recorded — never an edit to "
            "the bar row alone.",
            key,
            candidate,
            floor,
            VERIFICATION_BAR_LICENCES_KEY,
            floor,
        )
        return floor
    if candidate < allowed:
        # Back to the floor rather than to `allowed`: clamping to the licensed
        # value would adopt a number the operator did not write, on an argument
        # they did not make for it.
        logger.warning(
            "%s=%s is below its floor %s and below the %s licence's own lowest "
            "licensed value %s; clamping to %s. The licence bounds how far the "
            "bar may move, so going further takes a new licence and a new "
            "recorded argument.",
            key,
            candidate,
            floor,
            VERIFICATION_BAR_LICENCES_KEY,
            allowed,
            floor,
        )
        return floor
    return candidate


async def get_verification_bars(session: AsyncSession) -> dict[str, float]:
    """Merge per-bar ``config`` rows over the code defaults, DB winning per
    key, then clamp any unlicensed loosening back to its floor. A row's value
    may be ``{"value": x}`` or a bare JSON number. An unreadable row raises:
    silently falling back to the default would ignore an operator's attempt to
    move a bar — conservative relative to the defaults but not to operator
    intent — so the enforcement path (``qualification_state``) catches this and
    fails closed instead.

    The two postures are deliberately different and the difference is the
    readability of the row (T2.126). An *unreadable* row raises, because
    nothing can be inferred from it. A readable row *below its floor* is a
    statement this code can act on, so it degrades to the floor with a warning
    the way the ladder does, rather than taking down every recompute that reads
    a bar.

    A barred metric with neither a default nor a config row raises on the
    same terms, and it is the same argument one step further: an unstated
    bar is not a bar of zero, and resolving it to anything at all would let
    a judge qualify against a number nobody chose. The rows are selected
    over ``BAR_METRICS`` rather than over the defaults so that stating such
    a bar is a config write and needs no code change. Such a bar has no floor
    either: the row is the only statement of that number, so there is nothing
    it could have been lowered from."""
    rows = (await session.execute(
        select(Config).where(Config.key.in_(BAR_METRICS))
    )).scalars().all()

    licensed = await get_verification_bar_licences(session) if rows else {}

    bars = dict(VERIFICATION_BAR_DEFAULTS)
    for row in rows:
        value = row.value
        if isinstance(value, dict):
            value = value.get("value")
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError(
                f"config row {row.key} carries an unreadable bar value "
                f"{row.value!r}; fix or delete the row"
            )
        bars[row.key] = _clamp_to_floor(row.key, float(value), licensed)

    unstated = sorted(set(BAR_METRICS) - set(bars))
    if unstated:
        raise ValueError(
            f"no bar stated for {', '.join(unstated)}: the metric is gated but "
            "carries no default and no config row, so nothing can be qualified "
            "against it. State the bar as a config row (doc 17 §6)"
        )
    return bars
