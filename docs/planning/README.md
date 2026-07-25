# darkmem — implementation planning

**Status:** planning corpus, opened 2026-07-25. Living documents — see the
amendment protocol in [`agent-runbook.md`](agent-runbook.md).

This directory is the bridge between the closed design corpus (`docs/design/00–20`)
and executable work. The design docs say *what darkmem is*; these say *what to build
next, in what order, by which agent, and how anyone knows it is done*.

## Read in this order

| Doc | What it is | Read it when |
|---|---|---|
| [`feature-epics.md`](feature-epics.md) | The epic spine: seven roadmap lanes, ~35 feature rows, each traced to an owning design doc. | Once, for orientation. |
| [`agent-runbook.md`](agent-runbook.md) | The task contract every agent follows: how to pick up a task cold, the model routing policy, the verification bar, the amendment protocol. | Before executing any task. |
| [`tasks/`](tasks/) | One file per epic, each a numbered task list. This is the work. | When you pick up a task. |
| [`progress.md`](progress.md) | Live status of every task. | Continuously. |
| [`gate-ledger.md`](gate-ledger.md) | The measured evidence that cleared each gate G-A…G-G. | At a phase boundary. |
| [`e2e-test-plan.md`](e2e-test-plan.md) | What gets end-to-end coverage, with what fixtures, at which merge gate. | When a task's acceptance names an e2e spec. |
| [`risks-and-lanes.md`](risks-and-lanes.md) | What may run concurrently, what strictly serialises, and the failure modes to watch. | When scheduling more than one agent. |
| [`plan-review.md`](plan-review.md) | The 2026-07-25 adversarial review: 49 findings and their dispositions. | When you suspect the plan is wrong — check whether a reviewer already found it. |

## The task files

| Epic | File | Tasks | Phase gate |
|---|---|---|---|
| E0 — Baseline & harness | [`tasks/E0-baseline-and-harness.md`](tasks/E0-baseline-and-harness.md) | 19 | G-A |
| E1 — Engine core at target shape | [`tasks/E1-engine-core.md`](tasks/E1-engine-core.md) | 75 | G-B |
| E2 — The truth core (L2) | [`tasks/E2-truth-core.md`](tasks/E2-truth-core.md) | 53 | G-C / G-D |
| E3 — Synthesis & reach (L3) | [`tasks/E3-synthesis-and-reach.md`](tasks/E3-synthesis-and-reach.md) | 26 | G-E |
| E4 — Hardening & scale | [`tasks/E4-hardening-and-scale.md`](tasks/E4-hardening-and-scale.md) | 10 | demand-gated |
| EH1 — Documents / PKM (horizon) | [`tasks/EH1-documents-pkm.md`](tasks/EH1-documents-pkm.md) | 17 | G-F |
| EH2 — .NET migration (horizon) | [`tasks/EH2-dotnet-migration.md`](tasks/EH2-dotnet-migration.md) | outline only | G-G |

**200 tasks** across six executable epics. Each carries a model tier, a **size**, its
dependencies, its owning design doc, its honesty tag, and the gate it serves.

Sizes are S (≤ ~2h), M (one focused session — the target), and L (more than a day).
Distribution: 31 S / 141 M / 28 L. **An `L` task may not be executed directly** — it
needs a reviewed step-level plan first (runbook §3).

The corpus was adversarially reviewed on 2026-07-25 by three independent Fable-tier
reviewers; 49 findings and their dispositions are in
[`plan-review.md`](plan-review.md). That review added 32 tasks the first draft had
missed — chiefly the homelab cutover, the deployment artifact, demo retirement, the
measurement runners, and the facts/articles retrieval channels.

EH2 is deliberately **not** broken into tasks. It is appetite-gated behind G-G, which
requires the Python target shipped first; task-level detail written now would be
obsolete before anyone reads it. Its file records the entry conditions and the proven
spikes so the lane can be planned properly when it opens.

## Three rules that override anything written here

1. **The design corpus wins.** On any conflict between a task and `docs/design/00–20`,
   the design doc is right and the task is a defect. Fix the task (see the amendment
   protocol), never the doc.
2. **No layer advances on intuition.** Every phase boundary is a measured number in
   `gate-ledger.md`, not a judgement call (doc 20 §4).
3. **Scaffolding is not substrate.** A task that lands an object inert is done when the
   object is landed *and labelled inert* — never when it "would work if wired"
   (invariant 23).
