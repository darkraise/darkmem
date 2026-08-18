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
   cause" break it. Whether *exhaustivity* counts as strengthening depends
   on how the hypothesis carries it — see the **exhaustivity rule** below.
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
  **Three further slots are single-valued, ratified by the owner
  2026-08-06** and stated here as rules rather than only as rulings on
  particular pairs, because a rule that lives only in its own precedent is
  not one a later labeller can apply:
  - **the host or platform a single named instance runs on** — a differing
    host for the same named instance is `contradicted`;
  - **the kind a named instance is** (`IS_A`) — a differing kind for the
    same named instance is `contradicted`;
  - **the object of a named replacement or migration** (`REPLACES`) — the
    one thing a named replacement retired. A hypothesis naming a *different*
    replaced object, with the sentence shape otherwise preserved, is
    `contradicted`, not unsupported. This is an object swap, not a reversal,
    so the reversal rule below does not reach it.
- **Additional-value rule** (ruled by the owner 2026-08-10, rule-then-pairs
  on eg-0405). The exclusive-slot rule above is written for a *differing*
  value. It says nothing about an **added** one — a hypothesis that keeps
  the premise's value and asserts a second alongside it ("listens on port
  9100" -> "listens on ports 9100 and 9101"). Two blind passes split on
  exactly that, one reading it as crossing the exclusion and one as the
  `overreach` slice's own definition.

  **The slot's cardinality decides, and it is a property of the slot rather
  than of the sentence.** Where the slot is single-valued *in the world the
  premise describes*, a second value is `contradicted`: one process
  listening on one named port cannot also be listening on another and still
  make the premise true as stated. Where the slot is genuinely multi-valued,
  the second value is unasserted content and the pair is `unsupported` — a
  CI matrix testing Python 3.12 may well also test 3.11 (eg-0377), a host
  runs several services, a person holds several roles.

  Ask *"could both values hold at once without making the premise false?"*
  If yes, `unsupported`. If no, `contradicted`. This is the same question
  the exclusive-slot rule already asks about a differing value; the ruling
  is that adding does not escape it, not that adding is a new kind of thing.

