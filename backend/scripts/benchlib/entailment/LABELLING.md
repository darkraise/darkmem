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
other verdict). The authoring target is **≥ 130 `l2-fact` pairs** — 41
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

## The contacted-pairs rule (Rule B)

The 41 T2.25 pairs were contacted twice by judge identity
`66df91cee44d2415` and **stay live**: contact without response is not
tuning, and their labels are the only fully human-scale cross-checked
core. But the ≥ 200 new pairs are grown as a set **no judge identity has
ever contacted**, and T2.41 must report every barred metric on **both**
populations — all live pairs, and the never-contacted subset — with the
gate verdict required to hold on both. Stated here before any number
exists.

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

## History

- **2026-07-30 (T2.25).** 41 pairs seeded, author-labelled; 41/41
  blind-agreement on the pre-commit check.
- **2026-08-03 (T2.54 Step 3).** Composition frozen: targets, seed
  20260731, relation classification, contacted-pairs rule, blind
  protocol. No T2.54 pair authored yet as of this entry.

### Skip log (Step 4)

Every skipped (premise, slice) slot with its reason, per Rule A. The
skipped slot keeps its id and slice with a hand-authored premise.

**Batch 1 (slots 0–49, eg-0042..eg-0091; 3 skips):**

- slot 10, `direction`, `11606722-ee98-5a68-a01f-3f2b5f1e49e7`
  (`vector related to telegraf`): RELATED_TO is symmetric and
  direction-ineligible per the reversal-exclusivity table. Authored as
  eg-0052 with a hand-authored HAS_PART premise.
- slot 19, `value-swap`, `7ff82019-0e6e-5ba1-a679-933ebecb9ac0`: the
  swappable slot is not single-valued (a generic USES object), so the
  exclusive-slot rule cannot fix `contradicted`. Authored as eg-0061
  with a hand-authored single-valued-port premise.
- slot 24, `value-swap`, `37a75f1f-b666-5ca3-9ae6-4cd8c8b8a2e5`:
  RELATED_TO's object is multi-valued by nature; exclusive-slot rule
  inapplicable. Authored as eg-0066 with a hand-authored token-TTL
  premise.

**Batch 2 (slots 50–99, eg-0092..eg-0141; 5 skips, all `value-swap` on
non-single-valued relations):**

- slot 69, `3d8b8266…` (USES): generic USES object admits many values.
  Authored as eg-0111, hand-authored premise.
- slot 75, `0d272cc9…` (HAS_PART): a whole has many parts and a part may
  sit in several wholes; neither slot is single-valued. Authored as
  eg-0117, hand-authored premise.
- slot 78, `60a400b1…` (IMPROVES_ON): a tool can improve on several
  predecessors and be improved on by several successors. Authored as
  eg-0120, hand-authored premise.
- slot 81, `7ff82019…` (USES): same fact as batch 1's slot-19 skip, same
  ground. Authored as eg-0123, hand-authored premise.
- slot 86, `37a75f1f…` (RELATED_TO): same fact as batch 1's slot-24 skip,
  same ground. Authored as eg-0128, hand-authored premise.
