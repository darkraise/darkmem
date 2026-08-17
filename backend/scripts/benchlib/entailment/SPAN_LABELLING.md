# Claim/span gold — labelling rules (TH1.01 §5, doc 16 §4, doc 17 §6)

**Status: DRAFT, awaiting owner ratification. No pair may be authored against
it until then.** Rule-then-pairs is the whole discipline here: T2.124 spent most
of its length discovering that a rule written to settle a pair already in front
of you is a *fitted* rule, and the ordering is what stops that. Every rule below
was written before a single claim/span pair existed — the premise pool
(`span_harvest.json`, 800 blocks over 6 documents) exists, and nothing else does.

**This is a sibling of `LABELLING.md`, never a replacement and never merged into
it.** That file governs the claim/**fact** gold, whose premises are L2 fact text
and whose verdicts are three. This one governs claim/**span**, whose premises are
document bytes and whose verdicts are two. Where a rule transfers it is cited
rather than restated; where it does not, the difference is stated with its reason.

## What a pair is

A pair is `(premise_spans, hypothesis, verdict)` plus its slice, provenance and
rationale.

- **The hypothesis is one answer sentence.** The claim unit is the sentence
  because TH1.08's generation contract is per-sentence citation, so the
  citation-bearing unit is the counting unit. **No sub-sentence splitting** — a
  splitter that fragments a conjunction manufactures denominators.
- **The premise is the cited span set, verbatim.** An ordered list of one or more
  anchored spans; the premise is the concatenation of exactly those span bytes,
  joined by a blank line, in the order given. Nothing else.
- **An anchor names a harvested block and indexes into that block's own text,
  from 0.** `{document_uri, block_key, text_sha256, char_span}` resolving as
  `manifest_block.text[start:end]`. That is byte-for-byte what
  `app/services/faithfulness_gate.py::_entails` slices at serving time, and the
  match is deliberate: a judge qualified on premises production never constructs
  is qualified on a different task than the one it licenses. **Never** use a
  block's `source_char_span` — that is where the block sits in the source file,
  exported for traceability only.

## The two verdicts, and why there is no third

`entailed` | `not-entailed`.

The claim/fact gold keeps three because the contradiction role is qualified from
the same file. **Here there is no `contradicted`**, and this is a design decision
rather than an omission: no consumer makes a contradiction discrimination over
spans, so a `contradicted` census would mint numbers no role's gate reads — the
orphaned-bar shape. `grounded ⇔ entailed`; the faithfulness consumer branches on
the `entailed` verdict alone.

**So `not-entailed` covers two different things and deliberately does not
distinguish them**: the span fails to support the claim, and the span excludes the
claim. Hard negatives (value swaps, reversals) are still authored — they are the
near-misses the gold needs — they are simply labelled `not-entailed` and carried
by their slice. The cost is stated: if a future consumer wants
contradiction-over-spans, that is a new gold or a relabelling round, never a
reinterpretation of this one.

**The judge's own vocabulary is three** (`entailed` / `unsupported` /
`contradicted`). A perfect judge on a `not-entailed` gold pair may answer either
`unsupported` or `contradicted`; the scorer collapses both to not-entailed.
Labellers record this gold's two, never the judge's three.

## General decision procedure

1. **Score the whole hypothesis.** Inherited verbatim from the claim/fact gold's
   procedure 1. A conjunction with one unsupported conjunct is `not-entailed`.
   Partial credit does not exist.
2. **Use only the cited spans.** Not the rest of the block, not the rest of the
   document, not the repository, not what you know to be true of darkmem. This is
   the strictest rule here and the one most likely to be violated by accident,
   because the sources are *our own documents* and a labeller recognises their
   content. **A hypothesis that is true of the system but unsupported by the
   cited bytes is `not-entailed`** — pairs built exactly that way are wanted, and
   a judge that scores plausibility instead of entailment must fail them.
3. **Entailment tolerates rewording, never strengthening.** Synonyms, voice,
   clause order and dropping content preserve entailment. Adding content,
   tightening a quantifier, or upgrading a hedge to an assertion breaks it.
4. **No search for support.** If the span does not support the claim, the answer
   is `not-entailed` — never "but the next block does". Doc 16 §4 bars the
   fallback explicitly, and looking for a better span is how a grounding *check*
   becomes a grounding *service*.
5. **An uncited sentence is not a pair.** Uncited is ungrounded by definition
   (doc 16 §4), decided by the runtime before the judge is consulted. Do not
   author a pair with an empty `premise_spans` to represent it.

## Edge rulings — cite these by name in every rationale

These are the span variant's own rules. The claim/fact gold's exclusive-slot,
additional-value and reversal rules **do transfer** where a span happens to state
a single-valued slot; cite them by their names there.

- **The anaphora rule.** A hypothesis whose truth rests on an antecedent outside
  the cited span is `not-entailed`, even when the antecedent is obvious and even
  when it sits in the same block. "It was designed to avoid locking" cited alone
  does not assert what *it* is. This is the judge-sees-only-the-spans rule made
  operational, and it is the `context-dependence` slice's decision procedure. A
  judge that resolves the pronoun from world plausibility fails these by design.

- **Heading scope does not travel.** A paragraph or list item cited alone does
  **not** carry the heading it sits under. If the hypothesis needs the heading's
  subject to be true, it is `not-entailed` unless the heading block is *also*
  cited. This matters more here than anywhere else: the pool is 129 headings and
  560 list items, so most content is heading-scoped, and a labeller reading the
  rendered document sees a structure the judge never receives. To make a
  heading-scoped claim entailed, cite the heading **and** the item as a two-span
  premise — which is the `multi-span-composition` slice.

- **A table row carries no header.** Commonmark mints no table block: a pipe
  table survives the parser as **one `paragraph` block containing every row**
  (verified). So a "table fragment" is a sub-block span inside that paragraph. A
  span covering one row, cited without the header row, does not carry column
  semantics — "`| 9100 | metrics |`" alone does not assert that 9100 is a *port*.
  `not-entailed` unless the span includes the header.

- **A code block asserts its text, not its behaviour.** The pool carries 13 code
  blocks. A cited code span asserts what the code *says*. A hypothesis about what
  it *does* at runtime — what it returns, that it succeeds, that it is the
  command someone should run — is `not-entailed` unless the span's own text says
  so. Cited prose around the code is a separate span.

- **An unchecked checklist item asserts a thing to verify, not a fact about the
  system.** Two of the six source documents are QA checklists and test plans, and
  `- [ ] Activity bar chart renders with hover tooltips` is **not** an assertion
  that the chart renders. It asserts that rendering-with-tooltips is to be
  checked. A hypothesis stating the system *does* the thing is `not-entailed`; a
  hypothesis stating the checklist *requires* or *lists* the thing is `entailed`
  if the bytes say so. This rule exists because the pool makes the mistake easy
  and a whole genre of pairs turns on it.

- **Procedural prose asserts the step, not its execution.** The two runbooks are
  procedures. A span saying "Run `scripts/backup.sh`" asserts that the procedure
  directs this, not that it was run, not that it succeeded, and not that it is
  the only way. A hypothesis in the perfect tense ("the backup was run") or
  asserting necessity beyond the text is `not-entailed`.

- **A span may be entailed by its own repetition of a hedge.** If the span hedges
  ("may", "should normally"), a hypothesis that keeps the hedge is `entailed`; one
  that drops it to a flat assertion is `not-entailed` (strengthening, procedure
  3). The reverse — the span asserts flatly, the hypothesis hedges — is
  `entailed`, because weakening preserves entailment.

- **Truncation is decided by the citation, never by the sentence around it.** If
  the cited span stops before the clause that would support the claim, the pair
  is `not-entailed` **even though the surrounding block plainly supports it**.
  This is the `span-truncation` slice, and it is the failure a span-anchored
  citation system uniquely invents: the citation is the reader's evidence, and
  evidence the reader cannot see by following the citation is not evidence the
  label may lean on.

- **Multi-span composition is a conjunction of premises, not of documents.**
  Spans may come from different blocks and different documents; the premise is
  their ordered concatenation. A pair is `entailed` by composition only when no
  single cited span suffices — that is the point of the slice, and it is the
  recall-side hard case for a judge that reads only the first span.

## Round-1 amendments — RATIFIED BY THE OWNER 2026-08-17, rule-then-pairs

Both blind labelling passes surfaced gaps in the rules above. Each was put to the
owner **as a rule**, ruled, and written here **before** being applied to any pair.
That ordering is the point: a rule chosen while looking at the pair it settles is
a fitted rule. Agreement before these landed was A-vs-B **0.9731** (253/260) with
**0.9500** unanimous, so these govern a contested 20 rather than the corpus.

- **The definite-description rule (RULED: strict).** A definite description in the
  hypothesis that imports an identity the cited bytes never state is **external
  antecedent resolution**, and the pair is `not-entailed`. The discriminator is
  **kind versus identity**: a pointer is licensed when the bytes *display its
  kind* — a `- [ ]` supports "the checklist", an imperative supports "the
  procedure directs" — and refused when it imports something checkable the bytes
  never show: a name ("the bundled topology", "the break-glass purge"), a
  filename, a date, a section title whose heading is not also cited.

  This is the anaphora rule extended to descriptions, and it settles the largest
  family in the round: a premise reading "The app is the network edge in this
  topology" does **not** entail a hypothesis reading "In the bundled topology the
  app is the network edge", because *which* topology is content the reader cannot
  see by following the citation. Both blind labellers reached this independently
  and overturned the author on five pairs; the ruling makes their agreement a
  rule rather than a coincidence.

  **Direction of the ruling, stated because it is a policy choice and not a
  deduction:** it withholds rather than over-accepts, which is the conservative
  side for a groundedness label.

- **The `Expected:` rule (RULED: it is a hedge).** The QA sources are full of
  `Expected: still authenticated (cookie survives reload)`. That construction is
  a **hedge**: a hypothesis that keeps the expectation ("the tester is expected to
  remain authenticated") is `entailed`; one that drops it to a flat assertion
  ("the tester remains authenticated") is strengthening and `not-entailed`. This
  is the same shape as the checklist rule one step along — an expectation, like an
  unchecked box, asserts what *should* hold, never what does.

- **The imperative rule (RULED: `must` is strengthening).** A bare imperative does
  **not** entail necessity. "Stop the application" supports "the procedure directs
  stopping it" and does **not** support "the application must be stopped". The
  procedural-prose rule's two halves pointed opposite ways; this settles them
  toward the stricter reading. **Note this overturns all three parties** — author,
  labeller A and labeller B all read `sg-0157` as entailed. Recorded plainly
  because a rule that contradicts every reader is exactly the kind that must not
  be quietly applied.

- **The scope-drop rule (RULED: dropping a scope is weakening, so it is
  `entailed`).** Where a premise states something holds "in this posture" and the
  hypothesis drops the qualifier, procedure 3 governs as written: less asserted is
  still entailed.

  **This ruling runs opposite to the conservative direction of the
  definite-description ruling above, and that tension is recorded rather than
  smoothed.** It licenses "X holds in posture P" ⊨ "X holds", so a grounded label
  can be served for a sentence broader than its citation. The owner ruled it; the
  cost is stated here so a later reader meets it as a decision rather than as an
  inconsistency they have to reconstruct.

## The slices

One slice per pair, in `slice_tags` (a list, even when it holds one). The loader
requires a non-empty list of non-blank strings but **checks no vocabulary** — a
typo makes a phantom slice of one, so the vocabulary is pinned here and the
per-slice counts must be checked against the pair count before certification.

**The four span-specific slices** (TH1.01 §5 item 4), each with its verdict
constraint:

| Slice | Verdict | Decision procedure |
|---|---|---|
| `span-truncation` | `not-entailed` | the truncation rule above |
| `context-dependence` | `not-entailed` | the anaphora rule, or heading-scope-does-not-travel |
| `multi-span-composition` | `entailed` | entailed only by the conjunction; no single span suffices |
| `structure-fragment` | mixed | decided by what the bytes alone assert — table-row, code-block and checklist rules |

**The transferable slices**, reinterpreted over document prose: `verbatim`,
`paraphrase`, `weakening` (both `entailed`), `overreach`, `value-swap`,
`unrelated` (all `not-entailed`).

**The claim/fact `temporal` slice does not transfer.** Block spans carry no
validity window; temporal material appears only as ordinary prose content.

**Near-misses are the majority** (doc 17 §6). A gold of easy pairs measures
nothing: the judge's job is the boundary, so the boundary is where the pairs sit.

## Provenance — honesty over volume

Three values, and the loader refuses any other:

- `document-span` — premise is a block the shipping parser produced, drawn from
  `span_harvest.json`. **This is the default and should be the overwhelming
  majority.** Doc 17 §6's stance is that synthetic-only entailment gold is
  rejected as unrepresentative.
- `qa-draft` — hypothesis harvested from a real TH1.08 answer rather than
  authored. Premise still `document-span`; the value records the *hypothesis*'s
  origin, which is the axis that makes the distribution real.
- `hand-authored-fixture-span` — a pair on a committed fixture rather than parser
  output. Permitted, but it must not be the gold's substance.

The reservation that held `document-span` and `qa-draft` at zero pairs was lifted
by owner ruling 2026-08-17, once TH1.02 and TH1.08 shipped their producers.

## File discipline

Inherited from the claim/fact gold and not restated in full: append-only with
declared counts; **retire in place, never delete** (`"retired": true` plus the
reason); one slice per pair; a `rationale` citing a rule **by name** from this
file, never free text; ids monotonic and never reused.

**The byte-bind.** `text_sha256` is the anchored block's text digest at authoring
time. `resolve_anchor_text` re-hashes and raises `SpanAnchorDrift` on any
mismatch, and also when the block has left the manifest — so a changed source
*or* a changed parser forces retire-and-replace rather than silently serving a
premise nobody labelled. **Do not type hashes or offsets by hand**; compute them
with a script that locates the substring inside the anchored block's text.

**Judge output is quarantined** from every author and adjudicator: `cache_span/`
and any `verdicts/` sibling. An author who has seen a judge's answer on a pair is
no longer authoring blind.

## The blind protocol

Inherited from the claim/fact gold's Ruling 3, with the same structure:

1. **Rules first.** This file, ratified, before any pair.
2. **Authoring** by separately dispatched agents, each reading only a byte-prefix
   strip of this file and its own slot assignment — no shared context, no sight
   of another author's pairs.
3. **Two independent blind labelling passes** over the authored pairs, mixed with
   already-adjudicated covers so a labeller cannot tell which pairs are the live
   questions.
4. **Escalation to the owner** on any disagreement, ruled rule-then-pairs: the
   rule is added here first, then applied to the pair.
5. **Then, and only then**, TH1.10's single measurement.

**The contamination this round cannot claim away.** `CLAUDE.md` auto-injects into
every dispatched agent's context and states measured judge scores and bar values
verbatim. Every author and labeller on T2.124 reported it and it was disclosed
rather than denied. The same holds here, and it must be disclosed per artifact.
It bounds what a clean number from this gold can mean, and no amount of dispatch
hygiene removes it.

## What this file may not be used for

- It may not be edited to settle a pair already authored. That is a fitted rule,
  and the whole ordering exists to prevent it. A new rule is ratified first, then
  applied.
- It may not relax a bar. The bars live in
  `app/services/faithfulness_bars.py` as floors and are the owner's to move with
  a recorded argument — never to make a run pass.
