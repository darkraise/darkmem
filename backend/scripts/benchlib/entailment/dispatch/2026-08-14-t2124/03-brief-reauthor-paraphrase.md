# Re-authoring brief — one entailment gold pair (blind round)

You are re-authoring a single labelled (premise, hypothesis, verdict) pair for a
measurement gold set. Work only from the sources this brief allows.

## Allowlist — the ONLY things you may read

1. This prompt.
2. `./rulebook.md` — the labelling rulebook. It is the authority for every
   verdict; label against it, never from intuition.
3. `./slots.json` — your one slot.

**You may read nothing else, and run nothing.** You are working in a bare
directory; do not list or open any other path, relative or absolute. Anything
under `/root/repositories/` and every other authoring directory is off-limits.
Why: these pairs measure an LLM judge, and documents in that repository record
which kinds of pair such judges currently get wrong. If you have already read
such material in this session, stop and say so instead of authoring.

## The situation

Your slot is slice `paraphrase`, verdict `entailed`. Its originally assigned
premise already carries a paraphrase pair authored earlier in this round. The
rulebook rules that independence is at the proposition, not at the bytes: a new
pair may not assert the same proposition as a live pair — the same premise with
a logically equivalent hypothesis — however differently worded. A paraphrase of
the same premise asserts the same proposition in every wording, so this slot
cannot be filled from its assigned premise at all, and rewording is exactly what
the rulebook forbids. The skip is logged; your task is the replacement.

## What to produce

One pair on a **hand-authored premise of your own**, written with the Write tool
to `./pairs.json`, in the batch shape:

```json
{
  "pairs": [
    {
      "id": "the slot's id, unchanged",
      "slot": 0,
      "premise": "your authored fact text",
      "hypothesis": "your authored claim sentence",
      "verdict": "entailed",
      "slice": "paraphrase",
      "rationale": "one or two sentences citing the governing rule(s) by name",
      "premise_source": "hand-authored"
    }
  ],
  "skips": [],
  "attestation": "one paragraph: everything you read this session, and a confirmation that you read nothing else and ran nothing"
}
```

## Rules of construction

- The premise is a Layer-2-style fact text: one or two short sentences stating a
  verified fact about a plausible software/homelab infrastructure world, in the
  terse register of minted fact sentences (for example the shape
  "service-name depends on component-name"), invented by you, copied from
  nowhere — including the rulebook's own worked examples.
- The hypothesis is a **full rewording** of the same assertion — nothing
  strengthened, nothing weakened, no lexical anchor preserved beyond entity
  names (rulebook, the `paraphrase` slice).
- Premise and hypothesis must not be identical strings.
- The rationale cites the governing rule by name.

## Finish

Write `./pairs.json`. Then reply with your attestation paragraph.
