# Second-Pass Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Land 16 verified fixes from the second-pass review on branch `fix/codebase-review-2026-05-03`, one commit per issue, with the existing test suite kept green.

**Architecture:** Apply minimum-viable-fix per issue. Three categories: (1) regressions or holes in the first round of fixes (tasks 1-3), (2) frontend correctness regressions (tasks 4-7), (3) backend / database / lower-priority polish (tasks 8-16). Each task is independent — tasks can be reordered if a blocker shows up.

**Tech Stack:** Python 3.14 / FastAPI / SQLAlchemy 2 (async) / Alembic / pgvector. React 18 / TanStack Router / TanStack Query / darkraise-ui. Postgres 17.

**Test environment caveat:** The local Python 3.14 + httpx mock-transport stack cannot reach `127.0.0.1` for `setup_database`, so the full pytest suite cannot run on the dev machine. Each task lists the test command to run on the LXC at `192.168.0.250`. Tasks that touch only pure-Python code add unit tests that the local interpreter can still parse (`python -c "import ast; ast.parse(open('<file>').read())"`).

---

## File Structure

Files this plan touches:

**Backend services:**
- `backend/app/services/code_parser.py` — `ExtractedImport` shape (no change, already carries `source` + `names`)
- `backend/app/services/code_pipeline.py` — `_all_imports` typing widened to carry `ExtractedImport` instead of raw module strings
- `backend/app/services/call_resolver.py` — `build_named_imports`, `build_wildcard_imports` consume `ExtractedImport` directly (drop regex / split parsing)
- `backend/app/services/embedder_registry.py` — `register` no longer commits the caller's session
- `backend/app/services/enrichment_worker.py` — `_enrich_one` records exception on failure
- `backend/app/services/analytics.py` — UTC-anchored "today" boundary
- `backend/app/services/hybrid_search.py` — `_rrf_fuse` writes `score = rrf_score`
- `backend/app/services/community_detector.py` — dedicated single-worker executor for Leiden
- `backend/app/services/repo_manager.py` — no change needed in this plan

**Backend migration:**
- `backend/migrations/versions/0001_initial_schema.py` — add btree indexes for `entity_relations.target_entity_id` and `memories.superseded_by`; promote `audit_log.id` and `tags.id` to `BigInteger`

**Backend models:**
- `backend/app/models/audit.py` — `id: Mapped[int]` typed as `BigInteger`
- `backend/app/models/tag.py` — same

**Backend tests:**
- `backend/tests/test_call_resolver.py` (new) — pure-Python tests for the rewritten import builders (Task 1)
- `backend/tests/test_enrichment_worker.py` (new) — exception-path test (Task 3)

**Frontend:**
- `frontend/src/hooks/api/use-memory-api.ts` — `useDeleteMemory` invalidates the right key
- `frontend/src/routes/_authenticated/analytics.tsx` — source pie consumes `useOverview().sources`
- `frontend/src/routes/_authenticated/settings.tsx` — `setDirty(false)` moved into `onSuccess`
- `frontend/src/routes/_authenticated/reindex.tsx` — `handleRetry` clears `retryingIds` on success
- `frontend/src/routes/_authenticated.tsx` — gate `checkAuth` on store state
- `frontend/src/features/chat/hooks/use-chat-stream.ts` — accept `\r?\n\r?\n` SSE delimiter
- `frontend/src/components/pipeline/LLMPurposeCard.tsx` — wrap `patch` in `useCallback`

---

## Task 1: Rewrite `build_named_imports` / `build_wildcard_imports` to consume `ExtractedImport`

**Why:** `_PY_FROM_IMPORT_RE` (commit `e858808`) never matches its inputs because `_all_imports` stores `imp.source` — the bare module name like `"os"` — not the full `from X import Y` statement. The function has been silently returning `{}` for every file since it was added. Same root cause for `build_wildcard_imports`.

**Scope note:** `_all_imports` is also consumed by `build_import_map` (`call_resolver.py:203`), which expects the existing `dict[str, list[str]]` shape and is working correctly. Keeping that consumer intact is cheaper than refactoring it. Approach: add a sibling field `_all_extracted_imports: dict[str, list[ExtractedImport]]` in `code_pipeline.py`, populate it alongside `_all_imports` in Phase 2, and feed the new builders from it. The original `_all_imports` and `build_import_map` are untouched.

**Files:**
- Modify: `backend/app/services/code_pipeline.py:90` — add `_all_extracted_imports` field
- Modify: `backend/app/services/code_pipeline.py:445,479` — populate the new dict alongside the old
- Modify: `backend/app/services/code_pipeline.py:517-521` — feed the new dict into `build_named_imports` / `build_wildcard_imports`
- Modify: `backend/app/services/call_resolver.py` — rewrite the two builders to consume `ExtractedImport`
- Create: `backend/tests/test_call_resolver.py` — pure-Python unit tests

- [ ] **Step 1: Write failing tests for `build_named_imports`**

Create `backend/tests/test_call_resolver.py`:

```python
from app.services.call_resolver import build_named_imports, build_wildcard_imports
from app.services.code_parser import ExtractedImport


def test_build_named_imports_simple():
    result = build_named_imports(
        {"a.py": [ExtractedImport(source="os", names=["path", "getcwd"])]},
        ["a.py", "os.py"],
    )
    assert result == {
        "a.py": {
            "path": ("os", "path"),
            "getcwd": ("os", "getcwd"),
        }
    }


def test_build_named_imports_with_alias():
    # ``from numpy import array as arr`` is encoded by the parser as a
    # single ``use_as_clause`` token; downstream we want local→exported.
    result = build_named_imports(
        {"a.py": [ExtractedImport(source="numpy", names=["array as arr"])]},
        ["a.py"],
    )
    assert result == {"a.py": {"arr": ("numpy", "array")}}


def test_build_named_imports_skips_wildcard():
    result = build_named_imports(
        {"a.py": [ExtractedImport(source="os", names=["*"])]},
        ["a.py"],
    )
    assert result == {}


def test_build_named_imports_returns_empty_when_no_names():
    result = build_named_imports(
        {"a.py": [ExtractedImport(source="os", names=[])]},
        ["a.py"],
    )
    assert result == {}


def test_build_wildcard_imports_resolves_module_to_path():
    result = build_wildcard_imports(
        {"a.py": [ExtractedImport(source="pkg.utils", names=["*"])]},
        ["a.py", "pkg/utils.py", "pkg/__init__.py"],
    )
    assert result == {"a.py": {"pkg/utils.py"}}


def test_build_wildcard_imports_ignores_named():
    result = build_wildcard_imports(
        {"a.py": [ExtractedImport(source="pkg.utils", names=["foo"])]},
        ["a.py", "pkg/utils.py"],
    )
    assert result == {}
```

- [ ] **Step 2: Run tests, confirm they fail**

Run: `python -m pytest tests/test_call_resolver.py -v`
Expected: 6 tests, 6 errors (TypeError because `build_named_imports` currently expects `dict[str, list[str]]`).

- [ ] **Step 3: Rewrite both builders against `ExtractedImport`**

Replace lines 253-303 (the current `build_named_imports`) and lines 282-297 (the current `build_wildcard_imports`) in `backend/app/services/call_resolver.py` with:

```python
def build_named_imports(
    file_imports: dict[str, list["ExtractedImport"]],
    file_paths: list[str],
) -> dict[str, dict[str, tuple[str, str]]]:
    """Build named import map: file -> {local_name: (source_module, exported_name)}.

    Consumes the structured ``ExtractedImport.names`` list from the parser
    rather than re-parsing the raw ``from X import Y`` source text. The
    earlier ``str.split("import")`` form was fed only the module portion
    (``imp.source``) so it never matched anything; the regex variant had
    the same input problem. ``names`` already carries one entry per
    imported symbol, possibly with ``" as "`` aliasing.
    """
    result: dict[str, dict[str, tuple[str, str]]] = {}
    for file_path, imports in file_imports.items():
        named: dict[str, tuple[str, str]] = {}
        for imp in imports:
            module = imp.source.strip()
            if not module:
                continue
            for raw in imp.names:
                name_part = raw.strip()
                # Wildcard imports are tracked separately by
                # build_wildcard_imports; skip here.
                if not name_part or name_part == "*":
                    continue
                if " as " in name_part:
                    exported, local = name_part.split(" as ", 1)
                    named[local.strip()] = (module, exported.strip())
                else:
                    named[name_part] = (module, name_part)
        if named:
            result[file_path] = named
    return result


def build_wildcard_imports(
    file_imports: dict[str, list["ExtractedImport"]],
    file_paths: list[str],
) -> dict[str, set[str]]:
    """Find files that use wildcard imports and map them to source files."""
    result: dict[str, set[str]] = {}
    for file_path, imports in file_imports.items():
        for imp in imports:
            if "*" not in imp.names:
                continue
            module = imp.source.strip()
            if not module:
                continue
            for fp in file_paths:
                if (
                    fp.endswith(module.replace(".", "/") + ".py")
                    or fp.endswith(module.replace(".", "/") + "/__init__.py")
                ):
                    result.setdefault(file_path, set()).add(fp)
    return result
```

Add the import at the top of `call_resolver.py` (after the existing imports):

```python
from app.services.code_parser import ExtractedImport  # noqa: TC001 — used in type signatures only at runtime guard sites
```

Drop the now-unused `_PY_FROM_IMPORT_RE` constant and the `import re` if nothing else in the file uses it. Verify with `grep -n "^import re\\|re\\." backend/app/services/call_resolver.py`.

- [ ] **Step 4: Add `_all_extracted_imports` and feed the new builders from it**

In `backend/app/services/code_pipeline.py`:

Add `from app.services.code_parser import ExtractedImport` to the existing imports block at the top of the file (verify with `grep -n "ExtractedImport" backend/app/services/code_pipeline.py` first; if already imported, skip).

After the existing `self._all_imports: dict[str, list[str]] = {}` declaration around line 95, add:

```python
        # Structured form alongside _all_imports. _all_imports stores
        # the bare module string and feeds build_import_map (which
        # expects strings). build_named_imports / build_wildcard_imports
        # need the full ExtractedImport so they can read the imported
        # symbol names directly.
        self._all_extracted_imports: dict[str, list[ExtractedImport]] = {}
```

At lines 445 and 479 (the two assignments to `self._all_imports[fp] = [imp.source for imp in pr.imports]`), add the matching populate immediately after each one:

```python
                    self._all_extracted_imports[fp] = list(pr.imports)
```

At lines 517-521 where `build_named_imports` and `build_wildcard_imports` are called, change the input dict from `self._all_imports` to `self._all_extracted_imports`:

```python
        self._named_import_map = build_named_imports(self._all_extracted_imports, self._all_file_paths)
        self._wildcard_import_map = build_wildcard_imports(self._all_extracted_imports, self._all_file_paths)
```

