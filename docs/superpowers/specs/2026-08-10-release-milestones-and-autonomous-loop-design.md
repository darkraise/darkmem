# Release milestones and the autonomous execution loop — design

**Date:** 2026-08-10 · **Status:** design, owner-approved in conversation ·
**Supersedes nothing; amends** `docs/planning/agent-runbook.md` §6 (see §7).

## 1. The problem, measured

278 task rows, **232 done (83%)**, two gates cleared, a deployable image on
disk — and **zero releases, zero tags, no changelog**. Version fields exist and
are unmanaged (`0.2.0` backend/frontend, `0.1.0` SDK/extension). Nothing has
ever been deployed for use.

The cause is not the task count. It is that **epics carry entry gates, so work
queues behind measurement**. Gates gate *labels*, not code — `T2.95`'s serving
boundary already refuses an unbacked claim — so the serialisation buys nothing
it does not already have, and costs everything downstream of an open gate.

## 2. Version scheme

`v0.N`, one version per shipped feature-group, git-tagged. No patch discipline:
one user, one dev environment, `v0.1.3` would be ceremony.

**Two version lines.** The deployable is one image carrying API + SPA, so
backend and frontend share the product version. The SDK and extension sit
outside the box (doc 15 §2) and keep their own. Tagging syncs the product pair
only.

**v0.1 is not the schema freeze.** The environment is development and the data
is disposable by the owner's decision (2026-08-10). The baseline stays
regenerable, `gate.sh`'s single-revision assertion stays live, and CLAUDE.md's
freeze trigger — *the first deploy whose data must survive* — remains in the
future.

## 3. The release ladder

| Version | Headline | Tasks | New tasks |
|---|---|---|---|
| **v0.1** | **It runs.** Capture, retrieval, code graph, 21 jobs, MCP, SPA, SDKs, extension | already done | 0 |
| **v0.2** | Resume & checkpoints | T3.17, T3.21, T3.18 | 3 |
| **v0.3** | Auto-context into agent tools | T3.10, T3.20, T4.06, T4.07, T4.08 | 5 |
| **v0.4** | Synthesised articles, shipped unlabelled | T3.02–T3.06, T3.23 | 6 |

**14 tasks to the next three releases**, against 44 open today. That number is
the visibility fix.

**The 44 open rows account for exactly three ways**, and the arithmetic is
stated so it can be checked rather than trusted:

| Bucket | Count | What |
|---|---|---|
| Assigned to v0.2–v0.4 | **14** | the ladder above |
| Parked | **24** | EH1 documents/PKM (15), research agent (T3.07–08), API keys and webhooks (T4.01–05), the two audit records (T4.09–10), E1's straggler T1.54 |
| Gate track (§4) | **6** | T2.114, T2.116, T3.22, T3.24, TH1.10, TH1.17 — measurement runs and gold work, which produce gates, not features |

Parked work carries `Version: —` and stops implying imminent effort. The gate
track is **not** parked: it is live work on its own milestone line, and two of
its rows (T2.114, T2.116) are open findings from 2026-08-10.

## 4. Gates produce versions instead of blocking them

Clearing a gate is a user-visible change, so it ships as a release:

- **G-C + G-D clear → a version whose headline is "badges go live."** The v0.4
  articles gain their `grounded` badge with no code change.
- G-E and G-F likewise, in their turn.

**Per-task gate marking** replaces the epic-level entry gate:

- `Gate: G-x (label)` — build and ship it; only the badge waits. **Most tasks,
  including all of v0.4.**
- `Gate: G-x (blocking)` — genuinely cannot proceed. Rare (T2.41).

## 5. The autonomous loop

`/loop` in dynamic mode. One task per iteration, start to finish.

**Each iteration:**
1. Read `progress.md` (canonical on `master`) and the current version's task set.
2. Take the next unclaimed task; claim it in one commit.
3. Execute under the runbook: read the owning design doc, TDD, mutation-drill
   every guard, real Verify output.
