import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { useNavigate } from "@tanstack/react-router"
import { useOverview, useHealth } from "@/hooks/api"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageHeader } from "darkraise-ui/layout"
import { Stat, StatLabel, StatValue } from "darkraise-ui/components/stat"
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
  type YAxisTickContentProps,
} from "recharts"
import { relativeTime } from "@/lib/format"
import { sourceColor } from "@/lib/source-colors"

export const Route = createFileRoute("/_authenticated/")({
  component: OverviewPage,
})

function formatXAxis(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T00:00:00")
  if (days <= 7) return d.toLocaleDateString("en-US", { weekday: "short" })
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" })
}

function ServiceDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`}
    />
  )
}

function StatBlock({
  label,
  value,
  delta,
}: {
  label: string
  value: string | number
  delta?: number
}) {
  return (
    <Stat>
      <StatLabel>{label}</StatLabel>
      <StatValue>{value}</StatValue>
      {delta != null && delta > 0 && (
        <div className="mt-0.5 text-sm text-green-500">+{delta} today</div>
      )}
    </Stat>
  )
}

function PipelineHealth({ recentErrors }: { recentErrors: number }) {
  const { data: health } = useHealth()
  if (!health) return null
  return (
    <div className="flex flex-wrap items-center gap-4 text-sm">
      <span className="flex items-center gap-2">
        <ServiceDot ok={health.pipeline} />
        <span
          className={health.pipeline ? "text-foreground" : "text-destructive"}
        >
          {health.pipeline ? "Active" : "Inactive"}
        </span>
      </span>
      <span className="text-muted-foreground flex items-center gap-1.5">
        <ServiceDot ok={health.services.pgvector} /> pgvector
      </span>
      <span className="text-muted-foreground flex items-center gap-1.5">
        <ServiceDot ok={health.services.llm} /> LLM
      </span>
      {recentErrors > 0 && (
        <span className="text-destructive text-sm">
          {recentErrors} error{recentErrors > 1 ? "s" : ""} in recent runs
        </span>
      )}
    </div>
  )
}

function OverviewPage() {
  const [days, setDays] = useState(7)
  const { data, isLoading, isError, refetch } = useOverview(days)
  const navigate = useNavigate()

  if (isLoading) {
    return (
      <div className="space-y-4 p-6">
        <PageHeader title="Overview" />
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <Skeleton key={i} className="h-24 w-full rounded-md" />
          ))}
        </div>
        <Skeleton className="h-12 w-full rounded-md" />
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
          <Skeleton className="h-48 w-full rounded-md" />
          <Skeleton className="h-48 w-full rounded-md" />
        </div>
        <Skeleton className="h-48 w-full rounded-md" />
      </div>
    )
  }

  if (isError) {
    return (
      <div className="space-y-4 p-6">
        <PageHeader title="Overview" />
        <Card>
          <CardContent className="flex flex-col items-center gap-3 py-12 text-center">
            <p role="alert" className="text-destructive text-sm">
              Failed to load overview data.
            </p>
            <Button variant="outline" onClick={() => refetch()}>
              Retry
            </Button>
          </CardContent>
        </Card>
      </div>
    )
  }

  const counts = data?.counts
  const todayCount =
    data?.activity?.find(
      (a) => a.date === new Date().toISOString().slice(0, 10),
    )?.count ?? 0
  const totalSourceCount = data?.sources?.reduce((s, r) => s + r.count, 0) ?? 0

  const chartData = (data?.activity ?? []).map((a) => ({
    ...a,
    label: formatXAxis(a.date, days),
  }))

  return (
    <div className="space-y-4 p-6">
      <PageHeader title="Overview" />

      {/* ===== DESKTOP LAYOUT (lg+) ===== */}
      <div className="hidden grid-cols-2 gap-4 lg:grid">
        {/* Left: stats + pipeline */}
        <Card>
          <CardContent className="pt-5">
            <div className="grid grid-cols-2 gap-x-8 gap-y-5">
              <StatBlock
                label="Memories"
                value={counts?.memories ?? "—"}
                delta={todayCount}
              />
              <StatBlock label="Tags" value={counts?.tags ?? "—"} />
              <StatBlock label="Entities" value={counts?.entities ?? "—"} />
              <StatBlock
                label="Relations"
                value={counts?.relationships ?? "—"}
              />
            </div>
            <div className="border-border mt-4 border-t pt-3">
              <PipelineHealth recentErrors={data?.recent_errors ?? 0} />
            </div>
          </CardContent>
        </Card>

        {/* Right: activity chart */}
        <Card>
          <CardHeader className="flex-row items-center justify-between pb-2">
            <CardTitle className="text-muted-foreground text-sm font-medium tracking-wider uppercase">
              Activity
            </CardTitle>
            <div className="flex gap-1">
              <Button
                variant={days === 7 ? "secondary" : "ghost"}
                className="h-6 px-2"
                onClick={() => setDays(7)}
              >
                7d
              </Button>
              <Button
                variant={days === 30 ? "secondary" : "ghost"}
                className="h-6 px-2"
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
                  <XAxis
                    dataKey="label"
                    tick={{ fill: "#8b949e", fontSize: 11 }}
                  />
                  <YAxis
                    tick={{ fill: "#8b949e", fontSize: 11 }}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#161b22",
                      border: "1px solid #21262d",
                      color: "#c9d1d9",
                      fontSize: 13,
                    }}
                  />
                  <Bar dataKey="count" fill="#58a6ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-muted-foreground py-8 text-center text-sm">
                No activity data yet
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Desktop: sources | tags */}
      <div className="hidden grid-cols-2 gap-4 lg:grid">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-muted-foreground text-sm font-medium tracking-wider uppercase">
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
                        fontSize: 13,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="min-w-0 flex-1 space-y-1.5">
                  {data.sources.map((s, i) => (
                    <div
                      key={s.name}
                      className="flex items-center gap-2 text-sm"
                    >
                      <span
                        className="h-2 w-2 shrink-0 rounded-full"
                        style={{ backgroundColor: sourceColor(s.name, i) }}
                      />
                      <span className="truncate">{s.name}</span>
                      <span className="text-muted-foreground ml-auto">
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
            <CardTitle className="text-muted-foreground text-sm font-medium tracking-wider uppercase">
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
                    tick={{ fill: "#8b949e", fontSize: 11 }}
                    allowDecimals={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={100}
                    tick={(props: YAxisTickContentProps) => {
                      const value = String(props.payload.value)
                      const label =
                        value.length > 14 ? value.slice(0, 13) + "…" : value
                      return (
                        <text
                          x={props.x}
                          y={props.y}
                          dy={4}
                          textAnchor="end"
                          fill="#c9d1d9"
                          fontSize={12}
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
                      fontSize: 13,
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
          <CardTitle className="text-muted-foreground text-sm font-medium tracking-wider uppercase">
            Recent Memories
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data?.recent_memories?.length ? (
            <div className="space-y-1.5">
              {data.recent_memories.map((m) => (
                <div
                  key={m.id}
                  role="button"
                  tabIndex={0}
                  className="border-border hover:bg-accent/50 flex cursor-pointer items-center gap-3 rounded-md border p-2 transition-colors"
                  onClick={() =>
                    navigate({ to: "/memories", search: { focus: m.id } })
                  }
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault()
                      navigate({ to: "/memories", search: { focus: m.id } })
                    }
                  }}
                >
                  <span className="flex-1 truncate text-sm">{m.content}</span>
                  <Badge variant="secondary" className="shrink-0">
                    {m.source}
                  </Badge>
                  <span className="text-muted-foreground shrink-0 text-sm">
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
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4 lg:hidden">
        <Card>
          <CardContent className="pt-4">
            <StatBlock
              label="Memories"
              value={counts?.memories ?? "—"}
              delta={todayCount}
            />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <StatBlock label="Tags" value={counts?.tags ?? "—"} />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <StatBlock label="Entities" value={counts?.entities ?? "—"} />
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <StatBlock label="Relations" value={counts?.relationships ?? "—"} />
          </CardContent>
        </Card>
      </div>

      <Card className="lg:hidden">
        <CardContent className="pt-4">
          <PipelineHealth recentErrors={data?.recent_errors ?? 0} />
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-[3fr_2fr] lg:hidden">
        <Card>
          <CardHeader className="flex-row items-center justify-between pb-2">
            <CardTitle className="text-muted-foreground text-sm font-medium tracking-wider uppercase">
              Activity
            </CardTitle>
            <div className="flex gap-1">
              <Button
                variant={days === 7 ? "secondary" : "ghost"}
                className="h-6 px-2"
                onClick={() => setDays(7)}
              >
                7d
              </Button>
              <Button
                variant={days === 30 ? "secondary" : "ghost"}
                className="h-6 px-2"
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
                  <XAxis
                    dataKey="label"
                    tick={{ fill: "#8b949e", fontSize: 11 }}
                  />
                  <YAxis
                    tick={{ fill: "#8b949e", fontSize: 11 }}
                    allowDecimals={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: "#161b22",
                      border: "1px solid #21262d",
                      color: "#c9d1d9",
                      fontSize: 13,
                    }}
                  />
                  <Bar dataKey="count" fill="#58a6ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-muted-foreground py-8 text-center text-sm">
                No activity data yet
              </p>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-muted-foreground text-sm font-medium tracking-wider uppercase">
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
                        fontSize: 13,
                      }}
                    />
                  </PieChart>
                </ResponsiveContainer>
                <div className="min-w-0 flex-1 space-y-1.5">
                  {data.sources.map((s, i) => (
                    <div
                      key={s.name}
                      className="flex items-center gap-2 text-sm"
                    >
                      <span
                        className="h-2 w-2 shrink-0 rounded-full"
                        style={{ backgroundColor: sourceColor(s.name, i) }}
                      />
                      <span className="truncate">{s.name}</span>
                      <span className="text-muted-foreground ml-auto">
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
          <CardTitle className="text-muted-foreground text-sm font-medium tracking-wider uppercase">
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
                  tick={{ fill: "#8b949e", fontSize: 11 }}
                  allowDecimals={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  tick={{ fill: "#c9d1d9", fontSize: 12 }}
                  width={70}
                />
                <Tooltip
                  contentStyle={{
                    background: "#161b22",
                    border: "1px solid #21262d",
                    color: "#c9d1d9",
                    fontSize: 13,
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
          <CardTitle className="text-muted-foreground text-sm font-medium tracking-wider uppercase">
            Recent Memories
          </CardTitle>
        </CardHeader>
        <CardContent>
          {data?.recent_memories?.length ? (
            <div className="space-y-1.5">
              {data.recent_memories.map((m) => (
                <div
                  key={m.id}
                  role="button"
                  tabIndex={0}
                  className="border-border hover:bg-accent/50 flex cursor-pointer items-center gap-3 rounded-md border p-2 transition-colors"
                  onClick={() =>
                    navigate({ to: "/memories", search: { focus: m.id } })
                  }
                  onKeyDown={(e) => {
                    if (e.key === "Enter" || e.key === " ") {
                      e.preventDefault()
                      navigate({ to: "/memories", search: { focus: m.id } })
                    }
                  }}
                >
                  <span className="flex-1 truncate text-sm">{m.content}</span>
                  <Badge variant="secondary" className="shrink-0">
                    {m.source}
                  </Badge>
                  <span className="text-muted-foreground shrink-0 text-sm">
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
