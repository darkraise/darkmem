# T2.124 round-4 dispatch record — steps 7–8, the firewall as executed

Layer-1 pair authoring against the ratified `round4_frame.json` (T = 280,
contradicted 80 / entailed 110 / unsupported 90; sitting 2 ratified 2026-08-13).
Executed 2026-08-14 by the step-7/8 controller. Step 9 (independence and
freshness pass) was deliberately NOT run by this party — it requires a party
outside the authoring lineage.

| File | What it is |
|---|---|
| `01-brief-nontemporal.md` | The allowlist brief for the 239 assigned-premise slots (8 batches) |
| `02-brief-temporal.md` | The 41 hand-authored temporal slots (2 batches; verdict mix in slots) |
| `03-brief-reauthor-*.md` | The single-slot re-author briefs for the duplicate findings |
| `04-slots.json` | Every batch's slot file exactly as its author saw it |
| `05-authored.json` | Every batch's returned output, verbatim: pairs, skips, attestations |

## The dispatch mechanism, and why it is not the Agent tool

**Measured before any author was dispatched:** a sub-agent launched through the
session's Agent tool receives the repository's project instructions
(`CLAUDE.md`) injected into its context, and that document carries measured
judge results. A probe agent (not an author) confirmed it could quote them.
Dispatching authors that way would have been the B1 defect class — every
"blind" party handed a judge score on day one, completing silently.

Authors were therefore dispatched as **fresh headless CLI sessions**
(`claude -p`) from bare directories outside the repository, each containing
only the rulebook strip, the batch's `slots.json`, and an empty MCP config. A
second probe from such a directory confirmed the context carries no project
instructions and no judge measurement. Tools were limited to Read/Write/Edit;
model `opus` for all thirteen dispatches. Blindness beyond that is
attestation-based, as in every prior round: each output carries the author's
attestation of exactly what it read (all thirteen in `05-authored.json`).

## The rulebook strip

Byte-prefix of `LABELLING.md` above `## History`, produced by truncation and
verified `strip == file_bytes[:len(strip)]`: 46477 bytes,
sha256 `de26555369fcbb5b8a2a23f59664c184ea92dfe76acc3093bfca2e40298141f5`.
Identical copy in every batch directory. No paraphrase, no condensation.

## The contamination screen

The corrected screen (decimal pattern anchored to a non-letter prefix, ported
from master before any dispatch) ran over every brief and every slot file
before its dispatch: **all clean, zero hits**. Over the strip it returns
exactly the five enumerated baseline lines (bars, composition arithmetic,
identities — the recorded non-leak residual), matching the gate ledger's
baseline.

## Slots, ids, verdicts — all mechanical

`build_round4_assignment()` (seeded by the committed frame file's own sha)
produced the 239 non-temporal slots; slot *s* → id `eg-(0418+s)`, so file order
is slot order. Direction slots carry their reversal class and therefore their
verdict; every other non-temporal slice has one lawful verdict under the frame
(overreach's contradicted cell is 0). The 41 temporal slots (`eg-0657`–
`eg-0697`) carry fixed verdicts in blocks ordered alphabetically by verdict
name — contradicted 20, entailed 8, unsupported 13 — a content-free ordering.
Slots sharing a (premise, verdict) with another slot were annotated
`shared_note` instructing differentiation; the annotation is derived from the
assignment alone.

## Skips — 21, all logged, census untouched

Every skip was re-authored in place for the same slice and verdict with a
hand-authored premise, so slice targets stayed exact and only the l2-fact
count moved (239 assigned − 21 = 218 l2-fact; 62 hand-authored; floor is 140).

- **15 × value-swap on a multi-valued relation** (USES / DEPENDS_ON / CAUSES /
  RELATED_TO): the exclusive-slot rule cannot fix `contradicted` — the named
  known-infeasible shape. Found independently by six authors.
- **2 × direction under a `shared_note`** (n3, slots 70 and 82): the direction
  hypothesis is determined by the premise, so the differentiation the note
  requires is impossible and rewording the reversal is barred; the authors
  skipped to hand-authored premises. (Conservative — the colliding slots were
  value-swap, whose hypotheses could not actually duplicate a reversal — but
  the safe direction.)
- **3 × n3 value-swap** variants of the first ground (in the 15 above).
- **1 × paraphrase duplicate** (`eg-0564`, logged by the controller): the
  committed duplicate check found it byte-identical to `eg-0430` — two blind
  authors converged on the same wording for the same shared premise. A second
  paraphrase of one premise asserts the same proposition in every wording
  (rulebook, independence-at-the-proposition), so the later-minted member (id
  order — mechanical) moved to a hand-authored premise. Rewording was not an
  option; it is exactly what that rule bars.

Two further duplicate findings (`eg-0592`, `eg-0614`, both weakening at
similarity 1.0) were re-authored **on their assigned premises** toward
different propositions — a different weakening axis is a genuinely different
claim — with the excluded proposition quoted in the re-author brief
(this round's own blind product; no judge information).

## Step-7 catches, final state (all green)

- Loader (`load_entailment_gold`): OK, 280 pairs.
- `retired_pair_overlap`: empty — no retired content reproduced.
- `find_duplicate_propositions` (0.85, within class): none.
- `cross_gold_near_overlap` vs the archived gold's live rows: none.
- Controller diagnostic — the same near screen run over the archive's
  **retired** rows too (the U3 residual sitting-2 named: a rewording of a
  lattice-retired pair would pass the committed predicate): none.

## Step-8 reconciliation

Cell-by-cell census against the ratified matrix: **exact on all 11 populated
cells**; census 80/110/90; slice targets exact; **no clause-5b absorption
needed**. Pinned from here by `tests/test_round4_census.py`.
`gate_eligibility` dry run: not eligible, with exactly the two reasons this
stage predicts — 280/280 author-labelled (Layer 2 is step 10) and no resample
block (step 11). Size and l2-fact floors are silently satisfied (280 ≥ 200;
218/280 ≥ 50%).

## Known-open for step 9 (recorded, deliberately NOT fixed here)

Three same-premise, same-verdict pairs whose hypotheses assert one proposition
in different words, sitting **below** the committed 0.85 token threshold, found
by controller-side review after assembly:

- `eg-0424` / `eg-0558` (weakening; token Jaccard 0.833)
- `eg-0425` / `eg-0559` (paraphrase — two paraphrases of one premise are one
  proposition by construction)
- `eg-0463` / `eg-0590` (paraphrase, same ground)

Step 9's independence pass owns the resolution; fixing them from inside the
authoring lineage would defeat the check. Two lookalikes are **lawful** and
should not be over-corrected: `eg-0465`/`eg-0592` and `eg-0486`/`eg-0614`
generalise opposite endpoints of their shared premise — two propositions.

Structural note for the next frame: the round-4 assignment barred premise
reuse within `direction` and `verbatim` only. Paraphrase can share a premise
across slots (and with verbatim), and any two paraphrases of one premise are
proposition-duplicates however worded — the three collisions above and all
three catch-iii findings came from exactly this gap. A future assignment
should extend the determined-slice exclusion to the entailed-equivalence
slices.
