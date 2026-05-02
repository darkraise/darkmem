# Setup Wizard — Multi-Step Onboarding

**Status:** Approved design, ready for implementation
**Date:** 2026-05-02
**Owner:** Darkraise

## Goals

Replace the single-page admin password form at `/setup` with a four-step wizard that bootstraps a fresh darkmem install in one continuous flow:

1. Admin password
2. Default LLM provider with per-purpose model selection (skippable)
3. Default code repository path with detection of existing repos under it (skippable)
4. Finish — review the draft, submit everything in one finalize call, auto-login, navigate to home

The wizard is the only entry point for first-time setup. All draft state is held client-side until the user clicks Finish; nothing is persisted on intermediate steps.

## Non-Goals

- Multi-user setup. darkmem is single-admin; the wizard provisions one operator account.
- Cloning remote repos during setup. Step 3 only registers existing local directories the operator already cloned themselves.
- LLM Profile composition beyond one Profile per purpose. Power users compose alternative profiles after setup on the existing Settings → LLM page.
- Persistence of intermediate wizard state across reloads. A reload during setup resets to step 1.
- Replacing or extending the existing `validate_local_path` security model. The wizard reuses the same blocklist.

## User Flow

```
GET /api/v1/setup/status → { initialized: false }
   ↓
/setup mounts step 1 (admin password)
   ↓
   Next →
   Step 2: pick provider (api_kind, base_url, api_key)
           click "Fetch available models" → POST /api/v1/setup/probe-models
           pick one model per purpose (6 combo-boxes)
           Next or Skip →
   Step 3: ServerPathBrowser — GET /api/v1/setup/fs/roots, /list
           click "Use this folder" → list with detect_repos=true
           Next (with detected repos) or Skip →
   Step 4: review summary + checkbox list of detected repos
           Finish → POST /api/v1/setup
           response sets auth cookie
           setAuthenticated(true), navigate("/")
```

Reload at any step returns the user to step 1.
Manual URL entry cannot land on a later step because each step is a state mutation, not a route.

## Architecture Overview

### Frontend

- **Route:** `frontend/src/routes/_guest/setup.tsx` (single route, four step components rendered by client state).
- **State:** `frontend/src/features/setup/setupWizardStore.ts` — Zustand store, in-memory only.
- **Components:**
  - `SetupWizard` shell: progress indicator, step renderer, footer with Back/Next/Skip/Finish.
  - `StepPassword`, `StepLLM`, `StepRepoPath`, `StepFinish`.
  - `ServerPathBrowser` (reusable; also used on Settings page).

### Backend

- **New router:** `backend/app/api/routes/setup.py` mounted at `/api/v1/setup`.
- **Removed router contents:** `POST /api/v1/auth/setup` and `GET /api/v1/auth/status` are deleted from `routes/auth.py`.
- **Shared dependency:** `require_uninitialized` (in `app/api/auth.py`) — gates every wizard endpoint by checking that the `admin_password_hash` Config row does not exist.
- **Existing helper reused:** `validate_local_path` from `app/services/repo_manager.py`, extended with an optional `must_not_be_repo` flag.
- **Existing helper reused:** `_replace_orchestrator` from `app/api/routes/config.py` for atomic LLM swap.

### Settings page addition

- New "Default code repo path" card on `/settings` reuses `ServerPathBrowser` with auth.
- Endpoints: `GET` and `PUT /api/v1/config/repos-path` (authenticated).

## Wizard Store Shape

```ts
type Purpose =
  | "embedding" | "extraction" | "classification"
  | "reasoning" | "summarization" | "reranker"

type SetupWizardState = {
  step: 1 | 2 | 3 | 4
  password: { value: string; confirm: string }
  llm: {
    skipped: boolean
    provider_name: string
    api_kind: string
    base_url: string
    api_key: string
    supports_embedding: boolean
    models: string[]
    perPurpose: Record<Purpose, { model: string; reasoning: boolean; dimensions?: number }>
  }
  repos: {
    skipped: boolean
    basePath: string
    detected: { name: string; subPath: string; selected: boolean }[]
  }
  // setters and step transitions
}
```

The required purposes for advancing from step 2 are `extraction`, `classification`, and `reasoning`. `embedding` is also required *unless* `supports_embedding=false` (e.g. Anthropic, DeepSeek). `summarization` and `reranker` are always optional. Skipping step 2 sets `skipped = true` and bypasses validation. Skipping any individual purpose at finalize time means that purpose falls back to the `Settings.llm_*` default (already handled by `services.config.get_llm_config`).

## Backend Endpoints

All endpoints under `/api/v1/setup/*` declare `Depends(require_uninitialized)` and 403 once setup has completed.

### `GET /api/v1/setup/status`

Replaces `/api/v1/auth/status`. Public; no `require_uninitialized` since the response itself answers that question.

