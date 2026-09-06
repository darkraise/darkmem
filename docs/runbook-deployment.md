# Runbook — deploying darkmem on this machine

The compose stack, what a deploy does and does not carry, and the one failure
mode that is silent. Written 2026-08-17 after production was found running
against a schema it did not have.

## The stack

One image (`darkraise/darkmem`) carrying the API and the built SPA, plus
Postgres. Both sit on the stack's own bridge network with explicit publishes —
the app `8000:8000`, Postgres `127.0.0.1:5432:5432` (host loopback only, so
`pg_dump` and `psql` below work unchanged). Nothing binds `:80`.

Renamed from `darkraise/darkmem-api` and moved off `network_mode: host` on
2026-08-18. The compose *service* was renamed `darkmem-api -> darkmem` in the
same change, so the container is now `darkmem-prod-darkmem-1`, and a stack
still running under the old service name is an orphan: the first cutover needs
`docker compose down --remove-orphans`.

```
./scripts/build-push.sh <version>      # builds; DARKMEM_PUSH=0 keeps it local
DARKMEM_VERSION=<version> docker compose up -d
```

`.env` must carry `DB_PASSWORD` and a `JWT_SECRET` of 32+ characters, plus
`COOKIE_SECURE=false` for a plain-HTTP LAN.

**Publishing is a master push's consequence** (changed 2026-08-29; this said
"a tag's consequence, and nothing else's", which described the flow before CI
took over versioning). Nothing local pushes: `build-push.sh` honours
`DARKMEM_PUSH=0` and `release.sh` sets it, so a local cut only builds and
deploys on this machine. What publishes is `git push origin master` — that runs
`.github/workflows/release.yml`, which derives the next version from the
conventional-commit types since the last tag, re-runs the whole CI pipeline,
pushes the image to Docker Hub (`darkraise/darkmem`) and GHCR
(`ghcr.io/darkraise/darkmem`), and **only then** writes the tag and the GitHub
release.

Two guards stand where the hand-pushed tag used to. A push releases only if it
carries a `feat`, `fix`, `perf` or breaking commit — a docs-only or chore-only
push cuts nothing — and only if `CHANGELOG.md` already has a `## vN.N.N`
section for the version the commits derive. That second check runs before the
suite and before any push, so a version can never ship with no account of what
changed. The changelog stays hand-written; the GitHub release body is generated
from the commits alongside it.

The reasoning behind the old rule still holds and is why the tag is written
last rather than first: a tag that exists is a tag whose image is already in
both registries, so a failed publish leaves nothing to explain away. A branch
push and a pull request publish nothing. Deploying this host still uses the
locally built image and never needs the registry.

`scripts/release.sh` no longer tags. It syncs the version fields, builds,
deploys and probes `/openapi.json` — the local proof that the version you are
about to cut actually serves. CI sees the synced fields, skips its own bump and
publishes under the same number.

## The silent failure this runbook exists for

**Before the schema freeze, a deploy can succeed and leave the database wrong.**

A schema change *regenerates* `0001_baseline.py` in place rather than appending a
revision, so the revision id never moves. `entrypoint.sh` runs
`alembic upgrade head` at every container start; on a database already stamped
`0001` that compares `0001` to `0001`, finds them equal, and does nothing. The
deploy reports a clean migration while the code goes on to query columns the
database does not have.

Measured on production 2026-08-17: five columns missing
(`knowledge_articles.resynthesis_held_*`, `api_keys.key_id`/`revoked_at`), and
`article_synthesis` dying on every scheduled run for days. It was invisible
because a job's failure lands in its own `config` row — not a log anyone reads,
not a health check.

**The guard.** `app/schema_guard.py` runs from `entrypoint.sh` after the
migration. It stamps a hash of the baseline file into the database it migrated
and compares on every boot:

- no stamp → record it and proceed (fresh database, or one predating the check)
- stamp matches → proceed
- **stamp differs → refuse to start**, printing the remedy

It fails closed on purpose. Serving on is quiet and cost days; refusing is loud
and the fix is cheap before the freeze. **There is no override flag**, because an
env var to skip it would be reached for at exactly the moment it is protecting
you.

**Retire this check at the freeze.** Once the baseline is frozen and changes
arrive as ordinary additive revisions, the revision id moves again and alembic's
own comparison does the job. Retiring it is part of the freeze protocol
(`docs/planning/baseline-schema-inventory.md`), not a later cleanup.

