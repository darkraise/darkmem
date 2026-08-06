# The five open E2 blockers — adversarial review

**Analysis only. This document recommends and stops** — no code, no task file, no tracker
row, no gate verdict; the one write on this branch is this file. Written 2026-08-06
against `feat/e2-truth-core` (HEAD `d087939c` plus the day's six commits, latest
`3f67152a`). Every claim below cites a file that was actually opened; arithmetic is shown;
inference is labelled. Brief: `docs/planning/briefs/2026-08-06-blocker-review.md`, whose
findings were treated as claims to refute. Two of them are overturned in part (§4.1, §4.3)
and one is corrected in fact (§5).

The brief's own arithmetic checks out first: the twelve remaining tasks partition exactly
as 7 (the T2.54 chain) + 1 (T2.85) + 1 (T2.59) + 3 (T2.31/T2.35/T2.50) = 12.

---

## 1. T2.54 — the labelling sitting

**Decision owed:** schedule and scope the owner's sitting; rule on the Option-B
doctrine-alignment prompt revision (already argued lawful in
`analyses/2026-08-05-t2.11-judge-bar.md` §5B); optionally mint T2.11a. **Owner:** the
human owner (the sitting), the controller (the ruling and the mint).

**The gold's state, re-verified independently** by counting
`backend/scripts/benchlib/entailment/gold.json`: 241 live pairs, `label_source` =
{adjudicated: 239, author: 2}, provenance = {l2-fact: 153, hand-authored-synthetic-fact:
72, hand-authored-bench-corpus: 16} — 153/241 = 63.5 % l2-fact. Matches the 2026-08-05
analysis exactly. `gate_eligibility`
(`backend/scripts/benchlib/judge_qualification.py:147-182`) refuses on exactly three
conditions, and today only the third fires: `author-labelled: 2/241`.

**Is the ~3 h estimate real?** Yes as owner-chair time on the happy path, with a fat
conditional tail. The sitting's fixed order is in
`backend/scripts/benchlib/entailment/LABELLING.md:346-350` and `:417-426`: fork ruling →
escalation queue → resample. The parts:

- **Fork ruling** — four items (`LABELLING.md:352-384`), each with cited evidence;
  item 4 needs no ratification. Reading plus ruling: ~30–60 min.
- **Escalations** — 2 pairs (`entailment/escalation_queue.json`): ~10–20 min.
- **Resample** — n = 93 at ≤ 1 disagreement, stratified, seeded (`LABELLING.md:420-423`;
  ratified 2026-07-31). At 1–1.5 min/pair: ~1.5–2.5 h. The 2026-07-31 amendment priced
  the n = 37 → 93 increase at "roughly 1–1.5 h more", consistent.

Happy path total ≈ 2.5–4 h. **The tail is the fork ruling's outcomes, and it converts
owner-hours into calendar-days:** rejecting proposal 1 retires-and-replaces six named
`value-swap` pairs (eg-0048/0088/0098/0109/0154/0201, `LABELLING.md:358-361`), each
replacement re-blinded under the Step-5 protocol — agent authoring plus two blind passes
*between* the ruling and the resample, because the resample may only run "after the set
is stable" (`LABELLING.md:419-420`) and its `contradicted` census contains all six.
Rejecting proposal 3 does the same for eg-0142. So a rejection splits the sitting in two
with an agent round in the gap. A resample failure adds a rule-then-pairs pass and a
fresh draw; two consecutive failures stop the task (plan blocker B4).

**Can anything be dispatched without contaminating the resample?** The three owner acts
cannot: ratifying is the owner's act by definition, the escalations are Layer 3, and the
resample is "the **first** independent accuracy measurement this gold will have received"
(`LABELLING.md:457-459`) — the Step-5 1.0000 inter-pass figure is confirmed
correlated-error and may enter G-D only as procedural evidence. What *can* be prepared by
agents with zero contamination: the seeded stratified sample draw (mechanical; the drawer
sees labels, the owner sees only premise/hypothesis), the retire-and-replace
authoring-and-blinding round *if* a proposal is rejected, Option B's prompt-revision
brief (conditional on ratified text), and T2.11a's generator build.

