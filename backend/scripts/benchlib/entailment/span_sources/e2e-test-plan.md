# darkmem E2E Test Plan

**Execution model:** This plan is a runbook for **Claude Code (me)** to execute via the Playwright MCP tools. Each phase is a user journey with explicit browser steps, expected states, and verification points. Supporting Python scripts in `scripts/` handle API-level checks that are awkward through the browser (bulk ingest, DB audit, performance timing).

**When the user says "run phase N" or "run the full E2E plan":**
1. Verify Playwright MCP is connected (`browser_navigate` etc. available).
2. Follow the phase's steps in order, using Playwright tools for UI interaction and Bash for supporting scripts.
3. Capture a `browser_snapshot` at each verification point and compare against the expected state.
4. Write observations into the phase's **Execution log** section (in this doc or a sibling file under `docs/e2e/runs/`).
5. Stop and report any FAIL or unexpected state before moving on — do not batch failures silently.

**Prerequisites:**
- Fresh darkmem deployment: backend on `http://localhost:8000`, frontend on `http://host.docker.internal:3636`, admin password NOT set.
- Ollama running with the configured embedding model and chat model.
- Playwright MCP browser process available via `mcp__playwright__browser_*` tools.
- Python 3.12+ with `httpx` in PATH for supporting scripts.

**Fresh state check** (always run first):
- `curl http://localhost:8000/api/v1/auth/status` → `{"initialized": false}`
- `curl http://localhost:8000/api/v1/analytics/stats` → zeros (or 401, needs auth)

---

## How Claude executes this plan

### Standard playwright tools I use

| Tool | Purpose |
|---|---|
| `mcp__playwright__browser_navigate(url)` | Go to a URL |
| `mcp__playwright__browser_snapshot()` | Get accessibility tree of the current page (preferred over screenshots for data extraction) |
| `mcp__playwright__browser_take_screenshot()` | Visual screenshot for design/UX verification |
| `mcp__playwright__browser_click(element, ref)` | Click a button, link, or other element |
| `mcp__playwright__browser_type(element, ref, text)` | Type into an input |
| `mcp__playwright__browser_fill_form(fields)` | Fill multiple form fields at once |
| `mcp__playwright__browser_press_key(key)` | Send Enter, Escape, Tab, etc. |
| `mcp__playwright__browser_wait_for(text)` | Wait for text to appear/disappear |
| `mcp__playwright__browser_console_messages()` | Pull console errors/warnings |
| `mcp__playwright__browser_network_requests()` | Inspect recent HTTP calls |
| `mcp__playwright__browser_resize(w, h)` | Test responsive layouts |
| `mcp__playwright__browser_close()` | **Always** call when finished — shared instance |

### Standard flow for each step

1. Perform the action (navigate / click / type).
2. Call `browser_snapshot()` and check the expected element/text is present.
3. If a mutation was triggered, wait for the spinner/toast then re-snapshot.
4. If an assertion fails, call `browser_console_messages()` and `browser_network_requests()` to capture context before logging the failure.
5. Move to the next step.

### Supporting scripts

For operations that are slow/awkward through the UI (bulk ingest, DB queries, performance timing), run the corresponding script via Bash:

```bash
cd docs/e2e/scripts
python 00_health_check.py
python 04_memories_batch_mcp.py --password "e2e-admin-pw"
python 12_perf_baseline.py --password "e2e-admin-pw"
python 13_db_audit.py
```

Scripts print PASS/FAIL lines I can read from the output. Log their results in the phase's Execution log.

### Execution log template

After each phase, append an entry to `docs/e2e/runs/YYYY-MM-DD-run.md` (create if missing):

```markdown
## Phase N — <name>  [PASS | FAIL | PARTIAL]

**Start:** HH:MM:SS
**Finish:** HH:MM:SS
**Observations:**
- <anything notable>

**Issues found:**
- [category] <description> — [file/component ref if applicable]
```

Categories: `bug`, `design-gap`, `ux`, `performance`, `security`, `accessibility`, `content`.

### When to stop and ask the user

Stop and report to the user (do not silently continue) when:
- A phase produces a **security** or **bug** category issue
- An expected UI element is completely missing (not just styled differently)
- A supporting script fails with a non-zero exit code
- Playwright MCP becomes disconnected or a browser page crashes
- The backend returns 5xx repeatedly

