# The autonomous loop — operating contract

**Opened 2026-08-10.** This is the document a fresh session reads to run the
release ladder unattended. It lives in the repo rather than in a prompt, because
the loop's whole defence against context loss is that the repository is the
state machine.

Design: `docs/superpowers/specs/2026-08-10-release-milestones-and-autonomous-loop-design.md`.
Task contract: `docs/planning/agent-runbook.md` — this narrows §6's review
cadence and changes nothing else.

## 1. The state machine

Four files carry every fact the loop needs. It rebuilds its picture from them at
the start of **every** iteration and never relies on conversation context
surviving compaction.

| File | Branch | Carries |
|---|---|---|
| `progress.md` | `master` | task state — owner, status, commit, review, note |
| `RELEASES.md` | `master` | scope — which version each open task ships in |
| `gate-ledger.md` | `master` | evidence — measured numbers, bars, verdicts |
| `CHANGELOG.md` | the release branch | what shipped |

The split is not an accident and `RELEASES.md` states it: **planning state is
canonical on `master`** (the generator that derives the `Version` column refuses
to run anywhere else), and **product artifacts travel with the code**, because
`release.sh` commits the version sync into the tree it tags. From an epic branch,
read the first three with `git show master:<path>`.

**Anything the next iteration must know is written to a file before the current
one ends.** A fact that exists only in the conversation does not exist.

## 2. The iteration — one task, start to finish

1. Read `progress.md` on `master` and the current version's task set in
   `RELEASES.md`.
2. Take the next unclaimed task in that version. **Claim it in one commit** —
   Owner set, status `wip`. If two agents race, the later commit loses and that
   agent picks another task.
3. Execute under the runbook: read the task's owning design doc, TDD,
   **mutation-drill every guard**, record the **real** Verify output — not
   "should pass", the output.
4. `./scripts/gate.sh`. Red that the change caused → fix it. Red it did not
   cause → **stop** (§5, condition 7).
5. Commit with the reasoning in the message. Update `progress.md` on `master`:
   status, commit sha, one-line note.
6. Check the stop conditions. Continue.

Never run two pytest sessions at once — they share `darkmem_test`, and conftest
drops the schema at session start, so a collision produces failures
indistinguishable from a real regression. Pass the Bash tool's own `timeout`
on long runs; a tool-level auto-background leaves work unverified. **Never pipe
a gate run through a filter that discards its output** — one red `frontend test`
step on 2026-08-10 is permanently undiagnosable because of exactly that, and
`gate.sh` streams rather than persisting per-step logs.

**Start from a branch that is current with `master`.**
`test_the_generator_is_the_same_on_this_branch_and_on_master` compares
`gen_progress.py` across the two, so a branch cut before it last changed reds
the floor for a reason the loop's own work did not cause — which routes
straight into stop condition 7 and ends the session over a stale checkout.
Rebase or re-land the generator first.

## 3. The version boundary

Write the `## vN.N` **CHANGELOG** section → **Fable review of the whole
version** → `./scripts/release.sh vN.N` → **stop and report**.

**Do not tag by hand first.** Spec §5 lists the order as "…→ tag → CHANGELOG →
sync → deploy", which was written before `release.sh` existed and **cannot be
executed**: the script refuses a version that is already tagged, and it writes
the tag itself, last, only after the deployment serves the new version. A
session following §5's arrows literally gets `v0.2 already tagged` and is one
bad inference away from deleting a tag or hand-deploying past the health gate.
The order above is the executable one; §5's sketch is flagged for the owner to
amend rather than silently rewritten.

`release.sh` runs `gate.sh --full` itself, so there is no separate gate step —
and it refuses to tag if the gate is red, the tree is dirty, a version field
failed to sync, the gate left changes it does not recognise, or nothing on
`:8000` serves the new version.

The owner looks before the next version starts. `release.sh` refuses a
malformed version, a dirty tree, an existing tag and a changelog that does not
name the release; it runs the gate, syncs the three product version fields,
builds, deploys, and writes the tag **last**, only after `/health` answers 200.