**Is there a defensible smaller sitting?** A smaller sitting *exists mechanically* and
must be refused as policy. Two findings:

1. **The eligibility lock does not enforce the resample.** `gate_eligibility` checks
   size, l2-fact floor, and author-labels — nothing else (verified in code, above). A
   fork-plus-escalations sitting (~1 h) flips the last two `author` pairs and the lock
   passes, letting T2.41 run `--gate` on a gold whose label-error bound is uncertified.
   That is a trap: the 2026-07-31 power computation established that 5 % gold noise
   consumes the entire 0.95 precision budget, and the first gate run irreversibly spends
   Rule B's never-contacted population (`LABELLING.md:386-395`). The lock under-enforces
   T2.54's Done-when; the controller must treat resample-done as process-bound, not
   lock-bound.
2. **"Unblocks G-D alone" is not a coherent target.** G-C's T2.11 consumes the *same*
   qualification record T2.41 mints (`VerificationJudge.judge()` has one lawful door);
   any sitting that unblocks G-D unblocks G-C's precondition in the same act. There is
   no partition of the sitting by gate.

**Recommendation** (confidence: high): one full sitting, ordered as LABELLING.md fixes
it, with the sample pre-drawn and the rejection-contingency agent round pre-briefed so a
rejected proposal costs calendar, not confusion. Sequence the Option-B ruling alongside,
per the 2026-08-05 analysis — its §4 forecast (a current-prompt gate run misses at
0.78–0.91 across the charitable range) was checked for internal consistency and stands.
**What would change my mind:** the owner ratifying all three proposals in under an hour
makes the tail vanish and the ~3 h estimate slightly conservative; a proposal-1 rejection
makes it wrong by days.

---

## 2. T2.85 — the belief-window ruling

**Decision owed:** ratify option 2 (`stated_expiry` column, arm writes
`invalid_at := stated_expiry`) plus the two doc-08 amendments. **Owner:** controller/owner.

**Four-index claim re-verified independently:** `rg "expired_at IS NULL AND invalid_at
IS NULL" backend/migrations/versions/0001_baseline.py` returns exactly four hits — lines
540, 564, 572, 579 — matching the analysis's table (`ux_knowledge_triples_open`, the two
FTS GINs, `ix_knowledge_triples_project_open`), and no reversed-order spelling exists.
The claim holds.

**Does option 2's schema edit collide with anything in flight?** No — the window is free
*today*. The 2026-08-05 amendment granted the round's baseline window to T2.84; T2.84 is
**done and controller-verified** (`a4b9504e` "add fact_access_stats to the baseline"
through `c05d0e9f`, verified in `0a47bf46`; `fact_access_stats` present at
`0001_baseline.py:621`). The working tree is clean and no other commit has touched the
baseline since. Unknown and worth one check at dispatch time: whether any yet-unclaimed
task plans a baseline edit this round — `progress.md` cannot answer it (its E2 rows are
known-stale, all `todo`).

**Is the freeze close enough to matter?** No, in both directions. The freeze is the
homelab cutover, which doc 20 sequences **after** G-C and G-D (restated in the
2026-07-31 Tier-3 ruling row), and both gates sit behind the §1 sitting — so the freeze
cannot arrive before this column can. And even if it did, a nullable `stated_expiry`
lands post-freeze as an ordinary additive revision; the freeze changes the mechanics,
not the availability. Freeze pressure is therefore not a reason to prefer option 3, whose
only advantage was needing no window.

**Recommendation** (confidence: high): the 2026-08-05 recommendation survives the attack;
ratify option 2 and grant the window promptly *because* it is momentarily uncontended —
the window, not the ruling, is the scarce resource. **What would change my mind:** a
concurrent baseline claim this round (drops option 2 to "next window", or promotes
option 3 if windows stay contended for weeks — the prior analysis already ranks it a
coherent second).

---

## 3. T2.59 — the retention ruling

**Decision owed:** state the retention policy (recommended: option D with riders R1–R3).
**Owner:** the human owner, through the controller.

The brief asked for the load-bearing *argument* to be checked, not the conclusion. The
argument is: the assistant's own unbounded `messages.content` and the storage substrate
sit below all four options, so A/B/C pay permanent costs to narrow a gap they cannot
close. Checked at the sources:

- `backend/app/services/chat.py:184-201` — the assistant message stores the **whole**
  generated answer as `content`, unbounded; `context.memories[].content` is trimmed to
  150 chars; `context.facts` is stored untrimmed. All three as the analysis stated.
- The ceiling mechanism holds on inspection: options A (redact events/context), B (stop
  writing previews), and C (tombstone at read time) all operate on *copied* content
  fields. Memory-derived substance in generated prose is paraphrase — there is no span
  to find after the fact — so no redaction scheme reaches it; only the conversation
  cascade does. No fifth mechanism that reaches prose was found.
- The substrate claim (WAL, dead tuples, backups below any application policy) is
  correct by construction and needs no probe.
- Spot-checked one census row for accuracy: `buffer_monitor.py:69` does build
  `LEFT(content, …) AS content_preview` into the journal payload.

One pressure point, stated so the owner weighs it: the ceiling argument proves A/B/C
cannot deliver *erasure*; it does not prove they deliver *nothing* — B's write-time
minimization has real prospective value. The analysis already absorbs that as rider R3
(new payloads copy content only on demonstrated need), so option D + riders is
effectively D plus B-where-free. The argument survives; the trade is stated fairly.

**Recommendation** (confidence: high): ratify D with R1–R3 as written. **What would
change my mind:** a multi-operator deployment or a concrete repo-publication plan — the
"the guarantee guards against nobody" premise is homelab-specific and is the one leg
that ages.

---

## 4. T2.31 / T2.35 / T2.50 — the measurement blockers

### 4.1 T2.31 — the contamination is real, but the claimed mechanism is refuted

The brief claims the on leg's heat is "manufactured by the off leg's traversal of the
gold set — the memories carrying heat are disproportionately the correct answers", i.e.
a self-fulfilling score. **The coupling is real; the bias direction is not.** The
arithmetic, from code actually read:

- The ablation runs at `retrieval_limit = len(entries)` = 94, the full corpus
  (`arm_ablation.py:848`, and the protocol line in all three 2026-08-06 eval reports).
- `fusion_fetch_depth(94) = max(300, 94) = 300` (`rank_fusion.py:40,66-74`), and the
  semantic channel is a pure `ORDER BY distance LIMIT :limit` with **no similarity
  threshold** (`repositories/vector.py:181-194`) — so every query's semantic arm returns
  all 94 corpus rows.
- The fused list is truncated to `limit` = 94 and `_record_access(fused)` records the
  **whole returned page** (`hybrid_search.py:87-93, 283-288`).

Therefore every one of the off leg's 102 queries bumps **every** memory's counter
exactly once: after the off leg, all 94 counters read 102 — *uniform*, not
answer-biased. With `HEAT_SCALE = 10` and baseline 0.0
(`rank_fusion.py:174, 150-151`), heat = 1 − e^(−102/10) ≈ 0.99996 for every row;
`arm_factor` = 1 + w·(s − 0) is then a constant multiplier, which preserves RRF order
exactly. The measured delta of an on/off run under today's harness is **≈ 0 by
construction — a vacuous zero, not a rigged win.** The answer-biased mechanism the brief
describes would require a page size well below the corpus size; at this protocol it
cannot occur.

Three consequences, all sharper than the brief's framing:

1. **The two named resolutions converge on the same vacuity.** Reset-between-legs: the
   on leg accrues its own uniform heat (every query still touches all 94) — vacuous.
   No-reset: uniform from the off leg — vacuous. Neither risks a false win; both
   guarantee a hollow zero, which is precisely the number `ArmNotMeasurable` exists to
   keep out of the ledger.
2. **Seed-and-freeze is the only live option, and the freeze half is load-bearing, not
   optional.** Heat saturates by count ≈ 30 (1 − e^(−3) = 0.95), so a seeded history
   with realistic counts (0–20, say) is crushed by the in-run +102 uniform additions:
   seeding without suppressing `_record_access` during the legs (or restoring counters
   between them) destroys the seeded variance. Deeper structural point: a full-corpus
   page can never produce a *discriminating* access history, so the eval's own traversal
   is incapable of generating the signal under any reset scheme — the history must be
   exogenous and modelled, which is the Fable-tier measurement-design work the brief
   correctly routes to T2.31 itself.