---

## Phase 0 — Preflight

**Goal:** Confirm the stack is live and in fresh state before touching anything.

### Steps

1. **Bash:** `python docs/e2e/scripts/00_health_check.py`
   - Expected: all 5 checks PASS (pgvector, llm, pipeline, auth/status, frontend reachable)
2. **Playwright:** `browser_navigate("http://host.docker.internal:3636")`
   - Expected: page loads, no console errors
3. **Playwright:** `browser_snapshot()`
   - Expected: redirected to `/setup` (fresh state) or `/login` (already initialized)
4. **Playwright:** `browser_console_messages()`
   - Expected: no red errors

### Pass criteria
- Script exits 0
- Browser reaches setup/login page
- No uncaught exceptions in console

---

## Phase 1 — First-time setup flow

**Goal:** Walk through the setup wizard, create the admin password, verify the cookie is set, reach the Overview page.

### Steps

1. `browser_navigate("http://host.docker.internal:3636/setup")`
2. `browser_snapshot()` — note the structure of the setup form
3. `browser_take_screenshot()` — capture baseline design
4. **Weak password test:** type `"short"` into the password field, click Submit
   - Expected: inline error about min-length, no redirect
5. **Valid password test:** clear, type `"e2e-admin-pw"`, click Submit
   - Expected: redirect to `/`, cookie `darkmem_session` is set (verify via `browser_network_requests()` on the Set-Cookie header)
6. `browser_snapshot()` on `/` — Overview page renders with zero-state stats

### Verification points
- Setup form rejects short passwords
- Cookie has `HttpOnly` and `SameSite=strict`
- Overview page renders without errors
- Pipeline health indicator shows Active

### Observations to capture
- Design: is the setup page visually consistent with the rest of the app?
- UX: is the password rule communicated before submit or only on error?
- A11y: are input labels associated? Focus visible?

---

## Phase 2 — Login, logout, and auth hardening

**Goal:** Validate login/logout flows plus the hardening decisions from the earlier auth audit.

### Steps

1. **Bash:** `python docs/e2e/scripts/01_auth_flow.py --password "e2e-admin-pw"`
   - This runs the full auth matrix: setup (skips if already done), login wrong/correct, /me with/without cookie, refresh, change-password, logout, revocation.
   - Expected: exits 0 with all green PASS lines
2. **Playwright logout flow:**
   - Open the user menu (likely top-right) → click Logout
   - Expected: redirect to `/login`
   - `browser_snapshot()` → login form visible
3. **Login with wrong password:**
   - Type `"wrong-password"` → Submit
   - Expected: inline error, still on `/login`
4. **Login with correct password:**
   - Type `"e2e-admin-pw"` → Submit
   - Expected: redirect to `/`, Overview renders
5. **Refresh the browser page** (`browser_navigate(current_url)`)
   - Expected: still authenticated (cookie survives reload)

### Verification points
- Wrong password shows an error (not a crash)
- Error text does not leak whether the account exists (single-admin, so less relevant but still check for generic wording)
- Cookie attributes from the Network tab: `HttpOnly`, `SameSite=Strict`, `Secure` only in production
- Browser refresh preserves session

### Known intentional gaps (not failures)
- No rate limiting on login — single-admin tool
- MCP endpoint at `/mcp` is unauthenticated — local-network-only

---

## Phase 3 — Overview page structure

**Goal:** Verify the Overview (`/`) page renders correctly on a fresh database and populates when data exists.

### Steps (empty state)

1. `browser_navigate("http://host.docker.internal:3636/")`
2. `browser_snapshot()` — capture all text and structure
3. Verify the following text or labels are present:
   - "Memories" card with value 0 or "—"
   - "Tags" card with value 0 or "—"
   - "Entities" card with value 0 or "—"
   - "Relations" card with value 0 or "—"
   - Pipeline health: Active + pgvector + LLM green dots
   - "No activity data yet" or similar
   - "No sources yet"
   - "No tags yet"
   - "No memories yet"
4. Toggle the `7d` / `30d` buttons
   - Expected: chart container updates (no errors)
