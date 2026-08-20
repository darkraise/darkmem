# LLM providers — a first-class connection layer under the eight purposes

**Status:** design, pre-implementation, revision 2. **Owner ruling:** 2026-08-20,
§0. **Reverses:** doc 04 §7, doc 19 §3, and the `app/models/llm_config.py`
docstring. **Touches:** the baseline schema, LLM config resolution, the config
REST contract, the setup wizard, the settings UI, `llm_seed.py`,
`benchlib/run_smoke.py` and `benchlib/ingest.py`, `scripts/cutover/spec.py`, and
two runbooks.

**Revision 2** incorporates an adversarial review that returned DO NOT SHIP on
revision 1 with six blocking findings. Three of them changed the design rather
than the prose: the §9 guard was both too strong and too weak (R1, R3), the seed
data contradicted the design in a way that would have silently flipped every
fresh install's wire protocol (R4), and §8's deployment path could not survive
the one deploy this change actually is (R5). §11 records the full disposition.

Configuring `api_kind`, `base_url` and `api_key` eight times over what is
normally two vendors is the ergonomic complaint this answers. A provider becomes
a stored row; a purpose names one and contributes only what genuinely varies per
purpose — the model, its params, and the three purpose-shaped flags.

---

## 0. The ruling this rests on, stated plainly

darkmem deleted exactly this indirection at the baseline. `llm_providers`,
`llm_profiles` and `ml_profiles` were dropped in T0.12c on doc 04 §7's argument
that "darkmem is not an LLM proxy", and `tests/test_llm_config.py` was written
to keep them dead: it asserts the three tables do not exist, that the three
`*_id` columns are absent, and that resolution executes one query containing no
`JOIN`.

**The owner reinstated the provider layer on 2026-08-20**, having been shown
that argument and the cheaper alternative — a UI-level provider preset stamped
down into the purpose rows at save time, which preserves every existing
invariant. The reinstatement was chosen on one requirement the snapshot design
cannot meet: **a credential rotation or endpoint move must propagate to every
purpose that uses it, with no re-apply step.** That is a live reference, and a
live reference is the indirection.

This document does not re-argue the decision. It records what the decision
costs, and confines that cost to the smallest surface that still delivers the
requirement.

**Two invariants are deliberately amended, and no others.** Doc 04 §7's "the
provider indirection is gone" becomes "provider connection is one join below the
purpose row"; the resolution contract "one row read and no joins" becomes "one
query, one join". Everything else here exists to keep the third invariant — that
**the resolved config object does not change shape** — exactly as true as it is
today.

**One deliberate exception to the propagation requirement**, named here rather
than buried in §9: the provider serving the `verification` purpose does not
propagate a `base_url` or `api_kind` change, because those two fields are the
judge's qualification identity. Its **API key still rotates normally**. §9
carries the reasoning.

---

## 1. Storage

### 1.1 The new table

```sql
CREATE TABLE llm_providers (
    name       VARCHAR(64) PRIMARY KEY,
    api_kind   VARCHAR(32)  NOT NULL DEFAULT 'openai',
    base_url   VARCHAR(512) NOT NULL DEFAULT '',
    api_key    VARCHAR(1024),
    updated_at TIMESTAMPTZ  NOT NULL DEFAULT now()
)
```

**Natural key, not a UUID.** It matches the table it joins to, whose primary key
is the purpose string. It keeps `pg_dump` output and the deployment runbook's
restore steps human-readable, which §8 shows is load-bearing rather than
cosmetic. And `ON UPDATE CASCADE` then makes a rename work without a second
column or a repoint pass.

### 1.2 The changed table

```sql
CREATE TABLE llm_purpose_configs (
    purpose         VARCHAR(64) PRIMARY KEY,
    provider_name   VARCHAR(64) NOT NULL
        REFERENCES llm_providers(name) ON UPDATE CASCADE ON DELETE RESTRICT,
    model           VARCHAR(255) NOT NULL,
    dimensions      INTEGER,
    reasoning       BOOLEAN NOT NULL DEFAULT false,
    params          JSONB NOT NULL DEFAULT '{}'::jsonb,
    classifier_kind VARCHAR(16),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT llm_purpose_configs_classifier_kind_check
        CHECK (classifier_kind IS NULL OR classifier_kind IN ('llm', 'local'))
)
```

