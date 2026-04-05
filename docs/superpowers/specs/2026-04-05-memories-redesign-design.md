# Memories Page Redesign

## Goal

Replace the current plain Memories page and absorb the separate Search page into a single polished memories browser with semantic search, filters, pagination, bulk actions, and a detail side panel.

## Scope

- Rewrite the Memories page with hybrid two-line rows, inline search, filters, pagination, bulk actions, and a side panel
- Remove the separate Search page and its sidebar link (Chat already handles the Reason/Q&A use case)
- Add a paginated search endpoint to the backend
- No manual memory creation — the web portal is for browsing and managing, not authoring

## Data & API

### New endpoint: `POST /memories/search/paginated`

Adds offset-based pagination without changing the existing `/memories/search` endpoint (which returns a plain array and is used by Analytics, MCP, and other consumers).

Request body:

```json
{
  "query": "docker compose",
  "tags_any": ["infra"],
  "source": "claude-code",
  "memory_type": "preference",
  "limit": 50,
  "offset": 0
}
```

Response:

```json
{
  "items": [ ...Memory objects ],
  "total": 847,
  "limit": 50,
  "offset": 0
}
```

The `source` and `memory_type` fields are new filter parameters added to the backend search logic. `query`, `tags_any`, and `limit` already exist. `offset` is new.

### Existing endpoints reused

- `DELETE /memories/:id` — delete a single memory
- `GET /tags` — populate the Tags filter dropdown
- `GET /health` — not used on this page

### Frontend hooks

- New `usePaginatedSearch(params)` hook — calls the paginated endpoint, keyed by all search/filter/pagination params
- Existing `useTags()` — for tag filter dropdown
- Existing `useDeleteMemory()` — for row and bulk delete

## Page Structure

### Header bar

"Memories" title on the left, total count badge on the right ("847 memories"). No create button — memories come from automated sources only.

### Search + filter bar

A single row below the header:

- **Search input** — takes most of the width. Pressing Enter triggers a semantic search via the paginated endpoint with `query` set. Clearing the input resets to unfiltered.
- **Source dropdown** — populated from distinct sources in the current result set. Client-side filtering option that triggers a new backend call with the `source` param.
- **Tags dropdown** — populated from `useTags()`. Selecting a tag triggers a new backend call with `tags_any`.
- **Type dropdown** — populated from distinct `memory_type` values in the current result set. Triggers backend call with `memory_type` param.

When any filter or search term changes, pagination resets to offset 0.

### Memory list

Hybrid two-line rows inside a bordered container:

- **Row line 1:** Checkbox, truncated content (single line, `truncate` class), delete button (small X icon, visible on hover only)
- **Row line 2:** Tag pills (small badges), then pushed to the right: source (colored by source), type (muted), relative timestamp — separated by dot characters
- **Selected state:** Subtle blue-tinted background when checkbox is active
- **Click behavior:** Clicking anywhere on the row (except checkbox/delete) opens the side panel for that memory
- **List header:** A "select all on this page" checkbox

### Pagination

Below the memory list. Shows "Showing 1–50 of 847" text with Previous and Next buttons. Buttons disabled at boundaries (first/last page). Page size is fixed at 50.

### Bulk action bar

Appears at the bottom of the list area when any checkboxes are active. Contains:

- "N selected" count
- Delete button (red, with confirmation)
- Archive button (muted) — sets `is_archived: true` via the existing `PUT /memories/:id` update endpoint

### Side panel

Uses the existing shadcn `Sheet` component. Opens from the right on row click. Contains:

- Full untruncated memory content
- All tags as badge pills
- Metadata section: source, type, importance score, created_at and updated_at timestamps (formatted)
- Delete button (with confirmation)
- Close button (X in corner)

Closing the panel does not deselect any checkboxes.

## Responsive behavior

- **Desktop (lg+):** Full layout as described. Side panel overlays from the right, list stays visible underneath.
- **Tablet/mobile (<lg):** Search and filter bar stack vertically (search on its own row, filters below). Rows stay the same. Side panel takes full width as a bottom sheet. Pagination stays at bottom.

## Files to Create or Modify

| Action | File | Purpose |
|--------|------|---------|
| Modify | `backend/app/schemas/memory.py` | Add `source` and `memory_type` to search request, add paginated response schema |
| Modify | `backend/app/services/memory.py` | Add `search_memories_paginated` method with offset, total count, source/type filters |
| Modify | `backend/app/api/routes/memories.py` | Add `POST /memories/search/paginated` route |
| Modify | `frontend/src/hooks/api/useMemoryApi.ts` | Add `usePaginatedSearch` hook and paginated types |
| Rewrite | `frontend/src/pages/Memories.tsx` | Full rewrite with new layout |
| Delete | `frontend/src/pages/Search.tsx` | Remove — functionality absorbed into Memories |
| Modify | `frontend/src/App.tsx` | Remove Search route and import |
| Modify | `frontend/src/components/Sidebar.tsx` | Remove Search nav item |

## Out of Scope

- Manual memory creation (removed — memories come from automated sources)
- Reason/Q&A mode (handled by Chat page)
- Inline editing of memory content
- Drag-and-drop reordering
- Export/import functionality
- Sort controls (results ordered by created_at desc by default, or by relevance when search query is active)
