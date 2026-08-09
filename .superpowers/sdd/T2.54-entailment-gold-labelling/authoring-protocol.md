# T2.54 pair-authoring protocol (shared by all four batches)

You are authoring new pairs for the claim/fact entailment gold set. This
file plus your batch brief is your complete task context.

## What you may read, and nothing else

- `backend/scripts/benchlib/entailment/LABELLING.md` — the labelling
  rules and the frozen T2.54 composition. **This is the authority.** Read
  it in full before writing any pair, and label only against its decision
  procedures and edge rulings, citing rules by name.
- `backend/scripts/benchlib/entailment/gold.json` — the existing pairs,
  for style and to avoid duplicate (premise, hypothesis) texts.
- `backend/scripts/benchlib/entailment/l2_harvest.json` — the harvest
  manifest your assigned premises come from (your batch brief already
  embeds the rows you need).
- Your batch brief and its embedded assignment listing.

Do **not** read anything else in this repository — no `docs/`, no other
`scripts/`, no planning or evaluation material, no application code. Do
not run tests, do not call any model API, do not export any credential.
Your environment is deliberately keyless. Write your output file and stop.

## The pair contract

Every pair you author is one JSON object:

```json
{
  "id": "<assigned in the listing — use it verbatim>",
  "premise": "<see premise rules>",
  "hypothesis": "<an article-style claim sentence>",
  "verdict": "entailed | contradicted | unsupported",
  "slice_tags": ["<the assigned slice>"],
  "provenance": "l2-fact | hand-authored-synthetic-fact",
  "label_source": "author",
  "rationale": "<the rule you decided under, cited by name>"
}
```

`l2-fact` pairs additionally carry the `fact_key` object **byte-for-byte
as given in your listing**, and their `premise` must be the listing's
`premise` string **byte-for-byte** — never re-cased, never punctuated,
never "improved". The loader refuses anything else.

## Premise rules

- A slot with a `fact_key` is an `l2-fact` slot: premise = the minted
  fact text verbatim. These premises are terse lowercase clauses
  ("grafana uses nginx") — that is the real production shape; do not
  dress them up.
- A slot you **skip** (rules below), and every `temporal` slot, takes a
  hand-authored premise: `provenance: "hand-authored-synthetic-fact"`, no
  `fact_key`, premise written by you — one or two sentences, realistic
  for a homelab/infrastructure domain, in the style of the existing
  hand-authored pairs.

## Skip rules (log every skip; never skip silently)

Skip an assigned (premise, slice) combination **only** when the
construction is infeasible under LABELLING.md, and record
`{"slot", "slice", "triple_key", "reason"}` in your output's `skips`
list. The named infeasible shapes:

- a `direction` slot whose relation is symmetric (`RELATED_TO`) — the
  reversal is entailed and the slice admits no such verdict;
- a `value-swap` slot whose swappable slot is **not** single-valued —
  `value-swap` verdicts are fixed `contradicted` by the exclusive-slot
  rule, and a multi-valued slot (a service can *use* many things) only
  yields `unsupported`. Judge single-valuedness from the relation and the
  named entities alone (an `IS_A` kind, a single named instance's host,
  the one thing a named migration replaced — usually single-valued; a
  generic `USES`/`DEPENDS_ON`/`RELATED_TO` object — usually not).
- anything else genuinely unconstructible — with the reason spelled out.

A skipped slot still produces a pair: same id, same slice, hand-authored
premise built so the slice's construction works.

## Verdict discipline (mechanical where the freeze made it mechanical)

- `verbatim`, `paraphrase`, `weakening` → `entailed`. Premise and
  hypothesis must not be string-identical.
- `value-swap` → `contradicted`, exclusive-slot rule cited.
- `unrelated` → `unsupported`.
- `direction` → exactly the verdict the reversal-exclusivity table in
  LABELLING.md fixes for the relation. Do not re-litigate the table.
- `overreach` → almost always `unsupported`; `contradicted` only when the
  strengthening crosses an exclusion (cite which).
- `temporal` → any verdict, decided by the window / open-window /
  evaluation-time / implicature rules. Across your temporal slots, cover
  all three verdicts and all four rule shapes.

## Quality bar

- Near-misses are the point: maximise surface overlap on `value-swap`,
  `overreach`, `direction`; prefer corpus-plausible swap values; author
  weakening/overreach mirror pairs from the same material where natural.
- Every rationale cites its rule by name (e.g. "exclusive-slot rule",
  "reversal rule, non-exclusive case", "open-window rule").
- No duplicate (premise, hypothesis) text pair anywhere in the gold —
  when the same premise appears in several of your slots (it will), the
  hypotheses must differ; check `gold.json` and your own batch.
- Hypotheses are single claim sentences in article register — the kind a
  synthesis draft would emit.

## Output

Write exactly one JSON file at the path your batch brief names:

```json
{"pairs": [ ...50 pair objects, in id order... ],
 "skips": [ ...skip log entries, possibly empty... ]}
```

Then reply with a two-line summary (pairs written, skips). Do not edit
`gold.json` or any other repository file.