3. **No frozen protocol needs touching.** `FROZEN.md`'s eight decisions govern ingestion
   granularity, databases, cache keys, gate pinning, `created_at`, the refine mirror,
   seeding, and live-call reporting — none govern access recording. Doc 17 §7 demands
   determinism, which a versioned seed fixture satisfies. The precedent for adding a
   preparation step without amending anything frozen is T2.32's own `needs_artifact`
   (PPR snapshot, relation vectors); the access-history seed is the third artefact of
   that kind, plus the suppression step, which is new but of the same species.

Confidence: high — the refutation is arithmetic over code, not judgment. The brief's
*conclusion* ("T2.31 cannot be measured as specified") survives; its severity model and
its menu of fixes do not.

### 4.2 T2.35 — the claim survives; one cost refinement

Verified structurally: `w_context_boost` is coded blocked with exactly the brief's
reason (`arm_ablation.py:329-336` — the runner declares no context, the gold carries no
axis, the boost is neutral at every magnitude). **There is no cheaper honest path to a
measurement** — the boost needs a context axis to exist somewhere. The refinement:
authoring the axis into the *existing* corpus is the expensive variant, because corpus
growth re-opens the whole gold (`SLICES.md:77-84`: every live pair re-adjudicated, every
multi-hop `baseline_consequence_rank` re-measured). A **separate, dedicated context
corpus + gold file** avoids that tax entirely; nothing in doc 17 §4 requires the
seven-slice file to host every measurement, and the standing gate asks only for "a
retrieval-eval delta with its twin". It still needs SLICES.md-grade decision procedures
and Fable design — gold authoring is the honest cost either way.

**Recommendation** (confidence: medium-high): leave T2.35 blocked; mint a context-gold
authoring task scoped to a dedicated corpus; T2.35 measures when it lands. The honest
floor, if the owner deprioritises it: record "cannot show its number; magnitude stays at
its current config value" in the activation log as a result, which the standing gate
explicitly admits.

### 4.3 T2.50 — the separation reading is correct, and the multi-hop ceiling question is answered, not fatal

**Separation of powers:** correct, and not merely by runbook inference — T2.50's own
text states it ("split out of T2.32 so the model that builds the snapshot does not also
judge its number", `tasks/E2-truth-core.md:1294-1295`). The brief's author built both
arms and the harness extension; disqualified from the verdict. **Minimum independent
judge:** one fresh Fable-tier dispatch executing T2.50, whose brief hands only recorded
artifacts — the two eval reports, ledger rows `500e272d` (w_ppr@0.3) and `a1b2b903`
(w_dual@0.3), `SLICES.md`, and the standing bar — plus the runbook §6 adversarial review
its gate-feeding output already owes. No re-run is required for the verdict inputs
(below); one deterministic, zero-live-call snapshot inspection is the only new
measurement the judge may need.

**The ceiling question — attacked as instructed, and it does not hold in its strong
form.** Two findings, both from files/data the brief did not consult:

1. **The entity-linking semantics is no longer undecided — T2.32 decided it in shipped
   code.** The snapshot builds synonymy KNN edges over entity-name embeddings inside
   itself (`app/services/ppr_snapshot.py:37-41`, `_synonymy_sql` at 176-201; threshold
   0.8, top-k 5). Two same-named entity rows of different types embed identically (the
   entity-embedding cache keys on `(name_lower, fingerprint)`), so cosine = 1.0 ≥ 0.8
   and the edge exists. **PPR is a name-embedding linker; its multi-hop ceiling is
   14/14, not 6/14.** The T0.06a amendment's obligation — "state this arm's
   entity-linking semantics before reading any multi-hop verdict" — is dischargeable by
   citing that code, confirmed by one snapshot inspection (e.g. that `hv-27`'s two nodes
   are connected). The dual arm's semantics needs the same statement read off T2.94's
   channel; **Unknown here** — settled by the judge reading that reader's candidate
   join, not by argument.
2. **The attribution the slice-level report cannot support is recoverable from the
   ledger, offline, free.** Both legs' `pair_scores` are recorded per run (verified: 102
   entries per leg in `benchlib/runs/ledger.jsonl`). Computed from them:
   - `w_ppr@0.3`: the two multi-hop flips are **rg-0104 and rg-0105 — both `name-only`
     bridges (hv-27)**; zero `shared-entity` pairs flipped (several had their anchor
     *demoted* with B still absent from top-10).
   - `w_dual@0.3`: the single flip is **rg-0108 — `name-only` (acs-01)**.
   - `w_ppr@1.0` (superseded probe): **zero** multi-hop flips; temporal collapsed to
     mrr 0.0 / hit 0.0.

   Under strict node-identity semantics these gains would be impossible as traversal;
   under PPR's actual name-linking semantics the hv-27 flips are consistent with genuine
   bridge traversal through synonymy edges. The rival hypothesis — reshuffle noise, the
   exact shape the `w_importance` activation-log entry documented (+0.1429 multi-hop
   hit from perturbation, with ΔMRR −0.7745) — is not yet excluded, and the
   discriminating check is deterministic: whether B's memory receives PPR mass through
   the bridge node for those queries' seeds. That check is the independent judge's to
   run, not this document's (the brief forbids judging the arms here).

