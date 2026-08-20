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

**Publishing is a tag's consequence, and nothing else's** (changed 2026-08-20;
this said "nothing is ever pushed to a registry", which stopped being true when
CI gained a publish job). Nothing local pushes: `build-push.sh` honours
`DARKMEM_PUSH=0` and `release.sh` sets it, so cutting a release still only
builds and tags on this machine. What publishes is
`git push origin <tag>` — that runs `.github/workflows/release.yml`, which
re-runs the whole CI pipeline and only then pushes the image to Docker Hub
(`darkraise/darkmem`) and GHCR (`ghcr.io/darkraise/darkmem`).

The reasoning that produced the old rule is unchanged and is why the push is a
separate step: a local tag can be deleted and a pushed image cannot. A branch
push publishes nothing. Deploying this host still uses the locally built image
and never needs the registry.

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

### Three rows a re-seed does not reproduce

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
