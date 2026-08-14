# T2.124 step 9 — the independence and freshness pass, as executed

Run 2026-08-14 by the step-9 controller, a party outside the step-7/8 authoring
lineage. Split deliberately in two, because the two halves have different
authority:

- **Mechanical checks** — run by the controller, reproducible by anyone from
  `benchlib/run_step9_independence.py`. They compute; they do not judge.
- **Adjudication** — run by two independent blind parties, because deciding
  whether two hypotheses assert one proposition is judgement, and the party
  that runs a census does not certify it.

| File | What it is |
|---|---|
| `01-brief.md` | The adjudication brief, verbatim as both parties received it |
| `02-cases.json` | The 24 cases, verbatim as both parties received them |
| `03-verdicts-adjudicator-1.json` | Adjudicator 1's returned verdicts and attestation |
| `04-verdicts-adjudicator-2.json` | Adjudicator 2's returned verdicts and attestation |
| `05-mechanical-pass.json` | The mechanical pass's raw output |

## The mechanical half: four gates, all clean, and one of them is not evidence

Zero retired-pair byte overlap, zero within-class duplicates at the committed
0.85, zero cross-gold near overlap, zero cross-verdict near pairs.

**The duplicate gate's zero is not a duplicate-free census.** Both it and
`census_independence` score hypotheses by content-token Jaccard, which sees
lexical overlap and not entailment. Measured on this census: the three
duplicates the authoring lineage recorded *by reading* score 0.8333, 0.3333 and
0.2857 — none caught at 0.85 — and the ruled-lawful pair `eg-0486`/`eg-0614`
scores 0.2857, exactly equal to the recorded duplicate `eg-0425`/`eg-0559`. The
two populations interleave completely, so no threshold separates them and the
gate cannot be repaired by moving its number.

So the mechanical pass also reports the **candidate population**: every live
pair sharing a byte-identical premise and verdict, the only place a
same-proposition duplicate can occur. 24 pairs — 16 entailed, 7 unsupported, 1
contradicted — which is the denominator the adjudication worked through
exhaustively.

## The adjudication: parties and blindness

Two fresh headless CLI sessions (`claude -p`, model `opus`), each from its own
bare directory outside the repository containing only the brief, the rulebook
strip and the cases, with an empty MCP config and tools limited to Read/Write.
The same mechanism the step-7 authors were dispatched under, and for the same
measured reason: a sub-agent launched through the session's Agent tool receives
the project instructions, which carry judge results.

A probe from such a directory confirmed it before dispatch: no project
instructions, no repository context, no judge measurement, no model identifier
described as measured against a bar. **Residual, recorded rather than
glossed:** the user-level global instruction file *is* present in that context.
It was read and carries no evaluation score, no bar and no judge result — but it
is not nothing, and the blindness claim here is "no project context and no
measured result", not "an empty context".

The rulebook strip is the byte-prefix of `LABELLING.md` above `## History`,
46477 bytes, sha256 `de26555369fcbb5b8a2a23f59664c184ea92dfe76acc3093bfca2e40298141f5`
— byte-identical to the strip the step-7 authors received.

The contamination screen ran over the brief and the cases before dispatch: all
eight patterns, zero hits on both. **That is the check that matters here** — the
brief and the cases are the entire blind read-set, and they are clean.

**This README is not blind-party material and it does fire the screen. Enumerated
rather than waved through**, on the same principle as the ledger's strip
baseline: a reviewer must be able to tell a leak from a known residual.

| Line | Hit | What it is |
|---|---|---|
| 3 | `step-7/8` | A step reference the ratio pattern reads as a fraction |
| 24, 30 | `0.85` | The committed Jaccard threshold |
| 29–31 | `0.8333`, `0.3333`, `0.2857` | Hypothesis-similarity scores from this pass |
| 77–78 | `3/3`, `2/2` | Control-recovery counts |
| 90 | `18/24` | Inter-adjudicator agreement |
| 94 | `0.95`, `80` | The stated contradiction bar and census arithmetic |

**None is a measured judge result.** The similarity scores come from
`duplicate_propositions`, which reads pair text only — its own docstring records
that nothing it reports can be a function of how any model performed — and the
rest are the committed threshold, this pass's own agreement counts, and a bar
plus census arithmetic, which the ledger's baseline already records as the
sanctioned residual category. A hit here outside this table is a finding.

**Neither adjudicator was told which cases were expected to be duplicates**, and
both attested to it. Case order is a seeded shuffle keyed on the gold's own
content hash, so presentation order carries no signal from the controller's
similarity ranking.

## The control set, and why the result is trustworthy

Five of the 24 cases carry a previously recorded label: three duplicates found
by the authoring lineage (`eg-0424`/`eg-0558`, `eg-0425`/`eg-0559`,
`eg-0463`/`eg-0590`) and two pairs the owner ruled **lawful**
(`eg-0465`/`eg-0592`, `eg-0486`/`eg-0614`). They were not marked in the brief.

**Both adjudicators recovered all five, independently: 3/3 duplicates called
DUPLICATE, 2/2 lawful called DISTINCT.** That is the instrument validating
itself on positive and negative controls before its unlabelled verdicts are
read.

## Result

- **8 unanimous duplicates** — the 3 recorded, plus `eg-0418`/`eg-0554`,
  `eg-0422`/`eg-0556`, `eg-0423`/`eg-0557`, `eg-0427`/`eg-0561`,
  `eg-0504`/`eg-0634`.
- **6 contested** (adjudicator 1 DUPLICATE, adjudicator 2 DISTINCT), all at
  medium confidence on both sides.
- **10 unanimous distinct**, including both lawful controls.
- Raw agreement 18/24.

**Every duplicate and every contested case is in the `entailed` class.** All 7
unsupported and the 1 contradicted candidate were called DISTINCT unanimously,
so the contradicted census — the one carrying the 0.95 bar — is 80 rows over 80
independent propositions, confirmed rather than assumed.

The 6 contested cases are not noise: both parties identified the *same* single
question and applied it consistently. In each, one hypothesis is the specific
restatement and the other existentially generalises one of its slots, so one
entails the other. Adjudicator 1 reads a pure weakening as the same
proposition; adjudicator 2 reads the named entity as content the generalisation
drops.

**The owner's two lawful rulings turn on a distinction none of the six share.**
Both lawful pairs generalise **opposite** slots — one drops the subject, the
other drops the object — so neither entails the other. In all six contested
cases the generalisation runs one way only. Whether that distinction is the
governing rule is the owner's to say; it is recorded here because the precedent
already exists and points at these cases.

## What this pass does not decide

Whether any finding loops back to step 7's re-author path, and whether the
remedy is slot repairs or a frame fix. The root cause sits upstream in step 5's
premise exclusion, which covers direction and verbatim reuse but not
paraphrase-entailed reuse. That is an owner decision and is deliberately not
taken here.