So: **the gain is uninterpretable *as reported at slice granularity*, and fully
interpretable from what is already on disk.** The number the brief most valued is not
invalidated; it is under-analysed, and the analysis needs no live calls.

**The multi-hop-up / temporal-down signature:** partially real, partially
probe-magnitude. Temporal scales with weight (w_ppr mrr 0.653 → 0.262 at 0.3, → 0.000 at
1.0; hit 1.0 → 0.5 → 0.0), so the *depth* of the collapse is a probe artefact — but it
is nonzero at the comparable-voice weight, and it has a structural candidate mechanism
(inference): temporal siblings share their subject entities, so any graph list is
time-blind by construction and injects the wrong sibling with the same mass as the right
one. The per-pair ledger data lets the judge separate signature from artefact; the gold's
shape is not the confound — the slice is doing its designed job of punishing time-blind
signals.

Confidence: high on the separation reading; high on "interpretable with the recorded
data"; medium on the traversal-vs-reshuffle question pending the judge's snapshot check.

---

## 5. The ledger row from the vacuous `w_dual` run

**Decision owed:** whether naming-in-the-report suffices or the ledger needs a
retraction row. **Owner:** controller.

**The contract:** `benchlib/ledger.py` is a generic append-only JSONL — "round-trips
whatever keys the caller passes", no schema, prior lines never rewritten. `FROZEN.md` is
silent on the ledger. Doc 17 §7 is reproducibility; §8 makes the **dated report file**
the canonical activation artifact and the gate-ledger's arm activation log the decision
record. No retraction-row semantics exist anywhere, and no precedent row of that kind is
in the file.