```python
class StatusResponse(BaseModel):
    initialized: bool
```

### `POST /api/v1/setup/probe-models`

In-memory probe. No DB writes.

```python
class ProbeModelsRequest(BaseModel):
    api_kind: Literal["openai", "anthropic", "ollama", "google", "deepseek", "zai"]
    base_url: str
    api_key: str | None = None

class ProbeModelsResponse(BaseModel):
    models: list[str]
    fetched_via: str
    error: str | None
```

Logic mirrors `list_llm_provider_models_route` in `routes/config.py`: Anthropic uses `x-api-key + anthropic-version`, Ollama hits the native `/api/tags` path, others use `Bearer` against `/v1/models`. The user's typed connection details are used directly — no DB lookup.

### `GET /api/v1/setup/fs/roots`

```python
class FsRoot(BaseModel):
    path: str
    label: str

class FsRootsResponse(BaseModel):
    roots: list[FsRoot]
```

Windows: enumerate `A:\` through `Z:\` via `os.path.exists`.
POSIX: `[{path: "/", label: "/"}, {path: str(Path.home()), label: "~"}]`.

### `GET /api/v1/setup/fs/list`

Query params: `path` (required, urldecoded), `detect_repos: bool = False`.

```python
class FsListEntry(BaseModel):
    name: str
    path: str
    is_dir: bool
    is_git: bool
    has_repos: bool
    repo_count: int

class FsListResponse(BaseModel):
    path: str
    parent: str | None
    entries: list[FsListEntry]
    is_git: bool
    blocked_reason: str | None
```

Validation:
- Resolve via `validate_local_path`. If it raises, return 422 with the error string in `blocked_reason`.
- When `detect_repos=true`, the call also implies `must_not_be_repo=true` — used on the wizard's "Use this folder" confirm to refuse a path that is itself a git repo. Plain navigation calls leave it false so the user can step through any folder layer.
- Symlinks are not followed during the immediate-child scan (`Path.iterdir()` returns symlink entries but the `is_git` / `has_repos` checks use `Path.is_dir()` without resolving target trees).

### `POST /api/v1/setup`

The single finalize endpoint.

```python
class SetupLLMPurpose(BaseModel):
    model: str
    reasoning: bool = False
    dimensions: int | None = None

class SetupLLM(BaseModel):
    provider_name: str = Field(min_length=1, max_length=64)
    api_kind: str
    base_url: str
    api_key: str | None = None
    supports_embedding: bool = True
    purposes: dict[Literal["embedding","extraction","classification","reasoning","summarization","reranker"], SetupLLMPurpose]

class SetupRepo(BaseModel):
    name: str
    sub_path: str

class SetupRepos(BaseModel):
    base_path: str
    repos: list[SetupRepo] = []

class SetupRequest(BaseModel):
    password: str = Field(min_length=8, max_length=128)
    llm: SetupLLM | None = None
    repos: SetupRepos | None = None

class SetupSectionStatus(BaseModel):
    ok: bool
    message: str | None = None

class SetupResponse(BaseModel):
    password: SetupSectionStatus
    llm: SetupSectionStatus
    repos: SetupSectionStatus
    repos_added: list[str]
    repos_failed: list[dict]
```

Handler order — wraps the work in a single outer transaction with savepoints (`session.begin_nested`) around each optional block so failures in LLM or repos roll back only that block while the password commit holds:

1. `require_uninitialized` runs first.
2. Acquire `request.app.state.llm_config_lock` (matches the existing `update_llm_config` pattern; prevents two concurrent admins or a wizard + a settings save from racing on `app.state.llm`).
3. **Password block** — hash, write `Config(admin_password_hash)`, write `AuditLog(action="auth_setup")`. Failure here propagates as a 500; nothing else has been attempted yet.
4. **LLM block** (skipped when `llm is None`), inside a savepoint:
   - Create one `LLMProvider` row named `provider_name`.
   - For each purpose in `llm.purposes`, create one `LLMProfile` row named `default-{purpose}`. Embedding profile: `is_embedding=True`, `reasoning=False`. Other purposes: `is_embedding=False`, `reasoning=<provided>`.
   - For each purpose, create one `LLMPurposeConfigRow` linking purpose → provider_id + profile_id with `model` set; `dimensions` only for embedding.
   - Any exception rolls back the savepoint only; outer transaction continues. Status flips to `llm.ok=False` with the error message.
5. **Repos block** (skipped when `repos is None`):
   - In a savepoint: write `Config(key="repos_default_local_path", value={"path": base_path})`. If this savepoint fails, set `repos.ok=False` and skip the per-repo loop.
   - Per-`SetupRepo`, run `validate_local_path(base_path / sub_path, must_not_be_repo=False)` and create a `Repository(provider="local", local_path=..., status="ready")` with no `url`, each in its own savepoint so per-row failures don't affect other rows.
   - Per-row failures push `{name, error}` to `repos_failed`; successes push `name` to `repos_added`.
6. Commit the outer transaction.
7. Only if the LLM block succeeded: re-resolve `fetch_llm_config` and rebuild the orchestrator via `_replace_orchestrator`.
8. Audit-log `setup_complete` with the per-section outcomes.
9. Issue auth cookie via `set_auth_cookie`. Return `SetupResponse`.

### `GET /api/v1/config/repos-path`, `PUT /api/v1/config/repos-path` (authenticated)

```python
class ReposPathResponse(BaseModel):
    path: str | None