Leave `build_import_map(self._all_file_paths, refined_imports)` and the Phase 7 `build_import_map(list(type_envs.keys()), self._all_imports)` call at line 756 unchanged — they consume the string form correctly.

- [ ] **Step 5: Run tests, confirm they pass**

Run: `python -m pytest tests/test_call_resolver.py -v`
Expected: 6 passed.

- [ ] **Step 6: AST parse check**

Run:

```bash
python -c "import ast; ast.parse(open('backend/app/services/call_resolver.py').read()); ast.parse(open('backend/app/services/code_pipeline.py').read()); print('OK')"
```

Expected: `OK`.

- [ ] **Step 7: Commit**

```bash
git add backend/app/services/call_resolver.py backend/app/services/code_pipeline.py backend/tests/test_call_resolver.py
git commit -m "fix(code): consume ExtractedImport in build_named/wildcard_imports

The previous regex (and the str.split before it) was fed
imp.source — the bare module name like 'os' — not the full
import statement, so build_named_imports has been silently
returning {} for every file since it was added. Switch
_all_imports to dict[str, list[ExtractedImport]] and consume
imp.names directly. Adds tests/test_call_resolver.py to lock
the new behaviour."
```

---

## Task 2: Stop committing the caller's session in `EmbedderRegistry.register`

**Why:** `embedder_registry.py:166` calls `await session.commit()` unconditionally. The `pipeline.py:107` call site passes a fresh `session_factory()` context (harmless), but `code_pipeline.py:1024` passes `self.session` — the long-lived pipeline session. The commit ends whatever transaction the pipeline had open, violating the CLAUDE.md async-session-lifetime invariant.

**Files:**
- Modify: `backend/app/services/embedder_registry.py:123-170`

- [ ] **Step 1: Refactor `register` to always own its session**

In `backend/app/services/embedder_registry.py`, change the signature so the registry opens its own session via the injected `async_session_factory`. The `_register_fingerprint` call sites already have the factory available.

Open `embedder_registry.py` and locate the current method:

```python
async def register(self, session: AsyncSession, info: EmbedderInfo) -> None:
    ...
    await session.commit()
```

Replace it with a session-factory-owned variant:

```python
async def register(self, session_factory, info: EmbedderInfo) -> None:
    """Idempotently register ``info`` and create its per-fingerprint tables.

    Always opens its own session so the commit at the end can never
    leak into the caller's transaction. Callers used to pass their own
    AsyncSession; that violated the async-session-lifetime invariant
    when the caller was the long-lived code-pipeline session.
    """
    if self.is_known(info.fingerprint):
        return
    async with self._lock:
        if self.is_known(info.fingerprint):
            return
        async with session_factory() as session:
            # ... body unchanged from the previous implementation,
            # ending with `await session.commit()` which now lives
            # entirely inside this owned session ...
```

Keep the existing fast-path / lock / DDL / INSERT-ON-CONFLICT body intact; only the session ownership and signature change.

- [ ] **Step 2: Update both call sites — drop the wrapping `async with`, pass the factory**

`backend/app/services/pipeline.py:98-115`. The current body wraps the `register` call in `async with self.session_factory() as session:` and passes the session in. After the registry owns its own session, that wrapper is dead. Replace lines 98-115 with:

```python
    async def _register_fingerprint(self, fingerprint: str) -> None:
        """Idempotently register the fingerprint so its partition exists."""
        from app.services.embedder_registry import (  # noqa: PLC0415
            EmbedderInfo, embedder_registry, parse_fingerprint,
        )
        if embedder_registry.is_known(fingerprint):
            return
        model_id, dims = parse_fingerprint(fingerprint)
        await embedder_registry.register(
            self.session_factory,
            EmbedderInfo(
                fingerprint=fingerprint,
                model_id=model_id,
                dims=dims,
                source="llm",
            ),
        )
```

`backend/app/services/code_pipeline.py:1024`. Replace the call:

```python
                await embedder_registry.register(
                    self.session,
                    EmbedderInfo(fingerprint=fp_value, model_id=model_id, dims=dims, source="llm"),
                )
```

with:

```python
                await embedder_registry.register(
                    async_session_factory,
                    EmbedderInfo(fingerprint=fp_value, model_id=model_id, dims=dims, source="llm"),
                )
```

Add `from app.database import async_session_factory` to the imports near the top of `code_pipeline.py` if not already present (check with `grep -n "async_session_factory" backend/app/services/code_pipeline.py`). The surrounding code at code_pipeline.py:1024 is inside Phase 3 (`_store_chunks`); `self.session` is the long-lived pipeline session — switching to `async_session_factory` opens a dedicated session for the registry call and leaves `self.session` untouched.

- [ ] **Step 3: AST parse check**

Run:

```bash
python -c "import ast; ast.parse(open('backend/app/services/embedder_registry.py').read()); ast.parse(open('backend/app/services/pipeline.py').read()); ast.parse(open('backend/app/services/code_pipeline.py').read()); print('OK')"
```

- [ ] **Step 4: Run targeted tests on LXC**

