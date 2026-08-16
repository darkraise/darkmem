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

- **Frame rule** (ruled 2026-08-15, rule-then-pairs on eg-0510). A
  hypothesis that generalises a premise entity into a quantified phrase
  usually supplies a frame noun — "at least one component of the estate",
  "somewhere in the environment", "a component of the nimbus deployment".
  Whether the frame counts as asserted content depends on whether it
  **differentiates**.
  - A **universal discourse frame** — "the estate", "the environment",
    "the stack", or any phrase naming the whole world the premise
    describes rather than a distinguished part of it — is vacuous:
    restricting a quantifier to the discourse domain restricts nothing,
    and the frame's head noun ("component", "system") is part of the
    frame and vacuous with it. Such a frame moves no verdict; an
    existential so framed is ordinary weakening and is `entailed` when
    its witness is in the premise (eg-0452, eg-0459, eg-0513, eg-0520).
  - A **proper-subset frame** — a named deployment, cluster, tier, or any
    phrase some entities of the premise's world could fail to satisfy —
    is asserted content, because it sits in the restrictor of the
    asserted existential; a definite article does not shelter it. The
    exhaustivity rule protects *presupposed* content, and the definite's
    existence presupposition is indeed not asserted — but the witness's
    membership in the frame is not presupposed by anything; it is the
    existential's own restrictor. Membership must be established **by the
    premise**; lexical resemblance between witness and frame (eg-0510's
    "nimbus-02" / "the nimbus deployment") is world knowledge and
    inadmissible under procedure 2. Unestablished membership makes the
    pair `unsupported` — never `contradicted`: absence is not exclusion
    (procedure 4).
  - The test: *could an entity of the premise's world fail to be in the
    frame without any further fact being false?* If no — the frame is the
    world — it is vacuous. If yes, it differentiates and must be earned.

- **Dependency-strength rule** (ruled 2026-08-15, rule-then-pairs on
  eg-0506 and eg-0499). The reversal table classifies `DEPENDS_ON`
  without stating its forward strength; this rule states it.
  `DEPENDS_ON` asserts a **generic requirement for intended operation**:
  X needs Y for X to work as intended. It fixes no timing, no failure
  mode, and no condition on Y.
  - Renderings at the same generic level are paraphrase and `entailed`:
    "needs Y in order to run", "requires Y to function", "relies on Y"
    (eg-0506, eg-0591). "Run" and "function" are read here at the
    relation's own generic level — "operate as intended" — never as a
    claim about process start-up.
  - Renderings that fix *when* the need bites (start-up versus first
    use), *how* absence manifests (cannot start, crashes, degrades), or
    *which condition on Y* matters (reachable, available, healthy) assert
    a failure mechanism the relation does not carry: a lazily-bound or
    degraded-mode dependency makes the premise true and the hypothesis
    false. These are `unsupported` (eg-0499, eg-0525, eg-0636) — and
    never `contradicted` from the bare relation, by procedure 4.
  - The test: *could X depend on Y and the hypothesis still be false?* No
    for a generic requirement rendering; yes for a mechanism-specific one.
  - **Cross-relation vocabulary is decided by relation entailment, not
    synonym feel.** Rendering a premise's relation with another taxonomy
    relation's characteristic vocabulary is rewording only when the
    premise's relation semantically guarantees the hypothesis's. `USES`
    does not guarantee `DEPENDS_ON` — use without dependence is coherent
    — so necessity vocabulary ("relies on", "requires", "needs") over a
    `USES` premise is strengthening, `unsupported` (eg-0634). The forcing
    argument: "needs Y to function" is paraphrase-level for "relies on";
    if "uses" entailed "relies on", transitivity would make "uses" entail
    "needs Y to function", which is false on its face.

