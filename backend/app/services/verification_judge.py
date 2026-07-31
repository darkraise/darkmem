"""The one `verification`-purpose NLI judge (doc 17 §6, doc 11 §6) — T2.26.

One judge, three consumers: the fact-level contradiction veto (doc 08 §4.2),
the article claim-level entailment pass (doc 09 §4.3), and block-answer
faithfulness (doc 16 §4, horizon). The judge lives here — not in the harness —
so the qualification run measures the exact prompt, parser and call
construction every consumer will run.

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

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import Config
from app.services.extraction_clean import _content_seed

logger = logging.getLogger(__name__)

JUDGE_PROMPT_VERSION = 1

JUDGE_VERDICTS = frozenset({"entailed", "contradicted", "unsupported"})

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

USER_TEMPLATE = "PREMISE:\n{premise}\n\nHYPOTHESIS:\n{hypothesis}"


def build_messages(premise: str, hypothesis: str) -> list[dict]:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
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

    async def qualification_probe(self, premise: str, hypothesis: str) -> ProbeVerdict:
        """The ungated door, named for its only lawful caller: the
        qualification harness must be able to measure an unqualified judge.
        A source scan pins that nothing else under ``app/`` reaches it."""
        raw = await self.llm.chat_completion(
            "verification",
            build_messages(premise, hypothesis),
            response_format={"type": "json_object"},
            seed=_content_seed(premise + "\n" + hypothesis),
        )
        return parse_verdict(raw)

    async def judge(
        self,
        session: AsyncSession,
        premise: str,
        hypothesis: str,
        record_path: Path | None = None,
    ) -> ProbeVerdict:
        """The gated door — the only entry a consumer may use. Refuses with
        ``JudgeNotQualifiedError`` unless the recorded qualification matches
        the currently resolved judge identity and clears the currently
        merged bars, recomputed on every call (detected, never remembered)."""
        state = await qualification_state(
            session, self.llm.config,
            record_path=record_path if record_path is not None else QUALIFICATION_RECORD_PATH,
        )
        if not state.qualified:
            raise JudgeNotQualifiedError(
                "the verification judge is not qualified for its current "
                "identity and bars; no consumer may ship on its verdicts "
                "(doc 17 §6). Reasons: " + "; ".join(state.reasons)
            )
        return await self.qualification_probe(premise, hypothesis)


# ── judge identity: what a qualification is recorded against ─────────────

# caching_llm._KEYED_CONFIG_FIELDS minus nothing: the same resolved-config
# fields whose change makes a cached answer stale make a qualification
# stale. api_key is deliberately absent — rotating a credential is not a
# model swap.
IDENTITY_FIELDS = ("model", "base_url", "api_kind", "dimensions", "reasoning", "params")


def judge_identity(cfg) -> dict:
    """The identity a qualification binds to: the resolved purpose config's
    behaviour-shaping fields plus the prompt version and the hash of ALL
    prompt text (system prompt + user-message template — both are sent on
    every call, so an edit to either is a judge change and must move the
    identity even without a version bump)."""
    identity = {field: getattr(cfg, field, None) for field in IDENTITY_FIELDS}
    identity["prompt_version"] = JUDGE_PROMPT_VERSION
    identity["prompt_sha"] = hashlib.sha256(
        (SYSTEM_PROMPT + USER_TEMPLATE).encode("utf-8")
    ).hexdigest()[:16]
    return identity


def judge_identity_hash(identity: dict) -> str:
    canonical = json.dumps(identity, sort_keys=True, default=str, ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()[:16]


# ── the qualification record and the computed state ──────────────────────

QUALIFICATION_RECORD_PATH = Path(__file__).resolve().parent / "verification_qualification.json"

# Bar config-row key -> the recorded metric it governs.
BAR_METRICS = {
    "groundedness_gate_precision_bar": "entailed_precision",
    "groundedness_gate_recall_bar": "entailed_recall",
    "contradiction_precision_bar": "contradiction_precision",
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


async def qualification_state(
    session: AsyncSession,
    llm_config: dict,
    record_path: Path = QUALIFICATION_RECORD_PATH,
) -> QualificationState:
    record = load_qualification_record(record_path)
    if record is None:
        return QualificationState(False, ("no qualification record",), None)

    reasons: list[str] = []

    if not record.get("gate_eligible"):
        reasons.append("the record is not gate_eligible (interim or rehearsal output)")

    cfg = llm_config.get("verification") if llm_config else None
    if cfg is None:
        reasons.append("no verification purpose in the resolved LLM config")
    else:
        current_hash = judge_identity_hash(judge_identity(cfg))
        recorded = record.get("judge_identity") or {}
        recorded_hash = recorded.get("identity_hash")
        if recorded_hash != current_hash:
            reasons.append(
                f"judge identity mismatch: recorded {recorded_hash!r}, current "
                f"{current_hash!r} — a model, param or prompt change requires "
                "re-qualification (doc 17 §11)"
            )

    bars = await get_verification_bars(session)
    metrics = record.get("metrics") or {}
    for bar_key, metric_key in BAR_METRICS.items():
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

VERIFICATION_BAR_DEFAULTS: dict[str, float] = {
    "groundedness_gate_precision_bar": 0.95,
    "groundedness_gate_recall_bar": 0.90,
    "contradiction_precision_bar": 0.95,
}


async def get_verification_bars(session: AsyncSession) -> dict[str, float]:
    """Merge per-bar ``config`` rows over the code defaults, DB winning per
    key. A row's value may be ``{"value": x}`` or a bare JSON number; an
    unreadable row falls back to the default rather than failing the
    enforcement path."""
    rows = (await session.execute(
        select(Config).where(Config.key.in_(VERIFICATION_BAR_DEFAULTS))
    )).scalars().all()

    bars = dict(VERIFICATION_BAR_DEFAULTS)
    for row in rows:
        value = row.value
        if isinstance(value, dict):
            value = value.get("value")
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            bars[row.key] = float(value)
        else:
            logger.warning("config row %s carries an unreadable bar value %r; "
                           "using the default", row.key, row.value)
    return bars
