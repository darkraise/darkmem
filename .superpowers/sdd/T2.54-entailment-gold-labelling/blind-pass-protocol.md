# T2.54 blind labelling protocol (both passes, all batches)

You are one of two independent blind labellers for the claim/fact
entailment gold set. You receive pairs as `{id, premise, hypothesis}` and
return a three-way verdict for each, decided ONLY by the rules below.

**Blindness is the instrument.** You must not see the recorded labels,
the other labeller's output, or any other batch's output. Therefore:
**read no file in the repository at all** — your batch brief is fully
self-contained (this protocol is embedded in it by reference; the rules
below are the complete rulebook). Do not open `gold.json`, `LABELLING.md`,
any manifest, any docs, any code. Do not run commands other than writing
your output file. Call no model API; your environment is keyless.

## The three verdicts

- **`entailed`** — a competent reader who accepts the premise as true must
  accept the hypothesis as true. Semantic entailment, not lexical overlap
  and not plausibility.
- **`contradicted`** — accepting the premise requires rejecting the
  hypothesis: the premise asserts (directly, or via a rule below) the
  negation of something the hypothesis asserts.
- **`unsupported`** — neither of the above. The premise is compatible with
  the hypothesis but does not establish it.

## General decision procedure

1. **Score the whole hypothesis.** A claim is entailed only if *all* of it
   is entailed. A conjunction with one supported and one unsupported
   conjunct is `unsupported` — partial credit does not exist.
2. **Use only the premise.** Your domain knowledge, what is "obviously
   true" of homelabs, and what other pairs say are all inadmissible. Some
   hypotheses are true in the wider corpus world but unsupported by their
   premise — score against the premise alone.
3. **Entailment tolerates rewording, never strengthening.** Synonyms,
   voice, clause order, dropping content (weakening) preserve entailment.
   Adding content, tightening a quantifier, upgrading "a factor" to "the
   cause" break it.
4. **Contradiction requires exclusion, not absence.** If the premise
   merely fails to mention what the hypothesis asserts, that is
   `unsupported`. It is `contradicted` only when the premise (with the
   named rules below) excludes it.

## Edge rulings — cite these by name

- **Exclusive-slot rule.** A fact stating a single-valued configuration
  slot — a port, a version of one named instance, a scrape interval, the
  bucket holding a state file, a token lifetime, the kind a named
  instance is, the host a single named instance runs on — states *the*
  operative value. A hypothesis giving a different value for the same
  slot is **contradicted**, not unsupported, even with no surface
  negation. When the slot is genuinely multi-valued (a host running
  several services, a service using many things), the rule does not
  apply and a differing value is `unsupported`.
- **Window rule.** A temporal fact renders its validity window in text. A
  claim time-scoped inside the window is `entailed`; a present-tense
  claim over a window the fact *explicitly closes* — named end event or
  successor — is `contradicted`.
- **Open-window rule.** A fact valid "since X" with no closing event
  entails the same state at any later reference date.
- **Evaluation-time rule.** A hypothesis anchored to "currently"/"now" is
  decidable only if the premise fixes the state at an open or explicitly
  closed window. If its truth depends on an evaluation date the premise
  does not contain (a 90-day certificate and an unanchored "currently"),
  the verdict is `unsupported`.
- **Implicature-is-not-contradiction rule.** "Was frozen during Q1"
  *implicates* the freeze ended but does not assert it. Conversational
  implicature never upgrades `unsupported` to `contradicted`. Only
  asserted content and the rules here count as exclusion.
- **Reversal rule.** A hypothesis reversing an asymmetric relation is
  `contradicted` when one event or slot cannot carry both directions, or
  when the premise negates the reverse explicitly. It is `unsupported`
  when the reverse is merely unasserted and not excluded. The per-relation
  classification below is fixed; apply it, do not re-litigate it.

## Reversal-exclusivity, per relation

When a hypothesis reverses the premise's relation, the verdict is fixed
by the relation's semantics (unless the premise explicitly negates the
reverse, which always contradicts):

| relation family | reversed claim |
|---|---|
| uses | unsupported (mutual use coherent) |
| depends on | unsupported (circular dependency possible) |
| has part / contains | contradicted (proper parthood antisymmetric) |
| implements | contradicted (spec vs implementation roles cannot swap) |
| extends | contradicted (strict order) |
| replaces | contradicted (one replacement event cannot run both ways) |
| improves on | contradicted (improvement ordering cannot be mutual) |
| is a (kind/instance) | contradicted (antisymmetric for distinct terms) |
| deployed on / hosted on | contradicted (host and guest cannot swap) |
| causes | unsupported (feedback between phenomena coherent) |
| authored by | contradicted (a work's author cannot be authored by it) |
| happened on | contradicted (occurrent and its date/place cannot swap) |
| mentions | unsupported (mutual mention coherent) |
| cites | unsupported (mutual citation coherent) |
| inspired by | unsupported (mutual inspiration not excluded) |
| related to | the reversal is entailed (symmetric relation) |

## Premise register

Many premises are terse lowercase clauses ("grafana uses nginx"). That is
their real shape; treat them as full assertions. A hypothesis's casing
differences never matter to your verdict — only content does.

## Output

Write exactly one JSON file at the path your batch brief names: a list of
`{"id": "...", "verdict": "entailed|contradicted|unsupported",
"rule": "<the rule you decided under, by name, or 'general' with the
procedure step>"}` — one entry per pair in your batch, every id covered,
no extra ids. Then reply with one line: how many pairs you labelled and
your verdict counts. Do not report or discuss individual verdicts in your
reply text.
