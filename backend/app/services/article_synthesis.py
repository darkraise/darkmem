"""Article synthesis — the productive runs (T3.02, doc 09 §4.2).

An eligible subject in (T3.01), one stored article out, synthesised from
verified facts only and journalled so a bad article is traceable to its fact
set.

**The exclusion is a ``WHERE``, and that is a safety property rather than a
performance note.** Doc 09 §4.2 names two load-bearing exclusions — disputed
facts and candidate facts — and the done-when says "excluded at the query, not
filtered from the draft". The difference matters because a filter applied to a
*draft* removes facts and leaves prose: the model has already seen the disputed
fact and may have written a sentence whose citation no longer supports it, and
that sentence survives the filter. So a fact that must not ground an article is
never loaded.

**One statuses constant, not two.** ``VERIFIED_STATUSES`` is
:mod:`app.services.article_eligibility`'s, imported rather than restated: the
subject that *earned* an article and the facts that *fill* it must agree on
what "verified" counts as, and two copies is how they stop agreeing. The
eligibility module's own docstring makes the same point about resolving the set
in one place.

**What is deliberately not excluded.** A ``corroborated`` fact carrying
``contradiction_suspected_at`` is still a synthesis input. Doc 09 §4.2 names
two exclusions and no suspicion flag, and T2.109 moved the LLM contradiction
scan off every suppressive path after measuring it at 0.79–0.90 against a 0.95
bar — a flagged fact "keeps its rung, its badge and its place in retrieval".
Excluding it here would hand a sub-bar instrument a new suppressive channel, in
which a false positive silently drops a *true* corroborated fact from its
article. Adding the exclusion is a Tier-3 amendment to §4.2, not a tightening
anyone may make at a call site.

**The model proposes citations; nothing here trusts them.** Doc 09 §4.2 has
the ``synthesis`` call emit prose "with per-sentence candidate fact ids
attached" so T3.03's entailment pass verifies proposed citations rather than
searching for support. A proposal is not a grounding: a sentence citing an id
that was not in the input set is refused outright rather than dropped, because
an id the model invented means the response is describing a fact set that was
never handed to it, and keeping the rest would keep prose written under that
misapprehension.

**Recency's basis is the belief window, then the clock.** §4.2 fixes the
ranking as ``confidence × read-heat × recency`` and does not say what recency
is measured from. A fact's ``reference_time`` is when the claim is *about*,
which is what "recent knowledge" means for a fact; ``created_at`` is when
darkmem heard it. ``reference_time`` is ``NOT NULL`` on the table, so it is the
basis, and the fallback exists only for defence.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from uuid import uuid4
from typing import TYPE_CHECKING, Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.article_eligibility import (
    SUPPORTING_BELIEF_PREDICATE,
    VERIFIED_STATUSES,
    select_for_synthesis,
)
from app.services.articles_channel import ARTICLE_EMBEDDINGS_PARENT
from app.services.embedder_registry import child_table
from app.services.events import ARTICLE_STALE, record_event
from app.services.pin_suggestions import decode_subject_soft_key

if TYPE_CHECKING:  # pragma: no cover - typing only
    from app.services.claim_entailment import Claim, CoverageOutcome, CoverageResult

__all__ = [
    "DEFAULT_HUB_CAP",
    "DEFAULT_LENGTH_BUDGET_WORDS",
    "DraftArticle",
    "DraftRefused",
    "DraftSentence",
    "GatheredFact",
    "LENGTH_CEILING_FACTOR",
    "SYNTHESIS_PURPOSE",
    "SYNTHESIS_EVENT",
    "UNMEASURED_STATUS",
    "SynthesisOutcome",
    "gather_facts",
    "group_facts",
    "run_article_synthesis",
    "store_article",
    "synthesise_draft",
    "write_article_embedding",
    "write_coverage",
    "DEFAULT_DEBOUNCE_HOURS",
    "ResynthesisOutcome",
    "StaleArticle",
    "resynthesise_subject",
    "run_article_resynthesis",
    "stale_articles",
    "staleness_settled",
]

# Doc 09 §4.3 makes coverage the gate: an article below the threshold "does not
# ship as `corroborated`, it sets `review_state='open'`". An article with no
# *measured* coverage is not above the threshold -- it is unmeasured, which is
# the same serving outcome for a different reason. Writing `corroborated`
# because nothing has yet said otherwise is exactly the confident-but-wrong
# failure Layer 3 exists to prevent, and the column would accept it.
#
# This is permanent behaviour for an unmeasured article, not scaffolding T3.03
# deletes. T3.03 adds the measurement that can raise it, and finds the
# unmeasured ones by their NULL confidence.
UNMEASURED_STATUS = "candidate"
UNMEASURED_REVIEW_STATE = "open"

# `created` + `object_type='article'`, both already in the closed vocabularies,
# so no taxonomy widening is needed. Deliberately NOT `consolidated`: the dream
# digest groups that stream by `payload.cycle_id`, and foreign rows would
# corrupt a cycle's description.
SYNTHESIS_EVENT = "created"
ARTICLE_OBJECT_TYPE = "article"

# Doc 11's eighth purpose, seeded inert since day one. T3.02 is its first
# consumer; nothing else in the tree dispatches on it.
logger = logging.getLogger(__name__)

SYNTHESIS_PURPOSE = "synthesis"

# **Per-subject failures are counted and logged, not written to
# `pipeline_failures`, and that is a discovery rather than a preference.**
# The plan's Step 5 named that table on the `code_deriver` precedent, but
# `PipelineFailureService.record` takes a **required UUID `entity_id`** and a
# failed synthesis has no candidate for one: no article was written, and
# `SubjectCandidate` carries only a `subject_key` — a pinned subject need not
# have an `entities` row at all. Minting a UUID to satisfy the column, or
# looking up an entity that may not exist, would put a row in triage keyed to
# something that is not the thing that failed. The outcome's `refused`/`failed`
# counts are what a tick reports, and they are separate because a vendor outage
# and an unusable draft mean different things to an operator.

# Doc 09 §4.2's length budget: "a config word/token cap, defaulting to a few
# hundred words". It is the second of the two knobs the doc calls "two knobs on
# the same lever" -- with K it bounds both readability and the cost of T3.03's
# per-claim entailment pass.
DEFAULT_LENGTH_BUDGET_WORDS = 400

# ...with a hard ceiling. The budget is what the prompt asks for; the ceiling is
# what the response is held to. A model that overruns by a little is ordinary
# and the budget absorbs it; one that overruns by this much has ignored the
# instruction, and storing that article would hand T3.23 a chunking problem and
# T3.03 an unbounded bill.
LENGTH_CEILING_FACTOR = 1.5

# Doc 09 §4.2's hub cap: "top-K facts by fact-salience", K a `config` row
# "defaulting modest, e.g. 40". The cap does three jobs — it keeps a hub like
# `postgres` from producing an unreadable essay, it keeps the article focused,
# and because an article's claim count is bounded by its fact count it bounds
# the cost of T3.03's per-claim entailment pass. K and the length budget are
# two knobs on the same lever.
DEFAULT_HUB_CAP = 40

# Half-life for the recency term, in days. A fact stated a year ago is not
# worthless — it is less salient than one stated last week, which is what a
# decay expresses and a cutoff does not. Exponential rather than linear so the
# term is bounded in (0, 1] and cannot go negative and invert the product.
RECENCY_HALF_LIFE_DAYS = 180.0

# Facts carry a nullable `confidence`. A fact with none is not a fact with no
# confidence in it — it is one nothing measured — so it ranks at the same
# neutral value `memories.confidence` defaults to rather than at zero, which
# would drop every unmeasured fact below every measured one regardless of heat.
NEUTRAL_CONFIDENCE = 0.75


@dataclass(frozen=True)
class GatheredFact:
    """One verified fact, as a synthesis input.

    Carries the fields §4.2's grouping needs (``rel_type``, ``applies_when``)
    and the fields the draft needs (``fact``, the endpoint names), plus the
    ranking inputs so a caller can explain an ordering without re-querying.
    """

    id: str
    subject_name: str
    rel_type: str
    object_name: str
    fact: str
    applies_when: dict[str, Any] | None
    learned_in: list[str]
    confidence: float
    read_heat: float
    reference_time: datetime | None
    salience: float


# Doc 09 §4.2's predicate, verbatim: the subject's non-disputed
# corroborated/confirmed facts, unexpired. `disputed` and `candidate` are both
# `verification_status` values, so the `= ANY` clause is what implements both
# named exclusions — the flowchart's separate `AND not disputed` restates the
# first rather than adding a third.
#
# Ranked in SQL rather than in Python because the cap is a `LIMIT`: pulling a
# hub's several hundred facts across the wire to drop all but forty would make
# the cap a readability knob only, and §4.2 makes it a cost knob too.
_FACTS_SQL = text(
    f"""
    SELECT t.id,
           t.subject_name,
           t.rel_type,
           t.object_name,
           t.fact,
           t.applies_when,
           t.learned_in,
           t.confidence,
           t.reference_time,
           COALESCE(a.access_count, 0) AS read_heat,
           (
               COALESCE(t.confidence, CAST(:neutral AS double precision))
               * (1 + COALESCE(a.access_count, 0))
               * exp(
                   -GREATEST(
                       EXTRACT(EPOCH FROM (CAST(:now AS timestamptz) - t.reference_time))
                       / 86400.0,
                       0
                   ) * ln(2) / CAST(:half_life AS double precision)
               )
           ) AS salience
    FROM knowledge_triples t
    LEFT JOIN fact_access_stats a ON a.fact_id = t.id
    WHERE t.project = CAST(:project AS text)
      AND lower(t.subject_name) = CAST(:subject AS text)
      AND t.verification_status = ANY(CAST(:statuses AS text[]))
      AND {SUPPORTING_BELIEF_PREDICATE}
    ORDER BY salience DESC, t.id
    LIMIT :cap
    """
)


async def gather_facts(
    session: AsyncSession,
    *,
    subject: str,
    project: str = "default",
    cap: int = DEFAULT_HUB_CAP,
    now: datetime | None = None,
) -> list[GatheredFact]:
    """The subject's verified facts, ranked by §4.2's salience and capped.

    ``subject`` is matched lower-cased, matching how ``article_eligibility``
    groups subjects (``lower(t.subject_name)``): entity names are stored
    lower-cased and the eligibility scan keys on that, so a caller handing back
    the ``name_lower`` it was given finds the same rows.

    ``now`` is a parameter rather than a clock read so the ranking is testable
    for equality — the same reason ``inject_block.render_block`` takes its
    ``generated_at``.

    **Read-heat is computed here, never read from a stored column.** Doc 09
    §4.1 is explicit that heat is "computed at job time, never a stored heat
    column that would go stale"; the substrate is ``fact_access_stats``, the
    fact-keyed counter, joined exactly as the eligibility scan joins it.
    """
    stamp = now or datetime.now(timezone.utc)
    rows = (
        await session.execute(
            _FACTS_SQL,
            {
                "project": project,
                "subject": subject.lower(),
                "statuses": list(VERIFIED_STATUSES),
                "cap": max(0, cap),
                "now": stamp,
                "neutral": NEUTRAL_CONFIDENCE,
                "half_life": RECENCY_HALF_LIFE_DAYS,
            },
        )
    ).mappings().all()

    return [
        GatheredFact(
            id=str(row["id"]),
            subject_name=row["subject_name"],
            rel_type=row["rel_type"],
            object_name=row["object_name"],
            fact=row["fact"],
            applies_when=row["applies_when"],
            learned_in=list(row["learned_in"] or []),
            confidence=(
                float(row["confidence"])
                if row["confidence"] is not None
                else NEUTRAL_CONFIDENCE
            ),
            read_heat=float(row["read_heat"]),
            reference_time=row["reference_time"],
            salience=float(row["salience"]),
        )
        for row in rows
    ]


# ─────────────── grouping and the draft (Step 2) ───────────────


class DraftRefused(RuntimeError):
    """The synthesis call produced nothing this module will store.

    Raised rather than returning a partial draft. Every refusal here is a
    response that misdescribes its own inputs — an invented citation, an
    overrun, unparseable JSON — and the honest outcome for the run is that no
    article was written, which the caller journals. A partial article stored
    under any of them would be prose nobody can account for.
    """


@dataclass(frozen=True)
class DraftSentence:
    """One sentence and the fact ids the model proposes ground it.

    ``fact_ids`` is a *proposal*. T3.03 verifies it; nothing here does, and
    nothing here may treat it as grounding.
    """

    text: str
    fact_ids: list[str]


@dataclass(frozen=True)
class DraftArticle:
    """The lead is a claim like any other, and it cites facts.

    It was a bare string until T3.03. Under §4.3's rule that an uncited span is
    ungrounded, an uncited lead is a permanent failure in every article — so
    coverage would cap at N/(N+1), and at a 0.95 bar a *perfectly grounded*
    article would need nineteen sentences to pass against a length budget
    yielding roughly sixteen to twenty-six. Most articles would have routed to
    review on their length rather than their grounding, and every stub-judge
    test would still have passed.
    """

    lead: DraftSentence
    sentences: list[DraftSentence]

    @property
    def claims(self) -> list[DraftSentence]:
        """Every claim, lead first — the order the body renders in."""
        return [self.lead, *self.sentences]

    @property
    def body(self) -> str:
        return "\n".join(s.text for s in self.claims).strip()

    @property
    def word_count(self) -> int:
        return len(self.body.split())


def group_facts(
    facts: list[GatheredFact],
) -> "OrderedDict[tuple[str, str], list[GatheredFact]]":
    """Doc 09 §4.2's grouping: by relation type, then by ``applies_when``.

    Ordered, and the order is the salience order the gather returned — a group
    is keyed by the first fact that reached it, so the article's sections lead
    with its most load-bearing knowledge rather than with whatever relation
    sorts first alphabetically.

    The ``applies_when`` half is what keeps a scoped claim from reading as a
    universal one: "a fact that holds only in `env=prod` reads as a scoped
    claim, not a universal one". A fact with none groups under the empty
    context, which is the honest rendering of "no context restriction".
    """
    groups: OrderedDict[tuple[str, str], list[GatheredFact]] = OrderedDict()
    for fact in facts:
        context = (
            json.dumps(fact.applies_when, sort_keys=True) if fact.applies_when else ""
        )
        groups.setdefault((fact.rel_type, context), []).append(fact)
    return groups


def _draft_seed(facts: list[GatheredFact]) -> int:
    """A deterministic seed over the *ranked fact-id set*.

    Synthesis has no single ``content`` to hash the way extraction does, and
    the reproducibility rule still applies: the same subject over the same
    facts in the same order must produce the same article across calls. The
    ranked ids are exactly that input, and they are order-sensitive on purpose
    — a reordered fact set is a different prompt.
    """
    basis = "|".join(fact.id for fact in facts)
    return int(hashlib.sha256(basis.encode("utf-8")).hexdigest()[:8], 16)


_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


def _strip_fences(text: str) -> str:
    match = _FENCE_RE.search((text or "").strip())
    return match.group(1).strip() if match else (text or "").strip()


def _build_messages(
    subject: str,
    groups: "OrderedDict[tuple[str, str], list[GatheredFact]]",
    budget_words: int,
) -> list[dict]:
    """The prompt: the subject, its grouped facts, and the budget.

    **Only the gathered facts reach it.** The prompt is built from the grouped
    input and nothing else — no retrieval, no memory content, no prior article.
    An article's "only inputs are verified facts" (doc 09 §4.2), and a prompt
    that reached for context would make that false at the one place it is
    checkable.
    """
    lines: list[str] = []
    for (rel_type, context) in groups:
        scope = f" (applies when {context})" if context else ""
        lines.append(f"## {rel_type}{scope}")
        for fact in groups[(rel_type, context)]:
            lines.append(f"- [{fact.id}] {fact.fact}")

    system = (
        "You write short, factual reference articles about one subject, using "
        "ONLY the facts given. Every sentence must cite at least one fact id "
        "from the list. Never state anything the facts do not say. Never cite "
        "an id that is not in the list.\n"
        "Respond with JSON: {\"lead\": {\"text\": \"<one definitional "
        "sentence>\", \"fact_ids\": [\"<id>\"]}, "
        "\"sentences\": [{\"text\": \"<sentence>\", \"fact_ids\": [\"<id>\"]}]}"
    )
    user = (
        f"Subject: {subject}\n"
        f"Length budget: about {budget_words} words in total.\n\n"
        f"Facts:\n" + "\n".join(lines)
    )
    return [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]


def _parse(payload: str, allowed_ids: set[str]) -> DraftArticle:
    try:
        data = json.loads(_strip_fences(payload))
    except (json.JSONDecodeError, TypeError) as error:
        raise DraftRefused(f"the synthesis response was not JSON: {error}") from error
    if not isinstance(data, dict):
        raise DraftRefused("the synthesis response was not a JSON object")

    lead_raw = data.get("lead")
    if isinstance(lead_raw, str):
        # A bare string lead is the pre-T3.03 shape and carries no citation,
        # which §4.3 makes ungroundable. Refused rather than accepted with an
        # empty citation list, so the model is told rather than silently
        # scored down.
        raise DraftRefused(
            "the lead must cite facts like any other claim; a bare string lead "
            "is uncited and an uncited span is by definition ungrounded"
        )
    if not isinstance(lead_raw, dict):
        raise DraftRefused("the synthesis response carried no lead sentence")

    raw_sentences = data.get("sentences")
    if not isinstance(raw_sentences, list) or not raw_sentences:
        raise DraftRefused("the synthesis response carried no sentences")

    sentences: list[DraftSentence] = []
    for entry in [lead_raw, *raw_sentences]:
        if not isinstance(entry, dict):
            raise DraftRefused("a sentence entry was not an object")
        text_value = entry.get("text")
        ids = entry.get("fact_ids")
        if not isinstance(text_value, str) or not text_value.strip():
            raise DraftRefused("a sentence carried no text")
        if not isinstance(ids, list) or not ids:
            # Doc 09 §4.3: "a claim with no citation fails outright (no
            # search-for-support fallback -- an uncited span is by definition
            # ungrounded)". Refused at the draft rather than deferred to
            # T3.03, because an uncited sentence is not a claim the entailment
            # pass can evaluate.
            raise DraftRefused(f"a sentence cited no fact: {text_value[:60]!r}")
        cited = [str(i) for i in ids]
        invented = [i for i in cited if i not in allowed_ids]
        if invented:
            raise DraftRefused(
                f"the synthesis response cited {len(invented)} fact id(s) that "
                f"were not in its input set ({invented[0]!r}). The response is "
                f"describing a fact set it was never handed; keeping the rest "
                f"would keep prose written under that misapprehension."
            )
        sentences.append(DraftSentence(text=text_value.strip(), fact_ids=cited))

    return DraftArticle(lead=sentences[0], sentences=sentences[1:])


async def synthesise_draft(
    llm,
    *,
    subject: str,
    facts: list[GatheredFact],
    budget_words: int = DEFAULT_LENGTH_BUDGET_WORDS,
) -> DraftArticle:
    """One ``synthesis``-purpose call producing a draft, or a refusal.

    Raises :class:`DraftRefused` on anything this module will not store, and
    lets an orchestrator failure propagate untouched — the caller distinguishes
    "the model produced something unusable" from "the model could not be
    reached", and collapsing them would hide an outage behind a content error.
    """
    if not facts:
        raise DraftRefused("no verified facts to synthesise from")

    groups = group_facts(facts)
    messages = _build_messages(subject, groups, budget_words)
    payload = await llm.chat_completion(
        SYNTHESIS_PURPOSE,
        messages=messages,
        response_format={"type": "json_object"},
        seed=_draft_seed(facts),
    )
    draft = _parse(payload or "", {fact.id for fact in facts})

    ceiling = int(budget_words * LENGTH_CEILING_FACTOR)
    if draft.word_count > ceiling:
        raise DraftRefused(
            f"the synthesis response ran to {draft.word_count} words against a "
            f"{budget_words}-word budget and a {ceiling}-word ceiling. The "
            f"budget absorbs an ordinary overrun; this one ignored the "
            f"instruction, and storing it would hand T3.23 a chunking problem "
            f"and T3.03 an unbounded per-claim bill."
        )
    return draft


# ─────────────── the write and the journal (Steps 3-4) ───────────────


def fact_set_hash(fact_ids: list[str]) -> str:
    """Doc 09 §4.4's staleness basis: a digest of the **full** verified set.

    Two properties, and both are the doc's.

    **Uncapped.** §4.4 hashes "the subject's non-disputed
    corroborated/confirmed facts only" — the whole set, so staleness fires
    exactly when knowledge changed. Hashed over the top-K *input* set instead,
    read-heat drift reorders the cap boundary and flips the hash with no
    knowledge change at all, which is the precise failure §4.4 exists to
    prevent ("not when raw signal arrived").

    **Order-independent**, for the same reason: the set is what changed or did
    not, and a re-ranking is not a change to it.
    """
    basis = "|".join(sorted(fact_ids))
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


_LIVE_ARTICLE_SQL = text(
    "SELECT id FROM knowledge_articles "
    "WHERE project = CAST(:project AS text) "
    "AND subject_key = CAST(:subject AS text) "
    "AND status <> 'superseded' "
    "LIMIT 1"
)

_INSERT_ARTICLE_SQL = text(
    """
    INSERT INTO knowledge_articles
        (id, subject_key, project, title, content, status, confidence,
         applies_when, learned_in, synthesized_at, fact_set_hash, review_state)
    VALUES
        (CAST(:id AS uuid), CAST(:subject AS text), CAST(:project AS text),
         CAST(:title AS text), CAST(:content AS text), CAST(:status AS text),
         NULL,
         CAST(:applies_when AS jsonb), CAST(:learned_in AS text[]),
         CAST(:now AS timestamptz), CAST(:hash AS text), CAST(:review AS text))
    RETURNING id
    """
)


class LiveArticleExists(RuntimeError):
    """This subject already holds a live article, so this task writes none.

    Re-synthesis — supersession, the ``superseded_by`` pointer, the debounce
    and the staleness gate — is T3.05's, whole. Splitting it would mean
    flipping the prior row to ``superseded`` here to satisfy
    ``ux_knowledge_articles_live`` while deferring its pointer, and
    ``knowledge_articles`` has **no** ``chk_superseded_has_pointer`` (unlike
    ``memories``), so a deferred pointer does not error — it silently loses the
    lineage.

    In a wired run this is unreachable: ``select_for_synthesis`` already
    excludes subjects holding a live article. It is defence in depth for a
    caller that skipped the selector, which is why the write path is tested
    directly rather than through the driver.
    """


def _aggregate_applies_when(facts: list[GatheredFact]) -> dict[str, Any] | None:
    """The article's ``applies_when``, unioned from its supporting facts.

    Doc 04 §8.8 aggregates it, and doc 09 §4.2 calls the result *displayed
    provenance* rather than a trustworthy scope — so a key two facts disagree
    on keeps both values rather than picking one. Dropping the conflict would
    render a scope no fact asserts.
    """
    merged: dict[str, set[str]] = {}
    for fact in facts:
        for key, value in (fact.applies_when or {}).items():
            merged.setdefault(str(key), set()).add(str(value))
    if not merged:
        return None
    return {
        key: (values.pop() if len(values) == 1 else sorted(values))
        for key, values in ((k, set(v)) for k, v in merged.items())
    }


async def write_article_embedding(
    session: AsyncSession,
    llm,
    *,
    article_id: str,
    text_body: str,
) -> str | None:
    """Embed the article into ``article_embeddings__<slug>`` (T3.23).

    Returns the fingerprint written, or ``None`` when no embedder is
    configured — an install without one still synthesises and stores; it just
    has no L3 retrieval until it has one. Raising here would make the article
    unwritable on an install whose embedder is merely absent.

    ``_register_fingerprint``'s discipline applies: the partition is created
    before the insert, through the registry, never by naming a child table
    here.
    """
    if llm is None:
        return None
    from app.services.embedder_registry import (
        EmbedderInfo,
        embedder_registry,
        parse_fingerprint,
    )

    vector, fingerprint = await llm.embed(text_body)
    if not embedder_registry.is_known(fingerprint):
        model_id, dims = parse_fingerprint(fingerprint)
        await embedder_registry.register(
            session,
            # `source='llm'` is CHECK-constrained on `embedders`; the column
            # records how the vectors are produced, not which feature asked.
            EmbedderInfo(
                fingerprint=fingerprint, model_id=model_id, dims=dims, source="llm"
            ),
        )
    await session.execute(
        text(
            f"INSERT INTO {child_table(ARTICLE_EMBEDDINGS_PARENT, fingerprint)} "
            "(article_id, fingerprint, embedding) VALUES "
            "(CAST(:id AS uuid), CAST(:fp AS text), CAST(:vec AS vector)) "
            "ON CONFLICT (article_id, fingerprint) DO UPDATE "
            "SET embedding = EXCLUDED.embedding"
        ),
        {"id": article_id, "fp": fingerprint, "vec": str(vector)},
    )
    return fingerprint


async def store_article(
    session: AsyncSession,
    *,
    subject: str,
    project: str,
    draft: DraftArticle,
    facts: list[GatheredFact],
    all_verified_ids: list[str],
    now: datetime | None = None,
    actor: str | None = None,
) -> str:
    """Write one article and journal its inputs. Does not commit.

    ``facts`` is the capped set the draft was built from; ``all_verified_ids``
    is the subject's whole verified set, which is what the hash covers.

    The journal names the **fact ids** and never the prose. Write-time
    minimization is the standing rule, and it binds with its usual force here:
    the article row holds the text, the journal answers "which facts produced
    it", and ids stay honest about facts later invalidated in a way a copy of
    the prose would not.
    """
    existing = (
        await session.execute(
            _LIVE_ARTICLE_SQL, {"project": project, "subject": subject}
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise LiveArticleExists(
            f"{subject!r} already holds live article {existing}; re-synthesis "
            f"is T3.05's, whole."
        )

    stamp = now or datetime.now(timezone.utc)
    learned_in = sorted({tag for fact in facts for tag in fact.learned_in})
    applies_when = _aggregate_applies_when(facts)
    article_id = (
        await session.execute(
            _INSERT_ARTICLE_SQL,
            {
                "id": str(uuid4()),
                "subject": subject,
                "project": project,
                "title": subject,
                "content": draft.body,
                "status": UNMEASURED_STATUS,
                "applies_when": (
                    json.dumps(applies_when) if applies_when is not None else None
                ),
                "learned_in": learned_in,
                "now": stamp,
                "hash": fact_set_hash(all_verified_ids),
                "review": UNMEASURED_REVIEW_STATE,
            },
        )
    ).scalar_one()

    await record_event(
        session,
        event_type=SYNTHESIS_EVENT,
        object_type=ARTICLE_OBJECT_TYPE,
        object_id=article_id,
        project=project,
        actor=actor,
        payload={
            "subject_key": subject,
            # Ranked order, because which facts the cap admitted and in what
            # priority is the question a bad article is traced with.
            "fact_ids": [fact.id for fact in facts],
            "verified_fact_count": len(all_verified_ids),
            "cap": len(facts),
            "purpose": SYNTHESIS_PURPOSE,
            "fact_set_hash": fact_set_hash(all_verified_ids),
        },
    )
    return str(article_id)


# ─────────────── the run (Step 5) ───────────────


@dataclass
class SynthesisOutcome:
    """(see below) — ``unmeasured`` added by T3.03 (D14)."""
    """What one tick did, per the doc's own vocabulary.

    ``refused`` and ``failed`` are separate counts because they mean different
    things to an operator: a refusal is the model producing something this
    module will not store, a failure is everything else — an outage, a bad
    config, a bug. Collapsing them would make a vendor outage read as a run of
    unusable drafts.
    """

    projects: int = 0
    attempted: int = 0
    written: int = 0
    refused: int = 0
    failed: int = 0
    # Stored successfully, but coverage could not be scored (T3.03). **Not**
    # `failed` — nothing failed — and **not** `refused`, which already means
    # the model produced something unstorable. Three counts for three states,
    # the same discipline that keeps the first two apart: with G-D open this
    # is every article on every tick, and folding it into `failed` would make
    # a permanent standing state read as a permanent vendor outage.
    unmeasured: int = 0
    last_project: str | None = None
    # The projects this tick actually rotated onto. Carried so T3.05's
    # re-synthesis pass runs over the *same* batch: a second cursor would let
    # the two passes drift onto different projects, and a subject would then be
    # eligible for a first article in one pass and stale in the other on
    # different ticks, for no reason an operator could see.
    visited: list[str] = field(default_factory=list)


_ALL_VERIFIED_IDS_SQL = text(
    f"""
    SELECT t.id
    FROM knowledge_triples t
    WHERE t.project = CAST(:project AS text)
      AND lower(t.subject_name) = CAST(:subject AS text)
      AND t.verification_status = ANY(CAST(:statuses AS text[]))
      AND {SUPPORTING_BELIEF_PREDICATE}
    """
)

_NEXT_PROJECTS_SQL = text(
    """
    SELECT DISTINCT project FROM knowledge_triples
    -- Both sides cast. An uncast bind on the left of IS NULL has no type
    -- asyncpg can infer -- CLAUDE.md's raw-SQL CAST invariant. (Written
    -- without a colon-prefixed name here because text() parses bind params
    -- inside SQL comments too, and naming one turns this into a required
    -- parameter nobody passes.)
    WHERE (CAST(:after_project AS text) IS NULL
           OR project > CAST(:after_project AS text))
    ORDER BY project
    LIMIT CAST(:batch_size AS int)
    """
)


async def all_verified_fact_ids(
    session: AsyncSession, *, subject: str, project: str
) -> list[str]:
    """Every verified fact id for the subject — the hash's basis, uncapped.

    Deliberately a second query rather than a wider first one: the gather is
    ``LIMIT``ed because the cap is a cost knob, and lifting that limit to get
    the hash would spend on the wire exactly what the cap exists to save. This
    reads ids alone.
    """
    rows = await session.execute(
        _ALL_VERIFIED_IDS_SQL,
        {
            "project": project,
            "subject": subject.lower(),
            "statuses": list(VERIFIED_STATUSES),
        },
    )
    return [str(row[0]) for row in rows.all()]


async def synthesise_subject(
    session: AsyncSession,
    llm,
    *,
    subject_key: str,
    project: str,
    cap: int = DEFAULT_HUB_CAP,
    budget_words: int = DEFAULT_LENGTH_BUDGET_WORDS,
    now: datetime | None = None,
) -> str | None:
    """Gather, draft, store. Returns the article id, or ``None`` on a refusal.

    ``subject_key`` is the **soft key** ``name::entity_type`` that
    ``select_for_synthesis`` hands back, and the two halves go to different
    places: the *name* is what the fact queries match on
    (``lower(subject_name)``), and the *whole key* is what
    ``knowledge_articles.subject_key`` stores and what
    ``ux_knowledge_articles_live`` is unique on.

    Passing the soft key into the name match is the bug this signature exists
    to prevent: it matches nothing, so every subject "refuses" with no facts,
    the tick reports work attempted and none written, and nothing raises.

    Raises on anything that is not a refusal, so the caller can tell an outage
    from an unusable draft.
    """
    name, _entity_type = decode_subject_soft_key(subject_key)
    facts = await gather_facts(
        session, subject=name, project=project, cap=cap, now=now
    )
    if not facts:
        return None
    draft = await synthesise_draft(
        llm, subject=name, facts=facts, budget_words=budget_words
    )
    all_ids = await all_verified_fact_ids(session, subject=name, project=project)
    article_id = await store_article(
        session,
        subject=subject_key,
        project=project,
        draft=draft,
        facts=facts,
        all_verified_ids=all_ids,
        now=now,
    )
    # The article is written and journalled first; the embedding is what makes
    # it *retrievable*, and an embedder outage must not un-write an article
    # that is otherwise complete. A missing embedding is a subject absent from
    # L3 retrieval until the next run, which is recoverable; a rolled-back
    # article is work lost.
    try:
        await write_article_embedding(
            session, llm, article_id=article_id, text_body=draft.body
        )
    except Exception as error:  # noqa: BLE001 - retrievability is not storability
        logger.warning(
            "article_synthesis: %s stored but not embedded: %s", article_id, error
        )
    # The draft and its fact set ride back so the caller can measure coverage
    # **after this transaction commits** (T3.03 D9). Measuring inline would put
    # the judge call inside the article's own transaction, and a raise there
    # rolls the article back — work lost for a reason that has nothing to do
    # with whether the article was written correctly.
    return article_id, draft, facts


async def run_article_synthesis(
    session_factory,
    llm_provider=None,
    *,
    batch_size: int = 5,
    after_project: str | None = None,
    hub_cap: int = DEFAULT_HUB_CAP,
    budget_words: int = DEFAULT_LENGTH_BUDGET_WORDS,
    now: datetime | None = None,
) -> SynthesisOutcome:
    """One tick: a rotating batch of projects, each subject in its own session.

    **Per-subject sessions, not one per tick.** A model call is measured in
    seconds and there is one per subject; holding a write transaction open
    across all of them would keep locks for the length of the whole batch, and
    one subject's failure would roll back every article written before it. Each
    subject commits on its own, which is also what makes the per-subject
    failure isolation real rather than a `try` around a shared transaction.

    **The budget is T3.01's, not a second one.** ``select_for_synthesis``
    applies ``synthesis_budget`` from the ``article_selection`` config row and
    already excludes subjects that hold a live article. ``batch_size`` bounds
    *projects* per tick, a different level — so the two knobs compose rather
    than contradict.

    **The cursor advances over projects visited, not projects that succeeded.**
    A project failing deterministically would otherwise pin the rotation and
    starve every project behind it.
    """
    outcome = SynthesisOutcome(last_project=after_project)
    llm = llm_provider() if callable(llm_provider) else llm_provider

    async with session_factory() as session:
        projects = [
            row[0]
            for row in (
                await session.execute(
                    _NEXT_PROJECTS_SQL,
                    {"after_project": after_project, "batch_size": max(1, batch_size)},
                )
            ).all()
        ]

    for project in projects:
        outcome.projects += 1
        outcome.last_project = project
        outcome.visited.append(project)
        async with session_factory() as session:
            subjects = await select_for_synthesis(session, project=project)

        for candidate in subjects:
            outcome.attempted += 1
            if llm is None:
                # No orchestrator configured is not a draft failure; it is the
                # job having nothing to run with. Counted as failed so the tick
                # does not read as a clean no-op.
                outcome.failed += 1
                continue
            try:
                measurable = None
                async with session_factory() as session:
                    written = await synthesise_subject(
                        session,
                        llm,
                        subject_key=candidate.subject_key,
                        project=project,
                        cap=hub_cap,
                        budget_words=budget_words,
                        now=now,
                    )
                    if written is None:
                        outcome.refused += 1
                    else:
                        outcome.written += 1
                        measurable = written
                    await session.commit()

                # **After the commit, in its own session** (T3.03 D9). The
                # article is durable before the judge is ever asked, so a
                # refusal or an outage costs the measurement and never the
                # article.
                if measurable is not None:
                    article_id, draft, facts = measurable
                    if await _measure(
                        session_factory, judge_for(llm), article_id=article_id,
                        draft=draft, facts=facts, project=project,
                    ):
                        outcome.unmeasured += 1
            except DraftRefused as refusal:
                outcome.refused += 1
                logger.warning(
                    "article_synthesis: %s/%s refused: %s",
                    project, candidate.subject_key, refusal,
                )
            except LiveArticleExists:
                # Unreachable through the selector, which already excludes
                # these. Counted rather than raised so a caller that skipped
                # the selector degrades instead of aborting the batch.
                outcome.refused += 1
            except Exception as error:  # noqa: BLE001 - one subject must not end the tick
                outcome.failed += 1
                logger.warning(
                    "article_synthesis: %s/%s failed: %s",
                    project, candidate.subject_key, error,
                )

    return outcome


# ─────────────── coverage write-back (T3.03 Steps 4-6) ───────────────


_CITATION_SQL = text(
    "INSERT INTO article_citations (id, article_id, fact_id, claim_span) "
    "VALUES (gen_random_uuid(), CAST(:a AS uuid), CAST(:f AS uuid), "
    "int4range(:lo, :hi))"
)


def draft_claims(draft: DraftArticle) -> list["Claim"]:
    """Adapt the draft **downward** into the entailment module's own type.

    The direction is invariant 15's, not a preference: ``dream_jobs`` imports
    this module, so ``claim_entailment`` may not import it back — a hot-path
    module reaching the entailment pass would otherwise acquire an unpoliced
    transitive route to the dream family.

    Spans are computed over the same join ``DraftArticle.body`` uses, so a
    citation's ``claim_span`` indexes the text that was actually stored.
    """
    from app.services.claim_entailment import Claim

    claims: list[Claim] = []
    cursor = 0
    for sentence in draft.claims:
        start = cursor
        cursor += len(sentence.text) + 1  # the join newline
        claims.append(
            Claim(
                text=sentence.text,
                fact_ids=tuple(sentence.fact_ids),
                span=(start, start + len(sentence.text)),
            )
        )
    return claims


async def apply_coverage(
    session: AsyncSession,
    judge,
    *,
    article_id: str,
    draft: DraftArticle,
    facts: list[GatheredFact],
    project: str,
) -> "CoverageOutcome":
    """Measure the article's coverage and route it. Does not commit.

    Returns the outcome so the caller can count it; **never raises** on a
    refusing judge, an outage or a below-threshold article (T3.03 D14).

    An unmeasured article gets **no write at all** — not a 0.0 confidence, not
    a re-opened review state, not a journal row. It is already `candidate` +
    `review_state='open'` from T3.02, which is the correct serving outcome for
    something nothing has measured.
    """
    from app.services.claim_entailment import measure_coverage

    result = await measure_coverage(
        session,
        judge,
        claims=draft_claims(draft),
        fact_text={fact.id: fact.fact for fact in facts},
    )
    return await write_coverage(
        session, result, article_id=article_id, project=project
    )


async def write_coverage(
    session: AsyncSession,
    result: "CoverageResult",
    *,
    article_id: str,
    project: str,
) -> "CoverageOutcome":
    """Apply an already-measured result to a stored article. Does not commit.

    Split out of ``apply_coverage`` by T3.05, which must know the outcome
    *before* it decides whether to supersede a standing article and therefore
    cannot measure through the article it might not write. Both paths write
    through here so there is one writer of the coverage columns, the citation
    rows and the `verified` journal — the alternative was a second measure call
    per re-synthesis, paid to the judge, for a number already computed.
    """
    from app.services.claim_entailment import CoverageOutcome

    if result.outcome is CoverageOutcome.UNMEASURED:
        return result.outcome

    promoted = result.outcome is CoverageOutcome.PROMOTED
    await session.execute(
        text(
            "UPDATE knowledge_articles SET confidence = CAST(:c AS real), "
            "status = CAST(:s AS text), review_state = CAST(:r AS text) "
            "WHERE id = CAST(:id AS uuid)"
        ),
        {
            "c": result.coverage,
            # `corroborated` is the machine's ceiling here exactly as it is on
            # the fact ladder: `confirmed` is human-only and this writer must
            # not be able to reach it.
            "s": "corroborated" if promoted else UNMEASURED_STATUS,
            "r": None if promoted else UNMEASURED_REVIEW_STATE,
            "id": article_id,
        },
    )

    # One row per **entailed** claim — doc 09 §4.3 assigns the write to this
    # pass, and only a grounded claim earns one.
    for claim, fact_id in result.entailed:
        lo, hi = claim.span or (0, 0)
        await session.execute(
            _CITATION_SQL, {"a": article_id, "f": fact_id, "lo": lo, "hi": hi}
        )

    # Every transition journals (doc 09, convention 8). A refusal journals
    # nothing, because no measurement happened.
    await record_event(
        session,
        event_type="verified",
        object_type=ARTICLE_OBJECT_TYPE,
        object_id=article_id,
        project=project,
        payload={
            "outcome": result.outcome.value,
            "coverage": result.coverage,
            "claims": len(result.verdicts),
            "entailed": len(result.entailed),
            "uncited": result.has_uncited,
            "reason": result.reason,
        },
    )
    return result.outcome


def judge_for(llm):
    """The gated door, or ``None`` when there is no orchestrator to ask.

    Constructed per tick rather than held: `VerificationJudge` carries the
    resolved LLM config, and a judge built once at boot would answer for a
    configuration an operator has since changed.
    """
    if llm is None:
        return None
    from app.services.verification_judge import VerificationJudge

    return VerificationJudge(llm)


async def _measure(
    session_factory, judge, *, article_id: str, draft: DraftArticle,
    facts: list[GatheredFact], project: str,
) -> bool:
    """Run the coverage pass in its own transaction. Returns "unmeasured".

    Swallows nothing it should not: `apply_coverage` already returns rather
    than raising for every expected outcome, so a raise here is a real defect
    and is logged as one — but it still must not take the tick down, because
    the article it describes is already committed.
    """
    from app.services.claim_entailment import CoverageOutcome

    if judge is None:
        return True
    try:
        async with session_factory() as session:
            outcome = await apply_coverage(
                session, judge, article_id=article_id, draft=draft,
                facts=facts, project=project,
            )
            await session.commit()
        return outcome is CoverageOutcome.UNMEASURED
    except Exception as error:  # noqa: BLE001 - the article is already durable
        logger.warning(
            "article_synthesis: coverage pass failed for %s: %s", article_id, error
        )
        return True


# ─────────────── the staleness gate and re-synthesis (T3.05) ───────────────
#
# **The gate is the verified set, and re-synthesis reuses the writer's own
# basis.** Staleness is `fact_set_hash` recomputed through
# `all_verified_fact_ids` — the same function that wrote the stored hash —
# rather than through a query of its own. Candidate churn therefore cannot
# trigger a re-synthesis: a candidate fact is not in the basis at all, so no
# arrival or departure of one can move the digest. That is the done-when's
# property, and it holds by construction rather than by filtering.
#
# **Why the debounce anchors on a journal row.** Doc 09 §4.4 asks for "a config
# quiet-period so a burst of corroborations produces one re-synthesis", which
# needs to know *when the verified set last moved* — and nothing in the schema
# records that. `knowledge_triples` has no `updated_at`, and a promotion (the
# burst §4.4 names) writes no timestamp on the fact row at all. So this writes
# the fact down where the doc already required it to be written — §4.4 makes
# "labelled stale" a journalled transition — and reads its own `article_stale`
# row back as the clock. A tick that sees a *different* hash from the last
# journalled one records the new one and waits: the window restarts while the
# set is still moving, which is what makes a burst produce one re-synthesis
# rather than one per tick. An anchor on the article's own `synthesized_at` was
# the cheaper alternative and was rejected on that point: it bounds how often a
# subject re-synthesises, but starts its window at the *previous* write, so the
# first tick inside a burst re-synthesises from a half-moved fact set.
#
# **Why re-synthesis measures before it stores, inverting T3.03's order.** T3.03
# measures coverage *after* the article commits so a judge outage cannot destroy
# a stored article. That order is unavailable here: `ux_knowledge_articles_live`
# admits one non-superseded article per `(project, subject_key)`, so a
# re-synthesis cannot be stored beside the standing article and then judged —
# storing it means superseding the standing one first, which is the outcome §4.4
# forbids ("a subject never loses a good article to a bad re-synthesis"). So the
# draft is judged first and stored only if it may stand, and what T3.03's
# ordering protects is preserved in the form available: a failure costs one
# model call and never an article.
#
# **An unmeasured draft is not a failed one.** With G-D open the judge refuses
# unconditionally, so every measurement returns `UNMEASURED`. Holding
# re-synthesis for that would freeze L3 at whatever it first wrote, on every
# install, permanently, for a gate that governs a *badge*. Only a measured
# failure holds the supersession.
#
# **This lives in the synthesis module rather than beside it**, which is not a
# filing preference: `dream_jobs`' one-hop derivation makes every module the
# umbrella imports a family body, and invariant 15's scan fails the build when
# one family body imports another. Two modules for one job would have needed the
# gather/draft/store primitives moved to a third, neutral one — a refactor of
# shipped code to satisfy a layout nobody asked for.

# Doc 09 §4.4's quiet period. A day by default because the job that consumes it
# is daily: a window shorter than the tick cannot damp anything, since the tick
# is already the sampling rate.
DEFAULT_DEBOUNCE_HOURS = 24

# How far back a debounce read looks for its own anchor. It bounds the
# by-object `events` scan across monthly partitions — a bare `object_id` filter
# reads every child — and it must exceed the debounce window or the anchor
# would age out before it could mature. An article that has been stale longer
# than this re-journals and waits one more window: a bounded, self-correcting
# delay rather than an unbounded scan.
_ANCHOR_LOOKBACK_DAYS = 90

_LIVE_ARTICLES_SQL = text(
    """
    SELECT id, subject_key, fact_set_hash, status
    FROM knowledge_articles
    WHERE project = CAST(:project AS text)
      AND status <> 'superseded'
    """
)

_LAST_ANCHOR_SQL = text(
    """
    SELECT created_at, payload
    FROM events
    WHERE object_type = CAST(:object_type AS text)
      AND object_id = CAST(:id AS uuid)
      AND event_type = CAST(:event_type AS text)
      AND created_at >= CAST(:since AS timestamptz)
    ORDER BY created_at DESC
    LIMIT 1
    """
)

_SUPERSEDE_SQL = text(
    "UPDATE knowledge_articles SET status = 'superseded' "
    "WHERE id = CAST(:id AS uuid)"
)

_POINT_SQL = text(
    "UPDATE knowledge_articles SET superseded_by = CAST(:new AS uuid) "
    "WHERE id = CAST(:id AS uuid)"
)


@dataclass(frozen=True)
class StaleArticle:
    """A live article whose supporting fact set has moved under it."""

    article_id: str
    subject_key: str
    stored_hash: str | None
    current_hash: str


async def stale_articles(
    session: AsyncSession, *, project: str
) -> list[StaleArticle]:
    """Every live article in the project whose fact set no longer matches.

    An article whose subject now has *no* verified facts is stale rather than
    absent: the knowledge it was built on is gone, which is the strongest form
    of what staleness names. It will not re-synthesise — the gather finds
    nothing and the standing article keeps standing — but it is labelled, which
    is the honest outcome and the same one the retrieval channel serves.

    One id query per live article, deliberately: it reuses the writer's own
    basis (:func:`all_verified_fact_ids`), so the comparison cannot drift from
    what produced the stored hash. The retrieval channel's grouped query is the
    right shape for labelling a page of results on a request; this runs once a
    day, per project, over the articles that exist.
    """
    rows = (
        await session.execute(_LIVE_ARTICLES_SQL, {"project": project})
    ).mappings().all()

    stale: list[StaleArticle] = []
    for row in rows:
        name, _entity_type = decode_subject_soft_key(row["subject_key"])
        current = fact_set_hash(
            await all_verified_fact_ids(session, subject=name, project=project)
        )
        if current != row["fact_set_hash"]:
            stale.append(
                StaleArticle(
                    article_id=str(row["id"]),
                    subject_key=row["subject_key"],
                    stored_hash=row["fact_set_hash"],
                    current_hash=current,
                )
            )
    return stale


async def staleness_settled(
    session: AsyncSession,
    article: StaleArticle,
    *,
    project: str,
    debounce_hours: float = DEFAULT_DEBOUNCE_HOURS,
    now: datetime | None = None,
) -> bool:
    """Journal the staleness, and say whether the fact set has settled.

    Returns True only when this exact fact set was already journalled at least
    ``debounce_hours`` ago — the quiet period. Every other path writes a fresh
    anchor and returns False, which is both the label §4.4 requires and the
    restart of the window.

    ``now`` is compared against a timestamp the **database** wrote:
    ``record_event`` takes no caller clock. In production both are the real
    clock and they agree; a caller passing a fabricated ``now`` is comparing
    two clocks and will get an answer about neither.
    """
    stamp = now or datetime.now(timezone.utc)
    anchor = (
        await session.execute(
            _LAST_ANCHOR_SQL,
            {
                "object_type": ARTICLE_OBJECT_TYPE,
                "id": article.article_id,
                "event_type": ARTICLE_STALE,
                "since": stamp - timedelta(days=_ANCHOR_LOOKBACK_DAYS),
            },
        )
    ).mappings().first()

    payload = anchor["payload"] if anchor is not None else None
    anchored_hash = payload.get("fact_set_hash") if isinstance(payload, dict) else None

    if anchor is not None and anchored_hash == article.current_hash:
        observed = anchor["created_at"]
        if observed.tzinfo is None:
            observed = observed.replace(tzinfo=timezone.utc)
        return (stamp - observed) >= timedelta(hours=debounce_hours)

    written = await record_event(
        session,
        event_type=ARTICLE_STALE,
        object_type=ARTICLE_OBJECT_TYPE,
        object_id=article.article_id,
        project=project,
        payload={
            "subject_key": article.subject_key,
            "fact_set_hash": article.current_hash,
            "previous_fact_set_hash": article.stored_hash,
        },
    )
    if not written:
        # `record_event` never raises, and this row is the clock. A lost write
        # is a stalled re-synthesis rather than a wrong one — the next tick
        # journals again — so it is logged rather than raised, but it is not
        # silent: nothing else would ever report it.
        logger.warning(
            "article_staleness: anchor not journalled for %s; re-synthesis of "
            "%s is deferred until one lands",
            article.article_id,
            article.subject_key,
        )
    return False


@dataclass
class ResynthesisOutcome:
    """What one re-synthesis pass did.

    ``held`` is its own count and not a failure: a draft measured below the
    coverage threshold is the gate working, and folding it into ``failed``
    would make a corpus of thin subjects read as an outage.
    """

    projects: int = 0
    stale: int = 0
    debounced: int = 0
    attempted: int = 0
    resynthesised: int = 0
    held: int = 0
    refused: int = 0
    failed: int = 0
    unmeasured: int = 0
    last_project: str | None = None


async def resynthesise_subject(
    session: AsyncSession,
    llm,
    judge,
    article: StaleArticle,
    *,
    project: str,
    cap: int = DEFAULT_HUB_CAP,
    budget_words: int = DEFAULT_LENGTH_BUDGET_WORDS,
    now: datetime | None = None,
) -> tuple[str | None, str | None]:
    """Draft, judge, and — only if it may stand — supersede. Does not commit.

    Returns ``(article_id, reason)``: an id when the standing article was
    superseded — with ``"unmeasured"`` as the reason when no coverage number
    was produced — otherwise ``None`` and the reason it was not (``no_facts``,
    ``held``).

    The supersession is three statements in one transaction because
    ``ux_knowledge_articles_live`` admits one live row per subject: the prior is
    retired first so the insert has room, then pointed at the new id.
    ``knowledge_articles`` carries no ``chk_superseded_has_pointer``, so a
    pointer left unwritten would not error — it would silently lose the
    lineage, which is why the two writes are never separated by a commit.
    """
    from app.services.claim_entailment import CoverageOutcome, measure_coverage

    name, _entity_type = decode_subject_soft_key(article.subject_key)
    facts = await gather_facts(
        session, subject=name, project=project, cap=cap, now=now
    )
    if not facts:
        return None, "no_facts"

    draft = await synthesise_draft(
        llm, subject=name, facts=facts, budget_words=budget_words
    )

    result = None
    if judge is not None:
        result = await measure_coverage(
            session,
            judge,
            claims=draft_claims(draft),
            fact_text={fact.id: fact.fact for fact in facts},
        )
        if result.outcome is CoverageOutcome.HELD:
            return None, "held"

    all_ids = await all_verified_fact_ids(session, subject=name, project=project)
    await session.execute(_SUPERSEDE_SQL, {"id": article.article_id})
    new_id = await store_article(
        session,
        subject=article.subject_key,
        project=project,
        draft=draft,
        facts=facts,
        all_verified_ids=all_ids,
        now=now,
    )
    await session.execute(_POINT_SQL, {"id": article.article_id, "new": new_id})

    await record_event(
        session,
        event_type="superseded",
        object_type=ARTICLE_OBJECT_TYPE,
        object_id=article.article_id,
        project=project,
        payload={
            "subject_key": article.subject_key,
            "superseded_by": new_id,
            "fact_set_hash": article.current_hash,
            "previous_fact_set_hash": article.stored_hash,
        },
    )

    measured = None
    if result is not None:
        measured = await write_coverage(
            session, result, article_id=new_id, project=project
        )

    try:
        await write_article_embedding(
            session, llm, article_id=new_id, text_body=draft.body
        )
    except Exception as error:  # noqa: BLE001 - retrievability is not storability
        logger.warning(
            "article_staleness: %s stored but not embedded: %s", new_id, error
        )
    unmeasured = measured is None or measured is CoverageOutcome.UNMEASURED
    return new_id, ("unmeasured" if unmeasured else None)


async def run_article_resynthesis(
    session_factory,
    llm_provider=None,
    *,
    projects: list[str],
    debounce_hours: float = DEFAULT_DEBOUNCE_HOURS,
    hub_cap: int = DEFAULT_HUB_CAP,
    budget_words: int = DEFAULT_LENGTH_BUDGET_WORDS,
    now: datetime | None = None,
) -> ResynthesisOutcome:
    """One re-synthesis pass over an already-chosen batch of projects.

    Takes the project list rather than rotating its own cursor: the tick's
    rotation is `run_article_synthesis`'s, and a second cursor would let the two
    passes drift onto different projects — a subject could then be re-eligible
    for a first article in one pass and stale in the other, on different ticks,
    for no reason an operator could see.

    **Per-subject sessions**, for the reason the synthesis runner states: a
    model call is seconds long, and one subject's failure must not roll back
    another's article. The debounce anchor commits with the subject that wrote
    it, so a crash mid-batch loses at most one tick of the window.
    """
    outcome = ResynthesisOutcome()
    llm = llm_provider() if callable(llm_provider) else llm_provider
    judge = judge_for(llm)

    for project in projects:
        outcome.projects += 1
        outcome.last_project = project
        async with session_factory() as session:
            stale = await stale_articles(session, project=project)
            outcome.stale += len(stale)

            ready: list[StaleArticle] = []
            for article in stale:
                if await staleness_settled(
                    session,
                    article,
                    project=project,
                    debounce_hours=debounce_hours,
                    now=now,
                ):
                    ready.append(article)
                else:
                    outcome.debounced += 1
            await session.commit()

        for article in ready:
            outcome.attempted += 1
            if llm is None:
                # No orchestrator is the job having nothing to run with, not a
                # draft failure — counted so the tick does not read as a clean
                # no-op.
                outcome.failed += 1
                continue
            try:
                async with session_factory() as session:
                    new_id, reason = await resynthesise_subject(
                        session,
                        llm,
                        judge,
                        article,
                        project=project,
                        cap=hub_cap,
                        budget_words=budget_words,
                        now=now,
                    )
                    if new_id is not None:
                        outcome.resynthesised += 1
                        if reason == "unmeasured":
                            outcome.unmeasured += 1
                    elif reason == "held":
                        outcome.held += 1
                    else:
                        outcome.refused += 1
                    await session.commit()
            except DraftRefused as refusal:
                outcome.refused += 1
                logger.warning(
                    "article_staleness: %s/%s refused: %s",
                    project, article.subject_key, refusal,
                )
            except Exception as error:  # noqa: BLE001 - one subject must not end the tick
                outcome.failed += 1
                logger.warning(
                    "article_staleness: %s/%s failed: %s",
                    project, article.subject_key, error,
                )

    return outcome
