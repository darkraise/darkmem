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
   conjunct is `unsupported` — partial credit is a scorer policy
   decision that belongs to T2.26, not a labelling one.
2. **Use only the premise.** The corpus world, the labeller's domain
   knowledge, and what is "obviously true" of homelabs are all
   inadmissible. Several pairs are deliberately built so the hypothesis is
   *true in the corpus world* but unsupported by this premise: a judge that scores plausibility instead of
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
  contain a negation. This mirrors the production veto's
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
- **Additional-value rule**. The exclusive-slot rule above is written for a *differing*
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
  CI matrix testing Python 3.12 may well also test 3.11, a host
  runs several services, a person holds several roles.

  Ask *"could both values hold at once without making the premise false?"*
  If yes, `unsupported`. If no, `contradicted`. This is the same question
  the exclusive-slot rule already asks about a differing value; the ruling
  is that adding does not escape it, not that adding is a new kind of thing.

- **Exhaustivity rule**. Procedure 3 breaks entailment on strengthening, and exhaustivity
  is strengthening only when the hypothesis **asserts** it.
  - Exhaustivity carried by **information structure** — a cleft or
    pseudo-cleft ("X is what causes Y", "X is why Y"), focus, or a definite
    predicate nominal ("X is the replacement for Y") — is presupposed and
    defeasible, not asserted. It does **not** break entailment.
  - Exhaustivity carried **lexically** — "only", "sole", "alone", "every",
    "all" — is asserted content and does.
  - Independently of how it is carried, exhaustivity that clashes with a
    premise **explicitly marking** non-exhaustivity ("one contributing
    factor", "some hosts") strengthens. This is the case
    procedure 3's own "a factor" → "the cause" example is calibrated on.

  A bare relation rendering (`X causes Y`) marks exhaustivity neither way,
  so it neither licenses nor blocks on its own. This is the entailment-side
  counterpart of the implicature-is-not-contradiction rule below:
  non-asserted content does not move a verdict in **either** direction.
- **Window rule.** A temporal fact renders its validity window in text. A
  claim time-scoped inside the window is `entailed`; a
  present-tense claim over a window the fact *explicitly closes* — named
  end event or successor — is `contradicted`.
- **Inception-window rule**. The window rule fixes a window's *closing* boundary and the
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

  **The backward direction — "until X".** The two bullets above are written for "since X" and decide
  claims about the *new* state. The mirror case is a premise that renders
  the **old** state's close — "pushed to Docker Hub **until** the 22 January
  2026 move; since that date, Harbor" — against a claim putting the **old**
  state at an earlier date. **"Until X" fixes the window's close and asserts
  no start**, so a claim dated before X is `unsupported` unless the premise
  also fixes when the state began. Absence of a start is not establishment
  of one, by the same procedure 4 the bullets above rest on.

  This was ruled against the recorded label. a cited example cited the
  predecessor-named bullet for `entailed`, but that bullet licenses
  `contradicted` for the **new** state placed early — a different inference
  from `entailed` for the **old** state placed early, and the file already
  records that bullet as governing no live pair, "written because the
  question needed deciding, not because a pair needs it". Both blind passes
  reached `unsupported` independently and both said they were extending the
  rule in mirror image rather than citing it, which is what an unruled
  direction looks like from outside.

  The asymmetry is deliberate and is the one procedure 4 draws everywhere
  else: a premise earns a `contradicted` only by asserting the thing the
  hypothesis denies. An inception date alone asserts a beginning, not a
  prior absence.

- **Open-window rule.** A fact valid "since X" with no closing event
  entails the same state at any later reference date. This is
  the convention the production veto needs: `knowledge_triples` rows with
  `invalid_at` NULL are current.
- **Evaluation-time rule.** A hypothesis anchored to "currently"/"now" is
  decidable only if the premise fixes the state at an open or explicitly
  closed window. If its truth depends on an evaluation date the premise
  does not contain (a 90-day certificate and an unanchored "currently"),
  the verdict is `unsupported`.
- **Implicature-is-not-contradiction rule.** "Was frozen during Q1"
  *implicates* the freeze ended but does not assert it. Conversational
  implicature never upgrades `unsupported` to `contradicted`.
  Only asserted content and the rules above count as exclusion.
- **Reversal rule.** A hypothesis reversing an asymmetric relation is
  `contradicted` when one event or slot cannot carry both directions —
  replacement, a migration's from/to — or when the
  premise negates the reverse explicitly. It is `unsupported`
  when the reverse is merely unasserted and not excluded: dependency,
  load-balancing roles.

- **Frame rule**. A
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
    its witness is in the premise.
  - A **proper-subset frame** — a named deployment, cluster, tier, or any
    phrase some entities of the premise's world could fail to satisfy —
    is asserted content, because it sits in the restrictor of the
    asserted existential; a definite article does not shelter it. The
    exhaustivity rule protects *presupposed* content, and the definite's
    existence presupposition is indeed not asserted — but the witness's
    membership in the frame is not presupposed by anything; it is the
    existential's own restrictor. Membership must be established **by the
    premise**; lexical resemblance between witness and frame is world knowledge and
    inadmissible under procedure 2. Unestablished membership makes the
    pair `unsupported` — never `contradicted`: absence is not exclusion
    (procedure 4).
  - The test: *could an entity of the premise's world fail to be in the
    frame without any further fact being false?* If no — the frame is the
    world — it is vacuous. If yes, it differentiates and must be earned.

- **Dependency-strength rule**. The reversal table classifies `DEPENDS_ON`
  without stating its forward strength; this rule states it.
  `DEPENDS_ON` asserts a **generic requirement for intended operation**:
  X needs Y for X to work as intended. It fixes no timing, no failure
  mode, and no condition on Y.
  - Renderings at the same generic level are paraphrase and `entailed`:
    "needs Y in order to run", "requires Y to function", "relies on Y". "Run" and "function" are read here at the
    relation's own generic level — "operate as intended" — never as a
    claim about process start-up.
  - Renderings that fix *when* the need bites (start-up versus first
    use), *how* absence manifests (cannot start, crashes, degrades), or
    *which condition on Y* matters (reachable, available, healthy) assert
    a failure mechanism the relation does not carry: a lazily-bound or
    degraded-mode dependency makes the premise true and the hypothesis
    false. These are `unsupported` — and
    never `contradicted` from the bare relation, by procedure 4.
  - The test: *could X depend on Y and the hypothesis still be false?* No
    for a generic requirement rendering; yes for a mechanism-specific one.
  - **Cross-relation vocabulary is decided by relation entailment, not
    synonym feel.** Rendering a premise's relation with another taxonomy
    relation's characteristic vocabulary is rewording only when the
    premise's relation semantically guarantees the hypothesis's. `USES`
    does not guarantee `DEPENDS_ON` — use without dependence is coherent
    — so necessity vocabulary ("relies on", "requires", "needs") over a
    `USES` premise is strengthening, `unsupported`. The forcing
    argument: "needs Y to function" is paraphrase-level for "relies on";
    if "uses" entailed "relies on", transitivity would make "uses" entail
    "needs Y to function", which is false on its face.

- **Bare-sortal clause**. A quantified
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
    ordinary weakening: `entailed` when its witness is in the premise.
  - A noun that **partitions** the premise's world — "service",
    "software", "database", **"machine"** — is asserted content in the
    existential's restrictor and must be established **by the premise**.
    *"Machine" was placed here by ruling on 2026-08-17, on this corpus's own evidence rather than on intuition: nine
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
    relation: `DEPLOYED_ON` makes its target a "host",
    `DEPENDS_ON` makes its object a "dependency", `HAS_PART`
    makes its part a "part" or **"constituent"**, `USES` makes its
    object a **"resource"** and its subject a **"consumer"**, `DEPENDS_ON` makes its object a **"prerequisite"** and
    the other endpoint a **"dependent"**, and `RELATED_TO` earns **"connection"** — "there is a
    connection between" its endpoints, and `DEPLOYED_ON` earns **"installation"** for
    its *subject* as well as "host" for its target — a thing deployed on
    a host cannot fail to be an installation there, where it can easily
    fail to be a "service". **Owner-ratified
    2026-08-17**, on a blind labeller's explicit request: it is the one
    placement in this clause that sits close to the counterexample, since
    "deployment does not make a thing a service" and one could read
    "installation" as implying a deliberate install process rather than a
    workload scheduled onto a node. Both blind passes reached `earned`
    independently by the clause's own test before the ruling was sought,
    so the ratification confirms a reading rather than choosing one. `HAS_PART`'s generic
    semantics also carry the composition renderings of that role, so
    **"built from"** is inside it and needs no separate earning. These were placed 2026-08-17 by applying the
    branch above rather than by a fresh ruling: each names the role the
    relation itself creates, so the relation cannot hold while the slot
    filler fails the noun.

    **The clause reaches predicate nominals, not only existentials.**
    "Y **is a** software/service/machine that X uses" asserts the same
    partitioning kind as "at least one service", and the first sweep for
    this class matched only quantified forms — which is how a cited example
    ("Concourse is **a piece of software** that log-02 makes use of")
    survived the round that retired a cited example for the identical sortal. A
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
  like an explicit one. `DEPENDS_ON` earns "X has a dependency"; `DEPLOYED_ON` earns "X has a component deployed on it",
  because deployment on X places the subject in X's hosted stack; **nothing earns** "X has a component that depends on it" —
  a dependent of X is not thereby a component *of* X.

  **Referential-definite clause**. A partitioning sortal riding attributively inside a definite
  that *names* an entity — "the data-06 **machine**", "the auth-01
  **service**" — is **asserted content**, not presupposed, and must be
  earned exactly as it would be in an existential's restrictor. This is a
  **third surface shape**, after quantified restrictors and predicate
  nominals, and it was ruled against the opposite reading: a sortal in a
  referring expression patterns presupposition-wise with the exhaustivity
  rule's protected class, and the Frame rule's "a definite article does not
  shelter it" was argued from an asserted existential. The owner ruled the
  Frame rule's reach controlling. **Scan all three shapes; a shape-scoped
  sweep is how this class survived three rounds**.

  **Instance-hood default**. The
  exclusive-slot rule's "a single named instance" has a stated test at
  last: **any entity the harvest names is a single named instance**,
  including plural or phenomenon-like subjects ("alert storms"). A
  labeller never has to decide instance-versus-product from the premise,
  which they could not do without harvest evidence procedure 2 bars.

  **Durative adverbials**. "Paused
  **for the duration of** X" **asserts** coextension with X, unlike
  "during", which merely locates within it. A hypothesis putting the state
  past X's close is `contradicted`, not `unsupported`.

  **Engagement and invocation vocabulary**. `USES` does **not** earn "interacts with" —
  interaction connotes bidirectional exchange a passive-resource use does
  not carry — and does **not** earn "calls on ... to do its work", which
  fixes an invocation mechanism the relation leaves open. Both are
  `unsupported` over a bare `USES` premise. **"backend"** (as in "storage backend") and
  **"datastore"** are likewise **partitioning**, not earned: they sit
  between "resource" and "database" and the ruling puts them on the
  partitioning side. The head noun is what is ruled on — a guard scans
  words, so naming only the compound would leave the head unplaced.

  **The bound on both clauses, recorded rather than smoothed over.**
  a cited example ("idx-03 hosts at least one deployed service") and a cited example
  ("At least one service is deployed on spire-01") are semantically
  equivalent — same relation, same sortal — and **both measured
  instruments split them the same way**, accepting the first and
  rejecting the second. No rule can match both members, so the clause
  above rules both `unsupported` and the gold carries the correction on
  both. At this boundary the instruments are surface-form sensitive; the
  repetition study on a cited example (3 `entailed` / 2 `unsupported` on
  identical input, same seed) is the independent confirmation.

## Reversal-exclusivity, pre-classified for every relation

Decided per relation from its **semantics alone** — before any pair
existed — so a `direction` pair's verdict falls out mechanically from
which relation the seeded assignment handed its author, never from a
per-pair judgment call. **Exclusive** means one pair of endpoints cannot
carry both directions at once, so the reversed claim is `contradicted`
(reversal rule, exclusive case); **non-exclusive** means the reverse is
possible alongside the fact, so the reversed claim is `unsupported` —
unless the premise itself negates the reverse explicitly, which
always contradicts. **Symmetric** relations are ineligible for `direction`
pairs: the reversal is entailed, and the slice admits no such verdict.

| relation | class | reversed-claim verdict | why |
|---|---|---|---|
| `USES` | non-exclusive | unsupported | mutual use is coherent (two services calling each other) |
| `DEPENDS_ON` | non-exclusive | unsupported | circular dependency is not excluded by meaning |
| `HAS_PART` | exclusive | contradicted | proper parthood is antisymmetric: a part cannot contain its whole |
| `IMPLEMENTS` | exclusive | contradicted | spec and implementation are incompatible roles for one ordered pair |
| `EXTENDS` | exclusive | contradicted | extension is a strict order; mutual extension is incoherent |
| `REPLACES` | exclusive | contradicted | one replacement event cannot run both ways |
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