`api_kind`, `base_url` and `api_key` move to the provider and do **not** remain
as nullable overrides — the owner chose "provider owns connection outright", so
there is no coalesce anywhere and no "which value is live?" question at any read
site.

`ON DELETE RESTRICT` makes a delete of an in-use provider a 409 rather than a
cascade orphaning eight purposes. `ON UPDATE CASCADE` makes a rename work.

`classifier_kind` stays on the purpose row: it selects which classifier
implementation serves a purpose, which is purpose-shaped, not connection-shaped.

**`api_kind` remains the sole vendor axis.** It moves rows; it does not change
meaning. F-10's rule — one vendor column, every quirk resolved through
`app/services/llm_quirks.py` — is untouched, and the AST scan that fails the
build on an `api_kind ==` comparison at a call site is unaffected.

---

## 2. Resolution, and the invariant that must not move

### 2.1 One query, one join, same flat object

`app/services/config.get_llm_config` becomes a single `SELECT` joining
`llm_purpose_configs` to `llm_providers`, and **returns the identical
`dict[str, LLMPurposeConfig]` it returns today**. `LLMPurposeConfig` keeps
`base_url`, `api_key` and `api_kind` as flat fields, populated from the joined
provider.

This is the design's spine. Because the resolved object does not change shape,
the indirection is invisible to `LLMOrchestrator`, `llm_quirks`,
`VerificationJudge`, the health check, `CodeQueryService`, and every benchlib
*consumer*. None of those is edited.

The **writers** are a different set and are edited: the setup finalize handler
(§5), `benchlib/run_smoke.seed_llm_purpose_configs`, and
`benchlib/ingest.py:103`. Revision 1 wrongly listed the finalize handler among
the untouched consumers.

### 2.2 Why flatness is a correctness requirement

Two independent mechanisms hash the resolved config's fields:

**The benchlib cache key.** `benchlib/caching_llm.py:32` folds
`_KEYED_CONFIG_FIELDS` — `model`, `base_url`, `api_kind`, `dimensions`,
`reasoning`, `params` — off the resolved config via `getattr`, and `FROZEN.md`
fixes that as frozen. Had resolution returned a nested provider object or
renamed a field, every cache entry on every machine would miss. G-C's clear
(T2.131) rests on an independent party reproducing the run byte-identically at
**0 live calls**; that reproduction would stop being possible, and the failure
mode is a re-run that quietly costs money and yields different numbers rather
than an error.

**The judge identity.** `verification_judge.py:200` names the same six fields,
and the qualification record binds to their hash.

Flat resolution preserves both — **conditional on the seeded values being
carried byte-exactly**, which §5.2 is entirely about and which revision 1 got
wrong.

### 2.3 What happens to the T1.01 guard suite

| test | disposition |
|---|---|
| `test_purpose_resolution_is_a_single_query` | logic unchanged; **fixture SQL rewritten** (`:87` inserts dropped columns) |
| zero-rows / populated query-count parity | same — logic unchanged, fixture rewritten |
| `test_resolution_joins_nothing` | **replaced** by `test_resolution_is_one_query_with_one_join` |
| `test_indirection_tables_do_not_exist` | `llm_providers` case dropped; other two kept |
| `test_ref_columns_are_gone_from_the_table` | `provider_id` case dropped; other two kept |
| `test_api_kind_survives_as_the_vendor_field` | **re-pointed** at `llm_providers` |
| `test_provider_column_is_dropped` | kept — the duplicate `provider` column stays dead |
| `test_resolved_config_carries_the_inline_connection_details` (`:173`) | **rewritten** — same assertion, values now arriving across the join |
| `test_post_config_llm_writes_synthesis` | **rewritten** — body and assertion lose `base_url`/`api_kind` |
| `test_post_config_llm_ignores_verification_write` | **rewritten**, and extended by §9's new cases |

