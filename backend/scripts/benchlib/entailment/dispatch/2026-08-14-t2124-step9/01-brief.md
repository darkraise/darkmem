# Adjudication brief — do these hypothesis pairs assert the same proposition?

You are adjudicating an entailment gold set. You did not author it and you are
not being asked to check anyone's work — you are the instrument.

## What you have

- `RULEBOOK.md` — the labelling rulebook this gold was authored against. Read it
  first. It defines the verdict vocabulary and what the gold is for.
- `cases.json` — 24 cases. Each is one **premise** and **two hypotheses**
  (`A_hypothesis`, `B_hypothesis`) that were authored independently against that
  same premise and were given the **same verdict**.

## The question, for each case

**Do hypothesis A and hypothesis B assert the same proposition about the
premise?**

Two hypotheses are the **same proposition** when a reader who accepts one has
thereby accepted the other — they are paraphrases, or one is a pure weakening of
the other that adds no separate claim. They are **distinct** when each carries
something the other does not: a different entity, a different relation, a
different direction, a different scope, a different quantity, or a
generalisation the other does not license.

This is a question about meaning, not about wording. Two hypotheses may share
almost no vocabulary and still assert one proposition; they may share nearly all
of it and assert two. Judge the claim, never the tokens.

The reason this matters: the gold's censuses are counted in rows, but a recall
bar is a fraction of *propositions*. Where two rows assert one proposition, a
system that catches one banks two correlated hits, and the real bar is looser
than the stated one. So an over-call here is not "safe" — it corrupts the count
in the other direction. Call what you actually see.

## Output

Write `verdicts.json` in this directory:

```json
{
  "verdicts": [
    {
      "case": 1,
      "verdict": "DUPLICATE" | "DISTINCT",
      "confidence": "high" | "medium" | "low",
      "reason": "one or two sentences naming what A and B each assert, and what (if anything) one carries that the other does not"
    }
  ],
  "attestation": "state exactly which files you read, and confirm you were given no information about which cases were expected to be duplicates"
}
```

One entry per case, all 24, in case order.

Rules:

- Judge each case only on its own premise and two hypotheses. Cases are
  independent; nothing about one tells you anything about another.
- There is **no expected number** of duplicates. It may be zero, it may be all
  24. Do not balance your answers or reason about what a plausible rate would be
  — that would make the result a function of your expectations rather than of the
  text.
- Use `low` confidence freely where the case is genuinely borderline, and say in
  the reason what would settle it. A flagged borderline is useful; a confident
  guess is not.
- If a case looks malformed (the two hypotheses are byte-identical, or the
  premise does not support either), say so in the reason and mark it `low`.
- Do not edit any file other than `verdicts.json`.