**Review cadence.** Fable reviews at **epic or version completion**, as the
final gate for release — *not* per Opus-tier task. This narrows runbook §6's
first clause and is recorded as a Tier-2 amendment in the design spec §7. Its
second clause **stands unchanged**: anything feeding a gate claim is still
reviewed, because that is what a gate's credibility rests on.

## 4. Fable is the escalation target

Where Opus or Sonnet cannot decide, **ask Fable rather than guessing. Fable's
answer is the decision.** Named classes: a spec or doc conflict, a design call
with more than one defensible answer, "defect or deliberate?", and any semantic
gate.

Reach the owner only when **Fable says the call is owner-only**, or a stop
below fires. Verify a sub-agent's load-bearing factual claims against the tree
before acting on them; a ruling built on a wrong fact is still wrong.

## 5. The eight stops — the loop ends and reports

1. A gate number lands below its bar. That is the gate working. Report the
   number; **never re-run to improve it**, never widen the bar to fit it.
2. A **Tier-3 amendment** — the discovery contradicts the design corpus.
3. Anything that moves the gold sha or spends a measurement attempt.
4. A decision whose validity depends on **who** makes it rather than on the
   reasoning — the contamination class, not an authority class.
5. A missing credential or an unreachable external service.
6. The same task fails verification three times for different reasons — the
   plan, not the attempt, is probably wrong.
7. A red floor the loop's own change did not cause.
8. **The tell.** If the loop finds itself constructing an argument for why it
   *may* make a call it already flagged as the owner's, that construction **is**
   the stop signal.

Conditions 4 and 8 are not theoretical. On 2026-08-10 a session drafted a
T2.114 ruling and argued it was content-blind; a Fable reviewer refuted it —
the argument's evidential value depended on the author not having read the
scoreboard, and the pre-positioned fallback "reads as its author's own doubt."

**How far a stop reaches — scoped per condition, and PENDING OWNER
RATIFICATION.** Spec §6 is titled "the loop **ends** and reports", i.e. a full
halt. Narrowing that is not the loop's call to make silently, so the scoping
below is written down to be ruled on. Until it is ratified, prefer the full
halt where the two disagree.

- **Conditions 1, 2, 3, 4, 7, 8 → full halt.** Each one means the loop's own
  judgement or its evidence is in question, and continuing compounds it. For 7
  specifically, continuing is not even possible honestly: every task's
  definition of done requires a green floor, so "carry on with the next task"
  and "never mark a task `done` with a failing check" cannot both hold.
- **Conditions 5 and 6 → stop that task, not the loop.** A missing credential
  or a task that has failed three ways blocks *that* task and says nothing
  about the others. Mark it `blocked` with the reason in its Note, take the
  next one, and report what was left and why.

The v0.1 cut is the worked example: Task 2 hit condition 2, halted, and the
remaining tasks shipped — but that was under an explicit owner instruction to
exhaust the startable work, not under this document. That instruction is what
the ratification above is asking to make standing.

## 6. Proportionality

> **Does this artifact outlive the task?** If no, do the simple thing inline.

The recorded counter-example: a committed, documented premise-draw module was
written for a two-pair repair a ten-line inline computation would have served,
and the module's own defect then cost a dispatch round. The same rule on
documents — a design note that will be read once does not need a section
hierarchy.

## 7. What the loop may never do

- Write **any** gold set. There are five, not one: `extraction_bench/gold.json`
  and `gold_heldout.json`, and `benchlib/`'s `retrieval/`, `entailment/` and
  `contradiction/` sets. Stop condition 3's "the gold sha" means whichever one
  a task would touch — naming only the entailment set, as this list first did,
  invites the reading that the other four are fair game.
- Spend a G-D measurement attempt, or any measurement attempt.
- Freeze the schema. `v0.1` is not the freeze; the trigger — the first deploy
  whose data must survive — remains in the future.
- Move a bar, in either direction, to make a run pass.
- Run two pytest sessions at once.
- Mark a task `done` with a failing check. If the suite is red the task is
  `blocked` and the Note says so. That rule is the whole point of `progress.md`.
- Publish to any registry (spec §10). `release.sh` builds with
  `DARKMEM_PUSH=0` deliberately: a local tag can be deleted, a pushed image
  cannot.