The replacement join test asserts the resolution SQL contains exactly one
`JOIN`, names `llm_providers`, and names neither `llm_profiles` nor
`ml_profiles`. The N+1 hazard the original suite protects against — per-purpose
resolution, hierarchical `WITH` chains — remains fully guarded; the query-count
parity test is what carries that, and it is untouched in substance.

---

## 3. REST surface

### 3.1 New endpoints

All under `/api/v1/config/llm-providers`, all `require_auth`, all following
`docs/api-rest-conventions.md`.

| verb + path | status | notes |
|---|---|---|
| `GET /llm-providers` | 200 | list; `api_key` masked to `***`; each row carries `used_by[]` and `serves_verification` |
| `POST /llm-providers` | 201 | 409 on duplicate name |
| `PUT /llm-providers/{name}` | 200 | `api_key: "***"` means "do not rotate"; §9 restricts two fields on one provider |
| `DELETE /llm-providers/{name}` | 204 | **409** while any purpose references it |
| `POST /llm-providers/{name}/probe-models` | 200 | fetch the vendor's model list |
| `POST /llm-providers/probe-models` | 200 | probe an unsaved draft |

Both probe endpoints report a vendor failure as **200 with `error` set**, never
a raise — a probe failure is information about the vendor, not a failure of the
darkmem request. This matches the wizard probe's existing contract.

`llm_quirks.models_probe` supplies only URL, headers and label; the
response-body parsing (`data[]` versus `models[]`) currently lives inline in
`setup.py:probe_models`. **That parsing is extracted into a shared helper** in
this change, or the three probes drift.

The existing `POST /api/v1/setup/probe-models` stays where it is, gated
`require_uninitialized`. The two are not merged: they have opposite auth
postures on purpose.

### 3.2 The changed endpoint

`POST /api/v1/config/llm` keeps its known REST deviation. Each purpose body
loses `api_kind`, `base_url` and `api_key`, and gains `provider_name`. A
`provider_name` naming no row is a **422**, not a deferred FK error.

`LLMPurposeConfigSchema` keeps all three fields on the **read** side — it is the
resolved view, which the settings UI and health page display. Only the update
schema loses them.

**Creating a rowless purpose now requires a provider.** `config.py:163`
constructs `LLMPurposeConfigRow(purpose=purpose, model="")` when a purpose has
no row; under a NOT NULL FK that becomes a 500. The route therefore requires
`provider_name` in the body when no row exists, returning **422** naming the
missing field, and requires it only then.

### 3.3 The orchestrator swap must move with it

Today a connection change can only arrive through `POST /config/llm`, which
holds `app.state.llm_config_lock`, rebuilds `LLMOrchestrator`, calls
`_replace_orchestrator`, closes the old one, probes the new embedder's
dimensions and counts re-embed work.

A provider `PUT` now changes connection too. **It must take the same lock and
run the same swap**, or the process keeps calling the old endpoint until restart
— a silent failure whose symptom is "my new API key didn't take effect". The
swap block is extracted from `update_llm_config` into a shared helper and called
from both. Duplicating it guarantees drift.

**Provider `POST` and `DELETE` take the lock too.** Without it: a purpose POST
validates that a provider exists (passes), a concurrent DELETE succeeds (not yet
referenced), and the purpose flush hits the FK — a 500 where §3.2 promised a
422. Serialising all four writes closes the read-modify-write window.

Changing a provider's `base_url`, `api_kind` or `api_key` does **not** move the
embedding fingerprint, which is `model|dims` — so no re-embed is triggered and
`obsolete_after_change` stays absent from the provider route's response.
Pointing the same model at a different host does not invalidate its vectors.

**A provider PUT that flips `api_kind` to a no-embeddings vendor** while the
embedding purpose references it must name the affected purposes in its response.
`assert_can_embed` fails loud at runtime, but §4.3's form warning lives only on
the purposes panel, so the provider panel needs its own.

### 3.4 Dead fields and dead surfaces retired

`LLMPurposeConfig.provider_ref`, `.profile_ref` and `.ml_profile_ref` are
removed (T1.42b's scope, folded in here — a dead `provider_ref` beside a live
`provider_name` is a trap with a predictable victim).

