# Overview Page Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the minimal Overview page with a polished executive-summary dashboard backed by a single consolidated API endpoint.

**Architecture:** New `GET /analytics/overview` endpoint aggregates counts, activity, sources, tags, recent memories, and error count into one payload. The frontend consumes it via a single `useOverview(days)` hook. Two layout variants (desktop two-column hero, mobile top-down flow) are toggled via Tailwind `lg:` breakpoints.

**Tech Stack:** FastAPI + SQLAlchemy (backend), React + TanStack Query + Recharts + Tailwind CSS (frontend)

**Spec:** `docs/superpowers/specs/2026-04-05-overview-redesign-design.md`

---

### Task 1: Backend — Add `get_overview()` service method

**Files:**
- Modify: `backend/app/services/analytics.py`

- [ ] **Step 1: Add the `get_overview` method to `AnalyticsService`**

Add this method at the end of the `AnalyticsService` class, after the `_reprocess_batch_stream` method. It needs access to an optional `graph_repo` for entity/relationship counts, so we also update `__init__` to accept it.

```python
# In AnalyticsService.__init__, add graph_repo parameter:
class AnalyticsService:
    def __init__(
        self,
        session: AsyncSession,
        pipeline: ProcessingPipeline | None = None,
        graph_repo=None,
    ):
        self.session = session
        self.audit_repo = PostgresAuditRepository(session)
        self.pipeline = pipeline
        self.graph_repo = graph_repo
```

Then add the method (needs new imports at the top of the file: `from datetime import date, timedelta` and `from sqlalchemy import func` and `from app.models.memory import Tag, memory_tags`):

```python
    async def get_overview(self, days: int = 7) -> dict:
        # Counts
        memory_count = (await self.session.execute(
            select(func.count()).select_from(Memory).where(Memory.is_archived == False)  # noqa: E712
        )).scalar() or 0
        tag_count = (await self.session.execute(
            select(func.count()).select_from(Tag)
        )).scalar() or 0

        entity_count = None
        rel_count = None
        if self.graph_repo:
            try:
                stats = await self.graph_repo.get_stats()
                entity_count = stats["entity_count"]
                rel_count = stats["relationship_count"]
            except Exception:
                logger.debug("Graph stats unavailable")

        # Activity: daily memory counts for the last N days
        since = date.today() - timedelta(days=days - 1)
        activity_stmt = (
            select(
                func.date(Memory.created_at).label("day"),
                func.count().label("count"),
            )
            .where(Memory.created_at >= since)
            .group_by(func.date(Memory.created_at))
            .order_by(func.date(Memory.created_at))
        )
        activity_rows = (await self.session.execute(activity_stmt)).all()
        activity = [{"date": str(r.day), "count": r.count} for r in activity_rows]

        # Sources breakdown
        source_stmt = (
            select(Memory.source, func.count().label("count"))
            .where(Memory.is_archived == False)  # noqa: E712
            .group_by(Memory.source)
            .order_by(func.count().desc())
        )
        source_rows = (await self.session.execute(source_stmt)).all()
        sources = [{"name": r.source, "count": r.count} for r in source_rows]

        # Top tags
        tag_stmt = (
            select(Tag.name, func.count(memory_tags.c.memory_id).label("count"))
            .outerjoin(memory_tags)
            .group_by(Tag.name)
            .order_by(func.count(memory_tags.c.memory_id).desc())
            .limit(5)
        )
        tag_rows = (await self.session.execute(tag_stmt)).all()
        top_tags = [{"name": r.name, "count": r.count} for r in tag_rows]

        # Recent memories
        mem_stmt = (
            select(Memory)
            .options(selectinload(Memory.tags))
            .where(Memory.is_archived == False)  # noqa: E712
            .order_by(Memory.created_at.desc())
            .limit(5)
        )
        mem_rows = (await self.session.execute(mem_stmt)).scalars().all()
        recent_memories = [
            {
                "id": str(m.id),
                "content": m.content,
                "source": m.source,
                "memory_type": m.memory_type,
                "tags": [t.name for t in m.tags],
                "created_at": m.created_at.isoformat(),
            }
            for m in mem_rows
        ]

        # Recent pipeline errors
        error_stmt = (
            select(func.count())
            .select_from(AuditLog)
            .where(AuditLog.action == "pipeline")
            .where(AuditLog.details["error"].as_string() != "null")
            .where(AuditLog.details["error"].as_string().isnot(None))
        )
        recent_errors = (await self.session.execute(error_stmt)).scalar() or 0

        return {
            "counts": {
                "memories": memory_count,
                "tags": tag_count,
                "entities": entity_count,
                "relationships": rel_count,
            },
            "activity": activity,
            "sources": sources,
            "top_tags": top_tags,
            "recent_memories": recent_memories,
            "recent_errors": recent_errors,
        }
```

