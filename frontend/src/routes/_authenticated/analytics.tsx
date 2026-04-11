import { useMemo } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { useStats, useTags, useMemories } from "@/hooks/api"
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
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import { PageHeader } from "darkraise-ui/layout"

export const Route = createFileRoute("/_authenticated/analytics")({
  component: AnalyticsPage,
})

const COLORS = ["#58a6ff", "#3fb950", "#d2a8ff", "#ffa657", "#f778ba", "#8b949e"]

function AnalyticsPage() {
  useStats()
  const { data: tags } = useTags()
  const { data: memories } = useMemories()

  const tagData =
    tags?.slice(0, 10).map((t) => ({ name: t.name, count: t.memory_count })) ?? []

  const sourceData = useMemo(() => {
    if (!memories) return []
    const counts = new Map<string, number>()
    for (const m of memories) counts.set(m.source, (counts.get(m.source) ?? 0) + 1)
    return Array.from(counts.entries()).map(([name, value]) => ({ name, value }))
  }, [memories])

  return (
    <div className="p-6">
      <PageHeader
        title="Analytics"
        description="Tag and source trends. Pipeline and extraction metrics live on the Pipeline page."
      />

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Top Tags by Memory Count</CardTitle>
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
              <p className="text-muted-foreground text-sm">No source data yet.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
