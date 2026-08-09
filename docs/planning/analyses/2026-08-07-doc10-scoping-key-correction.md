# Proposed correction — doc 10 §6's citation re-verifier scoping key

**Status: RATIFIED 2026-08-07 — Option A applied to doc 10 §6.** The owner ruled Option A
(minimal fix); Option B's paragraph was not adopted, so §6 still states the changed-file
set as its cost bound and `CLAUDE.md`'s code-indexing section remains the record of
T2.48's shipped sha-comparison deviation. The proposal text below is retained as the
reasoning behind the edit.

**Raised:** 2026-08-07, from T2.48's execution. **Confirmed independently** by T2.48's
Fable adversarial review, which traced it in the shipped code rather than accepting the
executor's account.

## The defect

Doc 10 §6, the paragraph beginning *"The citation re-verifier is the second sanctioned
crossing"* (line 295), says the re-verifier

> walks the `fact_sources(kind='code', origin_key=repo_id)` evidence rows whose
> **`detail.symbol_key` falls in the run's changed/deleted file set**

`detail.symbol_key` does not hold a file path for every citation basis. In
`fact_lift.py`:

- **line 875** — language-basis citations: `symbol_key=file_path`. A path.
- **line 895** — import-basis citations: `symbol_key=target_key`. A **module key**
  (`httpx`), never a path.

Import-basis citations were **10 of 12** in the executor's census (the committed fixture
produces 5 of 7 — the count was corrected in T2.48's fix round; the ratio is the point,
not the absolute). So a literal implementation of §6 matches only the language-basis
citations against a changed *file* set, silently skips every import-basis one, and
**reports success**. The failure has no symptom: the job runs, finds nothing, and logs a
clean pass.

`detail.file_path` is the field that carries a path for every basis.

## Why nothing is broken today

T2.48 did not implement the clause literally. It scopes by comparing a citation's
`detail.reverified_at_sha` (falling back to the birth sha) against the repository's
`last_indexed_commit`, which is basis-independent. `CLAUDE.md`'s code-indexing section
records that deviation and its reason, so a reader of the baseline is not misled while
this correction waits.

The exposure is entirely forward-looking: **the next task to read §6 literally will build
a walk that reports success while doing almost nothing.**

## Proposed wording — Option A (minimal, recommended)

Replace, in that sentence only:

> …evidence rows whose `detail.symbol_key` falls in the run's changed/deleted file set,
> re-resolves each `symbol_key` against the new HEAD's `code_graph_nodes`…

with:

> …evidence rows whose **`detail.file_path`** falls in the run's changed/deleted file set,
> re-resolves each `symbol_key` against the new HEAD's `code_graph_nodes`…

and append to that paragraph's *Why*:

> **`detail.file_path`, not `symbol_key`, is what a file set is matched against.**
> `symbol_key` is basis-dependent — a path for a language-basis citation, a module key
> (`httpx`) for an import-basis one — so matching a file set against it would skip every
> import-basis citation and report a clean pass. The re-resolution still keys on
> `symbol_key`, which is what invariant 9's owner-qualified addressing requires; only the
> *scoping* predicate changes field.

This is the smallest edit that closes the trap. The re-resolution half is untouched and
remains correct.

## Option B (fuller) — also record the shipped alternative

Option A plus a sentence acknowledging that a changed-file set is not the only admissible
scoping, since T2.48 shipped a different one for a stated reason:

> Scoping by the run's changed-file set is the cost bound this section fixes, but it is
> not the only admissible one. T2.48 scopes instead by comparing a citation's
> `detail.reverified_at_sha` against its repository's `last_indexed_commit` — the
> persisted-set design depends on `record_event`, which never raises, so a swallowed emit
> would strand a run's citations permanently and the backstop healing it would have to be
> this same sha comparison. The declared cost is that an unchanged file's citation is
> re-resolved once per HEAD move rather than never, bounded by citation count (10–200),
> not repository size.

**Recommendation: Option A**, with Option B's paragraph as a separate decision. Option A
fixes a defect; Option B changes what the section *decides*, which is a larger edit than
a correction and deserves its own consideration.

## What this is under the amendment protocol

**Tier 3.** Runbook §5: "a design doc is wrong or ambiguous" is a stop-and-escalate
trigger, and the corpus doc outranks both the plan and execution reality until a human
rules. T2.48 logged it as Tier 1, which its review flagged as the wrong tier — the
correction is recorded here rather than in an epic file's amendment log for the same
reason.

Nothing is blocked on this. T2.48 is merged, green, and does not depend on the clause.