5. `browser_resize(768, 1024)` — tablet width
6. `browser_snapshot()` — mobile layout kicks in
7. `browser_resize(375, 812)` — mobile width
8. `browser_snapshot()` — grid collapses to single column
9. `browser_resize(1280, 800)` — back to desktop

### Steps (populated state — after Phase 4)
After Phase 4 ingests fixture memories:

10. `browser_navigate("http://host.docker.internal:3636/")`
11. `browser_snapshot()`
12. Verify:
    - Memory count matches fixture count (20+)
    - Tags count is non-zero
    - Activity chart has bars
    - Sources pie renders (e2e-fixtures segment)
    - Top tags horizontal bar chart renders
    - Recent Memories list shows real content, not placeholders

### Observations to capture
- Chart colors readable in dark theme
- Tooltips appear on hover
- Recent memory rows clickable (navigates to `/memories`)
- Layout switches cleanly at breakpoints (no flicker/jump)

---

## Phase 4 — Memory ingestion (MCP batch + UI CRUD)

**Goal:** Ingest fixture data via MCP, then verify UI CRUD operations on individual memories.

### Bulk ingest via MCP

1. **Bash:** `python docs/e2e/scripts/04_memories_batch_mcp.py --password "e2e-admin-pw"`
   - Expected: 20 memories ingested, stats confirm, obsolete counts near zero
2. **Bash:** `python docs/e2e/scripts/00_health_check.py` — re-verify health after load

### UI verification

3. `browser_navigate("http://host.docker.internal:3636/memories")`
4. `browser_snapshot()`
5. Verify: list shows ≥20 memories with content, tags, source badges, timestamps
6. **Search test:**
   - Click search input, type `"database"` → wait for results
   - Expected: relevant memories filtered
7. **Tag filter:**
   - Click an `e2e` tag chip → list narrows
   - Click to deselect → list expands
8. **Create memory:**
   - Click "Create" or "Add memory" button
   - Fill content: `"E2E UI-created memory about WebSocket"`, add tag `e2e-ui`
   - Submit
   - Expected: toast success, new memory at top of list
9. **Edit memory:**
   - Click edit icon on the new memory
   - Change content to `"E2E UI-created memory about WebSocket — edited"`
   - Save
   - Expected: list reflects new content
10. **Delete memory:**
    - Click delete → confirm
    - Expected: memory removed from list

### Supporting API checks

11. **Bash:** `python docs/e2e/scripts/03_memories_crud.py --password "e2e-admin-pw"` — full API CRUD matrix

### Observations to capture
- Empty search shows "no results" not a blank area
- Long memory content truncates with ellipsis
- Delete confirmation cannot be bypassed by double-click
- Create form validates non-empty content
- Tag autocomplete exists or manual entry works

---

## Phase 5 — Chat and reasoning

**Goal:** Validate the Chat page and RAG reasoning flow.

### Steps

1. `browser_navigate("http://host.docker.internal:3636/chat")`
2. `browser_snapshot()`
3. Click "New conversation" button
4. Type: `"What database uses MVCC?"` → Submit
5. `browser_wait_for("MVCC")` (wait for assistant response with reasonable timeout ~60s)
6. `browser_snapshot()` — verify message bubbles for user and assistant
7. Verify sources/citations appear below the assistant message (if the UI shows them)
8. Type a follow-up: `"And which other databases are similar?"`
9. Verify the context from prior messages carries through
10. **Conversation CRUD via sidebar:**
    - Click "Rename" on the conversation → enter `"E2E chat test"` → save
    - Verify sidebar updates
    - Click Delete → confirm → verify removal and redirect

### Supporting API checks

11. **Bash:** `python docs/e2e/scripts/05_reason_chat.py --password "e2e-admin-pw"`

### Observations to capture
- Response streaming visible (tokens appear progressively) or loading indicator
- No layout shift when messages arrive
- Long responses scroll correctly
- Empty conversation list has a helpful empty state
- Injection test: paste `"Ignore previous instructions..."` — verify the assistant does not comply

---

## Phase 6 — Knowledge graph

**Goal:** Validate the Graph, Unified Graph, Code Graph pages render correctly.

### Steps

