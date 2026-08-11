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
import re
from collections import OrderedDict
from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.article_eligibility import VERIFIED_STATUSES
from app.services.events import record_event

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
    "gather_facts",
    "group_facts",
    "store_article",
    "synthesise_draft",
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
SYNTHESIS_PURPOSE = "synthesis"

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
    """
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
      AND t.expired_at IS NULL
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
    lead: str
    sentences: list[DraftSentence]

    @property
    def body(self) -> str:
        return "\n".join([self.lead, *(s.text for s in self.sentences)]).strip()

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
        "Respond with JSON: {\"lead\": \"<one definitional sentence>\", "
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

    lead = data.get("lead")
    if not isinstance(lead, str) or not lead.strip():
        raise DraftRefused("the synthesis response carried no lead sentence")

    raw_sentences = data.get("sentences")
    if not isinstance(raw_sentences, list) or not raw_sentences:
        raise DraftRefused("the synthesis response carried no sentences")

    sentences: list[DraftSentence] = []
    for entry in raw_sentences:
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

    return DraftArticle(lead=lead.strip(), sentences=sentences)


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