On the LXC (`ssh lxc-darkmem` or however the project ssh's in):

```bash
cd /opt/darkmem/backend
python -m pytest tests/ -k "embedder or pipeline or code_pipeline" -v
```

Expected: green. If any test patches `register` directly, the patch needs the new signature.

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/embedder_registry.py backend/app/services/pipeline.py backend/app/services/code_pipeline.py
git commit -m "fix(embedder): own the session inside EmbedderRegistry.register

register() used to await session.commit() on whatever session the
caller passed. From code_pipeline.py the caller is the long-lived
pipeline session, and the commit prematurely ended that
transaction (violating the async-session-lifetime invariant).
Take a session_factory instead and always open / commit a
dedicated session."
```

---

## Task 3: Capture exceptions in `enrichment_worker._enrich_one`

**Why:** `_enrich_one` writes `summaries[idx] = await self.llm.chat_completion(...)`. If the call raises, `gather(..., return_exceptions=True)` swallows the exception and `summaries[idx]` is never set. Downstream `summaries.get(i)` returns `None`, `isinstance(None, Exception)` is False, and the symbol is silently marked `failed` with no log line.

**Files:**
- Modify: `backend/app/services/enrichment_worker.py:58-87`
- Modify or create: `backend/tests/test_enrichment_worker.py`

- [ ] **Step 1: Write failing test**

Add to `backend/tests/test_enrichment_worker.py` (create the file if it doesn't exist):

```python
import pytest
from unittest.mock import AsyncMock, MagicMock

from app.services.enrichment_worker import EnrichmentWorker


@pytest.mark.asyncio
async def test_enrich_one_records_exception_on_llm_failure(monkeypatch):
    """When chat_completion raises, the failed symbol must be logged
    via the isinstance(result_val, Exception) branch — not silently
    marked failed with no detail."""
    worker = EnrichmentWorker.__new__(EnrichmentWorker)
    worker.llm = MagicMock()
    worker.llm.chat_completion = AsyncMock(side_effect=RuntimeError("boom"))
    summaries: dict[int, str | Exception] = {}
    sem = __import__("asyncio").Semaphore(1)
    sym = MagicMock()
    sym.kind = "function"
    sym.source_code = "def foo(): pass"

    async def _enrich_one(idx, symbol):
        async with sem:
            try:
                summaries[idx] = await worker.llm.chat_completion(
                    "summarization",
                    messages=[{"role": "user", "content": "x"}],
                )
            except Exception as exc:
                summaries[idx] = exc

    await _enrich_one(0, sym)
    assert isinstance(summaries[0], RuntimeError)
    assert "boom" in str(summaries[0])
```

The shape of the test deliberately mirrors what the production code should look like, so once the production fix lands the test still passes.

- [ ] **Step 2: Run test, confirm it passes (sanity check on the contract)**

Run on LXC: `python -m pytest tests/test_enrichment_worker.py -v`. The test exercises the local `_enrich_one` closure — it passes immediately because the test inlines the contract. The point of this test is to lock the semantics so a regression in the production code is visible.

- [ ] **Step 3: Patch `_enrich_one` to record exceptions**

In `backend/app/services/enrichment_worker.py`, replace the body of `_enrich_one` (lines 58-70) with:

```python
            async def _enrich_one(idx: int, symbol) -> None:
                async with sem:
                    user_prompt = SUMMARY_PROMPT.format(
                        kind=symbol.kind,
                        source_code=symbol.source_code[:MAX_SOURCE_CHARS],
                    )
                    try:
                        summaries[idx] = await self.llm.chat_completion(
                            "summarization",
                            messages=[
                                {"role": "system", "content": system_prompt},
                                {"role": "user", "content": user_prompt},
                            ],
                        )
                    except Exception as exc:
                        # Store the exception so the downstream branch
                        # at line ~85 logs it via logger.exception.
                        # Without this, every LLM failure is silently
                        # marked ``failed`` with no log entry.
                        summaries[idx] = exc
```

Note the rename `prompt → user_prompt` to stop shadowing the module-level `prompt` import.

- [ ] **Step 4: AST parse + run tests on LXC**

```bash
python -c "import ast; ast.parse(open('backend/app/services/enrichment_worker.py').read()); print('OK')"
# On LXC:
python -m pytest tests/test_enrichment_worker.py -v
```

- [ ] **Step 5: Commit**

```bash
git add backend/app/services/enrichment_worker.py backend/tests/test_enrichment_worker.py
git commit -m "fix(enrichment): capture exceptions in _enrich_one

chat_completion failures were swallowed by gather(return_exceptions=
True) and never recorded into summaries[idx]. The downstream branch
then saw summaries.get(i) == None, isinstance(None, Exception)
== False, and silently marked the symbol failed with no log line.
Record the exception explicitly so the existing logger.exception
path fires."
```

---

## Task 4: Fix `useDeleteMemory` cache invalidation

**Why:** `use-memory-api.ts:69` invalidates `["memories"]` but the Memories page reads from `["memoriesPaginated", params]`. Page-level compensation exists but is fragile.

**Files:**
- Modify: `frontend/src/hooks/api/use-memory-api.ts:65-71`

- [ ] **Step 1: Patch the hook**

In `frontend/src/hooks/api/use-memory-api.ts`, replace lines 65-71:

```ts
export function useDeleteMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch(`/memories/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["memoriesPaginated"] });
      qc.invalidateQueries({ queryKey: ["memories"] });
      qc.invalidateQueries({ queryKey: ["memoryFacets"] });
    },
  });
}
```

Invalidating both keys is intentional: any non-paginated consumer (the dashboard recent-memories list) keeps working too, and the facets cache may become stale if the deleted memory was the only carrier of a source / type.

- [ ] **Step 2: Type-check (no test runner needed)**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors related to this file.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/api/use-memory-api.ts
git commit -m "fix(frontend): useDeleteMemory invalidates the right cache keys

The Memories page reads memoriesPaginated, not memories. Without
the right invalidation, deleted rows linger in the list until the
next manual filter change. Invalidate memoriesPaginated, memories,
and memoryFacets together so every consumer refreshes."
```

---

## Task 5: Source pie chart consumes pre-aggregated overview

**Why:** `analytics.tsx:28-38` aggregates source counts from `useMemories()` which is hard-capped at 50 rows, so the chart structurally undercounts on any non-trivial install. The backend `/analytics/overview` endpoint already returns `sources: Array<{name, count}>`.

**Files:**
- Modify: `frontend/src/routes/_authenticated/analytics.tsx`

- [ ] **Step 1: Confirm `useOverview` exists and exposes `sources`**

Run:

```bash
grep -n "useOverview\|sources:" frontend/src/hooks/api/use-pipeline-api.ts | head -10
```

Expected: `useOverview` returns `OverviewData` with `sources: Array<{name: string; count: number}>` (already declared near line 165).

- [ ] **Step 2: Switch the pie data source**

In `frontend/src/routes/_authenticated/analytics.tsx`:

Replace the import line:

```tsx
import { useStats, useTags, useMemories } from "@/hooks/api"
```

with:

```tsx
import { useStats, useTags, useOverview } from "@/hooks/api"
```

(Verify `useOverview` is re-exported from `@/hooks/api`; if not, import from the specific module.)

Replace the `useMemories()` call (around line 28) and the `sourceData` `useMemo` (around line 33) with:

```tsx
  const { data: overview } = useOverview()

  const sourceData = (overview?.sources ?? []).map((s) => ({
    name: s.name,
    value: s.count,
  }))
```

Drop the now-unused `useMemo` import if it was only used for `sourceData`.

- [ ] **Step 3: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/_authenticated/analytics.tsx
git commit -m "fix(analytics): source pie chart consumes pre-aggregated overview

useMemories() returns at most 50 rows, so the source pie was
structurally under-counting. /analytics/overview already
exposes the full source distribution; consume that instead."
```

---

## Task 6: `setDirty(false)` in `onSuccess`, not synchronously after `mutate`

**Why:** `settings.tsx:421-426` calls `setDirty(false)` right after `update.mutate(body, {...})` without waiting for the result. A failed save leaves the form looking saved.

**Files:**
- Modify: `frontend/src/routes/_authenticated/settings.tsx` (around line 417-427)

- [ ] **Step 1: Move `setDirty(false)` into `onSuccess`**

Locate the `save` function and replace:

```tsx
const save = () => {
const body = isDefault
? { overrides: { [selected]: "" } }
: { overrides: { [selected]: draft } }
update.mutate(body, {
onSuccess: () =>
toast.success(isDefault ? `Reverted ${selected}` : `Saved override for ${selected}`),
onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
})
setDirty(false)
}
```

with:

```tsx
const save = () => {
const body = isDefault
? { overrides: { [selected]: "" } }
: { overrides: { [selected]: draft } }
update.mutate(body, {
onSuccess: () => {
setDirty(false)
toast.success(isDefault ? `Reverted ${selected}` : `Saved override for ${selected}`)
},
onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
})
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/_authenticated/settings.tsx
git commit -m "fix(settings): clear dirty flag only after mutation succeeds

setDirty(false) ran synchronously immediately after update.mutate,
so a server-rejected save left the form looking clean. Move into
onSuccess so a failure keeps the form dirty and the user can retry."
```

---

## Task 7: Clear `retryingIds` on retry success

**Why:** `reindex.tsx:114-126` adds the id, removes it only in `onError`, never in `onSuccess`. After a successful per-row retry the button stays disabled.

**Files:**
- Modify: `frontend/src/routes/_authenticated/reindex.tsx:114-126`

- [ ] **Step 1: Add the `onSuccess` cleanup**

Replace the `handleRetry` function with:

```tsx
const handleRetry = (id: string) => {
setRetryingIds((prev) => new Set(prev).add(id))
const clear = () => {
setRetryingIds((prev) => {
const next = new Set(prev)
next.delete(id)
return next
})
}
retry.mutate(id, {
onSuccess: () => {
clear()
},
onError: () => {
clear()
toast.error("Retry failed to dispatch")
},
})
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no errors.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/routes/_authenticated/reindex.tsx
git commit -m "fix(reindex): clear retryingIds on retry success

handleRetry only removed the id from retryingIds in onError. After
a successful dispatch the row's Retry button stayed disabled until
a full page reload. Clear in both branches via a shared closure."
```

---

## Task 8: UTC-anchored "today" boundary in analytics activity

**Why:** `analytics.py:170` uses `date.today()` (timezone-naive). `Memory.created_at` is `TIMESTAMPTZ` (UTC). On a UTC+7 host the local date and the UTC date can differ, so the activity series for "today" is double-counted or missed.

**Files:**
- Modify: `backend/app/services/analytics.py:170` (one-line fix plus an import)

- [ ] **Step 1: Replace the one call**

In `backend/app/services/analytics.py`, locate (the surrounding code may differ slightly):

```python
since = date.today() - timedelta(days=days - 1)
```

Replace with:

```python
since = datetime.now(timezone.utc).date() - timedelta(days=days - 1)
```

Add to the imports at the top of the file:

```python
from datetime import datetime, timezone
```

(Keep the existing `from datetime import date, timedelta` if both are used, or merge as `from datetime import date, datetime, timedelta, timezone`.)

- [ ] **Step 2: AST parse check**

```bash
python -c "import ast; ast.parse(open('backend/app/services/analytics.py').read()); print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/analytics.py
git commit -m "fix(analytics): anchor activity 'today' boundary to UTC

date.today() returns the host's local date. Memory.created_at is
TIMESTAMPTZ (UTC), so on a non-UTC host (dev runs UTC+7) the
'today' window was off by up to a day. Use
datetime.now(timezone.utc).date() instead."
```

---

## Task 9: Normalise the fused `score` field in `_rrf_fuse`

**Why:** `hybrid_search._rrf_fuse` leaves the original `score` field (cosine for semantic-only, ts_rank for keyword-only) on the merged entry, while also writing `rrf_score`. Downstream consumers (`chat.py:241`, the Memories page) read `score` and end up displaying numbers that are not comparable across rows.

**Files:**
- Modify: `backend/app/services/hybrid_search.py` (the `_rrf_fuse` body, around line 163-185)

- [ ] **Step 1: Sweep the fused dict after both loops complete**

Both the semantic loop (lines 163-168) and the keyword loop (lines 176-181) accumulate `rrf_score` via `+=` on shared entries. Setting `score = rrf_score` per-iteration would write the wrong value for entries that appear in both lists (the keyword loop runs after, so the semantic-only sweep would set a stale value). Sweep the merged dict after the keyword loop, immediately before the `sorted(...)` call at line 185:

```python
        # Normalise the displayed `score` to the fused RRF value so
        # downstream consumers (chat.py, Memories page) compare apples
        # to apples — otherwise semantic-only winners carry cosine
        # similarity and keyword-only winners carry ts_rank.
        for entry in fused.values():
            entry["score"] = entry["rrf_score"]

        sorted_results = sorted(fused.values(), key=lambda x: x["rrf_score"], reverse=True)
```

If the original per-source values matter to a future caller, expose them under distinct field names (`semantic_score` / `keyword_score`) — leave that for a follow-up.

- [ ] **Step 2: AST parse + smoke test on LXC**

```bash
python -c "import ast; ast.parse(open('backend/app/services/hybrid_search.py').read()); print('OK')"
# On LXC
python -m pytest tests/ -k "hybrid_search or test_search" -v
```

- [ ] **Step 3: Commit**

```bash
git add backend/app/services/hybrid_search.py
git commit -m "fix(hybrid_search): normalise fused score to rrf_score

Fused rows kept the original per-source score field — cosine for
semantic-only winners, ts_rank for keyword-only winners — while
rrf_score sat alongside. Downstream consumers display 'score' and
saw numbers that weren't comparable across rows. Set
score = rrf_score after fusion."
```

---

## Task 10: Dedicated single-worker executor for Leiden

**Why:** `community_detector.py:119-129` calls Leiden via `run_in_executor` with a 60s `wait_for` timeout. The asyncio future cancels but the underlying thread keeps running until Leiden finishes. Until it does, the slot in the default thread pool stays consumed — and `_run_git`, `add_git_safe_directory`, and many other helpers share that pool.

**Files:**
- Modify: `backend/app/services/community_detector.py` (top-level + the run-in-executor call)

- [ ] **Step 1: Add a module-level dedicated executor**

At the top of `backend/app/services/community_detector.py`, after the imports:

```python
from concurrent.futures import ThreadPoolExecutor

# Dedicated single-worker pool so a long-running Leiden invocation
# can't starve the default ThreadPoolExecutor used by git helpers and
# other run_in_executor callers. asyncio.wait_for can cancel the
# asyncio future on timeout, but Python has no portable way to stop
# the thread; isolating it keeps the rest of the app responsive.
_LEIDEN_EXECUTOR = ThreadPoolExecutor(max_workers=1, thread_name_prefix="leiden")
```

- [ ] **Step 2: Use it in the call**

Locate the `run_in_executor(None, ...)` call and replace `None` with `_LEIDEN_EXECUTOR`:

```python
        future = loop.run_in_executor(_LEIDEN_EXECUTOR, _run_leiden, ...)
        try:
            partition = await asyncio.wait_for(future, timeout=60.0)
        except asyncio.TimeoutError:
            ...
```

- [ ] **Step 3: AST parse**

```bash
python -c "import ast; ast.parse(open('backend/app/services/community_detector.py').read()); print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/community_detector.py
git commit -m "perf(graph): isolate Leiden in a dedicated single-worker pool

asyncio.wait_for cancels the Future on timeout but the underlying
thread keeps running until leidenalg finishes. While it's running
it occupies a slot in the default ThreadPoolExecutor that git
helpers and other run_in_executor callers share. Move Leiden to
its own one-thread pool so it can never starve the rest."
```

---

## Task 11: Btree index on `entity_relations.target_entity_id`

**Why:** Migration `0001_initial_schema.py` covers source-side queries via the unique constraint on `(source, target, rel_type)`. Target-only filters and cascade deletes from `entities` on the target side fall back to a sequential scan.

**Migration-edit caveat (applies to tasks 11, 12, 13):** `0001_initial_schema.py` is the squashed greenfield migration. Editing it in place is correct for fresh installs, but any existing dev DB at `head` won't see the change. Operators on existing DBs need to either drop+recreate the test DB (the plan's smoke-test step does this) OR run a one-off `psql` `CREATE INDEX` and `ALTER TABLE` to bring an existing schema in sync — not in scope for this plan, but worth documenting in the PR description.

**Files:**
- Modify: `backend/migrations/versions/0001_initial_schema.py` (after the `op.execute("CREATE INDEX ix_entity_relations_memory_ids ...")` line near line 243)

- [ ] **Step 1: Add the index**

After the existing `op.execute("CREATE INDEX ix_entity_relations_memory_ids ON entity_relations USING gin (memory_ids)")`, add:

```python
    op.create_index(
        "ix_entity_relations_target",
        "entity_relations",
        ["target_entity_id"],
    )
```

In the corresponding `downgrade()` function (search for `entity_relations`), add the matching drop before `op.drop_table('entity_relations')`:

```python
    op.drop_index("ix_entity_relations_target", table_name="entity_relations")
```

- [ ] **Step 2: AST parse**

```bash
python -c "import ast; ast.parse(open('backend/migrations/versions/0001_initial_schema.py').read()); print('OK')"
```

- [ ] **Step 3: Smoke-test on LXC by re-running the migration on a fresh DB**

```bash
# On LXC:
psql -c "DROP DATABASE darkmem_test; CREATE DATABASE darkmem_test;"
DATABASE_URL=postgresql+asyncpg://.../darkmem_test alembic upgrade head
psql darkmem_test -c "\\d entity_relations"
```

Expected: `ix_entity_relations_target` listed under indexes.

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/versions/0001_initial_schema.py
git commit -m "perf(db): index entity_relations.target_entity_id

The unique constraint on (source, target, rel_type) covers
source-side queries. Target-only filters and cascade deletes from
entities on the target side were sequential-scanning the table."
```

---

## Task 12: Btree index on `memories.superseded_by`

**Why:** The self-FK is declared with `ondelete='SET NULL'`. Without an index, every delete on `memories` triggers a sequential scan to null out FKs. `memories` is the central table.

**Files:**
- Modify: `backend/migrations/versions/0001_initial_schema.py`

- [ ] **Step 1: Add the partial index**

In the migration file, locate the block of `op.create_index` calls around the memories table (near line 380-384) and add:

```python
    op.execute(
        "CREATE INDEX ix_memories_superseded_by ON memories(superseded_by) "
        "WHERE superseded_by IS NOT NULL"
    )
```

In `downgrade`:

```python
    op.execute("DROP INDEX IF EXISTS ix_memories_superseded_by")
```

- [ ] **Step 2: AST parse + LXC smoke test**

Same as Task 11.

- [ ] **Step 3: Commit**

```bash
git add backend/migrations/versions/0001_initial_schema.py
git commit -m "perf(db): partial index on memories.superseded_by

Self-FK with ondelete=SET NULL was forcing a sequential scan of
the memories table on every delete. Partial index (WHERE
superseded_by IS NOT NULL) keeps the index small while covering
the cascade path."
```

---

## Task 13: Promote `audit_log.id` and `tags.id` to BigInteger

**Why:** Migration uses `sa.Integer()` (serial / int4, 2.1B ceiling). `audit_log` writes one row per memory operation and is realistic to exhaust over time. `code_graph_nodes` and `code_edges` already use `BigInteger`.

**Files:**
- Modify: `backend/migrations/versions/0001_initial_schema.py:67,77`
- Modify: `backend/app/models/audit.py`
- Modify: `backend/app/models/tag.py`

- [ ] **Step 1: Update migration columns**

Locate the `audit_log` CREATE TABLE and the `tags` CREATE TABLE in the migration. Replace:

```python
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
```

with:

```python
        sa.Column('id', sa.BigInteger(), autoincrement=True, nullable=False),
```

in both tables.

- [ ] **Step 2: Update ORM models to match**

Open `backend/app/models/audit.py`. Replace whatever the existing `id` column declaration is with:

```python
from sqlalchemy import BigInteger
...
    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
```

Same in `backend/app/models/tag.py`.

- [ ] **Step 3: AST parse + LXC migration smoke test**

```bash
python -c "import ast; [ast.parse(open(p).read()) for p in ('backend/app/models/audit.py', 'backend/app/models/tag.py', 'backend/migrations/versions/0001_initial_schema.py')]; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add backend/migrations/versions/0001_initial_schema.py backend/app/models/audit.py backend/app/models/tag.py
git commit -m "fix(db): bigserial for audit_log.id and tags.id

Integer (serial) caps at ~2.1B; audit_log writes one row per
memory operation and was a realistic ceiling. Promote to
BigInteger to match code_graph_nodes / code_edges."
```

---

## Task 14: Throttle `checkAuth` network call to once per N seconds

**Why:** `_authenticated.tsx:82-92` already short-circuits with a redirect when `isAuthenticated === false`. When the user IS authenticated, it then awaits `checkAuth()` (`GET /api/v1/auth/me`) on every navigation to detect server-side revocation. That's an explicit verification, not an oversight — but firing it on every sidebar click is excessive. Throttle to once per 60 seconds via a module-level timestamp; the user still gets prompt revocation detection (within a minute), and inter-navigation is silent.

**Files:**
- Modify: `frontend/src/routes/_authenticated.tsx`

- [ ] **Step 1: Add a throttled-verify wrapper**

Replace the current `beforeLoad` block (lines 81-92):

```tsx
export const Route = createFileRoute("/_authenticated")({
  beforeLoad: async () => {
    if (!useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: "/login" })
    }
    const { checkAuth } = await import("@/lib/api")
    const ok = await checkAuth()
    if (!ok) {
      useAuthStore.getState().logout()
      throw redirect({ to: "/login" })
    }
  },
  component: AuthenticatedLayout,
})
```

with:

```tsx
// Re-verify the session against the server at most once per minute.
// Without this throttle every sidebar click round-tripped /auth/me,
// adding latency to every navigation. A 60s window still catches a
// server-side token revocation quickly enough to feel correct.
const AUTH_VERIFY_TTL_MS = 60_000
let _lastAuthVerifyAt = 0

