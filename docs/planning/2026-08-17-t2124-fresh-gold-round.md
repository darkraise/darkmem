# T2.124 round report — the fresh entailment gold (2026-08-17)

The round is complete and the gold is certified. This is the record a reader
who did not run it needs: what was produced, what it was measured against, and
what the certification does **not** establish.

**The one sentence the round exists to be able to say:** no judge model
contacted any pair in this gold at any point in the round. Every label came
from authoring, blind adjudication, or an owner ruling; the only model to see
a pair against its recorded label was the Layer-3 resample labeller, which is
the certification instrument and files no qualification attempt.

---

## 1. What shipped

| | |
|---|---|
| Live pairs | **280** (299 in file, 19 retired in place) |
| Census | contradicted **80**, entailed **110**, unsupported **90** |
| Provenance | `l2-fact` **218**, hand-authored **62**, bench-corpus 0, synthesis-draft 0 |
| Ids | `eg-0418`..`eg-0716` (authored `eg-0418`..`eg-0697`; the rest are replacements) |
| `label_source` | `adjudicated` on all 280; **0 author-labelled** |
| Eligibility | `gate_eligibility` → `eligible=True`, the composition line its only reason |

### Pinned inputs

| Artifact | sha256[:16] |
|---|---|
| `entailment/round4_frame.json` (ratified matrix) | `ae11bc172bac05e7` |
| `entailment/round4_excluded_triple_keys.json` | `38cae59683fa57e6` |
| `entailment/l2_harvest.json` | `d1a3e21ba4ee3969` |
| `gold.json` at the Layer-3 draw (`gold_sha256`) | `16072f9688209c89` |
| `gold.json` certified (file) | `9587dc0f4b3563b0` |
| `pairs_sha256` (the certification's basis) | `01a1bbc5508b8288` |

The two file shas differ for two reasons, both benign and both recorded: the
certification block is written into the file, and `resample_score.write_gold`
re-serialises at `indent=2` where the round authored at `indent=1`. Content is
provably untouched — `pairs_sha256` and every `pair_digests` entry re-derive,
and the drawn state reconstructs exactly at the drawn indent, seed included
(`test_the_real_gold_carries_a_basis_that_re_derives`).

---

## 2. Composition against the frame

The frame was ratified **before any pair was authored** (gate ledger, "T2.124
frame — owner ratification, sitting 1"), and the finished gold matches it cell
by cell (`test_round4_census.py`). Since step 12 the composition pins are
*derived* from the frame rather than transcribed, so a gold that matched
neither would fail in two files rather than pass a copied table.

### Skip log summary

**21 skips**, every one re-authored in place for the same slice and verdict on
a hand-authored premise, so slice targets stayed exact and only the provenance
split moved:

| Reason | Count |
|---|---|
| `value-swap` slots on multi-valued relations (the named infeasible shape) | 18 |
| `direction` slots whose shared-premise differentiation note could not be met | 2 |
| `paraphrase` duplicate on a shared premise | 1 |

239 assigned slots − 21 skips = **218** `l2-fact` pairs, 77.9% of live, against
doc 17 §11's 50% floor. Verbatim reasons and author attestations:
`entailment/dispatch/2026-08-14-t2124/` (04/05).

---

## 3. Agreement rates, as measured

**Layer 2 (step 10), the full 280-pair adjudication.** Two separately
dispatched blind labellers, no shared context, stripped rulebook export.
Pass A and pass B agreed with each other on **279/280 (0.9964)**; one pair
escalated. The escalation ruling (2026-08-15, rule-then-pairs) added **2 rules**
and found `eg-0510` and `eg-0634` wrong under them — retired and replaced
rather than flipped, because `weakening` and `paraphrase` admit only `entailed`
and an in-place flip would have broken the ratified matrix.

**The repair rounds** (2026-08-16 and 2026-08-17) each ran the same two-pass
protocol over a seeded batch mixing the pairs under adjudication with already
adjudicated covers, so a labeller cannot tell which pairs are live questions.
Notable results, recorded as they came:

- The replacements round's **round 1 is VOID and kept**: its rulebook prefix
  predated the two rules that were that session's *output*, and both labellers
  caught it independently and said so before answering. Two labellers agreeing
  without the deciding rule agree about something else.
- `2026-08-17-t2124-rulings-batch`: **30/30** A-vs-B, all eight replacements
  unanimous, *despite* each labeller flagging five constructions the rulebook
  does not enumerate. The general tests decided; the enumeration gaps produced
  flagged-but-consistent judgement rather than divergence.
- Escalations in the repair rounds landed overwhelmingly on **covers**, and
  were rule gaps rather than authoring slips — which is the protocol working:
  the covers are what make the batch blind, and they are also what surfaces a
  rule the file does not yet state.

---

## 4. The Layer-3 resample — the certification

| | |
|---|---|
| n | **93** (stratified: full census of contradicted, plus unsupported and the entailed remainder) |
| Disagreements | **0**, against a bar of ≤ 1 |
| Seed | `369569686`, derived from the pre-certification file's own bytes |
| Labeller | **glm-5.2** — non-Claude, owner-directed |
| Date | 2026-08-17 |

Recorded `--from-raw` off the sitting that was actually read, never by a second
run: `--write-gold` re-sits the model, an LLM sitting is not reproducible, and
a re-run would certify a sitting nobody inspected. T2.115 measured 1
disagreement and recorded 0 by exactly this route.

**Both pre-registered risks resolved in the gold's favour.** `eg-0529` was
guaranteed in the draw as a full-census contradicted pair and read as recorded
once the instance-hood ruling was in the excerpt. glm-5.2, entirely unmeasured
on this gold, disagreed with none of the 93.

**What the result is evidence for.** The prior sitting — deepseek-v4-pro
against a rulebook that did not yet contain the bare-sortal clause — rejected
11 of the 25 probe-measured pairs still live. A third vendor, given the written
clauses, disagreed with none of 93. Writing the rules down is what closed the
gap, and that was the bet stated in the pre-registration *before* the draw
rather than claimed after it.

---

## 5. Census independence, both classes, both readings

Disclosed by the runner for every class whose recall a bar gates (step 13), so
the entailment role's reader sees the census their own bar is applied to:

| Class | Bar | Rows | Independent propositions | Effective bar on rows | On propositions |
|---|---|---|---|---|---|
| contradicted | 0.95 | 80 | **80** | 76/80 = 0.95 | 76/80 = 0.95 |
| entailed | 0.90 | 110 | **101** | 99/110 = 0.90 | 91/101 = 0.901 |

The contradicted census carries no duplicate on either source — a clean
improvement on the retired set's 80 rows over 78 propositions, which was found
in review *after* an attempt had been spent against it. The entailed census
carries nine, all from the step-9 adjudication sidecar and none visible at the
bytes; the sidecar recorded 14 components and five lost a member to the
step-10/11 retirements, so five collapse nothing now. The sidecar is left
unpruned because it is the adjudication record.

Neither reading eases either bar in this gold: the effective bar on
propositions is at or above the stated bar for both classes.

---

## 6. The retirement clause (D6) — verified, not re-implemented

Pair set `4975c5cc` is retired for **every** role, and the machinery is
T2.117's, landed and test-pinned. This round verifies and cites it:

| Refusal site | Test |
|---|---|
| Harness, before any model call | `scripts/benchlib/tests/test_judge_qualification.py::test_the_runner_refuses_the_retired_pair_set_in_every_mode` |
| Writer | `…::test_the_writer_refuses_a_retired_pair_set_for_every_role` |
| App-side reader | `backend/tests/test_verification_judge.py::test_tripwire_the_retired_pair_set_is_refused_for_every_role` |
| A record on the retired set qualifies nothing | `…::test_a_record_on_the_retired_pair_set_qualifies_no_role` |
| Set identity is not pair identity (the append bypass) | `…::test_appending_one_pair_does_not_un_retire_a_gold` |
| A retired pair under a new id is still retired | `…::test_a_retired_pair_under_a_new_id_is_still_retired` |

**`retired_pair_digests.json` is unchanged this round** — byte-identical
(`1069b68e2cbe014f`) to its state before the round's first authoring commit,
carrying 415 digests over `pairs_content_hash` `4975c5cc…`.

**And the fresh gold does not reproduce a retired pair.**
`retired_pair_overlap` over *every* pair in the file — live and retired — is
the empty set. The digest basis excludes the id, so this catches the
`eg-0367`/`eg-0404` shape the census has produced twice before.

**No attempt has been filed against this pair set.**
`count_gold_touching_attempts` returns **0** for `01a1bbc5508b8288…` and **2**
for the retired `4975c5cc…`, so the counter is answering rather than empty.
Count it against the run ledger in the **main checkout**: `benchlib/runs/` is
gitignored, so a worktree's copy is local and near-empty and reads 0 for
everything.

---

## 7. Residuals — what this round did not achieve

Carried forward verbatim in substance from the plan's §9, because a passing
round does not retire them.

**U1 — "the authoring party is not the adjudicating party" is structural, not
epistemic.** Authors and both blind labellers are Claude-family agents. The
achievable property is the structure: separate dispatches, no shared context,
stripped export. Genuine label independence enters only at the Layer-3
resample, on one non-Claude model. **The certification measures inter-model
agreement more than label truth**, and the runner's own docstring says so.

**glm-5.2 has now joined the circularity-compromised set.** T2.125 needs a
*fourth* model for the judge it qualifies — deepseek, gpt-5.5 and glm-5.2 have
all now been spent against this lineage in one role or another.

**U2 — "neither references which slices any judge has missed" is a property of
the artifacts, not of the people.** The miss decompositions are published in
this repo and the frame-script author has read them. The verifiable form is
zero degrees of freedom exercised in the frame plus an independent review
attacking exactly that. A reader who wants to discount the round knows what to
discount.

**U3 — freshness is content-level, not proposition-shape-level.** The closed
16-relation taxonomy and the bench-corpus domain mean fresh pairs resemble
retired ones in *shape*. Only byte-identity is refused by machinery. The
precise residual: `cross_gold_near_overlap` screens against the archive's
**live** pairs only, so a rewording of one of the archive's 15 lattice-retired
pairs would pass the near-screen — 15 pairs whose near-duplicates are
unscreened, and zero whose exact duplicates are.

**U4 — the entailed lattice sizing fixes recall's denominator only.**
`entailed_precision` (0.95) and `contradiction_precision` (0.70) have
judge-dependent denominators; no census makes them exact. "Sized so their bars
are expressible" covers two bars, not four.

**Two defects found during the round and recorded rather than smoothed.** The
certification writer is formatting-blind and reformatted the whole file while
stamping it (§1); and LABELLING.md's skip log stated "15 value-swap slots"
while listing 18, so its sub-counts summed to 18 against a correct total of 21.

---

## 8. Floor

`./scripts/gate.sh` — **GATE GREEN**. 891 benchlib tests pass; the extraction
F1 bench is at or above every G-B floor (entity name+type F1 = 0.912, relation
F1 = 0.883, `deepseek-v4-flash`, `--algo-only`). This discharges step 4's
floor exemption for the whole round.
