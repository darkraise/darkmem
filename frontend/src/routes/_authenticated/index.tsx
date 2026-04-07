import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { useNavigate } from "@tanstack/react-router"
import { useOverview, useHealth } from "@/hooks/api"
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { PageHeader } from "darkraise-ui/layout"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  PieChart,
  Pie,
  Cell,
} from "recharts"

export const Route = createFileRoute("/_authenticated/")({
  component: OverviewPage,
})

const SOURCE_COLORS: Record<string, string> = {
  "claude-code": "#58a6ff",
  "mcp-test": "#3fb950",
  api: "#d2a8ff",
  "rest-test": "#ffa657",
  dashboard: "#f778ba",
}

const FALLBACK_COLORS = ["#58a6ff", "#3fb950", "#d2a8ff", "#ffa657", "#f778ba", "#8b949e"]

function sourceColor(name: string, index: number): string {
  return SOURCE_COLORS[name] ?? FALLBACK_COLORS[index % FALLBACK_COLORS.length]
}

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

function formatXAxis(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T00:00:00")
  if (days <= 7) return d.toLocaleDateString("en-US", { weekday: "short" })
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

function ServiceDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`}
    />
  )
}

function StatValue({
  label,
  value,
  delta,
}: {
  label: string
  value: string | number
  delta?: number
}) {
  return (
    <div>
      <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
        {label}
      </div>
      <div className="text-3xl font-bold mt-1">{value}</div>
      {delta != null && delta > 0 && (
        <div className="text-xs text-green-500 mt-0.5">+{delta} today</div>
      )}
    </div>
  )
}

function PipelineHealth({ recentErrors }: { recentErrors: number }) {
  const { data: health } = useHealth()
  if (!health) return null
  return (
    <div className="flex items-center gap-4 text-sm flex-wrap">
      <span className="flex items-center gap-2">
        <ServiceDot ok={health.pipeline} />
        <span className={health.pipeline ? "text-foreground" : "text-destructive"}>
          {health.pipeline ? "Active" : "Inactive"}
        </span>
      </span>
      <span className="flex items-center gap-1.5 text-muted-foreground">
        <ServiceDot ok={health.services.qdrant} /> Qdrant
      </span>
      <span className="flex items-center gap-1.5 text-muted-foreground">
        <ServiceDot ok={health.services.neo4j} /> Neo4j
      </span>
      <span className="flex items-center gap-1.5 text-muted-foreground">
        <ServiceDot ok={health.services.llm} /> LLM
      </span>
      {recentErrors > 0 && (
        <span className="text-destructive text-xs">
          {recentErrors} error{recentErrors > 1 ? "s" : ""} in recent runs
        </span>
      )}
    </div>
  )
}

function OverviewPage() {
  const [days, setDays] = useState(7)
  const { data } = useOverview(days)
  const navigate = useNavigate()

  const counts = data?.counts
  const todayCount =
    data?.activity?.find((a) => a.date === new Date().toISOString().slice(0, 10))?.count ?? 0
  const totalSourceCount = data?.sources?.reduce((s, r) => s + r.count, 0) ?? 0

  const chartData = (data?.activity ?? []).map((a) => ({
    ...a,
    label: formatXAxis(a.date, days),
  }))

  return (
    <div className="p-6 space-y-4">
      <PageHeader title="Overview" />

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
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
              Activity
            </CardTitle>
            <div className="flex gap-1">
              <Button
                variant={days === 7 ? "secondary" : "ghost"}
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setDays(7)}
              >
                7d
              </Button>
              <Button
                variant={days === 30 ? "secondary" : "ghost"}
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setDays(30)}
              >
                30d
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                  <XAxis dataKey="label" tick={{ fill: "#8b949e", fontSize: 10 }} />
                  <YAxis tick={{ fill: "#8b949e", fontSize: 10 }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: "#161b22",
                      border: "1px solid #21262d",
                      color: "#c9d1d9",
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="count" fill="#58a6ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-muted-foreground text-sm py-8 text-center">
                No activity data yet
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Desktop: sources | tags */}
      <div className="hidden lg:grid grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
              Sources
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data?.sources?.length ? (
              <div className="flex items-center gap-4">
                <ResponsiveContainer width={100} height={100}>
                  <PieChart>
                    <Pie
                      data={data.sources}
                      dataKey="count"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={28}
                      outerRadius={45}
                      paddingAngle={2}
                      strokeWidth={0}
                    >
                      {data.sources.map((s, i) => (
                        <Cell key={s.name} fill={sourceColor(s.name, i)} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: "#161b22",
                        border: "1px solid #21262d",
                        color: "#c9d1d9",
                        fontSize: 12,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-1.5 flex-1 min-w-0">
                  {data.sources.map((s, i) => (
                    <div key={s.name} className="flex items-center gap-2 text-xs">
                      <span
                        className="w-2 h-2 rounded-full shrink-0"
                        style={{ backgroundColor: sourceColor(s.name, i) }}
                      />
                      <span className="truncate">{s.name}</span>
                      <span className="ml-auto text-muted-foreground">
                        {totalSourceCount > 0
                          ? Math.round((s.count / totalSourceCount) * 100)
                          : 0}
                        %
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">No sources yet</p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
              Top Tags
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data?.top_tags?.length ? (
              <ResponsiveContainer width="100%" height={120}>
                <BarChart
                  data={data.top_tags}
                  layout="vertical"
                  margin={{ left: 0, right: 0, top: 0, bottom: 0 }}
                >
                  <XAxis
                    type="number"
                    tick={{ fill: "#8b949e", fontSize: 10 }}
                    allowDecimals={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={100}
                    tick={(props: { x: number; y: number; payload: { value: string } }) => {
                      const label =
                        props.payload.value.length > 14
                          ? props.payload.value.slice(0, 13) + "…"
                          : props.payload.value
                      return (
                        <text
                          x={props.x}
                          y={props.y}
                          dy={4}
                          textAnchor="end"
                          fill="#c9d1d9"
                          fontSize={11}
                        >
                          {label}
                        </text>
                      )
                    }}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#161b22",
                      border: "1px solid #21262d",
                      color: "#c9d1d9",
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="count" fill="#3fb950" radius={[0, 4, 4, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-muted-foreground text-sm">No tags yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Desktop: recent memories */}
      <Card className="hidden lg:block">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
            Recent Memories
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data?.recent_memories?.length ? (
            <div className="space-y-1.5">
              {data.recent_memories.map((m) => (
                <div
                  key={m.id}
                  className="flex items-center gap-3 p-2 border border-border rounded-md hover:bg-accent/50 cursor-pointer transition-colors"
                  onClick={() => navigate({ to: "/memories" })}
                >
                  <span className="text-sm truncate flex-1">{m.content}</span>
                  <Badge variant="secondary" className="text-xs shrink-0">
                    {m.source}
                  </Badge>
                  <span className="text-xs text-muted-foreground shrink-0">
                    {relativeTime(m.created_at)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-sm">
              No memories yet. Create one to get started.
            </p>
          )}
        </CardContent>
      </Card>

      {/* ===== MOBILE / TABLET LAYOUT (<lg) ===== */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 lg:hidden">
        <Card>
          <CardContent className="pt-4">
            <StatValue label="Memories" value={counts?.memories ?? "—"} delta={todayCount} />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <StatValue label="Tags" value={counts?.tags ?? "—"} />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <StatValue label="Entities" value={counts?.entities ?? "—"} />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <StatValue label="Relations" value={counts?.relationships ?? "—"} />
          </CardContent>
        </Card>
      </div>

      <Card className="lg:hidden">
        <CardContent className="pt-4">
          <PipelineHealth recentErrors={data?.recent_errors ?? 0} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 sm:grid-cols-[3fr_2fr] gap-4 lg:hidden">
        <Card>
          <CardHeader className="pb-2 flex-row items-center justify-between">
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
              Activity
            </CardTitle>
            <div className="flex gap-1">
              <Button
                variant={days === 7 ? "secondary" : "ghost"}
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setDays(7)}
              >
                7d
              </Button>
              <Button
                variant={days === 30 ? "secondary" : "ghost"}
                size="sm"
                className="h-6 px-2 text-xs"
                onClick={() => setDays(30)}
              >
                30d
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            {chartData.length > 0 ? (
              <ResponsiveContainer width="100%" height={160}>
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                  <XAxis dataKey="label" tick={{ fill: "#8b949e", fontSize: 10 }} />
                  <YAxis tick={{ fill: "#8b949e", fontSize: 10 }} allowDecimals={false} />
                  <Tooltip
                    contentStyle={{
                      background: "#161b22",
                      border: "1px solid #21262d",
                      color: "#c9d1d9",
                      fontSize: 12,
                    }}
                  />
                  <Bar dataKey="count" fill="#58a6ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-muted-foreground text-sm py-8 text-center">
                No activity data yet
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
              Sources
            </CardTitle>
          </CardHeader>
          <CardContent>
            {data?.sources?.length ? (
              <div className="flex items-center gap-4">
                <ResponsiveContainer width={100} height={100}>
                  <PieChart>
                    <Pie
                      data={data.sources}
                      dataKey="count"
                      nameKey="name"
                      cx="50%"
                      cy="50%"
                      innerRadius={28}
                      outerRadius={45}
                      paddingAngle={2}
                      strokeWidth={0}
                    >
                      {data.sources.map((s, i) => (
                        <Cell key={s.name} fill={sourceColor(s.name, i)} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{
                        background: "#161b22",
                        border: "1px solid #21262d",
                        color: "#c9d1d9",
                        fontSize: 12,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="space-y-1.5 flex-1 min-w-0">
                  {data.sources.map((s, i) => (
                    <div key={s.name} className="flex items-center gap-2 text-xs">
                      <span
                        className="w-2 h-2 rounded-full shrink-0"
                        style={{ backgroundColor: sourceColor(s.name, i) }}
                      />
                      <span className="truncate">{s.name}</span>
                      <span className="ml-auto text-muted-foreground">
                        {totalSourceCount > 0
                          ? Math.round((s.count / totalSourceCount) * 100)
                          : 0}
                        %
                      </span>
                    </div>
                  ))}
                </div>
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">No sources yet</p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card className="lg:hidden">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
            Top Tags
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data?.top_tags?.length ? (
            <ResponsiveContainer width="100%" height={120}>
              <BarChart
                data={data.top_tags}
                layout="vertical"
                margin={{ left: 0, right: 0, top: 0, bottom: 0 }}
              >
                <XAxis
                  type="number"
                  tick={{ fill: "#8b949e", fontSize: 10 }}
                  allowDecimals={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fill: "#c9d1d9", fontSize: 11 }}
                  width={70}
                />
                <Tooltip
                  contentStyle={{
                    background: "#161b22",
                    border: "1px solid #21262d",
                    color: "#c9d1d9",
                    fontSize: 12,
                  }}
                />
                <Bar dataKey="count" fill="#3fb950" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <p className="text-muted-foreground text-sm">No tags yet</p>
          )}
        </CardContent>
      </Card>

      <Card className="lg:hidden">
        <CardHeader className="pb-2">
          <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
            Recent Memories
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data?.recent_memories?.length ? (
            <div className="space-y-1.5">
              {data.recent_memories.map((m) => (
                <div
                  key={m.id}
                  className="flex items-center gap-3 p-2 border border-border rounded-md hover:bg-accent/50 cursor-pointer transition-colors"
                  onClick={() => navigate({ to: "/memories" })}
                >
                  <span className="text-sm truncate flex-1">{m.content}</span>
                  <Badge variant="secondary" className="text-xs shrink-0">
                    {m.source}
                  </Badge>
                  <span className="text-xs text-muted-foreground shrink-0">
                    {relativeTime(m.created_at)}
                  </span>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-sm">
              No memories yet. Create one to get started.
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