export const Route = createFileRoute("/_authenticated")({
  beforeLoad: async () => {
    if (!useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: "/login" })
    }
    const now = Date.now()
    if (now - _lastAuthVerifyAt < AUTH_VERIFY_TTL_MS) {
      return
    }
    const { checkAuth } = await import("@/lib/api")
    const ok = await checkAuth()
    if (!ok) {
      useAuthStore.getState().logout()
      throw redirect({ to: "/login" })
    }
    _lastAuthVerifyAt = now
  },
  component: AuthenticatedLayout,
})
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

Expected: no errors.

- [ ] **Step 3: Manually verify in browser**

Run dev server (`npm run dev` from `frontend/`), open DevTools Network tab, click between two authenticated routes (e.g., Memories → Jobs → Graph) within a minute. Confirm `GET /api/v1/auth/me` fires once at first load and not again until 60 seconds elapse. After 60 seconds, the next navigation should fire it once more.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/routes/_authenticated.tsx
git commit -m "perf(frontend): throttle /auth/me verify to once per 60s

beforeLoad re-ran checkAuth on every route transition, adding a
round-trip per sidebar click. Keep the verify (so revocations
land within ~1min) but throttle via a module-level timestamp."
```

---

## Task 15: Accept `\r\n\r\n` SSE delimiter in `useChatStream`

**Why:** `use-chat-stream.ts:75` splits on the literal string `"\n\n"`. SSE specifies the same, but Windows-flavoured backends or proxies that re-emit as `\r\n\r\n` would silently buffer events forever.

**Files:**
- Modify: `frontend/src/features/chat/hooks/use-chat-stream.ts:75`

- [ ] **Step 1: Replace the split**

Locate:

```ts
const events = buffer.split("\n\n")
```

Replace with:

```ts
const events = buffer.split(/\r?\n\r?\n/)
```

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/features/chat/hooks/use-chat-stream.ts
git commit -m "fix(chat): tolerate \\r\\n\\r\\n SSE separators

Splitting on the literal '\\n\\n' silently buffered events forever
when an upstream proxy normalised line endings. Use a regex that
accepts both LF and CRLF event boundaries."
```

