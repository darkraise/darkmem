import { useStats, useMemories } from "@/hooks/useApi";
import { MemoryCard } from "@/components/MemoryCard";

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="text-3xl font-bold mt-1">{value}</div>
      {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
    </div>
  );
}

export default function Overview() {
  const { data: stats } = useStats();
  const { data: memories } = useMemories();

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Overview</h2>
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard label="Memories" value={stats?.memories ?? "—"} />
        <StatCard label="Tags" value={stats?.tags ?? "—"} />
        <StatCard label="Entities" value={stats?.entities ?? "—"} />
        <StatCard label="Relations" value={stats?.relationships ?? "—"} />
      </div>
      <h3 className="text-lg font-medium mb-3">Recent Memories</h3>
      <div className="space-y-3">
        {memories?.slice(0, 10).map((m) => <MemoryCard key={m.id} memory={m} />)}
        {!memories?.length && <p className="text-muted-foreground">No memories yet.</p>}
      </div>
    </div>
  );
}