`app/services/config.py`'s legacy `LLM_PROVIDERS_KEY = "llm_providers"` and
`LLM_PROFILES_KEY` constants are retired. A `config`-table key and a real table
sharing one name is a grep hazard.

`frontend/src/features/llm/` is deleted. It is unmounted but present, and
`llm-profile-form.tsx` still reads `provider_ref`; a new providers feature
landing beside a dead same-named one is exactly the trap §3.4 exists to avoid.
Its vitest file goes with it.

`llm-tab.tsx`'s `RemovedChrome` — which renders "llm-providers tab" struck
through as "removed with the flattening — deleted, not disabled" — is removed.
It becomes false the day this lands.

The demo fixtures in `use-llm-tab-binding.ts` and the narration in
`frontend/src/demo/data/knowledge-curated.ts` (which describes resolution
"through a provider_ref or profile_ref") are updated to the new shape. Demo mode
is a shipped surface, not scaffolding.

---

## 4. Frontend

### 4.1 Placement

`LLMTab` gains an inner `Tabs` with two panels, **Providers** and **Purposes**.
The top-level Settings strip stays at seven; its own comment notes that **six**
equal columns already overflow on narrow viewports, so an eighth would worsen a
known problem in order to separate two panels that are used together.

### 4.2 Providers panel

Provider cards: name, `api_kind` select, base URL, masked key. Each carries a
**"used by N purposes"** badge (from `used_by[]`) so a delete 409 is never a
surprise, and a **"Test connection"** button reporting inline either the model
count or the vendor's error text.

Delete is disabled with an explanatory tooltip while the count is non-zero, and
still handles a 409 if the server disagrees — the count is a hint, not a lock.

A provider with `serves_verification` renders its `base_url` and `api_kind`
fields read-only, with a `HelpTip` explaining §9. Its key field stays editable.

### 4.3 Purposes panel

Each `PurposeCard`'s three connection fields collapse to one provider `Select`.
The free-text model `Input` becomes darkraise-ui's **`combobox`**, whose
`inputValue` prop accepts arbitrary text, so "fetched suggestions plus free
text" needs no local component. Restyling it is expected; re-implementing it is
not.

Suggestions come from the selected provider's probe, fetched on demand and
cached per provider for the session. A probe failure shows the vendor error
beneath the field and leaves the combobox fully typeable — a vendor that
under-reports its catalogue, or is briefly down, must never make a purpose
unconfigurable.

`embeddingKindWarning` re-derives from the **selected provider's** `api_kind`.

### 4.4 The Tier-C card

`TierCPurposeCard` renders `verification` read-only today and says why. It keeps
doing so, and names the provider serving it.

---

## 5. Seed data and the setup wizard

### 5.1 Two lists, not one

`DEFAULT_PROVIDERS` stays what it is: a **vendor catalogue** keyed by `api_kind`,
read by `provider_seed_by_kind` to supply the wizard's base-URL default. It is
not the set of rows written to `llm_providers`, and conflating the two is what
produced R4.

A new `DEFAULT_PROVIDER_ROWS` is the seeded set — the rows actually inserted:

| name | api_kind | base_url | api_key |
|---|---|---|---|
| `ollama-local` | `openai` | `OLLAMA_BASE_URL` (ends `/v1`) | none |
| `verification-judge` | `openai` | `OLLAMA_BASE_URL` | none |

`api_kind` is `openai`, not `ollama`, and this is the whole point of R4. Today's
`DEFAULT_PURPOSE_CONFIGS` rows all carry `api_kind="openai"` against a
`/v1`-suffixed Ollama URL — the OpenAI-compat path. The `DEFAULT_PROVIDERS`
entry named `ollama` carries `api_kind="ollama"` — the native path, `/api/...`,
`think:false`. Binding the purposes through that entry, as revision 1's "the
seed layer needs new values, not new structure" implied, would have **flipped
every fresh install's wire protocol** while presenting itself as a no-op.
`test_setup.py:172-180` pins the `/v1` URLs and would have caught it loudly
mid-implementation.