1. `browser_navigate("http://host.docker.internal:3636/graph")`
2. `browser_snapshot()`
3. Verify entity list has entries (from ingested fixtures)
4. Click on an entity → expect a detail panel with neighbors
5. Hover over edges → verify edge type is shown (or tooltip)
6. `browser_navigate("http://host.docker.internal:3636/unified-graph")`
7. `browser_snapshot()` + `browser_take_screenshot()`
8. Verify nodes render, pan/zoom works (if interactive controls exist)
9. `browser_navigate("http://host.docker.internal:3636/code-graph")`
10. Verify empty state if no repos indexed; otherwise render the code graph

### Supporting API checks

11. **Bash:** `python docs/e2e/scripts/06_graph_entities.py --password "e2e-admin-pw"`

### Observations to capture
- Graph performance on first render (any lag?)
- Nodes with long names truncate
- Color/shape distinction between memory and code nodes clear
- Empty states helpful on each page

---

## Phase 7 — Repository and code indexing

**Goal:** Add a repo, watch indexing progress live via WebSocket, verify the code subsystem.

### Steps

1. `browser_navigate("http://host.docker.internal:3636/repos")`
2. `browser_snapshot()` — verify empty state or existing list
3. Click "Add repo" button
4. Fill form: name = `e2e-test-repo`, local_path = `/workspace/darkmem/backend` (or equivalent path reachable from the container)
5. Submit
6. Verify the new repo appears with "cloning" or "indexing" status
7. **Watch progress:** periodically `browser_snapshot()` every 5–10 seconds until status = "ready" or "error"
8. Alternatively monitor the Pipeline page (`/pipeline`) for `repo.indexing_progress` events — open a second tab or switch and back
9. Once ready, click the repo to view detail
10. Verify file count and symbol count are non-zero
11. `browser_navigate("http://host.docker.internal:3636/code-graph")`
12. Select the repo → verify graph renders
13. `browser_navigate("http://host.docker.internal:3636/code-wiki")` → verify wiki content if generated
14. **Delete cleanup:** return to `/repos`, delete the test repo, confirm

### Supporting API checks

15. **Bash:** `python docs/e2e/scripts/07_code_repos.py --password "e2e-admin-pw"`

### Observations to capture
- Progress updates are live (via WebSocket) not manual refresh
- Long-running indexing does not block the UI
- Error state (if indexing fails) is clearly communicated
- Repo detail page includes status, file count, recent tasks

---

## Phase 8 — Analytics and reprocessing

**Goal:** Validate the Analytics page and reprocess flow.

### Steps

1. `browser_navigate("http://host.docker.internal:3636/analytics")`
2. `browser_snapshot()`
3. Verify all charts render with real data (post-ingestion)
4. Toggle time range controls
5. **Reprocess test:**
   - Navigate to `/pipeline`
   - Click "Reprocess All"
   - Verify SSE progress bar appears and updates
   - Wait for completion
   - Verify no errors in recent pipeline logs

### Supporting API checks

6. **Bash:** `python docs/e2e/scripts/08_analytics_reprocess.py --password "e2e-admin-pw"`
   - This also verifies the legacy `/reprocess-failed` endpoint is removed (Feature 2)

### Observations to capture
- Reprocess progress bar accurate (reaches 100%)
- Stats update live or on refresh
- Recent errors count (if any) is accurate

---

## Phase 9 — Pipeline failure tracking (Feature 2)

**Goal:** Induce a pipeline failure, verify the Unresolved Failures card appears, test retry/forget actions.

### Steps

1. **Bash:** `python docs/e2e/scripts/09_pipeline_failures.py --password "e2e-admin-pw"`
   - On a healthy system this returns 0 failures. To induce one, temporarily break the LLM connection.
2. **Induce failure:**
   - `browser_navigate("http://host.docker.internal:3636/llm")`
   - Edit the Embedding card, change `base_url` to `http://invalid-host:99999`, save
   - Navigate to `/memories`, create a new memory
   - Verify a pipeline failure appears within ~30 seconds
3. **Restore LLM:**
   - Return to `/llm`, restore the original `base_url`, save
4. **Pipeline page:**
   - `browser_navigate("http://host.docker.internal:3636/pipeline")`
   - `browser_snapshot()`
   - Verify "Unresolved Failures" card is visible with count ≥1
   - Click filter tabs: All / Memory / Code