- [ ] **Step 2: Update the dependency injector to pass `graph_repo`**

In `backend/app/api/deps.py`, update `get_analytics_service`:

```python
async def get_analytics_service(request: Request, session: AsyncSession = Depends(get_session)) -> AnalyticsService:
    pipeline = getattr(request.app.state, "pipeline", None)
    graph_repo = getattr(request.app.state, "graph_repo", None)
    return AnalyticsService(session, pipeline, graph_repo)
```

- [ ] **Step 3: Verify syntax**

Run: `cd backend && python -c "import ast; ast.parse(open('app/services/analytics.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/services/analytics.py backend/app/api/deps.py
git commit -m "feat(analytics): add get_overview service method"
```

---

### Task 2: Backend — Add `/analytics/overview` route

**Files:**
- Modify: `backend/app/api/routes/analytics.py`

- [ ] **Step 1: Add the route**

Add this after the existing `/pipeline-logs` endpoint at the bottom of the file:

```python
@router.get("/overview")
async def get_overview(
    days: int = 7,
    _user=Depends(require_auth),
    service: AnalyticsService = Depends(get_analytics_service),
):
    clamped_days = max(1, min(days, 90))
    return await service.get_overview(clamped_days)
```

- [ ] **Step 2: Verify syntax**

Run: `cd backend && python -c "import ast; ast.parse(open('app/api/routes/analytics.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/routes/analytics.py
git commit -m "feat(analytics): add /overview endpoint"
```

---

### Task 3: Backend — Test the overview endpoint

**Files:**
- Create: `backend/tests/test_overview.py`

- [ ] **Step 1: Write the test**

```python
from app.models.memory import Memory, Tag, memory_tags
from app.models.audit import AuditLog


async def test_overview_returns_counts(client, session, auth_headers):
    tag = Tag(name="test/overview")
    session.add(tag)
    await session.flush()

    m = Memory(content="overview test", source="api")
    m.tags.append(tag)
    session.add(m)
    await session.flush()

    resp = await client.get("/api/v1/analytics/overview", headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()

    assert data["counts"]["memories"] >= 1
    assert data["counts"]["tags"] >= 1
    assert len(data["sources"]) >= 1
    assert len(data["top_tags"]) >= 1
    assert len(data["recent_memories"]) >= 1
    assert isinstance(data["activity"], list)
    assert isinstance(data["recent_errors"], int)

    mem = data["recent_memories"][0]
    assert "id" in mem
    assert "content" in mem
    assert "source" in mem
    assert "tags" in mem
    assert "created_at" in mem


async def test_overview_days_param(client, session, auth_headers):
    session.add(Memory(content="days test", source="api"))
    await session.flush()

    resp = await client.get("/api/v1/analytics/overview?days=30", headers=auth_headers)
    assert resp.status_code == 200

    resp2 = await client.get("/api/v1/analytics/overview?days=999", headers=auth_headers)
    assert resp2.status_code == 200


async def test_overview_requires_auth(client):
    resp = await client.get("/api/v1/analytics/overview")
    assert resp.status_code in (401, 403)
```

- [ ] **Step 2: Run the tests**

Run: `cd backend && python -m pytest tests/test_overview.py -v`
Expected: 3 tests PASS

- [ ] **Step 3: Commit**

```bash
git add backend/tests/test_overview.py
git commit -m "test(analytics): add overview endpoint tests"
```

---

### Task 4: Frontend — Add `useOverview` hook and types

**Files:**
- Modify: `frontend/src/hooks/api/usePipelineApi.ts`

- [ ] **Step 1: Add the types and hook**

Add these at the end of the file, after the `useReprocessStream` function:

