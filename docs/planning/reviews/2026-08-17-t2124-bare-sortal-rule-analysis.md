# Bare-sortal rule gap — Fable analysis and recommendation (2026-08-17)

Analysis only; nothing committed by the analyst, no model call made, no file
changed. The ruling is the owner's under rule-then-pairs. Every load-bearing
claim below was re-verified against the committed probe artifacts by the
controller before being recorded.

## It refutes the controller's central inference, and that is the main result

The controller argued: *under a permissive bare-sortal reading eg-0486 is
entailed, so both vendors rejecting it means both reject the permissive reading.*
**That reduction is of a different sentence than the one written.** eg-0486's
hypothesis is "ledger-02 **has** at least one component that depends on it" — the
English possessive, whose primary reading asserts the component is a component
**of ledger-02** (compare "the building has a tenant that complains about it").
So the models were applying the **existing** Frame rule's unearned-membership
branch correctly, to an implicit proper-subset frame. They were not rejecting the
permissive reading at all.

The contrast pair settles it, and both are verified: **eg-0516** ("neon-04 **has**
at least one dependency") is the same possessive construction and **both models
accept it**, because `DEPENDS_ON` earns "dependency *of* neon-04"; nothing earns
"component *of* ledger-02", since a dependent of X is external to X.

## The permissive core mostly survives

gpt-5.5 — the stricter instrument on this construction — agrees with the gold on
**26/29**, and its 3 rejections are a strict subset of v4-pro's 14 (verified).
The stable cross-vendor rejections isolate **two narrow defect classes**, not a
construction-wide one:

1. the possessive-*have* frame where the relation does not earn membership;
2. sortals carrying real classificatory content — "service", "pieces of
   software" — whose application to the witness is world knowledge, which
   **procedure 2 already bars**.

Both readings the controller floated are refuted on the full 29: reading 2 (v4-pro
rejects 3/13 earned) and reading 3 — gpt accepts the subject-side unearned
eg-0550, eg-0426 and eg-0570, all verified. The subject/object axis was an
artifact of the two pairs the draw happened to sample.

## The bound on any rule anyone can write

**eg-0465** ("idx-03 hosts at least one deployed service") and **eg-0475** ("At
least one service is deployed on spire-01") are semantically equivalent — same
relation, same sortal — and **both instruments split them the same way**
(accept 0465, reject 0475; verified). No rule can match both members. At this
boundary the instruments are surface-form sensitive, which the v4-pro repetition
study on eg-0650 (3 entailed / 2 unsupported on identical input) independently
confirms.

## Recommended repair — 4 pairs, matrix-neutral

All are `entailed` in flip-forbidden slices, so all retire-and-replace, authored
only **after** the rule lands and Layer-2 blind-adjudicated:

| pair | slice | clause |
|---|---|---|
| eg-0486 | weakening | possessive frame, unearned by `DEPENDS_ON` |
| eg-0475 | weakening | "service" differentiates, unearned |
| eg-0465 | weakening | same sortal/relation as 0475 — consistency forces it although both models accept this surface form |
| eg-0699 | paraphrase | "pieces of software" is world knowledge (procedure 2) |

Contradicted 80 / entailed 110 / unsupported 90 all hold, entailed stays ≡ 0
(mod 10), 280 live. **No lattice retirement, no matrix amendment, no bar moved.**
**eg-0478 is not in the repair set** — verified: both instruments agree with the
gold, and `HAS_PART` earns "parts". The other 24 bare-sortal pairs keep their
labels; replacing correctly-labelled pairs because an instrument is noisy on them
would be fitting the gold to the models.

Draft rule text for LABELLING.md — a bare-sortal clause and a
possessive-existential clause, both applying the *already ratified* Frame-rule
differentiation test and procedure 2 to the sortal noun itself — is in the
analyst's full report; it is drafted so the owner rules on a sentence rather than
a direction.

## The decision this actually leaves the owner

The repair is small and the protocol path (classify → rule-then-pairs → redraw)
is designed for failure 1. **The bet is the redraw, and it stakes the task's last
permitted failure.** Pre-registered arithmetic, stated before anyone runs
anything: after repair, ~1.5 bare-sortal pairs land in a 93-draw in expectation;
v4-pro rejects ≈43% of the survivors under the current prompt; so
**P(≥ 2 disagreements) ≈ 9–34%**, the range turning on how much the new rule text
moves the instrument — the one quantity nobody can measure without a further
forbidden model contact.

**Recommendation: the owner sits the n = 93 redraw personally.** It is the
protocol's original design, the only uncompromised instrument left, and the only
sitting that measures label *correctness* rather than inter-model agreement.
Failing that, name a third model on grounds independent of these results. **If
the redraw must be one of the two spent LLMs, the honest answer is a fresh
round** — a 9–34% chance of ending the task on documented instrument noise, taken
to avoid one human sitting, is not a bet the evidence supports; nor is
re-authoring 250 pairs the instruments agree on at 92/93 to fix four.

## What nobody has measured

- **No human has adjudicated any of the 29 under any stated rule.** An owner
  sitting on the three both-rejected pairs plus the eg-0465/eg-0475 matched
  control is the only instrument separating "the models share an NLI prior the
  rulebook should adopt" from "the models share a correlated bias it should
  overrule".
- No probe exists under the *drafted* rule text — both models were probed against
  a silent rulebook, so every compliance figure is extrapolation.
- No repetition study for gpt-5.5 at all; "stable" is measured only for v4-pro on
  eg-0486/eg-0546.
- **eg-0698 has never been contacted by any instrument.**