`verification-judge` exists so `verification` does not share a provider by
default (§9). It is seeded at the same inert Ollama model the purpose is seeded
at today, so nothing about the judge's out-of-box state changes.

### 5.2 The pin test that makes R4 unrepeatable

**A test asserts that a fresh install's resolved `dict[str, LLMPurposeConfig]`
is field-for-field equal to what the pre-change seed resolved to**, for all
eight purposes. This is the mechanical guard: any future seed edit that
perturbs a resolved value — and therefore a benchlib cache key or the judge
identity — fails the build rather than being discovered by a gate re-run that
silently costs money. It proves §2.2's claim rather than asserting it.

### 5.3 The wizard

`StepLLM` is rebuilt provider-first: define one or more providers, each with a
live probe so a bad key is caught in the wizard rather than at first ingest;
then assign each purpose a provider and a model from that provider's fetched
list.

**The wizard's purpose set stays at six.** `setup.py`'s `PURPOSE_LITERAL` names
the six live user-facing purposes; `synthesis` and `verification` come from seed
and are not user-assignable. Widening it would make the Tier-C rows
wizard-writable, which is the capability T2.106 refused. Revision 1 said "each
of the eight" and was wrong.

`SetupWizardStore` grows a `providers` array. Finalize writes providers first,
then purposes, in one transaction, and **enforces §9's exclusivity** — the
finalize path writes purpose rows through the ORM directly and would otherwise
bypass a check living only on `POST /config/llm`.

The wizard is trust-on-first-use, gated only by `require_uninitialized`.
Rebuilding it must not touch that gate, and `SETUP_SECRET` must not reappear.

---

## 6. Blast radius

Sites that break mechanically and must move with this change:

**Backend writers.** `app/api/routes/setup.py:378-425` (finalize).
`app/api/routes/config.py:163` (rowless-purpose create, §3.2).

**Benchlib — two writers, not one.**
`benchlib/run_smoke.seed_llm_purpose_configs` seeds the four pinned rows and
must seed providers first. `benchlib/ingest.py:103` separately constructs an
`LLMPurposeConfigRow` with `api_kind`/`base_url`/`api_key` kwargs when the
classification row is absent — invalid kwargs *and* a NOT NULL FK. It is the
shared ingest driver under every harness. Revision 1's "single-site" was wrong.
`benchlib/tests/test_run_smoke.py:97-144` covers the seeding function.

**Backend tests inserting purpose rows.** `test_classifier_kind.py:40` and
`test_classifier_local.py:48` construct `LLMPurposeConfigRow` with no provider →
NOT NULL violation. `test_setup.py:42-112` and `test_setup_route.py:309` assert
`api_kind`/`api_key`/`base_url` on purpose rows. Plus the `test_llm_config.py`
set in §2.3.

**`scripts/cutover/spec.py`** — `llm_providers` is **already present**, in
`SOURCE_TABLES_A1` and in `DROPPED_TABLES` with the rationale "never exists in
the baseline; the flattening is greenfield", which this change falsifies. This
is a re-scoping with a semantic collision — a dropped 0006 *source* table and a
new *target* table sharing a name and not a shape — not the simple addition
revision 1 described. `test_cutover_transform.py:163-165` stubs it as a source
table. The resolution must be explicit: the dropped source table keeps its
entry and rationale (historical), and the new target table is registered
separately under its own shape.

**`benchlib/FROZEN.md`** states the bench rows are written inline
"(`provider_id`/`profile_id` left `NULL`)". Already stale — neither column
exists — and actively misleading once a non-nullable `provider_name` does. It is
amended, with the seeded provider values added to the table it already carries.
The pinned model values do not move, so no gate re-measurement is implied.

**`docs/runbook-deployment.md`** — §8.

**`CLAUDE.md`**, `app/models/llm_config.py`, `app/services/config.py`, doc 04 §7
and doc 19 §3 all assert the indirection is gone and resolution is "one row read
and no joins". All become false when this lands; amending them with §0's ruling
is part of this change. CLAUDE.md's "LLM configuration" section is what a future
reader consults first.

