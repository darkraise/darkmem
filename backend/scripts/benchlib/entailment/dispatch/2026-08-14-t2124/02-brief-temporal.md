# Authoring brief — entailment gold pairs, temporal slice (blind round)

You are authoring labelled (premise, hypothesis, verdict) pairs for a measurement
gold set. Work only from the sources this brief allows.

## Allowlist — the ONLY things you may read

1. This prompt.
2. `./rulebook.md` — the labelling rulebook: the three verdicts, the general
   decision procedure, the edge rulings (the window rules above all), the eight
   slices, and the provenance rules. It is the authority for every verdict;
   label against it, never from intuition.
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
      "premise": "your authored fact text",
      "hypothesis": "your authored claim sentence",
      "verdict": "the slot's verdict, unchanged",
      "slice": "temporal",
      "rationale": "one or two sentences citing the governing window rule by name",
      "premise_source": "hand-authored"
    }
  ],
  "skips": [],
  "attestation": "one paragraph: everything you read this session, and a confirmation that you read nothing else and ran nothing"
}
```

## Rules of construction

Every slot in this batch is slice `temporal` and carries `premise: null`: you
author **both** the premise and the hypothesis.

- The premise is a Layer-2-style **fact text**: one or two sentences stating a
  verified fact that **renders its validity window into the text** (rulebook,
  "What a pair is") — a dated span, an inception, a named end event or successor,
  or an open "since" window. Invent realistic facts about a plausible
  software/homelab infrastructure world; copy nothing from anywhere.
- **The verdict is fixed per slot.** Construct the pair so that verdict is
  correct under the rulebook's window semantics — the window rule, the
  open-window rule, the inception-window rule, the evaluation-time rule, and the
  implicature-is-not-contradiction rule. You choose the wording and the window
  shape; you never change a verdict.
- **Vary the construction across your batch** rather than repeating one shape:
  claims scoped inside a window, present-tense claims over explicitly closed
  windows, open windows read at later dates, unanchored "currently" claims,
  claims dated before an inception (with and without a named predecessor state),
  implicated-but-not-asserted endings. The slice exists to exercise the window
  rules broadly.
- Use **varied subjects, services, versions and dates** so no two of your
  premises state the same fact.
- The **rationale cites the specific window rule by name** and says in a clause
  why it decides this pair.
- Every pair stands alone: decide it against its own premise only.
- Do not reuse the rulebook's own worked example sentences or their subject
  matter (its named services, dates or migrations) as material; they are
  citations, not templates. Invent fresh subjects.

## Skips

With authored premises there is no infeasible assignment; a skip here should not
occur. If you nonetheless cannot lawfully realise a slot's verdict, record it in
`skips` with the reason rather than bending a rule.

## Finish

Write `./pairs.json`. Then reply with: the count of pairs authored, any skips
with reasons, and your attestation paragraph.
