# darkmem Manual E2E Checklist

Runbook for a human tester to walk through the UI after the scripted E2E suite passes. Use in tandem with `test-plan.md`.

## Setup

1. Run `python scripts/run_all.py --password e2e-admin-pw` — confirm all phases pass.
2. Open the frontend in a browser: `http://host.docker.internal:3636` or `http://localhost:3636`.
3. Open DevTools: Console, Network, and Application → Cookies panels.

## 1. First-time setup and login

- [ ] On fresh DB, the root URL redirects to `/setup`
- [ ] Setup form has password input with min-length validation
- [ ] Submitting valid password redirects to `/` (Overview)
- [ ] Application storage has `darkmem_session` cookie with `HttpOnly` flag
- [ ] Logging out redirects to `/login`
- [ ] Login with wrong password shows inline error, no redirect
- [ ] Login with correct password redirects to `/`

## 2. Overview page (`/`)

- [ ] Stats cards show 0 for memories, tags, entities, relations on empty DB
- [ ] Pipeline health indicator shows Active + pgvector + LLM green dots
- [ ] Activity chart shows "No activity data yet" on empty DB
- [ ] Sources pie shows "No sources yet"
- [ ] Top tags shows "No tags yet"
- [ ] Recent memories shows "No memories yet" with create hint
- [ ] Toggling 7d/30d on the activity chart works

**After ingesting the fixture data:**
- [ ] Stats update to show real counts
- [ ] Activity bar chart renders with hover tooltips
- [ ] Sources pie renders with color legend
- [ ] Top tags horizontal bar chart renders
- [ ] Recent memories list renders and clicking a row navigates to `/memories`
- [ ] Responsive layout: resize to 768px — mobile layout kicks in; resize back — desktop layout returns

## 3. Memories page (`/memories`)

- [ ] List shows all ingested memories with content preview, tags, source, timestamp
- [ ] Search input performs semantic search as you type (debounced)
- [ ] Tag filter chips select/deselect and filter the list
- [ ] Create memory dialog opens, accepts content + tags + type, closes on save
- [ ] New memory appears at the top of the list after create
- [ ] Edit memory loads current content, saves updates
- [ ] Delete memory prompts for confirmation, removes from list
- [ ] Pagination or infinite scroll works if there are > 20 memories
- [ ] Empty search shows "no results" message

## 4. Chat page (`/chat`)

- [ ] Sidebar shows conversation list
- [ ] "New conversation" button creates a conversation and opens it
- [ ] Typing a message and pressing Enter submits
- [ ] Assistant response streams in character by character (if streaming is enabled)
- [ ] Messages are saved on refresh
- [ ] Renaming a conversation updates the sidebar title
- [ ] Deleting a conversation removes it and redirects to a different conversation or empty state

## 5. Graph page (`/graph`)

- [ ] Entity list loads with count badges
- [ ] Clicking an entity shows its neighbors in a panel
- [ ] Hovering a neighbor highlights the edge type
- [ ] Empty state when no entities exist

## 6. Unified graph (`/unified-graph`)

- [ ] Graph renders both memory and code nodes with different visual styles
- [ ] Pan and zoom controls work
- [ ] Clicking a node opens a detail panel
- [ ] Filter controls (node type, edge type) update the rendering

## 7. Code graph (`/code-graph`)

- [ ] Repo selector populated with indexed repos (empty if no repos)
- [ ] Selecting a repo renders its call graph
- [ ] Empty state shows "no repos indexed yet" with a link to `/repos`

## 8. Code wiki (`/code-wiki`)

- [ ] Repo selector as above
- [ ] Wiki content renders (if generated for the repo)
- [ ] Table of contents sidebar navigates to sections

## 9. Repos page (`/repos`)

- [ ] List shows indexed repos with status badge (ready / cloning / indexing / error)
- [ ] "Add repo" dialog opens, accepts local path or URL
- [ ] After submitting, the repo appears in the list with "cloning" status
- [ ] WebSocket progress updates the status without a manual refresh
- [ ] Reindex button triggers a re-run
- [ ] Delete button asks confirmation then removes the repo
- [ ] Repo detail shows file/symbol counts and recent tasks

## 10. Vectors page (`/vectors`)

- [ ] Vector space visualization renders
- [ ] Hover shows the memory content for each point
- [ ] Filter controls work
- [ ] Empty state when no embeddings exist

