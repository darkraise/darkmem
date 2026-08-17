# T2.124 round report — the fresh entailment gold (2026-08-17)

The round is complete and the gold is certified. This is the record a reader
who did not run it needs: what was produced, what it was measured against, and
what the certification does **not** establish.

> ## ⚠️ CORRECTED 2026-08-17 — this record described a certification that was superseded
>
> Everything below was written against the **pre-repair** certification and was
> accurate then. After it was written, an adversarial review found ten live pairs
> standing on premises the round's own D3 rule excluded, the owner ruled
> retire-and-replace, and the gold was re-certified. The figures in §1 and the
> pinned shas are corrected in place; **the prose below still describes the older
> round in places**, and where it conflicts with `gate-ledger.md`'s "The repair
> round that produced the certified gold", the ledger governs.
>
> What changed: 19 retired → **29**, ids to `eg-0716` → **`eg-0726`**, certified
> file sha `9587dc0f…` → **`fdbe2af9967970b6`**, `pairs_sha256` `01a1bbc5…` →
> **`4748ac84960fed67`**, and the certifying sitting is **1 disagreement of 93 by
> `deepseek-v4-pro`**, not 0/93 by `glm-5.2`.

**The one sentence the round exists to be able to say — and it did not survive
the repair round, so it is retracted here rather than left standing.** It read:
*no judge model contacted any pair in this gold at any point in the round.* That
was true of the census round. It is **false of the certified artifact**: two
non-Claude models have since sat pairs in this file — `deepseek-v4-pro` and
`gpt-5.5`, over the 93-pair certifying resample and the 29-pair bare-sortal
rule-discovery probe. `gpt-5.5`, which later qualified as T2.125's judge, had met
**114 of the 280 live pairs** before that run, and its three known disagreements
(`eg-0475`, `eg-0486`, `eg-0699`) are among the retired.

Every label still came from authoring, blind adjudication, or an owner ruling —
no model's verdict was ever written into a label, and the probe was gated by
nothing and banked into nothing. The disclosure, the worst-case computation
showing no verdict moves, and the reason the strongest sentence is no longer
available are in `gate-ledger.md`, "G-D on the fresh gold".

---

## 1. What shipped

| | |
|---|---|
| Live pairs | **280** (309 in file, 29 retired in place) |
| Census | contradicted **80**, entailed **110**, unsupported **90** |
| Provenance | `l2-fact` **218**, hand-authored **62**, bench-corpus 0, synthesis-draft 0 |
| Ids | `eg-0418`..`eg-0726` (authored `eg-0418`..`eg-0697`; the rest are replacements) |
| `label_source` | `adjudicated` on all 280; **0 author-labelled** |
| Eligibility | `gate_eligibility` → `eligible=True`, the composition line its only reason |

### Pinned inputs

| Artifact | sha256[:16] |
|---|---|
| `entailment/round4_frame.json` (ratified matrix) | `ae11bc172bac05e7` |
| `entailment/round4_excluded_triple_keys.json` | `38cae59683fa57e6` |
| `entailment/l2_harvest.json` | `d1a3e21ba4ee3969` |
| `gold.json` at the Layer-3 draw (`gold_sha256`) | `cac8c9743606…` (the re-sit draw; the pre-repair draw was `16072f9688209c89`) |
| `gold.json` certified (file) | `fdbe2af9967970b6` |
| `pairs_sha256` (the certification's basis) | `4748ac84960fed67` |

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
| Disagreements | **1** (`eg-0423`, gold `entailed` read as `unsupported`), against a bar of ≤ 1 |
| Seed | `1550309571`, derived from the pre-certification file's own bytes |
| Labeller | **deepseek-v4-pro** — non-Claude, re-sitting after the excluded-premise repair |
| Date | 2026-08-17 |
| Certifies | `pairs_sha256` `4748ac84960fed67` |

> **This table was corrected 2026-08-17.** It recorded the **superseded**
> certification — 0 disagreements by `glm-5.2` at draw `16072f96…`, which
> certified the pre-repair pair set `01a1bbc5…`. That sitting happened and its
> artifact is kept (`resample_runs/2026-08-17-glm-5-2-16072f96.json`); it simply
> does not certify the shipped gold. The shipped certification is the re-sit
> above, `resample_runs/2026-08-17-deepseek-v4-pro-5c67d8c3.json`, and it lands
> **on** the bar rather than under it. Why that is on-protocol rather than a
> squeaked pass: the `≤ 1` bar was ratified 2026-07-31 and never moved, the seed
> derives from the file's own bytes, there was one sitting per draw with no
> re-running until it passed, and the two Layer-2 rounds that were voided were
> voided **passes**. The single disagreement `eg-0423` is one of the two pairs in
> the parked bare-sortal vocabulary gap, which cannot flip the qualification
> (worst case precision 0.981, recall 0.963 — both clear).

Recorded `--from-raw` off the sitting that was actually read, never by a second
run: `--write-gold` re-sits the model, an LLM sitting is not reproducible, and
a re-run would certify a sitting nobody inspected. T2.115 measured 1
disagreement and recorded 0 by exactly this route.

**Both pre-registered risks resolved in the gold's favour** — in the `glm-5.2`
sitting this described, which is the superseded one. `eg-0529` was guaranteed in
the draw as a full-census contradicted pair and read as recorded once the
instance-hood ruling was in the excerpt. glm-5.2, entirely unmeasured on this
gold, disagreed with none of the 93. The **certifying** re-sit is
`deepseek-v4-pro`'s at 1 of 93, above.

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

**No attempt had been filed against this pair set when this was written.**
`count_gold_touching_attempts` returned **0** for the then-current
`01a1bbc5508b8288…` and **2** for the retired `4975c5cc…`, so the counter was
answering rather than empty. Count it against the run ledger in the **main
checkout**: `benchlib/runs/` is gitignored, so a worktree's copy is local and
near-empty and reads 0 for everything.

> **Superseded 2026-08-17.** The certified pair set is now `4748ac84960fed67`,
> and **T2.125's qualification attempt has been filed against it** — one contact,
> `gpt-5.5`. Because `benchlib/runs/` is gitignored, that row was written only in
> the T2.125 worktree and must be carried into the main checkout's ledger at
> merge, or the anti-tuning counter reads 0 for a pair set that has been judged.
> Separately, and not counted by this counter at all: the same judge met 114 of
> these pairs in the certifying resample and the bare-sortal probe, neither of
> which files an attempt. See `gate-ledger.md`, "G-D on the fresh gold".

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

**glm-5.2 has now joined the circularity-compromised set.** On this section's
own reasoning T2.125 would need a *fourth* model for the judge it qualifies —
deepseek, gpt-5.5 and glm-5.2 have all now been spent against this lineage in one
role or another.

> **The owner overrode that requirement rather than meeting it** (recorded
> 2026-08-17): *accept the three available judge models; no fourth is required.*
> T2.125 ran on `gpt-5.5` under that ruling. The cost above is not withdrawn — it
> was accepted, which is the owner's to do — but no reader should conclude a
> fourth model was found. None exists in this tree.

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