5. **Per-row retry:**
   - Click Retry on a failure row
   - Verify spinner appears
   - Wait for resolution via WebSocket event
   - Row should animate out
6. **Forget:**
   - If failures remain, click Forget on one → verify immediate removal
7. **Bulk retry:**
   - Click "Retry all failed"
   - Verify progress bar appears (via `pipeline.retry_batch.progress` WebSocket events)

### Observations to capture
- Failure recorded correctly with accurate `failed_step`
- WebSocket updates are live (no manual refresh)
- Forget vs Retry labels are clear
- Progress bar updates smoothly
- Cards hide when counts drop to zero

---

## Phase 10 — Model change and obsolete re-embedding (Feature 3)

**Goal:** Change the embedding model, verify the obsolete modal appears, run the re-embed flow, verify progress.

### Steps

1. **Pre-change counts:** `browser_navigate("http://host.docker.internal:3636/pipeline")` → verify "Obsolete Embeddings" card is hidden (zero counts)
2. **Change model:**
   - `browser_navigate("http://host.docker.internal:3636/llm")`
   - Edit the Embedding card
   - Change `model` to a different value (e.g., append `-e2e-test` to the existing name)
   - Save
3. **Verify modal:**
   - `browser_snapshot()` — "Embedding Model Changed" dialog should be visible
   - Verify counts match actual obsolete rows (memories, entities, code_chunks)
4. **Click "Later":**
   - Dialog closes
   - Navigate to `/pipeline`
   - Obsolete Embeddings card should now be visible with the same counts
5. **Re-open by re-navigating to `/llm` and saving the same model again** (modal reappears)
6. **Click "Re-embed now":**
   - Redirects to `/pipeline`
   - Progress bars appear for each category
   - Wait for completion (WebSocket events drive the UI)
7. **Verify completion:**
   - All category counts drop to 0
   - Card hides
   - No errors in recent pipeline logs
8. **Prune cache:**
   - On `/pipeline`, if the card is visible click "Prune old cache entries"
   - Toast confirms deletion count
9. **Revert model:**
   - Return to `/llm`, revert the model name
   - Verify new obsolete rows appear (the reverted fingerprint is now different from the just-re-embedded rows)
   - Click "Re-embed now" again to restore to the original fingerprint

### Supporting API checks

10. **Bash:** `python docs/e2e/scripts/10_reembed_flow.py --password "e2e-admin-pw"`

### Observations to capture
- Modal content is clear about what will happen
- Progress bars update smoothly (once per chunk)
- Per-category re-embed button disables when a batch is running
- Mid-batch concurrent model change is blocked by UI guard (attempt saving while re-embed is running → button should be disabled)

---

## Phase 11 — WebSocket event surface

**Goal:** Capture all WebSocket events that fire during a typical session. Useful for catching schema drift or missing event types.

### Steps

1. **Bash (background):** Start `python docs/e2e/scripts/11_websocket_listener.py --password "e2e-admin-pw" --duration 120 &`
2. Trigger the key operations:
   - Create a memory via UI (`pipeline.completed` should fire)
   - Delete a memory (`memory.deleted`)
   - Add/remove a repo (`repo.clone_*`, `repo.indexing_*`)
   - Induce and retry a failure (`pipeline.failure.updated`, `pipeline.retry_batch.progress`)
   - Change LLM model and re-embed (`pipeline.reembed_batch.progress`)
3. Wait for the listener to finish (it exits after `--duration`)
4. Review the event count table

### Expected events (should see most/all during the session)
- `pipeline.completed`, `pipeline.partial`, `pipeline.failed`
- `pipeline.failure.updated`
- `pipeline.retry_batch.progress`
- `pipeline.reembed_batch.progress`
- `memory.deleted`
- `repo.clone_started`, `repo.clone_completed`
- `repo.indexing_started`, `repo.indexing_progress`, `repo.indexing_completed`

### Observations to capture
- No "unknown event type" warnings from the listener
- All event payloads validate (the listener prints schema errors if any)

---

## Phase 12 — Performance baseline

**Goal:** Measure latency for critical operations. Not a hard gate — warns on slow ops.

### Steps

