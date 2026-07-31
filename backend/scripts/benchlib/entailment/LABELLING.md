# Entailment gold — labelling rules (claim/fact variant, doc 17 §6)

This file is the authority for what each verdict and each slice *means*.
Label pairs against these decision procedures, not from intuition about the
words "entailed" or "grounded" — two labellers drawing a boundary
differently is how a precision number stops meaning anything. Every pair's
`rationale` field cites the rule it was decided under; a pair you cannot
write such a rationale for is a pair that does not enter the file.

Files: `gold.json` (41 pairs seeded by T2.25, all live). Loader and
validation: `benchlib/entailment_gold.py`,
`benchlib/tests/test_entailment_gold.py`. The claim/span variant (doc 16
§4, horizon) will be a sibling file under its own labelling rules — never
mixed into this one.

**Division of labour.** T2.25 (the harvest half) built this substrate and
seeded it with author-labelled pairs proving every slice and every verdict
is represented, including the hard near-misses. **T2.54 (the labelling
half) owns**: growing the set toward doc 17 §6's recommended ≥ 200 pairs
per variant, independently re-adjudicating every author-labelled pair
(flipping `label_source` to `adjudicated`), and the inter-label consistency
resample. §"Handoff to T2.54" below.

## What a pair is

- `premise` — a Layer-2-style **fact text**: one or two sentences stating a
  verified fact, in the shape `knowledge_triples.fact` will carry (temporal
  facts render their validity window into the text, because the judge sees
  only text).
- `hypothesis` — an article-style **claim sentence**, the kind a Phase-3
  synthesis draft would emit and doc 09 §4.3's entailment pass would check
  against the fact.
- `verdict` — exactly one of `entailed` / `contradicted` / `unsupported`
  (below).

## The three verdicts, and the binary G-D scores on

- **`entailed`** — a competent reader who accepts the premise as true must
  accept the hypothesis as true. Semantic entailment, not lexical overlap
  and not plausibility.
- **`contradicted`** — accepting the premise requires rejecting the
  hypothesis: the premise asserts (directly, or via a rule below) the
  negation of something the hypothesis asserts.
- **`unsupported`** — neither of the above. The premise is compatible with
  the hypothesis but does not establish it.

**Grounded ⇔ `entailed`.** That is the whole binary
(`entailment_gold.GROUNDED_VERDICTS`); `contradicted` and `unsupported`
are both ungrounded. The three-way split is kept because the veto consumer
(doc 08 §4.2) is qualified on precision of the *contradiction* verdict from
this same file — collapsing it to a binary would throw that away.

## General decision procedure

1. **Score the whole hypothesis.** A claim is grounded only if *all* of it
   is entailed. A conjunction with one supported and one unsupported
   conjunct is `unsupported` (eg-0028) — partial credit is a scorer policy
   decision that belongs to T2.26, not a labelling one.
2. **Use only the premise.** The corpus world, the labeller's domain
   knowledge, and what is "obviously true" of homelabs are all
   inadmissible. Several pairs are deliberately built so the hypothesis is
   *true in the corpus world* but unsupported by this premise (eg-0030,
   eg-0038, eg-0039): a judge that scores plausibility instead of
   entailment fails them, by design.
3. **Entailment tolerates rewording, never strengthening.** Synonyms,
   voice, clause order, dropping content (weakening) preserve entailment.
   Adding content, tightening a quantifier, upgrading "a factor" to "the
   cause" break it.
4. **Contradiction requires exclusion, not absence.** If the premise merely
   fails to mention what the hypothesis asserts, that is `unsupported`. It
   is `contradicted` only when the premise (with the named rules below)
   excludes it.

## Edge rulings — cite these by name in rationales

- **Exclusive-slot rule.** A fact stating a single-valued configuration
  slot — a port, a version of one instance, a scrape interval, the bucket
  holding a state file, a token lifetime — states *the* operative value.
  A hypothesis giving a different value for the same slot is
  **contradicted**, not unsupported, even though the surface text does not
  contain a negation (eg-0033..0037). This mirrors the production veto's
  purpose: a claim citing the wrong port against the fact must be
  refutable *by* the fact. When a slot is genuinely multi-valued
  (a host running several services, a person holding several roles), the
  rule does not apply and a differing value is `unsupported`.
- **Window rule.** A temporal fact renders its validity window in text. A
  claim time-scoped inside the window is `entailed` (eg-0016); a
  present-tense claim over a window the fact *explicitly closes* — named
  end event or successor — is `contradicted` (eg-0018).
- **Open-window rule.** A fact valid "since X" with no closing event
  entails the same state at any later reference date (eg-0017). This is
  the convention the production veto needs: `knowledge_triples` rows with
  `invalid_at` NULL are current.
- **Evaluation-time rule.** A hypothesis anchored to "currently"/"now" is
  decidable only if the premise fixes the state at an open or explicitly
  closed window. If its truth depends on an evaluation date the premise
  does not contain (a 90-day certificate and an unanchored "currently"),
  the verdict is `unsupported` (eg-0021).
- **Implicature-is-not-contradiction rule.** "Was frozen during Q1"
  *implicates* the freeze ended but does not assert it. Conversational
  implicature never upgrades `unsupported` to `contradicted` (eg-0020).
  Only asserted content and the rules above count as exclusion.
- **Reversal rule.** A hypothesis reversing an asymmetric relation is
  `contradicted` when one event or slot cannot carry both directions —
  replacement, a migration's from/to (eg-0022, eg-0024) — or when the
  premise negates the reverse explicitly (eg-0026). It is `unsupported`
  when the reverse is merely unasserted and not excluded: dependency,
  load-balancing roles (eg-0023, eg-0025).

## The eight slices

