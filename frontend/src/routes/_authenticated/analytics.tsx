import { useMemo } from "react"
import { createFileRoute } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import { DataTable, DataTableSkeleton } from "darkraise-ui/data-table"
import { useStats, useTags, useMemories, usePipelineLogs } from "@/hooks/api"
import type { PipelineLog } from "@/hooks/api"
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
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { PageHeader } from "darkraise-ui/layout"

export const Route = createFileRoute("/_authenticated/analytics")({
  component: AnalyticsPage,
})

const COLORS = [
  "#58a6ff",
  "#3fb950",
  "#d2a8ff",
  "#ffa657",
  "#f778ba",
  "#8b949e",
]

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

function StatTile({
  label,
  value,
}: {
  label: string
  value: string | number | null
}) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="text-muted-foreground text-xs font-medium tracking-wider uppercase">
          {label}
        </div>
        <div className="mt-1 text-3xl font-bold">{value ?? "—"}</div>
      </CardContent>
    </Card>
  )
}

const logColumns: ColumnDef<PipelineLog>[] = [
  {
    accessorKey: "id",
    header: "ID",
    size: 70,
    cell: ({ getValue }) => (
      <span className="text-muted-foreground font-mono text-xs">
        {String(getValue())}
      </span>
    ),
  },
  {
    accessorKey: "memory_id",
    header: "Memory",
    size: 200,
    cell: ({ getValue }) => {
      const v = getValue()
      if (!v) return <span className="text-muted-foreground text-xs">—</span>
      return (
        <span
          className="block max-w-[180px] truncate font-mono text-xs"
          title={String(v)}
        >
          {String(v).slice(0, 8)}…
        </span>
      )
    },
  },
  {
    accessorKey: "timestamp",
    header: "Time",
    size: 130,
    cell: ({ getValue }) => (
      <span className="text-muted-foreground text-xs">
        {relativeTime(String(getValue()))}
      </span>
    ),
  },
  {
    accessorKey: "details",
    header: "Details",
    cell: ({ getValue }) => (
      <span className="text-muted-foreground block max-w-[400px] truncate font-mono text-xs">
        {JSON.stringify(getValue())}
      </span>
    ),
  },
]

function AnalyticsPage() {
  const { data: stats } = useStats()
  const { data: tags } = useTags()
  const { data: memories } = useMemories()
  const { data: logs, isLoading: logsLoading } = usePipelineLogs(20)

  const tagData =
    tags?.slice(0, 10).map((t) => ({ name: t.name, count: t.memory_count })) ??
    []

  const sourceData = useMemo(() => {
    if (!memories) return []
    const counts = new Map<string, number>()
    for (const m of memories)
      counts.set(m.source, (counts.get(m.source) ?? 0) + 1)
    return Array.from(counts.entries()).map(([name, value]) => ({
      name,
      value,
    }))
  }, [memories])

  return (
    <div className="space-y-6 p-6">
      <PageHeader
        title="Analytics"
        description="Tag and source trends. Pipeline and extraction metrics live on the Pipeline page."
      />

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatTile label="Memories" value={stats?.memories ?? null} />
        <StatTile label="Tags" value={stats?.tags ?? null} />
        <StatTile label="Entities" value={stats?.entities ?? null} />
        <StatTile label="Relationships" value={stats?.relationships ?? null} />
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">
              Top Tags by Memory Count
            </CardTitle>
          </CardHeader>
          <CardContent>
            {tagData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={tagData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                  <XAxis
                    dataKey="name"
                    tick={{ fill: "#8b949e", fontSize: 10 }}
                    angle={-45}
                    textAnchor="end"
                    height={80}
                  />
                  <YAxis tick={{ fill: "#8b949e" }} />
                  <Tooltip
                    contentStyle={{
                      background: "#161b22",
                      border: "1px solid #21262d",
                      color: "#c9d1d9",
                    }}
                  />
                  <Bar dataKey="count" fill="#58a6ff" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-muted-foreground text-sm">No tag data yet.</p>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Sources</CardTitle>
          </CardHeader>
          <CardContent>
            {sourceData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={sourceData}
                    dataKey="value"
                    nameKey="name"
                    cx="50%"
                    cy="50%"
                    outerRadius={100}
                    label={(e) => e.name}
                  >
                    {sourceData.map((_, i) => (
                      <Cell key={i} fill={COLORS[i % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: "#161b22",
                      border: "1px solid #21262d",
                      color: "#c9d1d9",
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <p className="text-muted-foreground text-sm">
                No source data yet.
              </p>
            )}
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium">
            Recent Pipeline Activity
          </CardTitle>
        </CardHeader>
        <CardContent className="p-0">
          {logsLoading ? (
            <DataTableSkeleton columnCount={4} rowCount={5} />
          ) : !logs || logs.length === 0 ? (
            <p className="text-muted-foreground p-4 text-sm">
              No pipeline activity yet.
            </p>
          ) : (
            <DataTable columns={logColumns} data={logs} />
          )}
        </CardContent>
      </Card>
    </div>
  )
}
