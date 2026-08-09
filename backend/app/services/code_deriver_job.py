"""T2.96 — the production trigger for `code_deriver.assert_repo_graph`.

T2.27 shipped the Layer-1 assertion primitives (`derive_assertions`,
`assert_repo_graph`, `strip_repo_assertions`) with no caller anywhere in
`backend/app`, so `entities.repo_ids[]` / `entity_relations.repo_ids[]` had a
writer production never reached — confirmed in the schema inventory (doc 19
§6 / §7) and the gap this module closes.

**Why a Tier-C job rather than a hook on `CodePipeline.run`.** A reindex hook
is more direct — it runs exactly when a repo's imports could have changed —
but it only reaches repos indexed *after* it lands, so every repo indexed
before this task ships would sit with empty `repo_ids[]` until its next
reindex, which may never come for a repo nobody touches again. It would also
have to share the reindex background task's failure surface
(`repo.status`, `pipeline_failures` under `pipeline_name="code_index"`) or
grow a second one inline, either of which risks a derivation failure reading
as (or masking) an index failure. A job sweeps every already-indexed repo on
its own cron regardless of when it was last reindexed, and journals its own
failures under a `pipeline_name` the index run never touches. The cost is
staleness between an import change and the next tick, bounded by
`CODE_DERIVER_MIN_INTERVAL_SECONDS` — the same trade every other Tier-C sweep
in this file already makes (`code_reconcile`, `ppr_snapshot`).

**Not a dream-job family member.** Contract 6 fixes that family at six
(`app/services/dream_jobs.py`); this job registers directly in `app/main.py`,
the same way `ppr_snapshot` and `code_reconcile` do.

**Why re-derive every indexed repo on every tick, with no staleness
tracking.** `assert_repo_graph` is a pure DB read + write with no model
call — the LLM-free clause `test_code_deriver.py` enforces structurally —
and it is idempotent per repo (T2.27's strip-before-rewrite, inherited
here): re-running it costs a strip-and-rewrite, never a duplicate row.
Tracking "assertions older than indexed HEAD" would need either a new
column (schema changes are out of this task's scope this round — T2.98
owns the baseline) or a `config` row shaped like a per-repo cursor map,
both of which add real bookkeeping to skip work that already costs nothing
but a handful of statements per repo. If repo counts ever make that cost
real, a rotating batch cursor (mirroring `ppr_snapshot`'s) is the next
step, not this one.
"""
from __future__ import annotations

CODE_DERIVER_JOB_KEY = "code_deriver"

# Distinct from `pipeline_name="code_index"` (CodePipeline's own failure
# rows) so a derivation failure never reads as, and never overwrites, the
# index run's own failure state for the same repo.
CODE_DERIVER_PIPELINE_NAME = "code_deriver"

# Minute-precision, five-field: hourly, staggered off the top-of-hour
# cleanup jobs (`0 * * * *`) and `ppr_snapshot` (`30 * * * *`) so they don't
# all wake the loop in the same tick.
CODE_DERIVER_CRON = "50 * * * *"

# Floor beneath the cron, protecting against a runaway operator-set
# expression the same way every other job's floor does.
CODE_DERIVER_MIN_INTERVAL_SECONDS = 300

# Derivation is a handful of SELECTs and upserts per repo with no model
# call; this ceiling only guards against a stuck connection holding the
# per-job lock, the same role it plays for every other job in this file.
CODE_DERIVER_MAX_RUN_SECONDS = 900