One slice tag per pair (v1 discipline, inherited from the retrieval gold).
A pair that seems to belong to two slices is a badly constructed pair —
sharpen it until it belongs to one. Each slice constrains its lawful
verdicts; the loader enforces the table (`SLICE_VERDICTS`).

| Slice | Verdicts | Construction |
|---|---|---|
| `verbatim` | entailed | Near-literal restatement: reorder, voice, at most trivial synonym swaps. All content preserved. The control slice — if a judge fails it, the harness or the judge plumbing is broken. Premise ≠ hypothesis as strings (the loader rejects identity; string equality qualifies string comparison, not a judge). |
| `paraphrase` | entailed | Full rewording of the same assertion(s); nothing strengthened or weakened. Tests semantic equivalence under zero lexical anchor. |
| `weakening` | entailed | The hypothesis is *strictly weaker*: content dropped, values abstracted (15.6 → 15), specifics generalised. The **recall side's** hard case: an over-strict judge refuses these and fails recall. Where possible, author the mirror overreach pair from the same material (eg-0011/eg-0027, eg-0013/eg-0029) so the set teaches the asymmetry of entailment. |
| `temporal` | any | Validity-window semantics: window-scoped claims, closed windows, open windows, unanchored "currently". The only mixed-verdict slice, because the same construction yields all three outcomes depending on window state. |
| `direction` | contradicted, unsupported | Right entities, relation reversed. Split by the reversal rule: exclusive reversals contradict, non-exclusive ones are unsupported. |
| `overreach` | contradicted, unsupported | The hypothesis is *strictly stronger* than the fact: added values, tightened quantifiers, "a factor" → "the cause". The **precision side's** hard case: an overlap-driven judge accepts these and lets a hallucinated specific ship under a corroborated badge — the exact failure G-D exists to catch. Almost always `unsupported`; `contradicted` only if the strengthening crosses an exclusion. |
| `value-swap` | contradicted | Identical sentence shape, one (or two crossed) slot values swapped, verdict fixed by the exclusive-slot rule. Prefer swap values that are *corpus-plausible* — another entry's real value (eg-0034, eg-0036) — so plausibility actively misleads. |
| `unrelated` | unsupported | The premise bears on nothing in the hypothesis (or shares only an entity, eg-0041). The easy-negative floor, plus the world-knowledge trap when the hypothesis is corpus-true (eg-0038, eg-0039). |

`NEAR_MISS_SLICES` = weakening, temporal, direction, overreach, value-swap.
These are the pairs that decide whether the qualification number means
anything; the tests refuse a file in which any of them is empty.

## Provenance — honesty over volume

Every pair declares where its material actually came from, in a closed
vocabulary with top-level declared counts, because G-D's precision and
recall inherit any overstatement and nobody downstream can see it.

- `hand-authored-synthetic-fact` — both premise and hypothesis authored
  for this set, against a fact constructed to be realistic for the corpus
  domain. **No such premise is a real L2 fact**; nothing here was produced
  by the system under test.
- `hand-authored-bench-corpus` — the premise is a
  `benchlib/retrieval/corpus.json` entry's content **verbatim**
  (`corpus_key` names it; the cross-file validator enforces the equality,
  so corpus drift under a pair fails the suite and forces re-adjudication
  under retire-and-replace). The hypothesis is hand-authored.
- `synthesis-draft` — **reserved, zero pairs today.** For sentences
  harvested from real `article_synthesis` drafts, which do not exist:
  the job is a `PlaceholderJobRunner` until T3.02, which is *behind* the
  gate this gold feeds. The task text's "run it manually" path was
  verified unavailable on 2026-07-31 (see the E2 amendment log).
- `l2-fact` — **reserved, zero pairs today.** For premises taken from live
  `knowledge_triples` rows; the table has no producer until `fact_lift`
  (T2.10).

The two reserved counts are pinned to zero by test. When a producer lands,
harvesting from it is a deliberate, visible edit to that pin — never a
silent relabel of existing pairs.

## File discipline (doc 17 §11, inherited from the retrieval gold)

- **Append-only.** New pairs take the next `eg-` id at the end of the
  file. A wrong pair is retired in place (`"retired": true` + reason in
  `notes`) — never deleted, rewritten, or reordered.
- **Declared counts** (slice, verdict, provenance) cover live pairs only
  and are updated with every append or retirement; the loader and the
  pinned test counts move together, visibly.
- **Labelling is judge-blind.** No pair may be added, retired, or
  relabelled on the basis of what any judge model answers. The gold is
  built from the semantics above; if a qualification run disagrees with a
  pair, the pair is re-examined *against these rules* — and if the rules
  were wrong, this file changes first, visibly, with the rationale.

## Handoff to T2.54

What remains, in T2.54's scope, none of it started here:

1. **Volume.** Grow toward doc 17 §6's recommended ≥ 200 pairs for the
   claim/fact variant, keeping every slice populated and near-misses the
   majority of growth.
2. **Independent re-adjudication.** Every `label_source: "author"` pair
   was labelled once, by its author, at construction time. Re-adjudicate
   each against this file without looking at the recorded verdict first;
   agreement flips the pair to `adjudicated`, disagreement retires it in
   place with the reason and (if the material is sound) appends a
   corrected replacement.
3. **Inter-label consistency resample.** After re-adjudication, relabel a
   random ≥ 15% sample blind a second time and record the agreement rate
   in this file's history section. Systematic disagreement means a rule
   above is ambiguous — fix the rule, then re-adjudicate the affected
   slice, in that order.
4. **First real harvests.** When T3.02 drafts or T2.10 facts exist, pairs
   from them enter under the reserved provenances with the pinned zero
   counts updated — the seed pairs are not retroactively relabelled.