## Deploying a purely additive baseline change

**Read this before reaching for the drop below.** The drift-recovery procedure
discards the database; when the baseline diff is *only* new objects, it does not
have to be. Rehearsed against a copy of production on the dev database
(2026-08-23, the `llm_usage` cutover).

**The precondition, and it is the whole safety argument.** Diff the baseline
against the deployed revision and confirm there are **no deletions, and no change
to any existing object** — the new statements must be whole new tables and
indexes, standing alone:

```bash
git diff <deployed-ref>...HEAD -- backend/migrations/versions/0001_baseline.py
```

If that diff removes or changes a single line, stop and use the drop. An altered
column, a widened constraint or a dropped index cannot be reached this way, and a
partially applied baseline is worse than a rebuilt one.

**A pure-insertion diff does NOT establish the precondition, and reading it as
one is the trap.** A column added *inside* an existing `CREATE TABLE` is a
**modification** of that table even though the diff shows only `+` lines — the
baseline is regenerated in place, so a new column arrives as an inserted line in
a statement that already existed. Step 1's `pg_dump --table=<new_table>` emits
only the tables you name, so it never carries such a column, nor an index or
constraint declared against an existing table. The result lands the new tables
and **silently misses everything added to the old ones**, which is the drift this
whole section exists to prevent. Read the diff for what each hunk is *inside*,
never for its `+`/`−` counts. Worked example: the notes-foundation baseline diff
is +86/−0 and still fails this test — three of its nine new objects
(`projects.kind`, `documents.pinned_at`, `blocks.search_vector`) are columns
inside existing tables, and `ux_projects_one_personal`,
`ix_documents_project_updated` and the `search_vector` GIN index are declared
against tables that already exist.

**A stored generated column added to a populated table is a full table
rewrite**, on either path — Postgres must compute and write the value for every
existing row, holding an `ACCESS EXCLUSIVE` lock throughout. Budget the downtime
against the table's real size, and do not assume "just a column" is instant
because other `ADD COLUMN` forms are.

**Never transcribe the DDL by hand.** Derive it from the same code path a fresh
install runs, so what lands on production is what `alembic upgrade head` builds:

```bash
# 1. Migrate a scratch database with the new baseline and dump the new objects.
docker exec darkmem-prod-postgres-1 psql -U darkmem -d postgres \
  -c 'CREATE DATABASE darkmem_ddlref OWNER darkmem;'
cd backend && DATABASE_URL='postgresql+asyncpg://darkmem:<pw>@127.0.0.1:5432/darkmem_ddlref' \
  .venv/bin/python -m alembic upgrade head
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem_ddlref \
  --schema-only --table=public.<new_table> > /tmp/new-objects.sql

# 2. Back up anyway. This path does not destroy the database; a mistake in it can.
./scripts/backup.sh /root/darkmem-backups

# 3. Apply to the live database. ON_ERROR_STOP is not optional -- see the
#    restore trap recorded below.
docker compose stop darkmem
docker exec -i darkmem-prod-postgres-1 psql -U darkmem -d darkmem \
  -v ON_ERROR_STOP=1 < /tmp/new-objects.sql

# 4. Let the guard re-adopt. It stamps when it finds no row, which is the only
#    honest thing it can do -- and here the schema it adopts is one you have
#    just made identical to the migration's own output.
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem \
  -c "DELETE FROM config WHERE key='schema_baseline_sha';"
docker compose up -d darkmem
docker logs darkmem-prod-darkmem-1 2>&1 | grep 'schema baseline'   # expect "stamped"

# 5. Prove the result equals a fresh migrate, rather than assuming it.
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem --schema-only \
  | grep -v '^--\|^\\restrict\|^\\unrestrict\|^$' > /tmp/live.sql
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem_ddlref --schema-only \
  | grep -v '^--\|^\\restrict\|^\\unrestrict\|^$' > /tmp/fresh.sql
diff /tmp/fresh.sql /tmp/live.sql | grep '^<'          # MUST be empty
docker exec darkmem-prod-postgres-1 psql -U darkmem -d postgres \
  -c 'DROP DATABASE darkmem_ddlref;'
```