class ReposPathUpdate(BaseModel):
    path: str
```

PUT runs `validate_local_path(path, must_not_be_repo=True)` and stores the result in `Config(key="repos_default_local_path")`.

### `GET /api/v1/system/fs/roots`, `GET /api/v1/system/fs/list` (authenticated)

Same response shapes as the `/api/v1/setup/fs/*` endpoints; only difference is the auth dependency. The Settings page mounts `ServerPathBrowser` against these so post-setup edits do not depend on the wizard-only endpoints (which 403 once the install is initialised).

## Validation and Security

- **`validate_local_path`** gains an optional `must_not_be_repo: bool = False` parameter. The setup FS-list endpoint passes `must_not_be_repo=True` only when the user clicks "Use this folder" (final selection); navigation calls do not. The Settings PUT also passes `must_not_be_repo=True`.
- **`require_uninitialized`** — single guard for all wizard endpoints. Sole gate; no setup_secret needed because the install is local-network-only (per project memory).
- **API keys** sent to `/setup/probe-models` are used in-memory only; never logged, never persisted unless the user reaches finalize.
- **Concurrent finalize attempts** are prevented by the `Config.key` UNIQUE constraint; the second request 403s on the password block's pre-check, never writes.
- **FS-list endpoint disclosure surface:** only reachable when uninitialized. The blocklist still applies during the open window, so credential trees (`~/.ssh`, `~/.aws`, etc.) cannot be enumerated.

## Frontend Components

### `SetupWizard` shell

- Progress indicator (1 → 2 → 3 → 4) with current/completed/skipped chips.
- Renders the active step component.
- Footer: Back (disabled on step 1), Next (disabled when step is invalid), Skip (only on steps 2 and 3), Finish (only on step 4).

### `StepPassword`

- Two `Input` fields (password, confirm) plus inline validation.
- Validation: ≥ 8 chars, must match confirm.
- Next enabled when valid.

### `StepLLM`

- Provider name (free-text label, defaults to api_kind capitalised).
- `api_kind` `Select` reusing `API_KIND_OPTIONS`.
- `base_url` `Input` with sensible default per api_kind (mirroring existing UI's defaults).
- `api_key` `Input` with `type="password"` and visibility toggle.
- "Fetch available models" button → `POST /api/v1/setup/probe-models`. On success, fills `llm.models`. On error, inline message.
- Six per-purpose rows: each is a combo-box (datalist + free-text). "reasoning" toggle for the four non-embedding non-reranker purposes; "dimensions" override for embedding. The embedding row is hidden when `supports_embedding=false`.
- Skip button → `llm.skipped = true`, advance.
- Next enabled when the required purposes have a non-empty model id (extraction, classification, reasoning always required; embedding required only when `supports_embedding=true`).

### `StepRepoPath`

- Embeds `ServerPathBrowser` in `mode="select-parent"`.
- On confirm: stores `repos.basePath`, calls `GET /api/v1/setup/fs/list?detect_repos=true&path=...`, populates `repos.detected` with `selected: true` per entry.
- If the chosen path itself has a `.git`, the browser shows an inline error and refuses to confirm (server returns 422 from the `must_not_be_repo` check).
- Skip button → `repos.skipped = true`, advance.

### `StepFinish`

- Three summary cards: password ("Set"), LLM (provider name + per-purpose model rows or "Skipped"), repos (basePath + a checkbox list with editable name inline; "Skipped" if step 3 was skipped). Renaming a repo row mutates `repos.detected[i].name`; unchecking sets `selected=false` and excludes it from the finalize POST.
- Finish button → `POST /api/v1/setup` with the entire draft (only `selected` repos are sent).

### `ServerPathBrowser`

Props:

```ts
type Props = {
  value: string                       // current path
  onChange: (path: string) => void    // navigation
  onConfirm: (path: string) => void   // "Use this folder"
  mode: "select-parent"
  disabled?: boolean
}
```

Internal calls: routed through `apiBase` prop. When mounted from the wizard, `apiBase="/setup"`. When mounted from the Settings page, `apiBase="/system"`. Both endpoints return identical shapes.

Layout:
- Top: breadcrumb + manual path input.
- Sidebar: drive/root chips.
- Main: list of children with two badges per row (`git` and `repos:N`).
- Footer: "Use this folder" button (disabled when `is_git=true` for the current path).
- Inline error region.

For Settings page reuse, the same component takes `apiBase="/system"` and hits the authenticated mirror endpoints described above.

## Testing

### Backend unit tests (`backend/tests/unit/test_setup_route.py`)

- `require_uninitialized` returns 403 when the password row exists.
- `POST /setup/probe-models` builds the right URL/headers per `api_kind` (parameterise; mock `httpx.AsyncClient`).
- `GET /setup/fs/list` rejects `~/.ssh`, accepts a tmp directory, marks `is_git=true` correctly, populates `repo_count` correctly when `detect_repos=true`.
- `POST /setup` happy path: password + LLM + repos all succeed; verifies one provider, six profiles, six purpose rows, N repository rows, `setup_complete` audit log entry, auth cookie set.
- `POST /setup` partial: bad sub-path in repos → password and LLM committed, repo listed in `repos_failed`.
- `POST /setup` LLM-skipped: only password and repos rows written.
- `POST /setup` repos-skipped: only password (and LLM) written.
- `POST /setup` both-skipped: only password written.
- `POST /setup` rejects with 403 once a password row exists.
- `PUT /api/v1/config/repos-path` writes the Config row and applies `validate_local_path`.

### E2E migration

- `docs/e2e/scripts/01_auth_flow.py` switches from `POST /auth/setup` to `POST /setup` with the minimal `{password}` payload.
- `backend/tests/conftest.py` and `backend/tests/unit/conftest.py` migrate.
- `backend/tests/test_backfill_v2.py` migrates.
- `backend/scripts/seed_test_memories.py` migrates.

### Manual Playwright sweep

End-to-end verification once implementation is in place:

1. Reset DB to fresh-install state. Open `/`. Confirm redirect to `/setup`.
2. Walk steps 1 → 2 → 3 → 4 with all fields populated; click Finish; confirm cookie set, navigation to `/`.
3. Reset DB. Walk with step 2 skipped; confirm Settings shows `embedding` purpose using fallback defaults, no provider rows.
4. Reset DB. Walk with step 3 skipped; confirm Settings page exposes the empty "Default code repo path" field.
5. Confirm direct navigation to `/setup` after init redirects to `/login`.

## Open Items

None. All design choices closed; ready to write the implementation plan.

## File Inventory (touched by implementation)

**New files:**
- `backend/app/api/routes/setup.py` — wizard router (`/api/v1/setup/*`).
- `backend/app/api/routes/system.py` — authenticated FS endpoints (`/api/v1/system/fs/*`).
- `backend/tests/unit/test_setup_route.py`
- `frontend/src/features/setup/setupWizardStore.ts`
- `frontend/src/components/setup/SetupWizard.tsx`
- `frontend/src/components/setup/StepPassword.tsx`
- `frontend/src/components/setup/StepLLM.tsx`
- `frontend/src/components/setup/StepRepoPath.tsx`
- `frontend/src/components/setup/StepFinish.tsx`
- `frontend/src/components/setup/ServerPathBrowser.tsx`

**Modified:**
- `backend/app/api/auth.py` — add `require_uninitialized` dependency.
- `backend/app/api/routes/auth.py` — remove `auth_setup` and `auth_status`; keep login/logout/me/refresh/change-password.
- `backend/app/api/routes/config.py` — add `repos-path` GET/PUT.
- `backend/app/services/repo_manager.py` — add `must_not_be_repo: bool = False` flag to `validate_local_path`.
- `backend/app/main.py` (or `app/api/__init__.py` — wherever routers register) — mount `setup` and `system` routers.
- `frontend/src/routes/_guest/setup.tsx` — render `SetupWizard` instead of the inline form.
- `frontend/src/lib/api.ts` — point `checkSetupStatus` at `/setup/status`; remove `setup`; add `probeModels`, `fsRoots`, `fsList`, `finalizeSetup`, `getReposPath`, `setReposPath`, `systemFsRoots`, `systemFsList`.
- `frontend/src/routes/_authenticated/settings.tsx` — add the "Default code repo path" card with embedded `ServerPathBrowser` (`apiBase="/system"`).
- `frontend/src/hooks/api/*` — register the new query hooks if hook files mirror api endpoints (audit before edit).
- `docs/e2e/scripts/lib/client.py`, `docs/e2e/scripts/01_auth_flow.py` — migrate to `/setup` (minimal `{password}` payload).
- `backend/tests/conftest.py`, `backend/tests/unit/conftest.py`, `backend/tests/test_backfill_v2.py`, `backend/scripts/seed_test_memories.py` — migrate setup call.