1. **Bash:** `python docs/e2e/scripts/12_perf_baseline.py --password "e2e-admin-pw"`
2. Review the output — operations under baseline are PASS, under 3× baseline are WARN, over 3× are FAIL
3. **Playwright perf:**
   - `browser_navigate("http://host.docker.internal:3636/")`
   - `browser_network_requests()` — note initial page load size, request count
   - Navigate between pages: `/memories`, `/chat`, `/pipeline`, `/llm`, `/settings`
   - Watch for repeated fetches of the same data or slow endpoints

### Targets (soft)
- Initial page load < 2 s
- Route transitions < 500 ms
- `POST /memories/search` < 500 ms
- `GET /analytics/overview` < 300 ms
- WebSocket connect < 500 ms

### Observations to capture
- Any obvious N+1 HTTP patterns (e.g., one request per list row)
- Bundle sizes
- Requests to external CDNs (should be none)

---

## Phase 13 — DB-level audit

**Goal:** Direct SQL assertions that can only be verified at the database level.

### Steps

1. **Bash:** `python docs/e2e/scripts/13_db_audit.py`
   - Requires `DARKMEM_BACKEND_DIR` env var pointing to the backend folder
   - Or run from inside the backend container

### Checks performed
- `memory_embeddings` all have `model_fingerprint` set
- `entities` with embeddings all have `model_fingerprint` set
- No duplicate `(name, entity_type)` rows
- `memory_embeddings` is one-to-one with `memories`
- No orphaned `pipeline_failures` rows
- `entity_embedding_cache` primary key constraint holds
- `token_blocklist` and `audit_log` have entries

---

## Phase 14 — UI design, UX, and accessibility sweep

**Goal:** Catch design gaps, UX violations, accessibility issues, and responsive/dark-mode problems.

For each of the 14 authenticated routes and the 2 guest routes, run the following checklist. Record issues in the execution log.

### Routes

| Route | Purpose |
|---|---|
| `/setup` | First-time password setup |
| `/login` | Login form |
| `/` | Overview dashboard |
| `/memories` | Memory list and CRUD |
| `/chat` | Conversations and RAG chat |
| `/graph` | Entity graph |
| `/unified-graph` | Memory + code unified graph |
| `/code-graph` | Code-only call graph |
| `/code-wiki` | Auto-generated code wiki |
| `/repos` | Repo list and management |
| `/vectors` | Vector space visualization |
| `/analytics` | Analytics charts |
| `/pipeline` | Pipeline health, failures, re-embed |
| `/llm` | LLM config per purpose |
| `/settings` | Feature flags, classification, enrichment |

### Per-route checklist (fill in for each)

1. `browser_navigate(route)` and `browser_snapshot()`
2. **Empty state:** Does it show a helpful message when there's no data?
3. **Loading state:** Spinner or skeleton during data fetch? No layout jump?
4. **Error state:** Inline error on failed fetch (simulate by temporarily breaking the backend)?
5. **Keyboard focus:** Tab through interactive elements — is focus ring visible and order logical?
6. **Escape key:** Closes any open modal/dropdown
7. **Enter key:** Submits the active form
8. **Responsive:** `browser_resize(375, 812)` — does the layout survive on mobile?
9. **Dark mode:** Any unreadable text? Buttons with bad contrast?
10. **Icon-only buttons:** Do they have aria-labels? Hover tooltips?
11. **Destructive actions:** Delete/Forget/Reset confirmations?
12. **Toast placement:** Corner, auto-dismiss, stackable?
13. **Console:** Any red errors? React key warnings?
14. `browser_take_screenshot()` — save for later comparison

### Common design-gap patterns to watch for

