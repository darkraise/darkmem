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

Your slot is slice `weakening`, verdict `entailed`, on the assigned premise in
`./slots.json`. A previously authored pair on this same premise already asserts
the following proposition, and a deterministic duplicate check refused a second
pair asserting it:

> idx-03 hosts at least one deployed service.

## What to produce

One pair, written with the Write tool to `./pairs.json`, in the batch shape:

```json
{
  "pairs": [
    {
      "id": "the slot's id, unchanged",
      "slot": 0,
      "premise": "the slot's premise, byte-for-byte",
      "hypothesis": "your authored claim sentence",
      "verdict": "entailed",
      "slice": "weakening",
      "rationale": "one or two sentences citing the governing rule(s) by name",
      "premise_source": "assigned"
    }
  ],
  "skips": [],
  "attestation": "one paragraph: everything you read this session, and a confirmation that you read nothing else and ran nothing"
}
```

## Rules of construction

- Use the slot's premise byte-for-byte, `premise_source: "assigned"`.
- The hypothesis is **strictly weaker** than the premise — content dropped,
  values abstracted, specifics generalised; nothing added, nothing strengthened
  (rulebook, the `weakening` slice and general procedure 3).
- It must assert a **different proposition** than the one quoted above — not
  that claim in any wording. Weaken along a different axis of the premise than
  the one that proposition weakened along.
- The rationale cites the governing rule by name.

## Finish

Write `./pairs.json`. Then reply with your attestation paragraph.
