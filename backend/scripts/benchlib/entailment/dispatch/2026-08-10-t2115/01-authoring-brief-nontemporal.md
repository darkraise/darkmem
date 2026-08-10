# Authoring brief — entailment gold, round 3, non-temporal slots

You are authoring labelled entailment pairs for a measurement gold set. Work only
from the sources this brief allows.

## The allowlist — these are the ONLY things you may read

1. This brief.
2. `/root/repositories/darkmem/backend/scripts/benchlib/entailment/LABELLING.md`,
   **everything above the line `## History`**. That is the rulebook: the three
   verdicts, the decision procedure, the edge rulings, the eight slices, the
   provenance rules, the anchor contract and the reversal-exclusivity table.
3. `/tmp/claude-0/-root-repositories-darkmem/47891992-c807-4f74-99df-a0a67a1d10ec/scratchpad/round3-assignment.json`
   — your 57 slots.
4. `/root/repositories/darkmem/backend/scripts/benchlib/entailment/gold.json`
   — **for pair shape and style only.** Read a few pairs to match the JSON
   schema and the register of the rationales. Do not read it looking for
   patterns in which pairs are "hard".

**You may read nothing else in the repository.** Specifically and non-exhaustively
forbidden: `docs/planning/gate-ledger.md`, anything under `docs/eval/`,
`docs/planning/reviews/`, `docs/superpowers/plans/`, `entailment/resample_runs/`,
`progress.md`, task files, and `git log`. Do not run `git` at all.

**Why.** These pairs measure an LLM judge. Documents in this repository record
*which kinds of pair that judge currently gets wrong*. An author who has read
them cannot help but write toward or away from the known weakness, and the
resulting set would measure nothing. If you have already read any forbidden path
in this session, stop and say so — the round restarts rather than ships an aimed
census. This is not a formality; it is the reason the round exists in this shape.

## What to produce

57 pairs, one per slot in the assignment file, written to
`/tmp/claude-0/-root-repositories-darkmem/47891992-c807-4f74-99df-a0a67a1d10ec/scratchpad/round3-pairs.json`
as a JSON list.

Each slot names a `slice`. For slots with `premise_source: "l2-fact"`, the
`fact` field **is** your premise — use it byte-for-byte, and carry the
`triple_key` through as the pair's `fact_key` with `provenance: "l2-fact"`.
For slots with `premise_source: "hand-authored (harvest capacity exhausted)"`,
write your own premise in the same register and use
`provenance: "hand-authored-synthetic-fact"` with no `fact_key`.

Pair shape (match `gold.json`'s live pairs exactly):

```json
{
  "id": "eg-0352",
  "premise": "...",
  "hypothesis": "...",
  "verdict": "entailed | unsupported | contradicted",
  "slice_tags": ["<the slot's slice>"],
  "provenance": "l2-fact | hand-authored-synthetic-fact",
  "corpus_key": "...",
  "label_source": "author",
  "rationale": "one or two sentences citing the rule by name"
}
```

Ids run `eg-0352` upward in slot order. `label_source` is `"author"` for every
pair — two independent blind passes adjudicate them afterwards, and a pair that
does not survive two passes goes to a human, so write the rationale for a
skeptical reader rather than to persuade.

## The verdicts are properties of the construction, not judgements

`LABELLING.md`'s `SLICE_VERDICTS` fixes which verdicts each slice may carry:

| slice | lawful verdicts |
|---|---|
| verbatim, paraphrase, weakening | `entailed` only |
| value-swap | `contradicted` only |
| unrelated | `unsupported` only |
| direction, overreach | `contradicted` or `unsupported` |
| temporal | any (**not in this batch**) |

For `direction`, which of the two applies is decided by the
**reversal-exclusivity table** in the rulebook against the slot's `rel_type` —
not by preference. A `direction` slot on a **symmetric** relation is a known
infeasible shape: **skip it**, record the reason, and author it instead with a
hand-authored premise for the same slice (the rulebook's own skip mechanism —
slice targets stay exact and only the `l2-fact` count moves).

For `value-swap`, a slot whose swapped slot is not single-valued is likewise
infeasible: skip and hand-author for the same slice.

**Record every skip** in a `skips` list in your output file: slot number, the
assigned `triple_key`, and the reason. Skips are visible, never silent.

## What to report back

- the 57 pairs written to the output path;
- the `skips` list;
- **the `direction` verdict split** — how many came out `contradicted` under the
  reversal-exclusivity table and how many `unsupported`. This is load-bearing:
  a second batch of 9 hand-authored `temporal` pairs is sized from your split to
  land the contradicted census on an exact figure, so report it precisely.

## Quality bar

These pairs are a measurement instrument. Write them so a careful human labeller
who has never seen your reasoning would independently assign the same verdict
from the rulebook alone. Where a pair is near the boundary between two verdicts,
prefer the construction that the rulebook decides cleanly, and say in the
rationale which rule decides it.