- Inconsistent button sizes across pages
- Hard-coded colors instead of theme tokens
- Missing `disabled` state during mutations
- Double-submit produces duplicate rows
- Long content overflows without truncation
- Tooltips hidden behind other elements
- Progress bars reaching 100% before operation completes
- Form inputs without autocomplete hints
- Missing loading state during route transitions
- Page headers inconsistent (some use `PageHeader`, some don't)

### Accessibility deep-dive (if time permits)

- Run axe-core via `browser_evaluate()` with the axe bundle
- Tab through forms, verify labels announced correctly
- Test with a screen reader if available

---

## Phase 15 — Settings and feature flags

**Goal:** Verify all toggles in the Settings page persist and take effect.

### Steps

1. `browser_navigate("http://host.docker.internal:3636/settings")`
2. `browser_snapshot()` — inventory all settings cards
3. **Feature flags:**
   - Toggle `llm_enrichment_enabled` off → save → refresh → verify it stayed off
   - Toggle it back on
   - Same for `hybrid_search_enabled`, `reranker_enabled`
4. **Pipeline concurrency:**
   - Change to 3, save, refresh, verify
5. **Classification mode:**
   - Switch Simple ↔ Expanded → verify the card body changes
   - In Expanded mode, toggle a specific area on/off
6. **Enrichment worker:**
   - Enable → verify worker shows as running
   - Click "Run Now" → verify toast with count
   - Disable
7. **Embedding pipeline:**
   - Change batch size to 10 → save → verify
   - Change concurrency to 2 → save → verify
   - Change TTL to 30 → save → verify
   - Reset to defaults

### Supporting API checks

8. **Bash:** `python docs/e2e/scripts/02_config_flow.py --password "e2e-admin-pw"`

### Observations to capture
- All toggles persist across page reload
- Invalid values rejected with clear error
- Save button disables during mutation
- Visual feedback on successful save (toast)

---

## Phase 16 — Cleanup and teardown

**Goal:** Leave the system in a known state after the run.

### Steps

1. **Clean ingested fixture memories:**
   - Via API: `curl -b "darkmem_session=<token>" -X POST http://localhost:8000/api/v1/memories/search -H "Content-Type: application/json" -d '{"tags_any": ["e2e", "e2e-fixtures", "e2e-ui"]}'`
   - For each returned memory id: `curl -X DELETE -b "darkmem_session=<token>" http://localhost:8000/api/v1/memories/{id}`
2. **Delete test repos:** via `/repos` UI or API
3. **Prune obsolete cache entries:** `POST /api/v1/reembed/prune-cache`
4. **Verify zero state:**
   - `GET /analytics/stats` → low counts
   - `GET /pipeline-failures/counts` → zeros
   - `GET /reembed/obsolete-counts` → zeros
5. **`browser_close()`** to release the Playwright browser instance
6. **Write final execution log** — summarize the run in `docs/e2e/runs/YYYY-MM-DD-run.md`

---

## Known intentional gaps (document, don't fail)

From the three architectural features already shipped:

1. **MCP endpoint is unauthenticated** — local-network-only trust model
2. **No rate limiting on login** — single-admin tool
3. **No re-embed cancellation** — batches run to completion
4. **Concurrent LLM config change during re-embed** has a minor race — UI-level guard only
5. **`count_obsolete` on huge tables** — no index on `model_fingerprint` yet
6. **Bulk retry runs one INSERT per memory** — acceptable for typical batch sizes

When the plan uncovers these, mark as `[known]` in the log, don't fail the phase.

---

## Out of scope

- Multi-user scenarios (single-admin by design)
- Production-scale load testing
- Chaos / fault injection
- Cross-browser beyond Playwright's default Chromium
- Penetration testing beyond OWASP basics
- i18n and localization
- Mobile-native (desktop web is the target)

---

## Running the plan

### Full run (I execute)

When the user says **"run the e2e plan"** or **"execute phase N"**:

1. Read this document to the relevant phase.
2. For each step: perform the action, snapshot, verify, log.
3. At each verification point, compare against the expected state and capture observations.
4. After each phase, write the Execution log entry.
5. After all phases, produce a final summary: pass/fail per phase, issue inventory, recommendations.

### Manual run (user executes)

Scripts in `scripts/` can be run independently:

```bash
cd docs/e2e/scripts
source env.sh
python run_all.py --password "e2e-admin-pw"
```

UI phases still need Playwright or a human walkthrough per `checklist.md` (short runbook).

---

## Extending the plan

When a new feature lands:

1. Add a new phase in this document
2. If it has a UI component, add steps to Phase 14 (design sweep) too
3. If it has a distinct workflow, create a dedicated phase
4. Add a corresponding script in `scripts/` for API-level verification
5. Update `README.md` and `checklist.md` if UI-visible
