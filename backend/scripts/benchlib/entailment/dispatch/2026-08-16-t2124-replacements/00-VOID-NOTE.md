# Round 1 of these blind passes is VOID — stale rulebook (2026-08-16)

`02-labelling-prefix.md` was copied from the `2026-08-15-t2124-step10`
dispatch. That prefix **predates the two rules ruled that same day** — the
Frame rule and the Dependency-strength rule — because those rules were the
*output* of step 10's escalation, not an input to it. Verified: the stale
prefix is 752 lines against LABELLING.md's 1378, and contains zero
occurrences of "Frame rule", "Dependency-strength rule" or "2026-08-15".

Those two rules are the entire reason eg-0510 and eg-0634 were retired, so
their replacements were labelled against a rulebook that could not express
why they exist. **Both labellers caught it independently and said so before
being asked** — the defect is recorded here rather than in a summary because
the passes themselves are the evidence.

Both rounds are kept, not deleted:

- `03-pass-A-VOID-stale-prefix.json`, `04-pass-B-VOID-stale-prefix.json` —
  round 1. Both reached `entailed` on eg-0698 and eg-0699, and both flagged
  that the deciding rule was absent. **That agreement is not evidence**: two
  labellers agreeing without the rule agree about something else.
- `03-pass-A.json`, `04-pass-B.json` — round 2, against the full current
  LABELLING.md.

One cover pair changed between rounds. `eg-0491` is cited by id inside
LABELLING.md, so serving the full rulebook would have handed a labeller that
cover's recorded label; it was swapped for a pair the rulebook does not name.
Neither pair under adjudication is cited anywhere in the file, so no such
swap was needed for them — the rules *do* name the retired eg-0510/eg-0634,
and a labeller reaching the replacements' verdicts through those rules is the
rule working rather than a leak.