```typescript
export interface OverviewData {
  counts: {
    memories: number;
    tags: number;
    entities: number | null;
    relationships: number | null;
  };
  activity: Array<{ date: string; count: number }>;
  sources: Array<{ name: string; count: number }>;
  top_tags: Array<{ name: string; count: number }>;
  recent_memories: Array<{
    id: string;
    content: string;
    source: string;
    memory_type: string | null;
    tags: string[];
    created_at: string;
  }>;
  recent_errors: number;
}

export function useOverview(days: number = 7) {
  return useQuery<OverviewData>({
    queryKey: ["overview", days],
    queryFn: () => apiFetch(`/analytics/overview?days=${days}`),
  });
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no new errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/hooks/api/usePipelineApi.ts
git commit -m "feat(hooks): add useOverview hook and OverviewData type"
```

---

### Task 5: Frontend — Rewrite Overview page (desktop layout)

**Files:**
- Rewrite: `frontend/src/pages/Overview.tsx`

- [ ] **Step 1: Write the full Overview page**

Replace the entire file content with:

```tsx
import { useState } from "react";
import { useOverview, useHealth } from "@/hooks/useApi";
import { ServiceDot } from "@/components/ServiceDot";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { useNavigate } from "react-router-dom";

const SOURCE_COLORS: Record<string, string> = {
  "claude-code": "#58a6ff",
  "mcp-test": "#3fb950",
  api: "#d2a8ff",
  "rest-test": "#ffa657",
  dashboard: "#f778ba",
};

const FALLBACK_COLORS = ["#58a6ff", "#3fb950", "#d2a8ff", "#ffa657", "#f778ba", "#8b949e"];

function sourceColor(name: string, index: number): string {
  return SOURCE_COLORS[name] ?? FALLBACK_COLORS[index % FALLBACK_COLORS.length];
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

function formatXAxis(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T00:00:00");
  if (days <= 7) return d.toLocaleDateString("en-US", { weekday: "short" });
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

function StatValue({ label, value, delta }: { label: string; value: string | number; delta?: number }) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium">{label}</div>
      <div className="text-3xl font-bold mt-1">{value}</div>
      {delta != null && delta > 0 && (
        <div className="text-xs text-green-500 mt-0.5">+{delta} today</div>
      )}
    </div>
  );
}

function PipelineHealth({ recentErrors }: { recentErrors: number }) {
  const { data: health } = useHealth();
  if (!health) return null;
  return (
    <div className="flex items-center gap-4 text-sm flex-wrap">
      <span className="flex items-center gap-2">
        <ServiceDot ok={health.pipeline} />
        <span className={health.pipeline ? "text-foreground" : "text-destructive"}>
          {health.pipeline ? "Active" : "Inactive"}
        </span>
      </span>
      <span className="flex items-center gap-1.5 text-muted-foreground"><ServiceDot ok={health.services.qdrant} /> Qdrant</span>
      <span className="flex items-center gap-1.5 text-muted-foreground"><ServiceDot ok={health.services.neo4j} /> Neo4j</span>
      <span className="flex items-center gap-1.5 text-muted-foreground"><ServiceDot ok={health.services.llm} /> LLM</span>
      {recentErrors > 0 && (
        <span className="text-destructive text-xs">{recentErrors} error{recentErrors > 1 ? "s" : ""} in recent runs</span>
      )}
    </div>
  );
}

export default function Overview() {
  const [days, setDays] = useState(7);
  const { data } = useOverview(days);
  const navigate = useNavigate();

  const counts = data?.counts;
  const todayCount = data?.activity?.find((a) => a.date === new Date().toISOString().slice(0, 10))?.count ?? 0;
  const totalSourceCount = data?.sources?.reduce((s, r) => s + r.count, 0) ?? 0;

  const chartData = (data?.activity ?? []).map((a) => ({
    ...a,
    label: formatXAxis(a.date, days),
  }));

  return (
    <div className="p-6 space-y-4">
      <h2 className="text-xl font-semibold">Overview</h2>

      {/* ===== DESKTOP LAYOUT (lg+) ===== */}
      <div className="hidden lg:grid grid-cols-2 gap-4">
        {/* Left: stats + pipeline */}
        <Card>
          <CardContent className="pt-5">
            <div className="grid grid-cols-2 gap-x-8 gap-y-5">
              <StatValue label="Memories" value={counts?.memories ?? "—"} delta={todayCount} />
              <StatValue label="Tags" value={counts?.tags ?? "—"} />
              <StatValue label="Entities" value={counts?.entities ?? "—"} />
              <StatValue label="Relations" value={counts?.relationships ?? "—"} />
            </div>
            <div className="border-t border-border pt-3 mt-4">
              <PipelineHealth recentErrors={data?.recent_errors ?? 0} />
            </div>
          </CardContent>
        </Card>

        {/* Right: activity chart */}
        <Card>
          <CardHeader className="pb-2 flex-row items-center justify-between">
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Activity</CardTitle>
            <div className="flex gap-1">
              <Button variant={days === 7 ? "secondary" : "ghost"} size="sm" className="h-6 px-2 text-xs" onClick={() => setDays(7)}>7d</Button>
              <Button variant={days === 30 ? "secondary" : "ghost"} size="sm" className="h-6 px-2 text-xs" onClick={() => setDays(30)}>30d</Button>
            </div>
          </CardHeader>
          <CardContent>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                  <XAxis dataKey="label" tick={{ fill: "#8b949e", fontSize: 10 }} />
                  <YAxis tick={{ fill: "#8b949e", fontSize: 10 }} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #21262d", color: "#c9d1d9", fontSize: 12 }} />
                  <Bar dataKey="count" fill="#58a6ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-muted-foreground text-sm py-8 text-center">No activity data yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Desktop bottom row: sources | tags | recent */}
      <div className="hidden lg:grid grid-cols-4 gap-4">
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Sources</CardTitle></CardHeader>
          <CardContent>
            {data?.sources?.length ? (
              <div className="space-y-2">
                {data.sources.map((s, i) => (
                  <div key={s.name} className="flex items-center gap-2 text-sm">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: sourceColor(s.name, i) }} />
                    <span className="truncate">{s.name}</span>
                    <span className="ml-auto text-muted-foreground text-xs">{totalSourceCount > 0 ? Math.round((s.count / totalSourceCount) * 100) : 0}%</span>
                  </div>
                ))}
              </div>
            ) : <p className="text-muted-foreground text-sm">No sources yet</p>}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Top Tags</CardTitle></CardHeader>
          <CardContent>
            {data?.top_tags?.length ? (
              <div className="space-y-2">
                {data.top_tags.map((t) => (
                  <div key={t.name} className="flex items-center justify-between text-sm">
                    <span className="truncate">{t.name}</span>
                    <span className="text-muted-foreground text-xs">{t.count}</span>
                  </div>
                ))}
              </div>
            ) : <p className="text-muted-foreground text-sm">No tags yet</p>}
          </CardContent>
        </Card>

        <Card className="col-span-2">
          <CardHeader className="pb-2"><CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Recent Memories</CardTitle></CardHeader>
          <CardContent>
            {data?.recent_memories?.length ? (
              <div className="space-y-1.5">
                {data.recent_memories.map((m) => (
                  <div
                    key={m.id}
                    className="flex items-center gap-3 p-2 border border-border rounded-md hover:bg-accent/50 cursor-pointer transition-colors"
                    onClick={() => navigate("/memories")}
                  >
                    <span className="text-sm truncate flex-1">{m.content}</span>
                    <Badge variant="secondary" className="text-xs shrink-0">{m.source}</Badge>
                    <span className="text-xs text-muted-foreground shrink-0">{relativeTime(m.created_at)}</span>
                  </div>
                ))}
              </div>
            ) : <p className="text-muted-foreground text-sm">No memories yet. Create one to get started.</p>}
          </CardContent>
        </Card>
      </div>

      {/* ===== MOBILE / TABLET LAYOUT (<lg) ===== */}
      {/* Stat cards row */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 lg:hidden">
        <Card><CardContent className="pt-4"><StatValue label="Memories" value={counts?.memories ?? "—"} delta={todayCount} /></CardContent></Card>
        <Card><CardContent className="pt-4"><StatValue label="Tags" value={counts?.tags ?? "—"} /></CardContent></Card>
        <Card><CardContent className="pt-4"><StatValue label="Entities" value={counts?.entities ?? "—"} /></CardContent></Card>
        <Card><CardContent className="pt-4"><StatValue label="Relations" value={counts?.relationships ?? "—"} /></CardContent></Card>
      </div>

      {/* Pipeline health card */}
      <Card className="lg:hidden">
        <CardContent className="pt-4">
          <PipelineHealth recentErrors={data?.recent_errors ?? 0} />
        </CardContent>
      </Card>

      {/* Activity + Sources side by side */}
      <div className="grid grid-cols-1 sm:grid-cols-[3fr_2fr] gap-4 lg:hidden">
        <Card>
          <CardHeader className="pb-2 flex-row items-center justify-between">
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Activity</CardTitle>
            <div className="flex gap-1">
              <Button variant={days === 7 ? "secondary" : "ghost"} size="sm" className="h-6 px-2 text-xs" onClick={() => setDays(7)}>7d</Button>
              <Button variant={days === 30 ? "secondary" : "ghost"} size="sm" className="h-6 px-2 text-xs" onClick={() => setDays(30)}>30d</Button>
            </div>
          </CardHeader>
          <CardContent>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                  <XAxis dataKey="label" tick={{ fill: "#8b949e", fontSize: 10 }} />
                  <YAxis tick={{ fill: "#8b949e", fontSize: 10 }} allowDecimals={false} />
                  <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #21262d", color: "#c9d1d9", fontSize: 12 }} />
                  <Bar dataKey="count" fill="#58a6ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-muted-foreground text-sm py-8 text-center">No activity data yet</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Sources</CardTitle></CardHeader>
          <CardContent>
            {data?.sources?.length ? (
              <div className="space-y-2">
                {data.sources.map((s, i) => (
                  <div key={s.name} className="flex items-center gap-2 text-sm">
                    <span className="w-2 h-2 rounded-full shrink-0" style={{ backgroundColor: sourceColor(s.name, i) }} />
                    <span className="truncate">{s.name}</span>
                    <span className="ml-auto text-muted-foreground text-xs">{totalSourceCount > 0 ? Math.round((s.count / totalSourceCount) * 100) : 0}%</span>
                  </div>
                ))}
              </div>
            ) : <p className="text-muted-foreground text-sm">No sources yet</p>}
          </CardContent>
        </Card>
      </div>

      {/* Top Tags */}
      <Card className="lg:hidden">
        <CardHeader className="pb-2"><CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Top Tags</CardTitle></CardHeader>
        <CardContent>
          {data?.top_tags?.length ? (
            <div className="space-y-2">
              {data.top_tags.map((t) => (
                <div key={t.name} className="flex items-center justify-between text-sm">
                  <span className="truncate">{t.name}</span>
                  <span className="text-muted-foreground text-xs">{t.count}</span>
                </div>
              ))}
            </div>
          ) : <p className="text-muted-foreground text-sm">No tags yet</p>}
        </CardContent>
      </Card>

      {/* Recent Memories */}
      <Card className="lg:hidden">
        <CardHeader className="pb-2"><CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Recent Memories</CardTitle></CardHeader>
        <CardContent>
          {data?.recent_memories?.length ? (
            <div className="space-y-1.5">
              {data.recent_memories.map((m) => (
                <div
                  key={m.id}
                  className="flex items-center gap-3 p-2 border border-border rounded-md hover:bg-accent/50 cursor-pointer transition-colors"
                  onClick={() => navigate("/memories")}
                >
                  <span className="text-sm truncate flex-1">{m.content}</span>
                  <Badge variant="secondary" className="text-xs shrink-0">{m.source}</Badge>
                  <span className="text-xs text-muted-foreground shrink-0">{relativeTime(m.created_at)}</span>
                </div>
              ))}
            </div>
          ) : <p className="text-muted-foreground text-sm">No memories yet. Create one to get started.</p>}
        </CardContent>
      </Card>
    </div>
  );
}
```

- [ ] **Step 2: Type-check**

Run: `cd frontend && npx tsc --noEmit`
Expected: no new errors

- [ ] **Step 3: Commit**

```bash
git add frontend/src/pages/Overview.tsx
git commit -m "feat(overview): redesign dashboard with responsive layout"
```

---

### Task 6: Verify full build

**Files:** none (verification only)

- [ ] **Step 1: Type-check frontend**

Run: `cd frontend && npx tsc --noEmit`
Expected: clean (no new errors)

- [ ] **Step 2: Backend syntax check**

Run: `cd backend && python -c "import ast; ast.parse(open('app/services/analytics.py').read()); ast.parse(open('app/api/routes/analytics.py').read()); print('OK')"`
Expected: `OK`

- [ ] **Step 3: Run backend tests**

Run: `cd backend && python -m pytest tests/test_overview.py -v`
Expected: all tests PASS

- [ ] **Step 4: Build frontend**

Run: `cd frontend && npm run build 2>&1 | tail -5`
Expected: build completes (pre-existing warnings in other files are acceptable)