---

## Task 16: Wrap `LLMPurposeCard.patch` in `useCallback`

**Why:** `patch` is recreated every render. The functional setter form means there's no correctness bug today, but passing the new reference into memoized children defeats their memo. Cheap to fix.

**Files:**
- Modify: `frontend/src/components/pipeline/LLMPurposeCard.tsx` (the `patch` declaration around line 362-371)

- [ ] **Step 1: Wrap in `useCallback`**

Locate:

```tsx
const patch = (next: Partial<typeof draft>) => {
  setDraft((d) => ({ ...d, ...next }))
}
```

Replace with:

```tsx
const patch = useCallback(
  (next: Partial<typeof draft>) => {
    setDraft((d) => ({ ...d, ...next }))
  },
  [],
)
```

Ensure `useCallback` is imported from `react` at the top of the file (extend the existing `import { useState, useEffect, ... } from "react"` if needed).

- [ ] **Step 2: Type-check**

```bash
cd frontend && npx tsc --noEmit
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/pipeline/LLMPurposeCard.tsx
git commit -m "perf(frontend): memoise LLMPurposeCard.patch reference

Recreating patch on every render defeated the memo on consumers
that take it as a prop. Wrap in useCallback with an empty dep
list — the functional setDraft form means draft doesn't need to
be a dep."
```