## 11. Analytics page (`/analytics`)

- [ ] All charts render without errors
- [ ] Time range toggle works
- [ ] Data matches the Overview page

## 12. Pipeline page (`/pipeline`)

- [ ] Action row has "Retry Failed" and "Reprocess All" buttons
- [ ] **Obsolete Embeddings card** — should be hidden when counts are zero
- [ ] After changing the embedding model, the card appears with per-category counts
- [ ] Per-row Re-embed button triggers the background task; progress bar shows during run
- [ ] "Re-embed all obsolete" button runs all three categories sequentially under one progress view
- [ ] "Prune old cache entries" button returns a toast with deleted count
- [ ] **Unresolved Failures card** — hidden when no failures
- [ ] Filter tabs (All / Memory / Code) show counts
- [ ] Per-row Retry button spins, then the row either animates out (resolved) or updates (still failing)
- [ ] Per-row Forget button removes the row immediately
- [ ] Stats cards at the bottom show Pipeline, pgvector, LLM health
- [ ] Recent Pipeline Executions table shows per-memory status with embed/extract/vector/graph badges
- [ ] Error rows have a red border accent

## 13. LLM config page (`/llm`)

- [ ] Five purpose cards render (Embedding, Extraction, Reasoning, Summarization, Reranker)
- [ ] Each card shows provider, model, base URL, dimensions, api_key masked as `***`
- [ ] Edit button opens inline form
- [ ] Saving with `***` in api_key preserves the existing key
- [ ] Saving a new embedding model triggers the "Embedding Model Changed" modal
- [ ] Modal shows per-category obsolete counts (memories, entities, code chunks)
- [ ] "Later" closes the modal
- [ ] "Re-embed now" triggers `/reembed/all` and navigates to `/pipeline`

## 14. Settings page (`/settings`)

- [ ] Enrichment worker card: enable/disable toggle, batch size input, interval input, "Run Now" button
- [ ] Feature flags card: all toggles reflect current state and persist on change
- [ ] Classification card:
  - [ ] Mode toggle (Simple / Expanded) works
  - [ ] Simple mode shows the 7 universal types with descriptions
  - [ ] Expanded mode shows the area switches with dividers
  - [ ] Toggling an area persists across refresh
- [ ] Embedding pipeline controls: batch size, concurrency, cache TTL

## 15. Design and UX

- [ ] Keyboard focus is visible (outline) on all interactive elements
- [ ] Tab order through forms is logical
- [ ] Escape closes open dialogs
- [ ] Click-outside closes dropdowns and modals
- [ ] Dark mode: no unreadable text, consistent colors
- [ ] Long memory content truncates with ellipsis, full text on hover or click
- [ ] Icon-only buttons have aria-labels (inspect via DevTools)
- [ ] Toasts auto-dismiss after ~4 seconds
- [ ] Loading states: spinners or skeletons, no layout jumps
- [ ] Error toasts show specific error text, not just "Error"
- [ ] Destructive buttons (Delete, Forget) use destructive variant styling
- [ ] Form inputs have visible labels (no placeholder-only labels)
- [ ] Buttons disable while mutations are in flight (no double-submits)

## 16. Performance sanity

In the DevTools Network tab, verify:

- [ ] Initial page load < 2 s
- [ ] Search queries return < 500 ms
- [ ] WebSocket connection established within 500 ms of page load
- [ ] No obvious N+1 HTTP requests (e.g., one request per memory in a list)
- [ ] Bundle size (main chunk) < 1 MB gzipped
- [ ] No requests to external CDNs (everything self-hosted)

In the DevTools Performance tab, verify:

- [ ] No layout thrashing on scroll
- [ ] Chart animations are smooth (60fps target)
- [ ] Memory usage does not grow unbounded over 5 minutes of normal use

## 17. Console and Network errors

Over a full walkthrough, the browser Console should have:

- [ ] No red errors
- [ ] No 401 / 403 / 500 responses in Network tab
- [ ] No CORS warnings
- [ ] No "key prop" warnings from React
- [ ] No "unknown event type" WebSocket warnings

## Post-run report

After completing the checklist, note:

- Any failing checkboxes
- Any unexpected behavior not covered by a checkbox
- Perf numbers that seem off
- Design inconsistencies between pages

File issues or update `test-plan.md` with new phases as needed.
