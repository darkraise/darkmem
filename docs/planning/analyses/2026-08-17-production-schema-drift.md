# Production's schema drifted from the baseline, and `article_synthesis` has been dead because of it

**Measured 2026-08-17, read-only against the live compose stack.** Found while
verifying G-E's preconditions after the owner ruled "arm the loop, wait weeks".

## The finding

`article_synthesis` fails on **every** scheduled run in production and has been
recording the same error:

```
column "resynthesis_held_hash" does not exist
[SQL: SELECT id, resynthesis_held_hash FROM knowledge_articles
      WHERE project = $1 AND status <> 'superseded'
        AND resynthesis_held_at IS NOT NULL]
```

`job:article_synthesis` carries `"last_status": "error"` with that message and a
`last_run_at` of the most recent 05:00 tick. The job is enabled and firing; it
dies before doing anything.

**The consequence for G-E is total.** G-E measures per-article claim-support
coverage across the production corpus. Production holds 0 articles, and with the
synthesis job dead it would hold 0 articles no matter how large the memory corpus
grew. **Growing the corpus was never sufficient on its own**, and the plan
approved this morning — arm the research loop, wait weeks, then measure — would
have run its full course and produced nothing.

## The drift, sized exactly

Production's database is stamped revision `0001`. The tree's baseline is also
`0001`. Compared against a scratch database freshly migrated from the tree's
`0001_baseline.py`, production is missing **five columns across two tables and no
tables at all**:

| Table | Missing column |
|---|---|
| `knowledge_articles` | `resynthesis_held_at` |
| `knowledge_articles` | `resynthesis_held_hash` |
| `knowledge_articles` | `resynthesis_held_coverage` |
| `api_keys` | `key_id` |
| `api_keys` | `revoked_at` |

The `knowledge_articles` three are T3.05's staleness gate and debounced
re-synthesis. The `api_keys` two belong to the E4 API-key work. Both landed in
the baseline **after** production's database was created.

`api_keys` currently holds 0 rows, which is the only reason that half is not also
throwing — the surface is `done` and shipped in v1.0, and the first key created or
listed in production hits the same wall.

## Why it happened, and why nothing caught it

This is the documented hazard of the pre-freeze baseline policy, arriving
silently. CLAUDE.md states it: until the freeze, a schema change **regenerates
`0001_baseline.py` in place** and *you drop and recreate the database*; it never
appends a `0002`.

The revision id therefore never moves. Containers migrate at startup via
`entrypoint.sh`, but `alembic upgrade head` on a database already stamped `0001`
compares current to head, finds them equal, and does nothing. **So no deployed
database ever picks up a baseline change**, and every deploy since production's
database was created has reported a clean successful migration while shipping
code against a schema it does not have.

The drop-and-recreate half of the policy is prose. Nothing executes it, nothing
checks it, and no gate compares a deployed schema against the baseline — so the
divergence is invisible until a query names a missing column at runtime, on a
background job whose failure goes to a `config` row rather than to anyone's face.
`gate.sh` asserts the tree holds exactly one revision; it says nothing about
whether any running database matches it.

## The ordering consequence, which is the reason this is urgent

The repair is to drop and recreate production's database — the policy's own
remedy, cheap today: production holds **2 memories, 1 candidate fact, 0 articles,
0 API keys**, and the owner ruled on 2026-08-10 that this environment's data is
disposable. The schema freeze has not happened and this is not it.

**That repair must happen BEFORE the G-E corpus is grown, not after.** The
approved sequence was arm the loop, grow a corpus over weeks, measure G-E. If the
drift is repaired at the v1.0 deploy instead, the drop destroys the corpus the
wait was for. The corrected order is forced:

1. Drop and recreate production's database from the current baseline.
2. Deploy an image built from current `master` (production runs `0.5.0`, which
   predates T3.28's config surface, G-C's minted promotion record and T2.125's
   entailment record — none of which are in the running image).
3. Re-run setup / re-seed the eight LLM purposes, **including the `verification`
   row written today**, which the drop destroys.
4. Arm `auto_research` and start the corpus clock.
5. Measure G-E when the corpus supports articles.

Step 3 is easy to forget and expensive to notice: the `verification` purpose row
was written by hand on the owner's 2026-08-17 ruling and is not in
`llm_seed.py`'s defaults at the qualified identity — the seed points that purpose
at a local Ollama model, not at the `gpt-5.5` identity `fd39e7b2c47fa375` the
minted record binds to.

## Repair executed, 2026-08-17

Owner-authorised the same day ("drop and recreate now", plus "interim deploy, tag
later"). What ran, in order:

1. Full `pg_dump` to `/root/darkmem-backups/pre-v1.0-schema-repair-2026-08-17.sql`;
   the eight `llm_purpose_configs` rows and the `admin_password_hash` row captured
   separately as column-inserts for restore.
2. Image built from `master` at `25e4b41c`, tagged `v1.0-rc-schema-repair`,
   `25e4b41c` and `latest`. **Built with `DARKMEM_PUSH=0` and not pushed** —
   runbook §7 forbids publishing to any registry.
3. API stopped, database dropped and recreated, API started on the new image;
   `entrypoint.sh`'s `alembic upgrade head` laid down the current baseline.
4. Admin hash and all eight purpose rows restored, `verification` among them at
   the qualified `gpt-5.5` identity.

Verified after: `/health` returns `{"status":"ok","pipeline":true,...}`; all five
previously-missing columns present; the exact query that had been failing now
succeeds; every job loop started, `article_synthesis` included; and
`promotion_metrics_record.json` **is now in the running image for the first
time**, so G-C's promoted and born fact statuses reach production readers.

`verification_qualification.entailment.json` is still absent from the image — it
lives on the unmerged `feat/t2.124-fresh-gold` branch and arrives with that merge
and the next deploy. Until then production resolves the `verification` purpose
correctly and still cannot serve a grounded label.

`auto_research` was then written as `{"enabled": true, "max_findings_per_run": 20,
"max_content_chars": 8000}` and confirmed read back as
`ResearchBudget(enabled=True, ...)`.

**Arming is not driving, and the G-E plan should not be read as if it were.** The
loop ships with no `JobRegistry` job on purpose — a cron'd research pass would
refetch the same sources every tick, which is the manufactured-corroboration
hazard the origin rule exists to prevent. Its one door is MCP `research_run`, and
`ResearchGatherer` has no in-tree implementation by design, so **the caller must
be the gatherer**. Nothing in production will now produce a research origin on its
own. Growing the G-E corpus is a standing operational commitment — an MCP agent
with real web access filing real findings, repeatedly, over weeks — not a
configuration state that has been reached.

## What should exist and does not

A check that a deployed database's schema matches the baseline the running image
was built from. Today the only signal is a runtime `UndefinedColumnError` on
whichever query names a missing column first, routed to a job's `last_error`. The
same class of failure is waiting in `api_keys` behind a zero row count.

That is a task, not a fix to make here.