**Precedent for naming-in-the-report: yes, twice, the same day.** The ledger's last five
rows were inspected directly. Three of them are superseded-in-place: `83f4c11b`
(`w_heat`, vacuous — no signal wired; disclaimed in its own report's banner),
`c2470c25` (`w_ppr` at probe 1.0 — superseded magnitude; explained in the 0.3 report),
and `2ae27407` (`w_dual`, empty partition). Report-level disregard is the established
mechanism, and the decision layer will only ever cite the good runs.

**But this instance is defective in fact:** the `w_dual` report says the row "is named
here instead" while containing **no identifier for it**. Run id `2ae27407` appears
nowhere under `docs/` (grep, exit 1; `c2470c25` likewise). And this pair is the worst
case for anonymous disregard: the vacuous row and the good row are near-twins in the raw
ledger — same flag, same git sha `e4768c8f`, same weight 0.3, 91 seconds apart —
distinguishable only by their delta payloads. "Disregard the vacuous w_dual row" is not
mechanically followable today.

**Recommendation** (confidence: high): naming-in-the-report is sufficient *in kind* and
incomplete *in fact*. Fix by a docs-only edit (sanctioned separately; not made from this
analysis lane): the `w_dual` report names `2ae27407-…` as the disregarded run, and the
`w_ppr` report names `c2470c25-…` as the superseded 1.0 probe. Additionally require —
as part of the T2.31/T2.50 activation-log entries when they land — that each entry cite
its good run id **and** name any disregarded sibling rows, following the `w_importance`
entry's caveat discipline. A formal retraction row in `ledger.jsonl` is lawful under the
module contract but unwarranted: it would be a one-off convention with zero readers
(`read_runs` consumers are tests and the judge-qualification runner), solving a problem
the report-plus-activation-log layer already owns.

**Adjacent finding, sharper than the blocker itself:** the **good** `w_dual` row is
imperfectly attributed. Its recorded `git_sha` `e4768c8f` was committed 06:17:05Z; the
preparation code the run demonstrably executed (it embedded 62 relation vectors) landed
in `3f67152a` at 06:23:21Z — the run was made on a dirty tree, and
`run_smoke.git_sha()` (`run_smoke.py:245-250`) records bare `HEAD` with no dirty marker.
The one row future `w_dual` decisions would cite names a commit that cannot reproduce
it. The independent T2.50 judge should either re-run under the committed sha (warm
cache, zero live calls — their call, not this lane's) or record the dirty-sha caveat in
the activation-log entry. Longer-term, `git_sha()` appending a `-dirty` suffix is a
one-line hardening worth a minor task.

---

## Sequencing across the five

The controller's attention is the scarce resource; the blockers interact at exactly two
points — T2.54 gates blocker 1's whole chain and nothing else, and blockers 4/5 share
the T2.50 judge dispatch (whose activation-log entry is where blocker 5's naming lands).

1. **Schedule the T2.54 sitting first** — critical path for 7 of 12, and nothing else
   shortens it. Pre-draw the resample sample, pre-brief the rejection-contingency round,
   rule on Option B alongside, optionally mint T2.11a.
2. **In parallel, dispatch the independent T2.50 judge** — every input is already
   recorded; the semantics statement and the traversal-vs-reshuffle check are offline.
   This is the only measurement blocker that can close now, and it carries blocker 5's
   report-naming fix with it.
3. **Ratify T2.85 option 2 and grant the schema window now**, while the baseline is
   verifiably uncontended (T2.84 closed the granted window). The window is the
   perishable part.
4. **Ratify T2.59 option D** in the same controller pass — pure ruling, no dependency,
   closes one.
5. **T2.31 and T2.35 last** — both reduce to gold/fixture design (an exogenous access
   history; a context axis), both are standing-gate arms whose honest floor ("stays at
   zero/current, recorded as a result") is always available, and neither blocks anything
   else.

Blockers 2, 3, and 5 are rulings, not work: one controller pass covers all three.

## Findings that overturn or correct the brief, in one place

1. **T2.31's contamination mechanism is refuted** (§4.1): at `retrieval_limit = 94` every
   query's recorded page is the whole corpus, so the manufactured heat is uniform — the
   outcome is a guaranteed vacuous zero, not a self-fulfilling win; reset-between-legs
   and no-reset converge on the same vacuity; seed-and-freeze is the only live
   resolution and its freeze half (suppress recording during legs) is mandatory, not
   optional. No frozen protocol needs amending.
2. **The multi-hop gain is not uninterpretable** (§4.3): PPR's linking semantics is
   decided in shipped code (name-embedding, ceiling 14/14), and the ledger's per-pair
   scores attribute every flip — all three, across both arms, are `name-only` bridges.
   The remaining question (traversal vs reshuffle) is answerable offline.
3. **Blocker 5's disregard is currently not followable** (§5): the precedent the brief
   relies on is real, but the report never names run id `2ae27407`, and the vacuous row
   is a near-twin of the good one. One docs edit completes the mechanism; no ledger
   change is needed.
4. **The eligibility lock does not enforce the n = 93 resample** (§1): a ~1 h
   fork-plus-escalations sitting would make the gold lock-eligible with its label error
   uncertified — mechanically available, and to be refused as policy.
5. **The good `w_dual` run's ledger row is dirty-tree-attributed** (§5): its recorded
   sha predates the preparation code it executed.
