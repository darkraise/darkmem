# Layer 3 resample — MISS (2026-08-16). 2 disagreements, bar <= 1.

Model `deepseek-v4-pro` (owner ruling, item 4, 2026-08-12), n = 93, seed
20260808, gold sha `cac8c974…`, raw replies at
`resample_runs/2026-08-16-deepseek-v4-pro-cac8c974.json`.

**The attempt is spent and is NOT re-run.** Stop condition 1: a number below
its bar is the gate working. No redraw, no bar change, nothing written into
`gold.json`.

## The disagreements are not scattered — they are one shape

| id | hypothesis | gold | resample |
|---|---|---|---|
| eg-0486 | "ledger-02 has at least one component that depends on it." | entailed | unsupported |
| eg-0546 | "Consul uses at least one other component." | entailed | unsupported |

Both cite `frame rule` and nothing else. Of the **7** entailed pairs drawn,
**3** were bare-sortal existentials and it rejected **2 of the 3**; all
**4** non-existential entailed pairs were accepted. So the disagreement is
concentrated in one construction rather than spread across the class.

## The rule gap, stated precisely

The Frame rule distinguishes a **universal discourse frame** ("the estate",
"the stack" — vacuous, entailed) from a **proper-subset frame** (a named
deployment — asserted content, unsupported). It says nothing about the third
shape, which is the commonest one in this gold: a **bare sortal with no frame
phrase at all** — "at least one component", "at least one system". Is the bare
sortal vacuous like a universal frame, or a restrictor whose membership the
premise must establish?

**The one it accepted suggests the resample is applying a consistent principle
the gold does not state.** It accepted `eg-0650` ("Alert storms are deployed on
at least one **host**") while rejecting "at least one **component**". The
difference is that `DEPLOYED_ON`'s own semantics establish the host/guest roles,
so that sortal is earned by the premise; "component" is not earned by anything.

**Three independent parties converged on that principle in one day.** Both
round-2 blind labellers reached for it unprompted on `eg-0508`, in their own
words: frame membership must be established *by the premise*, and a relation's
semantics can establish it where world knowledge may not. The resample model
then drew the same line without seeing either of them.

## Blast radius

- **29** live pairs use a bare-sortal existential; **5** use an explicit
  universal frame.
- Most of the 29 sit in `weakening` and `paraphrase`, which admit only
  `entailed`, so resolving the gap against them is retire-and-replace at a
  scale the ratified matrix cannot absorb quietly.

## What this resample does NOT say

**No framed existential was drawn at all**, so this sitting is silent on
`eg-0698` — the replacement authored this same day, which carries the explicit
universal frame the rule does cover. Its Layer-2 adjudication stands on its own
evidence; nothing here confirms or disturbs it.

## Owed to the owner

Step 11's protocol is classify → rule-then-pairs → redraw, with two
*consecutive* failures stopping the task. This is failure 1 and it is
classified above. The next move is a **rule** ruling on the bare sortal, which
is the owner's under rule-then-pairs — and it is consequential in both
directions, since resolving it against the bare sortal touches 29 pairs and
resolving it for them makes the Frame rule's silence deliberate.
