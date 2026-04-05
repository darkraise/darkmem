# Overview Page Redesign

## Goal

Replace the current minimal Overview page with a polished executive-summary dashboard that surfaces key metrics, activity trends, source and tag breakdowns, and recent memories at a glance. The layout adapts responsively: a dense two-column hero on desktop, collapsing to a clean top-down flow on tablet and mobile.

## Data Layer

### New endpoint: `GET /api/v1/analytics/overview`

Consolidates all Overview data into a single request. Accepts an optional `days` query param (default 7, max 90) for the activity timeline range.

Response shape:

```json
{
  "counts": {
    "memories": 847,
    "tags": 34,
    "entities": 69,
    "relationships": 156
  },
  "activity": [
    { "date": "2026-04-05", "count": 12 },
    { "date": "2026-04-04", "count": 8 }
  ],
  "sources": [
    { "name": "claude-code", "count": 524 },
    { "name": "api", "count": 203 }
  ],
  "top_tags": [
    { "name": "infra", "count": 23 },
    { "name": "debug", "count": 18 }
  ],
  "recent_memories": [
    {
      "id": "uuid",
      "content": "User prefers Docker Compose...",
      "source": "claude-code",
      "memory_type": "preference",
      "tags": ["infra", "user"],
      "created_at": "2026-04-05T10:30:00Z"
    }
  ],
  "recent_errors": 2
}
```

Backend implementation:

- `counts`: reuse existing stats queries (memory count, tag count, graph stats)
- `activity`: `SELECT DATE(created_at), COUNT(*) FROM memory WHERE created_at >= now() - interval '$days days' GROUP BY DATE(created_at) ORDER BY date`
- `sources`: `SELECT source, COUNT(*) FROM memory WHERE is_archived = false GROUP BY source ORDER BY count DESC`
- `top_tags`: `SELECT t.name, COUNT(*) FROM tag t JOIN memory_tags mt ON t.id = mt.tag_id GROUP BY t.name ORDER BY count DESC LIMIT 5`
- `recent_memories`: `SELECT ... FROM memory WHERE is_archived = false ORDER BY created_at DESC LIMIT 5`
- `recent_errors`: count from last 5 pipeline audit logs where details->error is not null

### Health endpoint (unchanged)

`GET /health` stays separate with its own 30-second polling interval via `useHealth()`. It tests live connectivity and should not be bundled into the overview payload.

### Frontend hook

```typescript
function useOverview(days: number = 7) {
  return useQuery({
    queryKey: ["overview", days],
    queryFn: () => apiFetch(`/analytics/overview?days=${days}`),
  });
}
```

## Layout

### Desktop (lg, 1024px+) — Layout B: Two-column hero

```
┌─────────────────────────┬──────────────────────────┐
│  Stats (2x2 grid)       │  Activity Chart           │
│  + Pipeline health bar  │  (bar chart, 7d/30d)      │
└─────────────────────────┴──────────────────────────┘
┌────────────┬────────────┬──────────────────────────┐
│  Sources   │  Top Tags  │  Recent Memories          │
│  (list)    │  (list)    │  (compact rows)           │
└────────────┴────────────┴──────────────────────────┘
```

- Hero row: `grid grid-cols-2 gap-4`
  - Left card: stats in 2x2 inner grid, pipeline health below a `border-t`
  - Right card: Recharts BarChart filling the card height
- Bottom row: `grid grid-cols-4 gap-4` where sources and tags each take 1fr and recent memories takes 2fr

### Tablet and below (<1024px) — Layout A: Top-down flow

```
┌──────┬──────┬──────┬──────┐
│ Mem  │ Tags │ Ent  │ Rel  │  (4-col → 2-col on sm)
└──────┴──────┴──────┴──────┘
┌────────────────────────────┐
│ Pipeline health bar        │
└────────────────────────────┘
┌──────────────────┬─────────┐
│ Activity Chart   │ Sources │  (stacked on sm)
└──────────────────┴─────────┘
┌────────────────────────────┐
│ Top Tags                   │
└────────────────────────────┘
┌────────────────────────────┐
│ Recent Memories            │
└────────────────────────────┘
```

- Stats: `grid grid-cols-2 sm:grid-cols-4 gap-4` — four separate stat cards
- Pipeline: its own card
- Chart + sources: `grid grid-cols-1 sm:grid-cols-[3fr_2fr] gap-4`
- Top tags and recent memories: full-width stacked cards

Breakpoint at `lg` (1024px) toggles between the two structures using Tailwind's `hidden lg:block` / `lg:hidden` on wrapper divs.

## Visual Design

### Stat cards

- Large numeric value: `text-3xl font-bold`
- Uppercase muted label above: `text-xs uppercase tracking-wider text-muted-foreground`
- Optional delta below in green: `text-xs text-green-500` showing "+N today" when there's activity today (computed from activity array)
- On desktop: embedded in 2x2 grid inside the hero card
- On mobile: four separate Card components

### Pipeline health

- Slim inline bar with ServiceDot for each service
- Text: "Active" / "Inactive" plus service names with check/cross
- Error indicator: if `recent_errors > 0`, show red text "N errors in recent runs"
- On desktop: sits below stats inside the same card, separated by `border-t border-border pt-3 mt-3`
- On mobile: standalone card

### Activity chart

- Recharts `BarChart` with `ResponsiveContainer`
- Bar fill: `#58a6ff`, rounded radius `[4, 4, 0, 0]`
- Grid: `stroke="#21262d"`, dashed
- Axis ticks: `fill="#8b949e"`, small font
- X-axis: date labels (abbreviated: "Mon", "Tue" for 7d; "Apr 1", "Apr 2" for 30d)
- Tooltip: dark background matching theme
- Card header contains "Activity" title and a 7d / 30d toggle (two small buttons, active state highlighted)

### Sources list

- Colored dot (from SOURCE_COLORS or UNIFIED_PALETTE) + source name + percentage
- Percentage computed from counts: `(source.count / total) * 100`
- Sorted descending by count
- No chart — clean list with dot indicators

### Top tags

- Tag name + memory count, sorted descending, limited to top 5
- Simple rows: name left-aligned, count right-aligned in muted color
- No bars or visual indicators

### Recent memories

- Compact rows, not full MemoryCard
- Each row: truncated content (single line, `truncate` class), source as small badge, relative timestamp
- Limited to 5 entries
- Clicking a row navigates to `/memories` page
- Rows have subtle hover state and border

### Empty states

Each section shows a brief muted message when data is absent rather than hiding the section. This keeps the layout stable during loading and for new installations:

- Stats: show "—" for each value
- Activity: "No activity data yet"
- Sources: "No sources yet"
- Top tags: "No tags yet"
- Recent memories: "No memories yet. Create one to get started."

## Files to Create or Modify

| Action | File | Purpose |
|--------|------|---------|
| Modify | `backend/app/api/routes/analytics.py` | Add `/analytics/overview` route |
| Modify | `backend/app/services/analytics.py` | Add `get_overview()` service method |
| Modify | `frontend/src/hooks/api/usePipelineApi.ts` | Add `useOverview(days)` query hook |
| Rewrite | `frontend/src/pages/Overview.tsx` | Full page rewrite with new layout |

## Out of Scope

- Clicking a recent memory to scroll/highlight it on the Memories page (just navigates to /memories)
- Sparklines or mini-charts inside stat cards
- Drag-to-reorder dashboard sections
- Custom date range picker for activity (just 7d/30d toggle)