- **Bare-sortal clause** (extends the Frame rule; ruled 2026-08-17,
  rule-then-pairs on eg-0486, eg-0475 and eg-0699). A quantified
  hypothesis often carries no frame phrase at all — "at least one
  component", "at least one service". **The Frame rule's differentiation
  test applies to the bare noun itself**: *could an entity of the
  premise's world fail to satisfy this noun without any further fact
  being false?*
  - A noun **every** entity of the premise's world satisfies —
    "component", "system", **"thing"**, **"something"**, and kin, the same
    head nouns the universal-frame branch already treats as vacuous —
    restricts nothing,
    with or without a frame phrase. An existential built on it is
    ordinary weakening: `entailed` when its witness is in the premise
    (eg-0420, eg-0428, eg-0546).
  - A noun that **partitions** the premise's world — "service",
    "software", "database", **"machine"** — is asserted content in the
    existential's restrictor and must be established **by the premise**.
    *"Machine" was placed here by ruling on 2026-08-17 (rule-then-pairs on
    eg-0534), on this corpus's own evidence rather than on intuition: nine
    of its 56 distinct `DEPLOYED_ON` targets — `cpu`, `garage`, `minio`,
    `postgres`, `rack ups`, `udp`, `port 9500`, `traefik`, `memgraph` —
    are plainly not machines, so a deployment target can fail the noun
    with no further fact being false. "Host" survives the same test on the
    same data: those nine are hosts without being machines, which is
    exactly the line between an earned role and a partitioning kind.* What syncthing
    or nginx "obviously is" is world knowledge and inadmissible
    (procedure 2). Unestablished, the pair is `unsupported` — never
    `contradicted`, by procedure 4.
  - **A relation's own generic semantics count as establishment.** A
    sortal naming the role a slot necessarily plays is earned by the
    relation: `DEPLOYED_ON` makes its target a "host" (eg-0592, eg-0650),
    `DEPENDS_ON` makes its object a "dependency" (eg-0516), `HAS_PART`
    makes its part a "part" or **"constituent"** (synonyms of the role the
    relation creates are earned with it — eg-0606), `USES` makes its
    object a **"resource"** and its subject a **"consumer"** (eg-0640,
    eg-0468), `DEPENDS_ON` makes its object a **"prerequisite"** and
    the other endpoint a **"dependent"** (eg-0430), and `RELATED_TO` earns **"connection"** — "there is a
    connection between" its endpoints (eg-0524), and `DEPLOYED_ON` earns **"installation"** for
    its *subject* as well as "host" for its target — a thing deployed on
    a host cannot fail to be an installation there, where it can easily
    fail to be a "service" (eg-0469, eg-0704). `HAS_PART`'s generic
    semantics also carry the composition renderings of that role, so
    **"built from"** is inside it and needs no separate earning
    (eg-0582). These were placed 2026-08-17 by applying the
    branch above rather than by a fresh ruling: each names the role the
    relation itself creates, so the relation cannot hold while the slot
    filler fails the noun.

    **The clause reaches predicate nominals, not only existentials.**
    "Y **is a** software/service/machine that X uses" asserts the same
    partitioning kind as "at least one service", and the first sweep for
    this class matched only quantified forms — which is how eg-0512
    ("Concourse is **a piece of software** that log-02 makes use of")
    survived the round that retired eg-0699 for the identical sortal. A
    sweep for this defect must cover both shapes. The test mirrors the dependency-strength
    rule's: *could the relation hold and the slot-filler fail the
    sortal?* No for the "host" of a deployment; **yes** for a deployed
    thing being a "service" — deployment does not make a thing a service.
    Restrictor modifiers ("other", "named") are content judged the same
    way: established when the premise's witness demonstrably satisfies
    them.

- **Possessive-existential clause** (same ruling). "X **has** at least
  one N (that VPs)" is **not** the bare existential "at least one N VPs
  X": the *have*-construction asserts the N stands in the
  possession/part relation to X, projecting the implicit frame "N **of
  X**" — a proper-subset frame whose membership must be earned exactly
  like an explicit one. `DEPENDS_ON` earns "X has a dependency"
  (eg-0516); `DEPLOYED_ON` earns "X has a component deployed on it",
  because deployment on X places the subject in X's hosted stack
  (eg-0424); **nothing earns** "X has a component that depends on it" —
  a dependent of X is not thereby a component *of* X (eg-0486).

  **The bound on both clauses, recorded rather than smoothed over.**
  eg-0465 ("idx-03 hosts at least one deployed service") and eg-0475
  ("At least one service is deployed on spire-01") are semantically
  equivalent — same relation, same sortal — and **both measured
  instruments split them the same way**, accepting the first and
  rejecting the second. No rule can match both members, so the clause
  above rules both `unsupported` and the gold carries the correction on
  both. At this boundary the instruments are surface-form sensitive; the
  repetition study on eg-0650 (3 `entailed` / 2 `unsupported` on
  identical input, same seed) is the independent confirmation.


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

## History

### Round 4 — the fresh gold (T2.124), frame ratified 2026-08-13

**Pair set `4975c5cc` is retired from qualification use for every role.** The ground is
**publication contamination**: that gold's censuses, its duplicate findings and its
per-slice decompositions are published in `gate-ledger.md`, which makes the set unusable
for any future qualification independently of anything measured on it. A second ground —
that the entailed class was never lattice-sized to its own bar — is recorded as
corroborating only.

Round 4 authors a fresh census at ids `eg-0418+` on **fresh premises**: no premise from
the retired harvest is reused, because contamination transfers through a premise to the
propositions it determines (for `verbatim` the hypothesis is a near-literal restatement,
and for `direction` it *is* the reversal).

**The Rule B reading for a gold with no contacted pairs.** `rule_b_population` filters
`id >= RULE_B_FIRST_ID` and that filter is lexical and open-ended, so a continued
4-digit id sequence puts the **entire** fresh census inside Rule B: the pooled population
and the Rule B population **coincide** until the first qualification attempt spends
against this gold, after which they diverge in the usual way. One congruence per class
therefore suffices for lattice sizing, and T2.115's two-population obstruction — where
`N ≡ 0 (mod 20)` and `55 + N ≡ 0 (mod 20)` had no simultaneous solution — does not arise
on a restarted sequence.