**`diff | grep '^<'` must print nothing.** Lines only on the `>` side are
expected — they are the per-fingerprint embedding children and the monthly
`events` partitions, which are created at runtime and are absent from any fresh
migrate. A line on the `<` side is an object the new baseline builds that the
live database does not have, which is the drift this whole file exists for.

Deleting the stamp is deliberately the same act the guard refuses to give you a
flag for, so state why it is honest here: the guard protects against a schema
that *differs* from the baseline, and step 5 proves this one does not. Do not
reach for step 4 without step 5.

### What the rehearsal measured

Against a copy of production (50 memories, 490 events, 98 triples, 8 embedding
child tables), applying the `llm_usage` DDL this way left **every table's row
count unchanged**, produced columns and indexes byte-identical to a fresh
migrate, and the guard stamped on the next boot and admitted on the one after.

## Restoring a data-only dump into a fresh database

The drop procedure below ends in a restore, and the restore has two traps that
cost the entire `events` journal in rehearsal. Both are recorded here because
neither announces itself.

**1. The baseline does not create the per-fingerprint embedding children.**
`memory_embeddings__<slug>` and its seven siblings are created at runtime by
`embedder_registry.register`, so a freshly migrated database has **none** of
them and every `COPY` into one fails. Capture their DDL from the old database
*before* dropping it:

```bash
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem --schema-only \
  $(docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -tAc \
    "select string_agg('--table=public.'||table_name,' ') from information_schema.tables
      where table_schema='public' and table_name like '%\_\_%'") > /tmp/child-tables.sql
```

and apply it after the migration, before the data.

**2. A failed `COPY` silently eats the tables after it.** Without
`ON_ERROR_STOP`, psql treats the failed copy's data rows as SQL, and keeps
failing until it happens to resync. In rehearsal five missing child tables took
**`entity_relations` (98 rows) and the whole `events` journal (490 rows)** down
with them — and `psql` still exited **0**. Always:

```bash
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem --data-only \
  --exclude-table=alembic_version --disable-triggers > /tmp/data.sql
docker exec -i darkmem-prod-postgres-1 psql -U darkmem -d darkmem \
  -v ON_ERROR_STOP=1 < /tmp/data.sql
```

`--exclude-table=alembic_version` because the migration already wrote that row
and the duplicate key halts the restore. `--disable-triggers` because `memories`
carries a circular foreign key (`superseded_by`) that `pg_dump` itself warns
about. Then compare row counts table by table against the pre-cutover database
before declaring the cutover done — the failure mode here is a clean exit code
over a partial restore.

## Recovering from schema drift

Pre-freeze this is the policy's own remedy and the data is disposable by the
owner's 2026-08-10 ruling. **Post-freeze it is not available** — that is what the
freeze means.

```bash
# 1. Back up first, always.
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem \
  > /root/darkmem-backups/pre-repair-$(date +%F).sql

# 2. Capture what a re-seed will NOT reproduce (see below).
#    Both LLM tables, not just the purpose row: since 2026-08-20 the qualified
#    judge identity spans the two, and providers must be restored first because
#    llm_purpose_configs.provider_name is a NOT NULL foreign key. Two files
#    rather than one --table pair, so the restore order below is explicit.
#    This dump is also the ONLY carrier of every purpose's `params` — a re-seed
#    overwrites them with llm_seed.py's Ollama presets, silently (item 4).
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem \
  --data-only --table=llm_providers --column-inserts > /tmp/providers.sql
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem \
  --data-only --table=llm_purpose_configs --column-inserts > /tmp/purposes.sql
docker exec darkmem-prod-postgres-1 pg_dump -U darkmem -d darkmem \
  --data-only --table=config --column-inserts | grep admin_password_hash > /tmp/admin.sql

# 3. Stop the API so nothing holds a connection.
docker compose stop darkmem

# 4. Drop and recreate.
docker exec darkmem-prod-postgres-1 psql -U darkmem -d postgres \
  -c "DROP DATABASE darkmem;" -c "CREATE DATABASE darkmem OWNER darkmem;"

# 5. Start: the entrypoint migrates and stamps the new baseline.
docker compose up -d darkmem

# 6. Restore the rows step 2 captured. Providers before purposes.
#    Crossing the 2026-08-20 schema change? Run the one-time transition below
#    first — this restore cannot carry that deploy.
docker exec -i darkmem-prod-postgres-1 psql -U darkmem -d darkmem < /tmp/admin.sql
docker exec -i darkmem-prod-postgres-1 psql -U darkmem -d darkmem < /tmp/providers.sql
docker exec -i darkmem-prod-postgres-1 psql -U darkmem -d darkmem < /tmp/purposes.sql
```