- **Exhaustivity rule** (ruled by the owner 2026-08-08, rule-then-pairs on
  eg-0308). Procedure 3 breaks entailment on strengthening, and exhaustivity
  is strengthening only when the hypothesis **asserts** it.
  - Exhaustivity carried by **information structure** — a cleft or
    pseudo-cleft ("X is what causes Y", "X is why Y"), focus, or a definite
    predicate nominal ("X is the replacement for Y") — is presupposed and
    defeasible, not asserted. It does **not** break entailment
    (eg-0006, eg-0196, eg-0308).
  - Exhaustivity carried **lexically** — "only", "sole", "alone", "every",
    "all" — is asserted content and does (eg-0057, eg-0081, eg-0276).
  - Independently of how it is carried, exhaustivity that clashes with a
    premise **explicitly marking** non-exhaustivity ("one contributing
    factor", "some hosts") strengthens (eg-0031, eg-0032). This is the case
    procedure 3's own "a factor" → "the cause" example is calibrated on.

  A bare relation rendering (`X causes Y`) marks exhaustivity neither way,
  so it neither licenses nor blocks on its own. This is the entailment-side
  counterpart of the implicature-is-not-contradiction rule below:
  non-asserted content does not move a verdict in **either** direction.
- **Window rule.** A temporal fact renders its validity window in text. A
  claim time-scoped inside the window is `entailed` (eg-0016); a
  present-tense claim over a window the fact *explicitly closes* — named
  end event or successor — is `contradicted` (eg-0018).
- **Inception-window rule** (ruled by the owner 2026-08-10, rule-then-pairs
  on eg-0416). The window rule fixes a window's *closing* boundary and the
  open-window rule below covers claims dated at or after an open window's
  start. Neither reaches a claim dated **before** that start — "Since the
  January 2026 rollout, host metrics have been scraped by VictoriaMetrics"
  against "VictoriaMetrics was scraping host metrics in November 2025".
  Both blind passes flagged the gap independently and split on it, which is
  what a gap looks like from outside.

  **Whether "since <inception>" excludes the earlier state depends on
  whether the premise names what came before.**
  - "Since X, <state>", with **no predecessor named** — the premise fixes
    the state forward from X and asserts nothing about what held earlier.
    A claim about a date before X is `unsupported`, by general procedure 4:
    absence is not exclusion.
  - "Since X, <state>", where the premise **also names the state X
    displaced** — the premise does assert what held before, so a claim
    putting the *new* state before X is `contradicted`, on the same footing
    as the window rule's named-successor case.

  The asymmetry is deliberate and is the one procedure 4 draws everywhere
  else: a premise earns a `contradicted` only by asserting the thing the
  hypothesis denies. An inception date alone asserts a beginning, not a
  prior absence.

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
- `l2-fact` — premises taken verbatim from `knowledge_triples.fact` texts
  minted by the shipping `fact_lift` in the recorded harvest run. See the
  T2.54 composition-freeze section below for the full definition and the
  `fact_key` anchor contract; the loader enforces both.

`synthesis-draft`'s count is pinned to zero by test until T3.02 exists.
When a producer lands, harvesting from it is a deliberate, visible edit to
that pin — never a silent relabel of existing pairs.

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
- **Lattice retirement — retiring a *correct* pair for census shape**
  (ratified 2026-08-10, T2.115). Everything above retires a pair only
  when its label is **wrong**. A census whose size puts a ratified bar
  off its own lattice is a second, narrower reason, and it must never
  become a licence to remove inconvenient evidence. All of the following
  hold, each recorded in the task report:

  1. **Contacted only** — the pair is in the contacted population, so a
     round removes contaminated evidence and never fresh evidence.
  2. **Never the protected core** — none of the 41 T2.25 pairs Rule B
     keeps live.
  3. **A committed, zero-degrees-of-freedom draw** — the selection
     procedure lands in a commit *before* it executes and has no free
     parameters: seed from `resample_draw.derive_seed` over the
     pre-retirement file, eligible pool sorted by `id`, strata in a fixed
     stated order, `rng.sample(pool, quota)`. Drawn ids and a
     one-command reproduction go in the report. *Pinning a seed is not
     enough: the same seed under a different algorithm yields a different
     set, and choosing among defensible algorithms after seeing the seed
     is the aiming channel this clause closes.*
  4. **Content-blind beyond the stated stratification** — slice enters
     only as clause 5's largest-remainder stratification; no rationale,
     label, premise, hypothesis or judge result may enter the selection.
  5. **Composition preserved, not only size** — the pooled census of the
     affected verdict class **and its largest-remainder slice
     distribution** are unchanged after replacement. Retiring 15
     `value-swap` and authoring 15 `temporal` would reshape the census's
     difficulty at constant size.

     **5a. Off-target authoring is handled by the skip mechanism, not by a
     composition deviation** (amended 2026-08-10, ruling R-A; see the C-1
     record in History). A blind author writing to a slot whose slice and
     verdict targets were fixed *before* authoring may return a pair that
     misses either. That is an ordinary miss and the frozen protocol
     already answers it: **log a skip and re-author for the same slot**,
     which is what keeps slice targets exact. Re-briefing a badly-slotted
     construction rejects no content fact and consults no judge — the
     fitting hazard is discarding a product for its *adjudicated outcome*
     against a target that was **not** fixed beforehand, which this
     clause requires and which the skip mechanism does not touch.

     **5b. When a deviation is genuinely unavoidable, the absorbing slice
     is chosen by committed code, never after the fact.** If a round
     establishes that no re-authoring can satisfy the quota, the shortfall
     is absorbed by a rule that lands in a commit **before** authoring
     begins, exactly as clause 3 requires of the draw — prose is not
     enough here, because "largest remainder" alone leaves the reference
     distribution and the population unstated and a contaminated
     controller would pick the reading. The deviation, its arithmetic and
     the selecting rule are recorded in History **in the same commit as
     the pairs**.

     **5c. This clause was violated by the round that ratified it, and
     5a/5b do not absolve that round.** T2.115 executed under clause 5 as
     ratified above; the record of the violation stands unamended in
     History and in the gate ledger. Amending a rule so a completed run
     becomes compliant is the same move as moving a bar so a run passes.
     5a and 5b bind the **next** round.
  6. **Budget lineage recorded** — a reshape changes the gold sha and so
     mints a fresh `gold_touching_attempts`. Cumulative attempts across
     gold generations are recorded in the ledger and in every report, so
     a reset is visible rather than silent (ruling R4).

  **Independence is at the proposition, not at the bytes** (ratified
  2026-08-10, ruling R-B; the C-2 record in History is the finding it comes
  from). A new pair may not assert the same proposition as a live pair — the
  same premise with a logically equivalent hypothesis — however differently
  worded. The loader's byte-uniqueness check is necessary and **not
  sufficient**, and an instruction aimed at an observed collision reaches only
  the collisions that occur: round 3's two byte-identical duplicates were
  caught and skipped, and `eg-0367`, which never collided, walked past the same
  instruction into the gated census.

  A prose clause that caught nothing is exactly what produced this finding, so
  this one ships with `scripts/benchlib/duplicate_propositions.py` — a
  deterministic, content-blind check over pairs sharing a premise, pinned in
  `test_entailment_gold.py` against the **accepted** duplicate set. A new
  duplicate fails the build; the four recorded ids do not block. The check
  names ids and decides nothing about them.

  **The accepted set, measured rather than hand-found.** The check reports
  **nine** duplicate relations in the live gold, not the two the branch review
  found by eye — which is the argument for having a check at all. Of the nine,
  **two are `contradicted`** and therefore inside the census the G-D recall bar
  is computed over, and **both straddle the two populations**: `eg-0093`
  (contacted) / `eg-0367` (Rule B), and `eg-0194` (contacted) / `eg-0251`
  (Rule B). So the pooled contradicted census is 80 rows carrying **78**
  independent propositions, and Rule B's 40 contains **two** propositions the
  contacted population already held.

  The other seven are `entailed`, most of them one article or one cleft apart
  ("audit-log has at least one consumer." / "The audit-log has at least one
  consumer."), and they sit in paraphrase-shaped slices where rewording is the
  point. They do not touch the contradiction bars. They are still correlated
  items, so they inflate the *entailed* bars' apparent sample size, and the
  ladder's own precision/recall readings on `entailed` should be read with that
  in mind rather than treated as 200-odd independent trials.

  **The bias is not one-directional, and the first version of this paragraph
  said it was.** A judge that *misses* a duplicated proposition burns two of
  its four permitted misses — harder. A judge that *catches* it banks two
  correlated hits and may then miss four of the remaining independent items,
  which is a wider per-item tolerance than the bar names — strictly
  **easier**. Nothing about "the duplicates only make it stricter" is true,
  and reading it that way is the reassuring error.

  The worked arithmetic, and the measured example that made the asymmetry
  concrete, are recorded below the strip truncation point (History,
  "Duplicated propositions: the worked asymmetry") — **relocated there
  2026-08-13 by owner amendment**. They cite a judge result, and this
  paragraph sits ~390 lines above the truncation point that every pair author
  and both blind labellers read to. The rule that labelling is judge-blind is
  not satisfied by a file that hands them a score on page one; the byte-prefix
  rule bars condensing it away, so the material moves rather than shrinks.

  **Therefore: no further judge attempt may run on gold `98fc4b49` until the
  duplicates are retired and the gold re-certified.** Retiring them is
  *content-forced* by a deterministic finding, not a census-shape selection, so
  clause 1's contacted-only restriction does not govern it and a contaminated
  party is not the obstacle. Spending the final sanctioned attempt against a
  census carrying a known bar-easing correlated duplicate, and repairing
  afterwards, is the one ordering that could manufacture an edge pass out of a
  defect already in the record.

  **Inadmissible-duplicate retirement — a third ground, ratified 2026-08-10
  (ruling R-B).** The two retirement grounds above cover a pair whose *label* is
  wrong and a census whose *size* puts a bar off its lattice. A duplicate is
  neither: `eg-0367`'s label is correct and the census size is right — what was
  wrong is its **admission**, because the proposition was already in the set.
  Retiring it therefore needs its own ground, and the ground is deliberately
  narrow:

  1. **Only a pair the committed check reports**, at or above its threshold,
     sharing a premise and a verdict. No pair is retired on a reader's
     impression of similarity.
  2. **The member that retires is the later-minted one**, by id order. This is
     mechanical and content-blind: id order is authoring order, so the rule
     retires the pair that *entered* an occupied slot and keeps the one that was
     already there. Nobody chooses on difficulty, and no judge result may enter.
  3. **Replacement is mandatory and the census is preserved** — clause 5's
     absolute half binds here too. Retiring two `contradicted` pairs without
     replacing them would take the pooled census to 78 and put 0.95 off its
     lattice, which is the exact defect T2.115 existed to remove. So the
     replacements are authored **blind**, under the ordinary firewall, into the
     same slice and verdict.
  4. **Re-certification follows**, because the sha moves: a fresh `n = 93`
     resample, and the budget lineage recorded under clause 6.

  **What this costs, stated so nobody discovers it mid-round.** It is not a
  quick fix — a duplicate repair is a full retire-and-replace round with blind
  authoring, blind adjudication and a re-certification sitting. That cost is why
  the check exists: catching a duplicate at authoring time costs a re-brief,
  catching it after certification costs a round.

  **Quarantine before authoring, and what is on the list.** Two directories
  hold per-pair judge output and neither may be readable by an author or an
  adjudicator: `entailment/cache/` (raw responses) and `entailment/verdicts/`
  (the pair-id join, added 2026-08-10 after T2.115 found the disclosure its
  own review required was uncomputable without it). Both are gitignored, both
  are moved outside the repository before any authoring dispatch, and neither
  may have a pair id quoted from it in a report or the gate ledger. They exist
  so a **controller** can attribute a re-measure's delta to census content
  rather than judge behaviour; an author who read either would write the next
  round's pairs at the known misses, which is the one thing the firewall is
  for.

  **Reconciliation with the judge-blind clause above.** That clause bars
  retiring a pair "on the basis of what any judge model answers", and a
  lattice round is *triggered* by a gate failure. The two are compatible
  and this file says so explicitly rather than leaving a reader to
  reconcile them: the **trigger** is lattice arithmetic, recorded on
  2026-08-08 before it bit; the **selection** is seeded and content-blind
  by clauses 3–4. What is barred is choosing *which* pairs to retire from
  judge output, and clauses 3–4 make that unavailable.

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

---

# T2.54 composition freeze — 2026-08-03

Everything below was frozen **before any T2.54 pair was authored**; the git
history of this file against the pair-appending commits is the proof. The
seed, the targets and the relation classification are functions of
pre-judge data only (Rule A of the T2.54 plan): nothing here was chosen by,
about, or in sight of any judge model's behaviour.

## `l2-fact` — the definition (doc 17 §11, ruled 2026-07-31)

An `l2-fact` premise is **verbatim-equal to a `knowledge_triples.fact` text
minted by the shipping `fact_lift` in the recorded harvest run** — the run
whose manifest is committed at `entailment/l2_harvest.json`, naming the
bench database, corpus sha256, gate config, embedder fingerprint and git
sha. "Real" governs the premise **distribution**, not authorship or the
database of origin: a premise is real because the production code path
(extraction → clean → dedup → `fact_lift` → `fact_sentence`) produced it.
A hand-authored premise **never** qualifies, however faithfully it imitates
the shape — that is the clause's own does-not-license sentence, enforced by
the anchor below.

## The anchor contract (`fact_key`)

Every live `l2-fact` pair carries a `fact_key` object —
`{triple_key, subject_name, rel_type, object_name, project}` — and the
loader (`entailment_gold.py`) enforces three checks on every load:

1. **Manifest resolution, manifest as source of truth**: `triple_key`
   resolves to exactly one manifest row and the pair's other four fields
   byte-equal that row's. The pair never self-supplies the authoritative
   values.
2. **Verbatim premise binding, in bytes**: `premise == row["fact"]`.
   Never a recomputation from the pair's own fields — `compute_triple_key`
   canonicalises names while `fact_sentence` lowercases only the
   predicate, so cased fields could smuggle in a premise `fact_lift`
   never produced.
3. **Manifest self-consistency, once per load**: every manifest row
   re-derives its `triple_key` and `fact` through the *imported*
   `compute_triple_key` and `fact_sentence`. This is also the **sunset
   tripwire** for the temporal exemption below: the day `fact_sentence`
   renders validity windows, this check fails the floor loudly and the
   exemption is re-argued.

The byte-binding is deliberately brittle: drift fails loudly and forces
re-adjudication under retire-and-replace, exactly like corpus drift. A
forged manifest row is caught by reproducibility — the harvest re-run and
byte-diff of the sorted `facts` section (`tests/test_harvest_l2_facts.py`
on every floor run; T2.41's `--gate` evidence re-runs it against the
committed file).

## Frozen composition for the T2.54 authoring round (200 new pairs)

T2.25's slice proportions (fixed 2026-07-30) scaled to 200 by
largest-remainder rounding, ties broken alphabetically:

| slice | T2.25 | exact ×200/41 | target |
|---|---|---|---|
| verbatim | 4 | 19.51 | 20 |
| paraphrase | 6 | 29.27 | 29 |
| weakening | 5 | 24.39 | 24 |
| temporal | 6 | 29.27 | 29 |
| direction | 5 | 24.39 | 25 |
| overreach | 6 | 29.27 | 29 |
| value-swap | 5 | 24.39 | 24 |
| unrelated | 4 | 19.51 | 20 |
| **sum** | 41 | | **200** |

(197 floors + 3 remainders: verbatim .51, unrelated .51, then the .39
three-way tie → alphabetically `direction`.) Near-misses are 131/200 =
65.5%, matching T2.25's 65.9% by construction, not by choice.

**Premise assignment is mechanical.** The 171 non-`temporal` slots take
manifest premises via the seeded assignment in
`benchlib/entailment_assignment.py`: RNG seed **20260731** (committed in
the manifest header before any pair existed), a seeded shuffle of the slot
list and of the fact order, facts cycling so no premise exceeds the
**≤ 4 live pairs per premise** cap. Anyone can re-derive the assignment
with `python scripts/benchlib/entailment_assignment.py`. Authoring runs in
four batches over contiguous slot ranges (0–49, 50–99, 100–149, 150–170
plus the 29 temporal slots).

**Skips are visible, never silent.** An author may skip an infeasible
(premise, slice) assignment **only** with a recorded reason in the skip
log (History section below); the slot is then authored with a
hand-authored premise for the same slice, so slice targets stay exact and
only the `l2-fact` count moves. Known-infeasible shapes, named now: a
`direction` slot on a symmetric relation (see the table below), and a
`value-swap` slot on a fact whose swapped slot is not single-valued (the
exclusive-slot rule cannot fix `contradicted`, and `value-swap` admits no
other verdict).

**A third shape, found in round 3 (T2.115) rather than predicted: a
`direction` slot on a fact that already carries a live `direction` pair.**
For that slice the hypothesis *is* the reversal of the premise, so the
construction is determined and a second slot on the same fact reproduces
the existing pair byte-for-byte — which the loader rejects as a duplicate
live `(premise, hypothesis)`. The author cannot see it coming: the
colliding pair is outside the allowlist a blind authoring round runs
under. So it is a skip like the other two, logged with its reason and
hand-authored for the same slice. **Do not resolve it by rewording the
reversal** — that passes the uniqueness check while leaving a
near-duplicate in a measurement set, which is worse than the collision it
hides. A future round's assignment should exclude facts already carrying a
live pair of any slice whose hypothesis the premise determines. The authoring target is **≥ 130 `l2-fact` pairs** — 41
skips of margin — and the gate floor is ≥ 50% of live pairs (doc 17 §11,
ratified 2026-07-31).

**`temporal` is hand-authored, exempt, and disclosed.** `fact_lift`
renders no validity window into fact text (measured: `fact_lift.py`'s
one-reachable-branch finding), so no real premise can exercise the window
rules today. The 29 temporal pairs use hand-authored windowed premises;
the exemption sunsets the day a producer renders windows — the anchor
contract's check 3 is the tripwire. T2.41's gate report must carry this
caveat: the temporal slice is not representative of today's production
premise distribution.

## Reversal-exclusivity, pre-classified for every relation

Decided per relation from its **semantics alone** — before any pair
existed — so a `direction` pair's verdict falls out mechanically from
which relation the seeded assignment handed its author, never from a
per-pair judgment call. **Exclusive** means one pair of endpoints cannot
carry both directions at once, so the reversed claim is `contradicted`
(reversal rule, exclusive case); **non-exclusive** means the reverse is
possible alongside the fact, so the reversed claim is `unsupported` —
unless the premise itself negates the reverse explicitly (eg-0026), which
always contradicts. **Symmetric** relations are ineligible for `direction`
pairs: the reversal is entailed, and the slice admits no such verdict.

| relation | class | reversed-claim verdict | why |
|---|---|---|---|
| `USES` | non-exclusive | unsupported | mutual use is coherent (two services calling each other) |
| `DEPENDS_ON` | non-exclusive | unsupported | circular dependency is not excluded by meaning (eg-0025) |
| `HAS_PART` | exclusive | contradicted | proper parthood is antisymmetric: a part cannot contain its whole |
| `IMPLEMENTS` | exclusive | contradicted | spec and implementation are incompatible roles for one ordered pair |
| `EXTENDS` | exclusive | contradicted | extension is a strict order; mutual extension is incoherent |
| `REPLACES` | exclusive | contradicted | one replacement event cannot run both ways (eg-0022) |
| `IMPROVES_ON` | exclusive | contradicted | an improvement ordering over one comparison cannot be mutual |
| `IS_A` | exclusive | contradicted | instance/kind (and proper subkind) is antisymmetric for distinct terms |
| `DEPLOYED_ON` | exclusive | contradicted | host and guest cannot swap for the same pair: a platform is not deployed on its own workload |
| `CAUSES` | non-exclusive | unsupported | feedback between phenomena is coherent (stress causes insomnia causes stress) |
| `AUTHORED_BY` | exclusive | contradicted | a work's author cannot be authored by that work; holds under the legacy folds (WORKS_AT, PUBLISHED_IN) too |
| `HAPPENED_ON` | exclusive | contradicted | the occurrent and its date/place cannot swap roles; holds under the legacy folds (VISITED, LIVES_IN) |
| `MENTIONS` | non-exclusive | unsupported | two documents can mention each other |
| `CITES` | non-exclusive | unsupported | mutual citation is coherent (companion papers) |
| `INSPIRED_BY` | non-exclusive | unsupported | mutual inspiration between ongoing works/projects is not excluded |
| `RELATED_TO` | symmetric | — (direction-ineligible) | the reversal is entailed by symmetry; a direction slot landing here is a mandatory logged skip |

This table covers `RELATIONSHIP_TYPES` in `app/taxonomy.py` exhaustively
(16 relations, checked against the source on 2026-08-03).

## Step-5 rulebook fork — RATIFIED by the owner (2026-08-06)

> **All three proposals below were ratified in the T2.54 Step-6 sitting on
> 2026-08-06, and item 4's clarification was accepted.** They are no longer
> proposals; this file now *is* the rulebook they describe, and a future
> condensation that drops any of them is a fork to be fixed rather than a
> reading to be honoured.
>
> Consequences, applied:
>
> - **Rule 1 ratified** — the six `value-swap` host-swap pairs (eg-0048,
>   eg-0088, eg-0098, eg-0109, eg-0154, eg-0201) keep their recorded
>   `contradicted` verdicts. No retire-and-replace. **Their blind agreement
>   remains procedurally weak evidence** — it was manufactured by the shared
>   fork rather than independently reached — so they are exactly the pairs the
>   resample's full `contradicted` census exists to test.
> - **Rule 2 ratified** — zero live pairs change; the category is now lawful
>   for future authoring.
> - **Rule 3 ratified** — **eg-0142**'s recorded `contradicted` stands. The
>   blind passes' `unsupported` followed a rulebook that lacked the category,
>   so the divergence was a rulebook gap, not a mislabel.
> - **Item 4 accepted** — **eg-0023**'s recorded `unsupported` stands under
>   this file's existing load-balancing precedent. The reversal rule below now
>   names balancer/backend explicitly so a condensed restatement cannot lose it
>   again.
>
> Both escalations are therefore resolved and carry `label_source: "owner"` — a
> provenance distinct from `adjudicated`, which means two blind passes agreed.
> **The escalation queue is empty. The resample has NOT been run**; see the
> History entry for why it cannot be delegated.

### The proposals as they were put (retained verbatim for audit)



The Step-4 authoring protocol and the Step-5 blind-pass briefs embedded a
condensed rulebook instead of this file (to keep the skip log above from
de-blinding pairs). The Steps 0–5 review measured that the condensation was
**not** faithful: it extended the exclusive-slot rule in ways this file
never ratified, and the two rulebooks even differ from each other. Both
Step-5 escalations trace to this fork, and the six host-swap agreements
below rest on it. **Ratifying a labelling rule is the owner's act** —
rule-then-pairs — so the extensions are recorded here as *proposed*, with
their evidence, and nothing more. The owner's sitting must adjudicate them
**before** the escalation queue and before the resample: the resample's
`contradicted` census contains all six host-swap pairs, and resampling them
against this file *without* deciding these extensions would manufacture a
spurious failure that is about the rulebook, not the labels.

1. **Proposed: the host/platform slot of a single named instance is
   single-valued** (exclusive-slot). Applied by the authoring protocol
   *and* by both blind passes (their shared brief text: "the host a single
   named instance runs on"). Governs six live `value-swap` pairs, all
   recorded `contradicted` and blind-confirmed under the same extended
   text — the agreement was manufactured by the shared fork, not
   independently reached from this file: **eg-0048, eg-0088, eg-0098,
   eg-0109, eg-0154, eg-0201**. If rejected: their verdicts fall to
   `unsupported`, which `value-swap` does not admit → retire-and-replace
   all six, replacements re-blinded under the Step-5 protocol.
2. **Proposed: the kind a named instance is (`IS_A`) is single-valued**
   (exclusive-slot). Present in both forked rulebooks ("an IS_A kind" /
   "the kind a named instance is"). Governs **zero** live pairs' verdicts
   today — the only IS_A-premise pairs (eg-0090, eg-0152) are `overreach`
   and untouched by the exclusive-slot rule. If rejected: no current label
   changes; the category is struck from future authoring.
3. **Proposed: the object of a named replacement/migration (`REPLACES`) is
   single-valued** (exclusive-slot). Present **only** in the authoring
   protocol ("the one thing a named migration replaced") and absent from
   the blind rulebook — this asymmetry is the direct cause of the
   **eg-0142** escalation: the author recorded `contradicted` under the
   category, both blind passes (lacking it) said `unsupported` (absence,
   not exclusion). If ratified: the recorded label stands and the
   divergence was a rulebook gap. If rejected: eg-0142 is a mislabel →
   retire-and-replace, replacement re-blinded.
4. **Omission, not an extension:** the blind rulebook's reversal table
   dropped this file's explicit "load-balancing roles" precedent
   (non-exclusive, eg-0023/eg-0025), which plausibly caused the
   **eg-0023** escalation (both passes: `contradicted`; recorded:
   `unsupported`, which follows the ratified text). Nothing to ratify —
   this file already decides it — but the owner may want to name
   balancer/backend explicitly in the reversal rule so a condensed
   restatement cannot lose it again.

## The contacted-pairs rule (Rule B)

The 41 T2.25 pairs were contacted twice by judge identity
`66df91cee44d2415` and **stay live**: contact without response is not
tuning, and their labels are the only fully human-scale cross-checked
core. But the ≥ 200 new pairs are grown as a set **no judge identity has
ever contacted**, and T2.41 must report every barred metric on **both**
populations — all live pairs, and the second population — with the
gate verdict required to hold on both. Stated here before any number
exists.

**Amendment 2026-08-10 (T2.115, ruling R3) — the second population is
renamed, because it had stopped being what its name said.** The
2026-08-08 re-measure ran fresh inference on **all 351 pairs** ("nothing
replayed warm"), so judge identity `fd39e7b2` has contacted the entire
file and a literal *never-contacted* population has not existed since.
The strict reading is also unsustainable: every qualification run scores
all live pairs, so the population would empty after **every** attempt and
Rule B would mean "grow the gold before each attempt", which no
two-attempt budget survives.

The population is therefore defined as **pairs not contacted before the
grown-gold attempt, with the per-pair miss census withheld** — and the
substance that keeps it meaningful is the withholding: the ledger
deliberately publishes only slice-level attribution, so one contact
without published feedback is materially unlike the 241 pairs' three
contacts with a public failure census. This is a **weakening** of the
text above and is recorded as one rather than absorbed quietly.

**The boundary constant does not move.** `RULE_B_FIRST_ID` filters
`id >= …` and is open-ended upward, so pairs appended by any later round
join the population automatically. Moving it forward would shrink the
gated population to that round's own pairs, which is how a growth round
would silently make its own bar unrepresentable.

## The blind-adjudication protocol (Ruling 3)

- **The judge labels nothing.** No DeepSeek model, and no model of the
  judge's family, contributes any label; every labelling dispatch runs
  keyless. Authors and labellers are Claude-family agents working from
  this file.
- **Layer 1 — construction.** Five slices admit exactly one lawful verdict
  (`SLICE_VERDICTS`); their labels are properties of the construction the
  rationale documents.
- **Layer 2 — two independent blind passes over every live pair** (the 41
  legacy pairs included; this is their mandated re-adjudication). The
  stripped export (`entailment_adjudication.strip_for_blind`) carries
  **only** id, premise and hypothesis — a slice tag alone would leak the
  lawful verdict set. Two separately-dispatched labellers, no shared
  context, no access to recorded labels or to each other; batches within
  one labeller never see other batches' verdicts. Each returns a three-way
  verdict plus the rule cited by name. Merge rule: both passes agree with
  the recorded verdict → `label_source: "adjudicated"`; anything else →
  the owner's escalation queue, untouched. Both passes' agreement rates
  are recorded in the History section, whatever they are.
- **Layer 3 — the owner.** Escalation adjudication first (wrong label →
  retire-and-replace; ambiguous rule → fix this file first, then
  re-adjudicate the affected slice — rule-then-pairs). Then, only after
  the set is stable, the seeded blind resample: **n = 93, bar ≤ 1
  disagreement** (ratified 2026-07-31; certifies label error < 5% at ~95%
  confidence), stratified by gold verdict class — full census of
  `contradicted`, then `unsupported`, remainder `entailed` proportionally.
  On failure: classify each disagreement, apply rule-then-pairs, draw a
  fresh seeded sample; two consecutive failures stop the task (plan
  blocker B4).