The frame was ratified **before any pair was authored** (`gate-ledger.md`, "T2.124 frame
— owner ratification, sitting 1"); the emitted matrix is ratified separately once the
script's inputs exist. Nothing in this entry states or implies a measured result.

### Skip log (round 4, step 7 — authored 2026-08-14)

Twenty-one skips, every one re-authored in place for the same slice and
verdict with a hand-authored premise, so slice targets stayed exact and only
the `l2-fact` count moved: 218 of 280 live pairs anchor manifest facts
(floor 140). Verbatim reasons, slot files and author attestations:
`dispatch/2026-08-14-t2124/` (04/05).

- **15 value-swap slots on multi-valued relations** (`USES`, `DEPENDS_ON`,
  `CAUSES`, `RELATED_TO`) — the named known-infeasible shape; found
  independently by six blind authors: eg-0444, eg-0457, eg-0461, eg-0462,
  eg-0491, eg-0494, plus n3's third variant, eg-0518, eg-0526, eg-0533,
  eg-0537, eg-0542, eg-0579, eg-0583, eg-0588, eg-0645, eg-0646, eg-0647.
- **2 direction slots whose shared-premise differentiation note could not be
  met** (the hypothesis is determined by the premise; rewording the reversal
  is barred): eg-0488, eg-0500.
- **1 paraphrase duplicate** (eg-0564, controller-logged): byte-identical to
  eg-0430 under cross-batch convergence on a shared premise; a second
  paraphrase of one premise asserts the same proposition in every wording, so
  the later-minted member (id order) moved to a hand-authored premise.

Two same-premise weakening duplicates (eg-0592, eg-0614, similarity 1.0) were
re-authored on their assigned premises toward different weakening axes — not
skips; the premise stayed. Three sub-threshold duplicate propositions found
after assembly are recorded as **known-open for step 9** in the dispatch
record: eg-0424/eg-0558, eg-0425/eg-0559, eg-0463/eg-0590.


### Duplicated propositions: the worked asymmetry (relocated 2026-08-13)

**Relocated from "File discipline" by owner amendment, unchanged in substance.**
It was ~390 lines above the strip truncation point, so every party the
blind-adjudication protocol calls blind read a measured judge result before
authoring or labelling a single pair. Found by T2.124's plan review; the plan
had asserted this region carried no failure profile. The structural claim stays
in place above; only the arithmetic and the measured example moved.

**The bias is not one-directional, and the first version of this paragraph
said it was.** A judge that *misses* a duplicated proposition burns two of
its four permitted misses — harder. A judge that *catches* it banks two
correlated hits and may then miss four of the remaining 78 independent items:
a per-item tolerance of 4/78 ≈ 5.13% against the intended 4/80 = 5.00% —
strictly **easier**, and at measured recall ≈ 0.94 the catch is the common
case. The live instance is sharp: attempt 1 on this gold scored Rule B at
exactly **38/40 = 0.9500**, a zero-margin pass whose independent-item reading
is below the bar. Nothing about "the duplicates only make it stricter" is
true, and reading it that way is the reassuring error.


- **2026-08-10 (T2.115 lattice resize — the census split 40/40, certified at
  the bar's edge).** Rule B's second population held 25 contradicted pairs, so
  its recall lattice was 1.00 / 0.96 / 0.92 and **0.95 was not on it** — the
  bar it gates by was silently ≥ 0.96. The round put 0.95 on both lattices at
  once: contacted contradicted 55 → 40, second population 25 → 40, **pooled
  held at exactly 80** (76/80 and 38/40, both exact). Growth could not do it —
  `N ≡ 0` and `55 + N ≡ 0 (mod 20)` has no solution — and the Layer-3
  resample's full-census stratum caps the pooled census at 93 anyway, so
  retirement was the only route that changed nothing ratified.

  **The retirement.** Fifteen contacted contradicted pairs under the new
  lattice-retirement rule, drawn by `benchlib.lattice_retirement` — committed
  *before* it ran, because pinning a seed alone does not close the aiming
  channel when the executor writes the algorithm afterwards. Seed
  **2148355473** (the pre-round file's own sha256), pool 45 eligible after
  excluding the ten T2.25 core pairs, quota by largest remainder **8
  value-swap / 4 direction / 3 temporal**. Reproduce with

  ```bash
  git show 48ad7e8e~1:backend/scripts/benchlib/entailment/gold.json \
    > /tmp/gold-pre-round.json
  cd backend && PYTHONPATH=.:scripts python -m benchlib.lattice_retirement \
    --verdict contradicted --n 15 --gold /tmp/gold-pre-round.json
  ```

  **`--gold` is the load-bearing argument and the first version of this line
  omitted it** (corrected 2026-08-10). It defaults to the *current* gold file,
  and the seed is that file's own sha256 — so the one-command form drew seed
  2566671177 against a pool the round had already changed, reproducing
  nothing. Against the pre-round file it yields seed 2148355473, quota 8/4/3
  and exactly the fifteen ids marked below; re-verified 2026-08-10. Each
  retired pair carries
  `retirement_kind: "lattice"` so no later reader mistakes fifteen correct
  labels for mislabels.

  **The authoring: 66 pairs, `eg-0352`..`eg-0417`, two firewalled batches.**
  Neither author read the gate ledger, the qualification reports or
  `resample_runs/`; both bounded their rulebook read above this section and
  attested to it. The *controller* was contaminated — it had read the
  slice-level failure attribution — so it could not author, and the slice
  quotas were derived mechanically so the brief itself could not leak the
  weakness. **The harvest was exhausted**: 19 of 57 non-temporal slots had
  capacity, so scarce anchors went to the contradicted slices first by a rule
  stated before the draw, and the rest took hand-authored premises under the
  skip mechanism. `l2-fact` 235 → 238 of 402 live (59.2%, floor 50%) — six
  retired, nine added. This read "240 → 238" until 2026-08-10; no state of the
  file was ever 240, and the arrow pointed the wrong way as a result: the
  round *raised* the l2-fact count, it did not spend it.

  **Ten skips**, all logged: three `direction` on symmetric relations, five
  `value-swap` on non-single-valued slots, and **two of a shape nobody had
  predicted** — a `direction` slot on a fact that already carries a live
  `direction` pair, where the reversal is determined and the loader rejected
  the byte-identical duplicate. Added to the known-infeasible list above.

  **This round shipped with two Critical findings open against it, and they
  are the owner's to rule on.** Recorded here as well as in the gate ledger
  (2026-08-10, "C-1 / C-2") because a reader auditing the round's own record
  must not have to find the ledger to learn the census is disputed. Neither is
  adjudicated below; the ledger states the options and an agent may not choose
  among them.

  - **C-1 — clause 5 of the lattice-retirement rule was violated by the round
    that ratified it.** The draw retired 8 value-swap / 4 direction / 3
    temporal; the replacements landed 8 / 4 / **2** plus one
    **overreach**-contradicted (`eg-0405`), so the pooled slice distribution
    moved (temporal 15→14, overreach 0→1) while the census still landed at
    exactly 80. Clause 5 requires the distribution be unchanged. The rule
    cannot repair its own violation: clause 1 makes `eg-0405` ineligible for
    lattice retirement because it sits in Rule B's population.
  - **C-2 — `eg-0367` is a semantic near-duplicate of live `eg-0093`**:
    identical premise, the same reversed proposition reworded. Two sibling
    slots (13 and 28) collided byte-for-byte and were skipped, which is what
    the paragraph above records; **slot 15 is a third instance that never
    collided**, so the byte-uniqueness loader passed it and the instruction
    added after the first two — *do not resolve it by rewording the reversal* —
    was aimed at a shape it could not reach. The pooled census is therefore 80
    rows and at most 79 independent items, and the duplicate straddles both
    populations. The "all logged" account above is complete for the skips and
    incomplete for the shape.

  **Blind adjudication: 64/66 adjudicated on the first pass.** Pass A (Opus)
  and pass B (Sonnet), separately dispatched, no shared context. Agreement
  against the recorded labels **0.9848 each**; against each other **0.9697** —
  they split on two pairs, which is the independence signal a correlated pair
  would not produce.

  **Two escalations, both ruled rule-then-pairs**, and both passes flagged the
  first independently before either knew the other existed:
  - **eg-0416** → the **Inception-window rule**. "Since X" with no predecessor
    named asserts a beginning, not a prior absence. Recorded `unsupported`
    stands, `label_source: owner`.
  - **eg-0405** → the **Additional-value rule**. The slot's cardinality
    decides. Recorded `contradicted` stands, `label_source: owner`.

  **Slice re-adjudication under both new rules changed no label** — 57
  temporal pairs and every added-value shape across all 402 checked. The
  Inception-window rule's second bullet governs no live pair today; it is
  written because the question needed deciding, not because a pair needs it.

  **The certification took three sittings, and that is recorded rather than
  tidied.** `--write-gold` re-ran the model instead of recording the measured
  run, and an LLM sitting is not reproducible: sitting 1 found **1**
  disagreement (eg-0341), sitting 2 found **0**, sitting 3 found **1**
  (eg-0175). All three pass `bar ≤ 1`, but recording sitting 2 would have
  been choosing the best of three by accident. Sitting 2's record was
  withdrawn, and **sitting 3 is what the gold carries**, recorded from its own
  raw replies with `--from-raw` and no fresh model call. Three tool defects
  were fixed first: `--write-gold` re-running rather than recording, a second
  sitting overwriting the first's raw replies (same date, same model, same
  gold — the collision class T2.110 closed only for *different* golds), and a
  hardcoded `performed_by` date that stamped every run "owner-directed
  2026-08-08".

  **Both disagreements were model error and both were the same shape**: a rule
  cited whose own precondition excludes it. eg-0341's premise explicitly
  closes its window *and* names the successor, so the evaluation-time rule
  cannot reach it — identical to T2.110's eg-0018, the same model failing the
  same way two rounds running. eg-0175 is a pure value *swap* (first →
  fifteenth) and the model cited the **Additional-value rule**, which requires
  the premise's value be kept and a second asserted alongside. Worth stating
  plainly: a rule added hours earlier became a new way for the instrument to be
  wrong, which is a cost of amending a rulebook an LLM reads.


- **2026-08-08 (T2.110 Layer-3 resample — n = 93, 1 disagreement, PASS at the
  bar's edge).** The fresh seeded draw against the ruled gold (sha256
  `047cbd6f…`, seed 75283823, strata 80 census + 6 + 7) was sat by
  **deepseek-v4-pro**, non-Claude and owner-directed, via `resample_llm.py`.
  Raw replies: `entailment/resample_runs/2026-08-08-deepseek-v4-pro-047cbd6f.json`.
  **n = 93, disagreements = 1, bar ≤ 1 — the gold certifies**, and it is now
  gate-eligible on every condition. That the result sits *on* the bar rather
  than under it is recorded plainly: the previous round's two models each
  scored 0 against the 241-pair file, so this is the weakest passing sitting
  the set has had.

  **The one disagreement, classified: model error, gold stands.** eg-0018
  (gold `contradicted`, resample `unsupported`, rule cited "evaluation-time
  rule"). The premise — "Postgres 15 was the production database from March
  2025 **until the January 2026 upgrade to Postgres 16**" — closes its window
  explicitly *and* names the successor, which is the window rule's
  `contradicted` case and the very pair the window rule cites. The
  evaluation-time rule's own precondition is that the premise **fails** to fix
  the state "at an open or explicitly closed window"; here it fixes it at an
  explicitly closed one, so the rule the model cited excludes itself. No
  rulebook gap, so no rule-then-pairs: this is not the eg-0308 shape, where
  two competent readers split because the rulebook had not decided. eg-0018 is
  additionally `adjudicated` and one of the 41 T2.25 pairs carrying the
  set's only human-scale double cross-check.

  **The standing objection in `resample_llm.py`'s docstring applies to this
  number too** and is not weakened by the pass: an LLM sitting measures
  inter-model agreement more than label correctness, and the judge T2.41
  qualifies is itself an LLM entailment judge. It is evidence, and weaker
  evidence than the protocol assumed when it named the owner.

  **A collision was found and fixed here.** Run artifacts were named
  `{date}-{model}.json`, so this sitting silently overwrote the previous
  round's deepseek-v4-pro record — same model, same day, different gold. The
  prior file was restored from git and `resample_llm.py` now writes
  `{date}-{model}-{gold_sha8}.json` with `gold_sha256` in the payload, since a
  resample means nothing except relative to the file it certifies. Runs
  predating the fix keep their bare names.

- **2026-08-08 (T2.110 Layer-3 sitting — eg-0308 ruled, rule-then-pairs).**
  The one escalation of the growth round was ruled an **ambiguous rule, not a
  mislabel**, so the fix landed in this file first and the slice was
  re-adjudicated against it. Pass A read the cleft "is what causes" as an
  exhaustivity upgrade ('a cause' → 'the cause'); pass B read it as pure
  rewording. Both were reading a rulebook that **did not decide the question**:
  the implicature-is-not-contradiction rule already distinguished asserted from
  non-asserted content, but was scoped only to the `unsupported → contradicted`
  step and said nothing about the `entailed → unsupported` one. The new
  **exhaustivity rule** states the missing half.

  **eg-0308's recorded `entailed` stands**, `label_source: "owner"`. No
  retire-and-replace; the gold's composition is unchanged at 351.

  **What the substance turned on.** The gold already settles that adding
  exhaustivity to a bare `CAUSES` triple strengthens — eg-0276 (`overreach`,
  `unsupported`) does exactly that with "the only thing affecting", off the
  same premise shape. What it had never ruled is whether a *cleft* conveys
  exhaustivity the way *"only"* does. It does not: cleft exhaustivity is
  presupposed and defeasible where "only" is asserted. Note also that
  procedure 3's "a factor" → "the cause" example is calibrated against a
  premise that **explicitly marks** plurality of causes (eg-0032, "one
  contributing factor"), which a bare triple does not.

  **Slice re-adjudication (mandated by rule-then-pairs): no label changed**,
  and the ruling is confirmed by pairs that were already `adjudicated` rather
  than only by the pair under dispute.
  - `paraphrase` (51): two pairs besides eg-0308 carry an exhaustivity
    construction, and **both are already `adjudicated` `entailed` — two blind
    passes each, unanimous**: eg-0006 ("Automatic certificate renewal **is
    why** Caddy was picked...", a pseudo-cleft of the identical shape) and
    eg-0196 ("Redis **is the replacement** for Memcached", definite predicate
    nominal). The rule ratifies standing practice; the alternative ruling
    would have put eg-0308 at odds with two unanimous adjudications.
  - `overreach` (51): every exhaustivity-bearing hypothesis carries it
    **lexically** — "only" (eg-0057, eg-0081, eg-0159, eg-0276),
    "every"/"all" (eg-0031, eg-0073, eg-0115, eg-0137, eg-0144, eg-0161,
    eg-0165, eg-0195, eg-0206, eg-0209, eg-0246, eg-0311), "in every respect"
    (eg-0182) — or adds content outright. **None rests on information
    structure alone**, so the rule makes no overreach pair unlawfully
    `entailed`. This slice was checked though the escalation did not sit in
    it, because the new rule's second clause governs its boundary.

  The escalation queue is empty; `gold.json` carries 348 `adjudicated` +
  3 `owner` + **0** `author`. The eligibility lock's remaining condition is
  the fresh resample alone, whose draw is pinned to the new sha256.

- **2026-08-08 (T2.110, growth round — 110 pairs appended, eg-0242..eg-0351).**
  Grown because the 241-pair set was contaminated as a measurement surface —
  three recorded `gold_touching_attempts` and a public failure census — so
  G-D's re-measure needed pairs whose author could not aim. The author read
  neither the gate ledger's G-D sections, the G-D resolution-spike brief, the
  judge-qualification reports, nor `resample_runs/`; the residual (aggregate
  rates named in M1's own task text and in `verification_judge.py`'s bar
  comment) is recorded in the task report.

  **Census sizing, the reason for the round's shape.** `contradiction_recall_bar`
  = 0.95 = 19/20 resolves in steps of 1/N over the gold-contradicted census.
  At N = 55 the lattice brackets the bar at 52/55 ≈ 0.9455 and 53/55 ≈ 0.9636:
  0.95 is not achievable, so the operative bar was 0.9636 and one miss moved
  recall 0.018. The bar sits on the lattice only at N ≡ 0 (mod 20), and the
  Layer-3 resample's full-census stratum refuses N > 93, so the target census
  is **80** — the one multiple of 20 in (55, 93]. At 80, recall 76/80 = 0.9500
  exactly clears, 75/80 = 0.9375 misses, and a judge is permitted exactly 4
  misses. Every other slice scaled proportionally: 241 → 351 by
  largest-remainder rounding (verbatim 35, paraphrase 51, weakening 42,
  temporal 51, direction 44, overreach 51, value-swap 42, unrelated 35).

  **Premise assignment was mechanical** (Rule A, round 2): seed
  `int(sha256(gold.json @ 241 pairs)[:8], 16)` = 3872744570 — derived from the
  pre-growth file's own hash, so unchooseable — over a capacity-aware cycle
  (`entailment_assignment.build_round2_assignment`; existing premises carried
  prior usage, so the cycle skips facts at the ≤ 4-per-premise cap). Verdicts
  fall out of construction: the five fixed-verdict slices by `SLICE_VERDICTS`,
  `direction` by the reversal-exclusivity table (the draw yielded 6 exclusive
  reversals + 1 symmetric skip → 7 contradicted, 7 non-exclusive →
  unsupported), and the 16 hand-authored temporal pairs' mix (5 entailed /
  5 contradicted / 6 unsupported) chosen after the draw to land the census at
  exactly 80 = 13 (value-swap) + 7 (direction) + 5 (temporal) + 55 (prior).

  **Blind adjudication (Layer 2) ran before this entry was written**, so the
  passes could not read a skip log naming the new ids: two separately
  dispatched Claude-family labellers (pass A: Opus; pass B: Sonnet), each
  given only id/premise/hypothesis plus this file's rulebook sections (through
  the reversal-exclusivity table — the full table and the three ratified
  exclusive-slot extensions included, per the voided-resample lesson).
  Agreement, recorded whatever it is: **pass A vs recorded 109/110 =
  0.9909; pass B vs recorded 110/110 = 1.0000; pass A vs pass B 109/110 =
  0.9909.** 109 pairs flipped to `adjudicated`; **1 escalated untouched** to
  `entailment/escalation_queue.json` (eg-0308, `paraphrase`: recorded
  `entailed`; pass A said `unsupported`, reading the cleft "is what causes"
  as an exhaustivity upgrade — 'a cause' to 'the cause'; pass B agreed with
  the recorded verdict). The pair stays `author` and the queue is the
  owner's Layer-3 work list, so eligibility honestly reports 1/351
  author-labelled until the ruling, alongside the missing fresh resample.
  Unlike the Step-5 round, the two passes diverged from *each other* here —
  a small but real independence signal the 2026-08-03 review's
  correlated-error concern predicted would be absent.

  **The recorded resample does not carry over, by design.** The 2026-08-08
  n = 93 resample certified the 241-pair file — its draw is pinned to that
  file's sha256 — so the grown gold carries **no** `resample` block (keeping
  it would have satisfied the eligibility lock with a certification of a
  different file), reports ineligible until a fresh draw is scored, and the
  blind export, manifest and sheet were regenerated against the grown file's
  hash. `gold_touching_attempts` is keyed on `gold_sha256` and therefore reads
  0 for the grown file. The grown set has never been contacted by any judge
  identity (Rule B's population then spanned eg-0242..eg-0351; T2.115 extended its end to eg-0242..eg-0417 without moving the boundary, which is what the open-ended `id >=` filter is for).

### Skip log (T2.110 round)

Every skipped (premise, slice) slot, per Rule A; the slot keeps its id and
slice with a hand-authored premise.

**Slots 0–93, eg-0242..eg-0335; 12 skips (11 `value-swap`, 1 `direction`):**

- slot 6, `value-swap`, `2b8fd40f…` (`terraform uses tf-state`): generic USES
  object, not single-valued. Authored as eg-0248, hand-authored state-bucket
  premise.
- slot 14, `value-swap`, `c2cff8f6…` (`ntfy related to sms`): RELATED_TO
  multi-valued by nature. eg-0256, hand-authored polling-interval premise.
- slot 23, `value-swap`, `505aabfc…` (`grafana uses infra`): generic USES
  object. eg-0265, hand-authored port premise.
- slot 26, `value-swap`, `e31a032d…` (`restic uses wiki volume`): generic
  USES object. eg-0268, hand-authored retention premise.
- slot 36, `value-swap`, `6c47ab46…` (`license-report depends on internal
  package mirror`): generic dependency object admits many values. eg-0278,
  hand-authored port premise.
- slot 45, `value-swap`, `f5074b56…` (`ci runners uses docker-in-docker`):
  generic USES object. eg-0287, hand-authored pinned-version premise.
- slot 52, `value-swap`, `519cf15a…` (`terraform uses minio`): generic USES
  object. eg-0294, hand-authored retention premise.
- slot 56, `value-swap`, `cf0723ca…` (`unleash uses oidc`): generic USES
  object. eg-0298, hand-authored version premise.
- slot 60, `value-swap`, `60a400b1…` (`caddy improves on nginx`): IMPROVES_ON
  not single-valued (round-1 slot-78 ground). eg-0302, hand-authored port
  premise.
- slot 73, `direction`, `702b3d82…` (`fleet-cfg related to booking
  schedule`): RELATED_TO is symmetric and direction-ineligible per the
  reversal-exclusivity table. eg-0315, hand-authored HAS_PART premise.
- slot 92, `value-swap`, `c2cff8f6…` (`ntfy related to sms`): same ground as
  slot 14. eg-0334, hand-authored token-lifetime premise.
- slot 93, `value-swap`, `702b3d82…` (`fleet-cfg related to booking
  schedule`): RELATED_TO multi-valued by nature. eg-0335, hand-authored
  schedule premise.

**Round closed 2026-08-08:** 351 live pairs, `l2-fact` 235/351 (66.9%,
floor ≥ 50%), contradicted census exactly 80, slice counts exactly the
largest-remainder targets, 12 skips all logged above.

- **2026-08-08 (T2.54 Step 6, resample — RUN, by model, owner-directed).**
  n = 93, **0 disagreements**, bar ≤ 1. The gold is now lock-eligible.

  **No human sat, and the record says so.** The owner directed on 2026-08-08
  that a model perform the sitting rather than the owner. Two vendors ran it
  independently through `resample_llm.py`, one request per pair: **gpt-5.5**
  (OpenAI) and **deepseek-v4-pro** (DeepSeek). Each scored 0 disagreements
  against the recorded labels, and 0 against each other on all 93. Raw replies
  are committed under `entailment/resample_runs/`. Neither is Claude-family —
  the runner refuses a Claude-family model id outright — so the correlated
  error this entry's predecessor describes is not what produced the number.

  **The standing objection, recorded because a passing number must not bury
  it.** The entry below argues the resample must come from outside the family
  that labelled the set. Two non-Claude vendors satisfy that literally. They do
  not satisfy the deeper claim: several pairs are built so the hypothesis is
  true in the corpus world but unsupported by the premise, and scoring
  plausibility over entailment is a *generic* frontier-model failure rather
  than a Claude-specific one — and the judge T2.41 qualifies on this gold is
  itself an LLM entailment judge. This number therefore measures inter-model
  agreement more than it measures label correctness. It is evidence, and it is
  weaker evidence than this protocol assumed when it wrote "the owner".

  **Two caveats on what the 0 covers.** (1) **52% of the draw is now decided by
  a stated lookup rule** — 19 `direction` pairs by the reversal table, 29
  `value-swap` pairs by the exclusive-slot list. The resample's power to detect
  a *labelling* error lives in the other 45 pairs, where both vendors also
  matched on every one. Read the 0 as "45 judgment-bearing pairs confirmed
  twice", not "93 independent confirmations". (2) **The six host-swap pairs
  Rule 1 governs are no longer independently tested.** The proposals section
  above flags them as "exactly the pairs the resample's full `contradicted`
  census exists to test", their prior agreement having been manufactured by the
  shared fork. Ratified Rule 1 now reaches them mechanically, so their verdicts
  rest on the owner's ratification and not on this resample.

  **The first attempt failed 3-against-1, and was voided as an instrument
  defect** (owner-ruled, not counted against blocker B4's two-failure stop).
  Every disagreement — eg-0142, eg-0163, eg-0179 — traced to a rule the sheet
  did not carry: the excerpt held 4,150 of this file's 34,914 characters and
  omitted both the 16-relation reversal table and the three ratified
  exclusive-slot extensions. This file had predicted exactly that ("a future
  condensation that drops any of them is a fork to be fixed") and recorded the
  precedent: on eg-0142 "both blind passes (lacking it) said `unsupported`".
  Three labellers across two vendors, one omission, one identical error. The
  sheet now carries both, no label changed, and the re-run scored 0.

- **2026-08-06 (T2.54 Step 6, owner sitting — partial).** The owner ratified
  all three Step-5 rulebook extensions and accepted item 4's clarification, in
  the mandated rule-then-pairs order. Both escalations resolved without
  retire-and-replace: eg-0142 under ratified rule 3, eg-0023 under this file's
  pre-existing precedent. `gold.json` now carries 239 `adjudicated` + 2 `owner`
  and **zero** `author` labels, which clears the last eligibility-lock
  condition.

  **The n = 93 seeded blind resample remains outstanding, and it was
  deliberately not delegated.** Every label in this gold was produced by
  Claude-family agents, and the Steps 0–5 review measured the failure mode
  directly: the second blind pass "added ~zero bits and diverged identically to
  pass A" — correlated error, not independent confirmation. A Claude agent
  drawing the resample would reproduce the same correlated errors, pass the
  ≤ 1-disagreement bar comfortably, and certify nothing — while flipping the
  gold to lock-eligible, because `judge_qualification` checks size, the
  `l2-fact` floor and author-labels but **not** whether the resample ever ran.
  That combination — a passing number that means nothing, guarding a gate that
  cannot detect its absence — is the one outcome this protocol exists to
  prevent. The resample is the first independent accuracy measurement this gold
  receives and it must come from outside the family that labelled it.



- **2026-07-30 (T2.25).** 41 pairs seeded, author-labelled; 41/41
  blind-agreement on the pre-commit check.
- **2026-08-03 (T2.54 Step 3).** Composition frozen: targets, seed
  20260731, relation classification, contacted-pairs rule, blind
  protocol. No T2.54 pair authored yet as of this entry.
- **2026-08-03 (T2.54 Step 5).** Two independent blind passes over all
  241 live pairs (two labellers × five fresh-context batches each; the
  briefs, committed under `.superpowers/sdd/T2.54-entailment-gold-labelling/`,
  embed a **condensed** rulebook rather than this file, because the
  Step-4 skip log above names pair ids with their slices and would
  de-blind them — and the Steps 0–5 review later measured that the
  condensation forked from this file; see the unratified-extensions
  section above). Agreement rates, recorded whatever they are: **pass A
  vs recorded 239/241 = 0.9917; pass B vs recorded 239/241 = 0.9917;
  pass A vs pass B 241/241 = 1.0000**. 239 pairs flipped to
  `adjudicated`; 2 escalated untouched to
  `entailment/escalation_queue.json` (eg-0023: recorded `unsupported`,
  both passes `contradicted`; eg-0142: recorded `contradicted`, both
  passes `unsupported`).
- **2026-08-03 (T2.54 Steps 0–5 review, settled).** The 1.0000 inter-pass
  figure is the correlated-error signature, empirically confirmed: pass B
  added approximately zero independent bits — both of its divergences
  from the recorded labels were identical to pass A's, down to the rule
  citations. The double-agreement merge therefore degenerated to a single
  same-family check, and the 239 `adjudicated` flips carry **one**
  independent reading's assurance, not two. **The 1.0000 figure may enter
  G-D only as rule-determinism and procedural evidence, with this caveat
  attached — never as label-accuracy evidence.** The owner's n = 93
  resample is the **first** independent accuracy measurement this gold
  will have received, not a confirmation of an existing one; quoting
  1.0000 as agreement without this caveat would be overclaiming, and
  T2.41's report must not do it. Both escalations trace to the Step-5
  rulebook fork (unratified-extensions section above), which the owner
  adjudicates rule-then-pairs before the queue and before the resample.

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

**Batch 3 (slots 100–149, eg-0142..eg-0191; 7 skips, all `value-swap` on
non-single-valued slots):**

- slot 103, `ad6f7451…` (CAUSES): an effect can have several contributing
  causes; neither slot single-valued. Authored as eg-0145.
- slot 104, `702b3d82…` (RELATED_TO): multi-valued by nature. eg-0146.
- slot 107, `08cf924b…` (USES): generic USES object. eg-0149.
- slot 122, `c2cff8f6…` (RELATED_TO): multi-valued by nature. eg-0164.
- slot 133, `6c47ab46…` (DEPENDS_ON): generic dependency object admits
  many values. eg-0175.
- slot 134, `11606722…` (RELATED_TO): multi-valued by nature. eg-0176.
- slot 139, `a02af11e…` (DEPLOYED_ON): the subject names a bare product,
  not a single instance, and the harvest itself mints redis on two hosts
  — the host slot is not single-valued for it. eg-0181.

**Batch 4 (slots 150–170 + the 29 temporal pairs, eg-0192..eg-0241;
3 skips, all `value-swap`):**

- slot 151, `8b0af751…` (DEPLOYED_ON): bare-product subject, host slot
  not single-valued. Authored as eg-0193.
- slot 160, `a8abee19…` (USES): generic USES object. eg-0202.
- slot 166, `702b3d82…` (RELATED_TO): multi-valued by nature, same fact
  and ground as batch 3's slot 104. eg-0208.

**Authoring round closed 2026-08-03:** 241 live pairs, `l2-fact`
153/241 (63.5%, target ≥ 130 met with 23 of the 41-skip margin unused;
18 skips total, every one logged above), slice counts exactly the frozen
targets plus T2.25's seed, every non-temporal slice carrying live
`l2-fact` pairs, all 200 new pairs `label_source: "author"` pending the
Step-5 blind passes.