### Three rows a re-seed does not reproduce — and one whole column

**This is the part that is easy to lose and expensive to notice.**

This heading read "Two rows" until 2026-08-20. The judge identity now spans two
tables, so a restore that captures only the purpose row silently un-qualifies
the judge — precisely the failure this section exists to prevent.

1. **The `verification` LLM purpose row.** `llm_seed.py` seeds that purpose at a
   local Ollama model. The qualified judge identity is **`gpt-5.5`** at
   `https://api.openai.com/v1`, `api_kind=openai`,
   `params={"reasoning_effort": "high"}` — identity hash `fd39e7b2c47fa375`.
   `judge()` resolves the purpose from the *database* and the qualification
   record binds to that identity, so re-seeding instead of restoring silently
   un-qualifies the judge and no grounded label is served.

2. **The `llm_providers` row that purpose points at.** Since the 2026-08-20
   provider reinstatement the purpose row carries `provider_name` and nothing
   else of the connection: **`base_url` and `api_kind` — two of the identity's
   six fields — live on the provider row.** Restore it, and restore it *first*,
   because `llm_purpose_configs.provider_name` is a NOT NULL foreign key.

   **The restored `verification` purpose must point at a provider no other
   purpose references.** The API refuses to point a second purpose at it, but
   this restore writes rows by direct `psql` and passes no API check, so
   nothing here enforces it — a shared row puts the judge's endpoint behind an
   unrelated purpose's settings edit. If a restore lands shared, the fix is to
   repoint the *other* purposes at their own provider; `verification` itself
   cannot be moved.

   Verify both after restore:

   ```
   docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -c "
     select p.purpose, p.model, p.params, v.name, v.api_kind, v.base_url,
            (select count(*) from llm_purpose_configs x
              where x.provider_name = v.name) as purposes_on_this_provider
       from llm_purpose_configs p join llm_providers v
         on v.name = p.provider_name
      where p.purpose = 'verification';"
   ```

   `purposes_on_this_provider` must be **1**.

3. **`admin_password_hash`.** Without it `/api/v1/setup/*` reopens — the setup
   surface is gated only by that row existing.

4. **`params` on every *other* purpose row — the quiet one.** The three above
   fail loudly or visibly; this one does not. `llm_seed.py` pins all eight
   purposes to a **local Ollama** model, which is the right default for a fresh
   install with no cloud credentials and the wrong one for any instance that
   has been repointed at a cloud vendor. So a re-seed does not merely lose the
   connection — it replaces each row's `params` with the Ollama preset.

   An operator who notices the wrong endpoint and repoints the provider by hand
   gets a working instance with **empty or mismatched `params`**, and nothing
   reports it. That was the live state on this host between 2026-08-20 and
   2026-08-25: all eight rows read `{}`, so `temperature: 0` was gone from
   extraction and classification. Extraction still forwards
   `seed = sha256(content)[:8]` and DeepSeek still honours it, but a seed at a
   default temperature does not buy determinism — the reproducibility invariant
   was nominal rather than real, and no test, log or health check says so
   because an empty `params` is a legal config.

   Restoring the dump from step 2 carries these values; the hazard is only on
   the re-seed-instead-of-restore path. If you take it, the values this host
   runs are:

   | purpose | `params` |
   |---|---|
   | `extraction` | `{"temperature": 0, "max_tokens": 8192}` |
   | `classification` | `{"temperature": 0}` |
   | `reranker` | `{"temperature": 0}` |
   | `summarization` | `{"temperature": 0.3}` |
   | `reasoning` | `{"temperature": 0.7}` |
   | `synthesis` | `{"temperature": 0.3}` |
   | `embedding` | `{}` — an embed call takes neither knob |
   | `verification` | `{"reasoning_effort": "high"}` — see row 1; identity field, restore it, never re-seed it |

   Verify after any re-seed:

   ```
   docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -c "
     select purpose, params from llm_purpose_configs
      where params = '{}'::jsonb and purpose <> 'embedding';"
   ```

   Anything but zero rows means a purpose is running on vendor defaults.

