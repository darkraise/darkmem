# Authoring brief — entailment gold pairs (blind round)

You are authoring labelled (premise, hypothesis, verdict) pairs for a measurement
gold set. Work only from the sources this brief allows.

## Allowlist — the ONLY things you may read

1. This prompt.
2. `./rulebook.md` — the labelling rulebook: the three verdicts, the general
   decision procedure, the edge rulings, the eight slices, the provenance rules,
   and the reversal-exclusivity table. It is the authority for every verdict;
   label against it, never from intuition about what a word suggests.
3. `./slots.json` — your slots.

**You may read nothing else, and run nothing.** You are working in a bare
directory; do not list or open any other path, relative or absolute. Specifically
forbidden: anything under `/root/repositories/` (a software repository exists on
this machine; its planning documents, evaluation reports, ledgers, dispatch
records and gold files are all off-limits), any other authoring directory, and
any use of git or shell commands. Why: these pairs measure an LLM judge, and
documents in that repository record which kinds of pair such judges currently get
wrong. An author who has read them cannot help but write toward or away from the
known weaknesses, and the resulting set would measure nothing. If you have
already read such material in this session, stop and say so instead of authoring.

## What to produce

One pair per slot in `./slots.json`, written with the Write tool to
`./pairs.json`, in this exact shape:

```json
{
  "pairs": [
    {
      "id": "the slot's id, unchanged",
      "slot": 0,
      "premise": "see the construction rules",
      "hypothesis": "your authored claim sentence",
      "verdict": "the slot's verdict, unchanged",
      "slice": "the slot's slice, unchanged",
      "rationale": "one or two sentences citing the governing rule(s) by name",
      "premise_source": "assigned OR hand-authored"
    }
  ],
  "skips": [
    { "slot": 0, "id": "eg-....", "reason": "..." }
  ],
  "attestation": "one paragraph: everything you read this session, and a confirmation that you read nothing else and ran nothing"
}
```

## Rules of construction

- **The premise is fixed.** Use the slot's `premise` byte-for-byte with
  `premise_source: "assigned"`. Never substitute a different fact and never
  reword the premise.
- **The slice and the verdict are fixed.** You construct the hypothesis so the
  slot's verdict is correct under the rulebook. You choose the wording; you never
  choose the slice or the verdict, and you never flip a verdict to fit a
  hypothesis you like.
- The hypothesis is an article-style **claim sentence** (rulebook, "What a pair
  is"). Match the premise's register and domain.
- The **rationale cites the governing rule by name** — e.g. "reversal rule,
  exclusive case", "exclusive-slot rule", "general procedure 3", "additional-value
  rule" — and says in a clause why it decides this pair.
- `direction` slots: the hypothesis states the premise's relation with the two
  entities **reversed**. The slot's `reversal_class` and the rulebook's
  reversal-exclusivity table fix the verdict; cite the table row for the
  relation.
- `value-swap` slots: identical sentence shape, one slot value swapped for a
  realistic alternative value of the same type; the exclusive-slot rule fixes the
  verdict. If the premise's swappable slot is not single-valued in the world the
  premise describes, that is a known-infeasible shape — log a skip (below).
- `overreach` slots: the hypothesis is **strictly stronger** than the premise —
  added content, tightened quantifiers, an upgraded role — and the strengthening
  must NOT cross an exclusion (no swapped values of single-valued slots, no
  second value for a single-valued slot), so that the verdict is `unsupported`
  under general procedure 4: absence, not exclusion.
- `weakening` slots: the hypothesis is **strictly weaker** — content dropped,
  values abstracted, specifics generalised. Nothing added, nothing strengthened.
- `paraphrase` slots: full rewording of the same assertion; nothing strengthened
  or weakened, no lexical anchor preserved beyond entity names.
- `verbatim` slots: near-literal restatement — reorder or change voice, at most
  trivial synonym swaps; the premise and hypothesis must not be identical
  strings.
- `unrelated` slots: the hypothesis bears on nothing the premise establishes (it
  may share an entity name); verdict `unsupported`.
- Slots carrying a `shared_note`: another slot elsewhere uses the same premise
  with the same verdict. Build your hypothesis on a **different element, endpoint
  or value** than the most direct construction, so the two slots do not assert
  the same proposition however differently worded.
- Every pair stands alone: decide it against its own premise only, per the
  general decision procedure.
- Do not reuse the rulebook's own worked example sentences or their subject
  matter as material; they are citations, not templates.

## Skips — visible, never silent

Only the rulebook's known-infeasible shapes justify a skip. Log it in `skips`
with the concrete reason, then author the SAME slot with a **hand-authored
premise of your own** (same slice, same verdict), marking
`premise_source: "hand-authored"` — a realistic fact-style sentence in the same
register and domain as the assigned premises, invented by you, copied from
nowhere. If even a hand-authored premise cannot lawfully realise the slot's
slice and verdict, leave the slot as a skip with no pair and say why.

## Finish

Write `./pairs.json`. Then reply with: the count of pairs authored, every skip
with its slot and reason, and your attestation paragraph.