**Confirmed unaffected**, so nobody re-checks: `sdks/generate.py` hashes only its
three verbs' operations, so the OpenAPI additions do not break SDK generation;
`test_deployment_artifact.py` touches nothing LLM; the health check reads only
the resolved flat config; the vendor-conditional AST scan
(`test_api_kind_dispatch.py:265`) is unaffected.

**Baseline ownership.** CLAUDE.md requires schema changes to serialise through
one owner per epic, because the baseline is a single shared mutable file. This
change must claim that lane before touching `0001_baseline.py`; two lanes
editing it conflict every time.

---

## 7. Testing

**Backend.** The amended `test_llm_config.py` set (§2.3). FK `RESTRICT` → 409 on
a referenced delete. `ON UPDATE CASCADE` carrying a rename to every referencing
purpose. The `"***"` sentinel leaving a stored key untouched. The orchestrator
actually swapped by a provider edit (assert `app.state.llm` is a new object
carrying the new `base_url`). 422 for an unknown `provider_name` and for a
rowless-purpose create with none. The §9 guard cases, including the shared-state
sequence. The §5.2 resolved-seed pin.

**Judge identity pin.** The resolved `verification` config must still hash to
`fd39e7b2c47fa375` under `judge_identity_hash(judge_identity(cfg))` given the
recorded gpt-5.5 identity split across a provider row and a purpose row.

**Frontend.** `settings-llm.real.test.tsx` extends to provider CRUD, the
delete-blocked path, combobox free-text surviving a failed probe, the embedding
warning tracking the selected provider, and the read-only rendering of a
`serves_verification` provider's two frozen fields.

**Gate.** `./scripts/gate.sh` covers the rest, including the single-revision
assertion after the baseline regenerates.

**A known sentinel collision, pre-existing and unfixed:** a literal `***` cannot
be stored as an API key. Carried over from `config.py:156`; recorded, not
repaired, because repairing it changes an existing wire contract.

---

## 8. Deployment

The baseline regenerates in place, so `app/schema_guard.py` will refuse to boot
the new image against the existing production database. It fails closed with no
override flag, by design.

### 8.1 The transition is one-time and the runbook does not cover it

**The runbook's procedure cannot carry this deploy**, which revision 1 missed.
Step 2 dumps `llm_purpose_configs` with `--column-inserts` from the **old**
schema — columns `api_kind`, `base_url`, `api_key`, no `provider_name`. Step 6
restores it into the **new** schema. That `psql` fails on nonexistent columns;
and even with columns hand-stripped it fails the NOT NULL FK, because the
procedure never runs the wizard and the recreated database holds zero
`llm_providers` rows. The judge identity the runbook section exists to preserve
is exactly what would be lost.

So this change ships a **one-time transition script**,
`backend/scripts/cutover/llm_providers_transition.py`, which reads a dumped
old-schema purpose set and emits the new one:

1. Group the dumped rows by their distinct `(api_kind, base_url, api_key)`
   triple.
2. Name each group deterministically — `<api_kind>-<host>`, de-duplicated with a
   numeric suffix — so two runs over one dump produce identical names.
3. **Split `verification` onto its own provider** regardless of whether its
   triple is shared, per §9.
4. Emit provider `INSERT`s, then purpose `INSERT`s carrying `provider_name`.

It is idempotent, prints what it derived, and is covered by a test over a
representative dump including the shared-triple case.

### 8.2 Path A — drop and recreate

`docs/runbook-deployment.md:81`, with step 6 replaced by the §8.1 script. It
restores exactly `admin_password_hash` and the transformed LLM rows. It does
**not** restore `memories`, `events`, `knowledge_triples` or research origins.

**The loss is all of production's accumulated data**, not merely a clock —
revision 1 understated this. Every memory, event, fact and origin since the last
drop is destroyed, including whatever the G-E research corpus has accrued since
production was armed on 2026-08-17. How much that is cannot be determined from
the tree: `research_run` has no in-tree gatherer and no cron, so only an
inspection of the running database answers it. **Inspect before choosing this
path.**

### 8.3 Path B — hand-applied DDL