---

## Final verification

After all 16 tasks land:

- [ ] **Full backend pytest run on LXC**

```bash
ssh lxc-darkmem
cd /opt/darkmem/backend
python -m pytest tests/ -v
```

Expected: previous-baseline pass count plus the new tests from tasks 1 and 3.

- [ ] **Frontend type-check + build**

```bash
cd frontend
npx tsc --noEmit
npm run build
```

Expected: clean type-check; build succeeds.

- [ ] **Manual smoke checks on the dev server**

  - Memories page: delete a row and confirm the list refreshes immediately.
  - Settings → Assistant Prompts: simulate a save failure (e.g., disconnect backend), confirm dirty stays true.
  - Reindex page: trigger a per-row retry, confirm the button re-enables on success.
  - Analytics page: source pie reflects the full DB, not the first 50 rows.
  - Sidebar navigation: confirm `/auth/me` is NOT called on every click.

- [ ] **Push the branch and open a PR**

```bash
git push -u origin fix/codebase-review-2026-05-03
gh pr create --title "fix: 16 second-pass review fixes" --body-file <(cat <<'EOF'
## Summary
Sixteen verified fixes from the second-pass review of `fix/codebase-review-2026-05-03`. Three address regressions or holes in the first round of fixes; the rest are independent backend / frontend / DB issues. One commit per issue. See `docs/superpowers/plans/2026-05-03-second-pass-review-fixes.md` for the per-task breakdown.

## Test plan
- [ ] Backend `pytest tests/ -v` on the LXC
- [ ] Frontend `npx tsc --noEmit` + `npm run build`
- [ ] Manual smoke checks listed in the plan
EOF
)
```
