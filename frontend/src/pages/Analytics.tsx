import { useStats, useTags } from "@/hooks/useApi";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, PieChart, Pie, Cell } from "recharts";

const COLORS = ["#58a6ff", "#3fb950", "#d2a8ff", "#ffa657", "#f778ba", "#8b949e"];

export default function Analytics() {
  const { data: stats } = useStats();
  const { data: tags } = useTags();

  const tagData = tags?.slice(0, 10).map((t) => ({ name: t.name, count: t.memory_count })) ?? [];
  const sourceData = stats?.sources.map((s) => ({ name: s, value: 1 })) ?? [];

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Analytics</h2>
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-lg p-4">
          <h3 className="text-sm font-medium mb-4">Top Tags by Memory Count</h3>
          {tagData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={tagData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                <XAxis dataKey="name" tick={{ fill: "#8b949e", fontSize: 10 }} angle={-45} textAnchor="end" height={80} />
                <YAxis tick={{ fill: "#8b949e" }} />
                <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #21262d", color: "#c9d1d9" }} />
                <Bar dataKey="count" fill="#58a6ff" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-muted-foreground text-sm">No tag data yet.</p>}
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <h3 className="text-sm font-medium mb-4">Sources</h3>
          {sourceData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={sourceData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label={(e) => e.name}>
                  {sourceData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #21262d", color: "#c9d1d9" }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-muted-foreground text-sm">No source data yet.</p>}
        </div>
      </div>
    </div>
  );
}