One `CREATE TABLE`, one `ADD COLUMN`, a backfill, one `ADD CONSTRAINT` for the
FK, one `SET NOT NULL`, three `DROP COLUMN`. Then re-stamp `schema_baseline_sha`.

**It is not "purely additive"** — revision 1's phrasing was falsified by its own
list of three `DROP COLUMN`s, and that list also omitted the FK constraint.

**The enumeration above is still not a specification, and the gap is the
hazard.** `schema_guard` hashes the baseline *file*, not the schema. A
hand-applied DDL that omits one clause, plus a re-stamp, is permanent invisible
drift under a forged-clean stamp — the guard's own instrument turned against the
thing it was built to catch. If this path is taken, the DDL must be generated
from the regenerated baseline rather than hand-written, and the backfill must
use §8.1's script for its naming and verification-split policy.

Recorded as available. Not recommended.

### 8.4 The runbook amendment, needed either way

Today the runbook dumps `llm_purpose_configs` to preserve the qualified judge
identity. After this change that identity spans two tables, and a restore
capturing only the purpose row loses the judge's `base_url` and `api_kind` —
silently un-qualifying it, precisely the failure that section exists to prevent.

The dump command gains `--table=llm_providers`; the "two rows a re-seed does not
reproduce" heading becomes three; and the procedure **mandates that the restored
`verification` purpose points at a provider no other purpose references** (§9).

---

## 9. The verification judge — a side door this design must close

**This is the finding that most changes the shape of the work, and it is not
visible from the feature description.**

`LLMConfigUpdate` (T2.106) deliberately omits `verification` from the write
side. Its docstring records why: `VerificationJudge` dispatches on that purpose,
its qualification record binds to a resolved identity, and repointing that
identity from a settings form is a real capability whose write-time safety half
— warning the operator, or invalidating the record at the moment of a repoint —
was explicitly scoped out as later ladder work.

`IDENTITY_FIELDS` is `("model", "base_url", "api_kind", "dimensions",
"reasoning", "params")`. **Two of those six move to the provider row.** Without a
guard, editing a provider reaches exactly the capability T2.106 refused, through
a door that did not exist when it refused.

The judge's read side still fails closed: `qualification_state` re-derives the
hash per call and raises `JudgeNotQualifiedError` on a mismatch, so no stale
verdict is ever served. The damage is not wrong answers. It is that **G-D's
clear silently evaporates on an unrelated settings edit**, with the operator
told nothing, and the entailment record minted 2026-08-17 is not cheap to
re-mint.

### 9.1 The guard

**Rule 1 — field-scoped, not row-scoped.** On a provider referenced by
`verification`, `PUT` rejects a change to **`base_url` or `api_kind`** with a 409
naming the purpose. **`api_key` rotation and rename are permitted.**

Revision 1 froze the whole row, and that was wrong in the most expensive
possible direction. `IDENTITY_FIELDS`' own comment reads "`api_key` is
deliberately absent — rotating a credential is not a model swap": a key rotation
does not move the qualification hash, so freezing it protects nothing. Meanwhile
CLAUDE.md's 2026-08-20 ruling states the leaked gpt-5.5 judge key **is owed
rotation before publication**. Revision 1 would have made the single
highest-stakes credential in the system rotatable only by direct database write
— the exact re-apply step §0 says this design exists to eliminate.

**Rule 2 — exclusivity is a default and a warning, not an enforced invariant.**
The seed and the wizard give `verification` its own provider (§5.1), the purpose
write path refuses to assign another purpose to it, and `GET /llm-providers`
exposes `serves_verification` so the UI can explain the frozen fields.

**There is no deadlock, and revision 1's reasoning that there was one was
simply wrong.** It claimed a shared provider would freeze the co-tenant purpose
with no escape, because `verification` cannot be repointed. But the escape runs
the other way: **repoint the *other* purposes off the shared provider**, which
is permitted, ordinary, and one form submission. `verification` is then alone on
it and rule 1 constrains nothing anyone needs.