4. `./scripts/gate.sh`. Red that the change caused → fix. Red it did not cause →
   stop (§6).
5. Commit with the reasoning in the message; update `progress.md` on `master`.
6. Check stop conditions; continue.

**At a version boundary:** `./scripts/gate.sh --full` → **Fable review of the
whole version** → tag → CHANGELOG → sync version fields → **deploy** → stop and
report. The owner looks before the next version starts.

**Review cadence (owner ruling 2026-08-10).** Fable reviews at **epic or
version completion**, as the final gate for release — *not* per Opus-tier task.
Per-task review at this volume costs more than it catches, which is runbook §6's
own reasoning; this narrows its letter and is recorded as an amendment (§7).

**Fable as advisor.** Where Opus or Sonnet cannot decide, the loop **asks Fable
rather than guessing**. Named classes: a spec/doc conflict, a design call with
more than one defensible answer, "defect or deliberate?", and any semantic gate.
Fable's answer is the decision.

## 6. Stop conditions — the loop ends and reports

Fable is the escalation target. **The owner is reached only when Fable says a
call is owner-only, or one of these fires:**

1. A gate number lands below its bar. Report it; never re-run to improve it.
2. A Tier-3 amendment — the discovery contradicts the design corpus.
3. Anything that moves the gold sha or spends a measurement attempt.
4. A decision whose validity depends on **who** makes it rather than on the
   reasoning — the contamination class, not an authority class.
5. A missing credential or unreachable external service.
6. The same task fails verification three times for different reasons.
7. A red floor the loop's own change did not cause.
8. **The tell.** If the loop finds itself constructing an argument for why it
   *may* make a call it already flagged as the owner's, that construction is the
   stop signal.

Conditions 4 and 8 are not theoretical. On 2026-08-10 this session drafted a
T2.114 ruling, argued it was content-blind, and a Fable reviewer refuted it —
the argument's evidential value depended on the author not having read the
scoreboard, and the pre-positioned fallback "reads as its author's own doubt."
Everything in v0.2–v0.4 sits outside all eight conditions.

## 7. State, memory, and context loss

**The repository is the state machine.** `progress.md`, `gate-ledger.md`, the
task files and CHANGELOG carry every fact the loop needs. Each iteration
rebuilds its picture from them and **never depends on conversation context
surviving compaction**. Anything the next iteration must know is written to a
file before the current one ends.

Two supporting stores, neither load-bearing: file memory for narrative session
state, and darkmem itself for verified, durable facts.

**Runbook amendment (Tier 2).** §6 currently requires Fable review of "every
Opus-tier task, and every task whose output feeds a gate claim". The first
clause is replaced by review at epic/version completion. The second clause
**stands unchanged** — anything feeding a gate claim is still reviewed, because
that is what a gate's credibility rests on.

## 8. Proportionality

Over-engineering is a named failure mode here, with a concrete test:

> **Does this artifact outlive the task?** If no, do the simple thing inline.

Today's counter-example, recorded because it is the pattern to avoid: a
committed, documented premise-draw module was written for a two-pair repair that
a ten-line inline computation would have served — and the module's own defect
then cost a dispatch round.

The same rule on documents: a design note that will be read once does not need a
section hierarchy.

## 9. Success criteria

- `v0.1` tagged, deployed, and demonstrated — setup wizard walked, a memory
  captured through a door and retrieved, MCP answering. Not asserted from a
  green suite.
- Each subsequent version: tasks `done`, `--full` green, Fable-reviewed, tagged,
  changelogged, deployed.
- `progress.md` shows a `Version` column, so any row answers "which release?".
- The loop runs v0.2 unattended end to end and stops at the tag.

## 10. Out of scope

Semver patch releases, upgrade/migration guides, release notes for external
users, publishing to any registry, and the schema freeze. All revisit when the
repo is published or the data must survive.