### One-time: an image built before the provider layer

**Step 6 above cannot carry the deploy that first ships the 2026-08-20 provider
reinstatement.** Step 2 dumped `llm_purpose_configs` from the *old* schema, whose
rows carry `api_kind`/`base_url`/`api_key` columns and no `provider_name`. That
`psql` fails on nonexistent columns; and even with the columns hand-stripped it
fails the NOT NULL foreign key, because the recreated database holds **zero**
`llm_providers` rows until something writes them. The judge identity this
procedure exists to preserve is exactly what would be lost.

Transform the dump instead, between step 5 and step 6:

```bash
# Old-schema purpose rows as JSON: one object per purpose, connection fields
# still inline. Run this BEFORE step 4 drops the database — step 1's plain
# pg_dump is a backup, not a usable input here.
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -tAc \
  "select json_agg(row_to_json(t)) from llm_purpose_configs t;" > /tmp/old-purposes.json

# Emit provider INSERTs followed by purpose INSERTs that reference them.
# What it derived goes to stderr; read it before running the SQL.
/root/repositories/darkmem/backend/.venv/bin/python \
  /root/repositories/darkmem/backend/scripts/cutover/llm_providers_transition.py \
  < /tmp/old-purposes.json > /tmp/transitioned.sql
```

It groups the dumped rows by their distinct `(api_kind, base_url, api_key)`
triple, names each group `<api_kind>-<host>` deterministically, and **always
splits `verification` onto a provider of its own** — so the exclusivity rule
above holds by construction rather than by the operator remembering it. Two runs
over one dump produce identical names. Then run `/tmp/transitioned.sql` in place
of step 6's `providers.sql` + `purposes.sql` pair — it already emits the provider
`INSERT`s ahead of the purpose ones:

```bash
docker exec -i darkmem-prod-postgres-1 psql -U darkmem -d darkmem < /tmp/admin.sql
docker exec -i darkmem-prod-postgres-1 psql -U darkmem -d darkmem < /tmp/transitioned.sql
```

This is needed once, for the deploy that crosses the schema change. Afterwards
step 2 already dumps both tables and step 6 works unchanged.

## Verifying a deploy, rather than assuming it

```bash
curl -s localhost:8000/health                       # pipeline + pgvector + llm
curl -s localhost:8000/openapi.json | grep -o '"version":"[0-9.]*"' | head -1
docker logs darkmem-prod-darkmem-1 2>&1 | grep -i 'schema baseline'
docker exec darkmem-prod-postgres-1 psql -U darkmem -d darkmem -tAc \
  "select key, value->>'last_status', value->>'last_error' from config where key like 'job:%' and value->>'last_status' <> 'ok';"
```

**A 200 on `:8000` does not prove the new container answered it**, so
`release.sh` probes the version in `/openapi.json` rather than `/health`. Do the
same by hand.

The specific trap this warns about changed with the move to bridge networking,
and in the safer direction. Under host networking a stale dev server holding
`:8000` let the container crash-loop while curl cheerfully returned 200 from the
impostor. Under bridge the port is published, so a conflicting listener makes
`docker compose up` fail outright with an address-in-use error rather than
starting a container that cannot serve. The version probe still earns its keep —
it is what catches an *old* container answering, which no port check can.

**The last query is the one that would have caught the 2026-08-17 drift.** A job
sitting in `error` is invisible everywhere else; check it after every deploy.

## What a deploy carries beyond code

Two evidence records ship *in the image*, not in the database, so a deploy is how
they reach production:

- `app/services/promotion_metrics_record.json` — G-C's. While present with
  `gate_eligible: true`, promoted and born fact statuses reach readers.
- `app/services/verification_qualification.entailment.json` — T2.125's. The
  judge is qualified, and grounded article labels become servable, only while
  this record and the database identity agree — and since 2026-08-20 that
  identity is read across **two** rows: the `verification` purpose row for
  `model`/`params`, and the `llm_providers` row it names for `base_url` and
  `api_kind`. Restoring one without the other un-qualifies the judge.

Neither is minted by hand and neither is a config toggle. **Deploying an image
that carries one is a capability change**, not a version bump, and is worth
stating in the deploy's own record.