That matters beyond tidiness, because a shared state **can** arise and the
review found the path: `docs/runbook-deployment.md`'s restore writes purpose
rows by direct `psql`, never passing any API-level check. Revision 1's hard
exclusivity would have been unenforceable exactly where it was most needed. A
soft rule that degrades to "this provider's endpoint is frozen until you split
it", with an API-reachable remedy, survives that. §8.4 additionally has the
runbook mandate the split, so the state is unlikely as well as recoverable.

**The "no qualification record exists yet" premise is deleted.**
`app/services/verification_qualification.entailment.json` is committed and ships
in every image, so a record always exists at install time; what varies is
whether the *database* identity matches it. Revision 1 leaned on that false
premise to argue the wizard could not violate the rule. The wizard is instead
made to enforce it directly (§5.3).

### 9.2 What this deliberately does not do

It does not warn-and-confirm, and it does not invalidate the qualification
record on a repoint. Both are the write-time half T2.106 scoped out, and both
touch the ladder's enforcement path. This design **refuses the capability rather
than making it safe** — the same answer T2.106 gave, applied to a second door.

`synthesis` needs no equivalent guard: it is seeded inert with no consumer until
T3.02 and binds no measured identity.

---

## 10. Out of scope

- Per-purpose connection overrides (owner chose provider-owns-connection).
- Any change to what a purpose *does*, to the pipeline, or to the ladder.
- Retiring `schema_guard` — that belongs to the freeze.
- Lifting the `verification` `base_url`/`api_kind` restriction (§9.2).
- Repairing the `***` sentinel collision (§7).
- Moving any pinned bench model value, which would imply a gate re-measurement.

---

## 11. Review disposition (revision 1 → 2)

Adversarial review, Fable tier, 2026-08-20. Verdict on revision 1: **DO NOT SHIP
AS WRITTEN**. Every blocking finding was independently verified against the tree
before being accepted.

| # | Finding | Disposition |
|---|---|---|
| R1 | Row-scoped §9 freeze blocks the judge key rotation the owner ruling requires; `api_key` is not in `IDENTITY_FIELDS` | **Accepted** — rule 1 narrowed to two fields (§9.1) |
| R2 | Seed points all eight purposes at one shared `ollama` provider, violating the design's own exclusivity rule; "no qualification record at install" is false | **Accepted** — `verification-judge` seeded (§5.1); false premise deleted (§9.1) |
| R3 | The runbook's direct-`psql` restore can recreate the shared state the guard assumed impossible | **Accepted, and the guard redesigned** — exclusivity demoted to a default with an API-reachable remedy; the claimed deadlock did not exist (§9.1) |
| R4 | Seeded provider `api_kind="ollama"` vs purposes' `api_kind="openai"` would flip every fresh install's wire protocol | **Accepted** — two-list split (§5.1) plus a resolved-seed pin test (§5.2) |
| R5 | Path A's restore cannot survive the transition deploy: old-schema dump into new schema, zero provider rows | **Accepted** — one-time transition script (§8.1) |
| R6 | Blast radius missed `ingest.py:103`, six test files, and mischaracterised the cutover-spec edit | **Accepted** — §6 rewritten |

Non-blocking findings 1–12 are all incorporated: DELETE/POST under the lock
(§3.3), no-embeddings warning on the provider route (§3.3), shared probe parsing
(§3.1), the `***` collision recorded (§7), the dead `features/llm/` directory
and `RemovedChrome` and demo narration retired (§3.4), `LLM_PROVIDERS_KEY`
retired (§3.4), path B's missing FK clause and forged-stamp hazard (§8.3), the
wizard's six-not-eight purpose count (§5.3), baseline lane ownership (§6), and
the corrected G-E framing (§8.2). The "seven columns overflow" misquote is
fixed to six (§4.1).

**Carried forward from revision 1 unchanged**, per the review's own list of what
must not be lost in revision: the flat-resolved-object invariant as the spine
with both hash consumers named; the §9 finding itself; the extracted orchestrator
swap; `ON DELETE RESTRICT`; 422-not-deferred-FK; the separate auth postures on
the two probe surfaces; no per-purpose overrides; no re-embed on a
connection-only change; `classifier_kind` staying on the purpose row; and the
judge-identity pin test.
