import { useStats, useMemories, useHealth, usePipelineLogs } from "@/hooks/useApi";
import { MemoryCard } from "@/components/MemoryCard";
import { ServiceDot } from "@/components/ServiceDot";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <Card>
      <CardHeader className="pb-1">
        <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">{label}</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="text-3xl font-bold">{value}</div>
        {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
      </CardContent>
    </Card>
  );
}

export default function Overview() {
  const { data: stats } = useStats();
  const { data: memories } = useMemories();
  const { data: health } = useHealth();
  const { data: logs } = usePipelineLogs(5);

  const recentErrors = logs?.filter((l) => l.details?.error).length ?? 0;

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-4">Overview</h2>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <StatCard label="Memories" value={stats?.memories ?? "—"} />
        <StatCard label="Tags" value={stats?.tags ?? "—"} />
        <StatCard label="Entities" value={stats?.entities ?? "—"} />
        <StatCard label="Relations" value={stats?.relationships ?? "—"} />
      </div>

      {health && (
        <Card className="mb-6">
          <CardHeader className="pb-1">
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Pipeline Status</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-6 text-sm">
              <div className="flex items-center gap-2">
                <ServiceDot ok={health.pipeline} />
                <span className={health.pipeline ? "text-foreground" : "text-destructive"}>
                  {health.pipeline ? "Active" : "Inactive"}
                </span>
              </div>
              <div className="flex items-center gap-4 text-muted-foreground">
                <span className="flex items-center gap-1.5">
                  <ServiceDot ok={health.services.qdrant} /> Qdrant
                </span>
                <span className="flex items-center gap-1.5">
                  <ServiceDot ok={health.services.neo4j} /> Neo4j
                </span>
                <span className="flex items-center gap-1.5">
                  <ServiceDot ok={health.services.llm} /> LLM
                </span>
              </div>
              {recentErrors > 0 && (
                <span className="text-destructive text-xs">
                  {recentErrors} error{recentErrors > 1 ? "s" : ""} in last {logs?.length} runs
                </span>
              )}
            </div>
          </CardContent>
        </Card>
      )}

      <h3 className="text-lg font-medium mb-3">Recent Memories</h3>
      <div className="space-y-3">
        {memories?.slice(0, 10).map((m) => <MemoryCard key={m.id} memory={m} />)}
        {!memories?.length && <p className="text-muted-foreground">No memories yet.</p>}
      </div>
    </div>
  );
}
