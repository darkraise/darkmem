import { usePipelineLogs, useHealth, useReprocessStream } from "@/hooks/useApi";
import { ServiceDot } from "@/components/ServiceDot";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Progress } from "@/components/ui/progress";
import { toast } from "sonner";
import { useEffect, useRef } from "react";

function StatusBadge({ value }: { value: string }) {
  const variant = value === "ok" ? "default" : value === "error" ? "destructive" : "secondary";
  return <Badge variant={variant} className="text-xs">{value}</Badge>;
}

function ReprocessProgress({ label, stream }: { label: string; stream: ReturnType<typeof useReprocessStream> }) {
  const { progress, isPending } = stream;
  if (!isPending || !progress) return null;

  const pct = progress.total > 0 ? (progress.current / progress.total) * 100 : 0;

  return (
    <div className="space-y-2 p-3 border rounded-lg bg-muted/30">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground tabular-nums">
          {progress.current} / {progress.total}
        </span>
      </div>
      <Progress value={pct} />
      <div className="flex gap-3 text-xs text-muted-foreground">
        <span className="text-green-500">{progress.processed} succeeded</span>
        {progress.errors > 0 && <span className="text-destructive">{progress.errors} failed</span>}
        {progress.memoryId && (
          <span className="ml-auto font-mono">{progress.memoryId.slice(0, 8)}...</span>
        )}
      </div>
    </div>
  );
}

export default function PipelineLogs() {
  const { data: health } = useHealth();
  const { data: logs, isLoading } = usePipelineLogs(50);
  const reprocessAll = useReprocessStream("/analytics/reprocess/stream");
  const reprocessFailed = useReprocessStream("/analytics/reprocess-failed/stream");

  const totalRuns = logs?.length ?? 0;
  const successCount = logs?.filter((l) => !l.details?.error).length ?? 0;
  const errorCount = totalRuns - successCount;

  const prevAllPending = useRef(false);
  const prevFailedPending = useRef(false);

  useEffect(() => {
    if (prevAllPending.current && !reprocessAll.isPending && reprocessAll.progress) {
      const p = reprocessAll.progress;
      if (p.errors > 0) {
        toast.success(`Reprocessed ${p.processed}/${p.total} memories`, { description: `${p.errors} errors` });
      } else {
        toast.success(`Reprocessed ${p.processed}/${p.total} memories`);
      }
    }
    prevAllPending.current = reprocessAll.isPending;
  }, [reprocessAll.isPending, reprocessAll.progress]);

  useEffect(() => {
    if (prevFailedPending.current && !reprocessFailed.isPending && reprocessFailed.progress) {
      const p = reprocessFailed.progress;
      if (p.total === 0) {
        toast.info("No failed entries to retry");
      } else if (p.errors > 0) {
        toast.success(`Retried ${p.processed}/${p.total} failed memories`, { description: `${p.errors} still failing` });
      } else {
        toast.success(`Retried ${p.processed}/${p.total} failed memories`);
      }
    }
    prevFailedPending.current = reprocessFailed.isPending;
  }, [reprocessFailed.isPending, reprocessFailed.progress]);

  const handleReprocessAll = () => {
    reprocessAll.mutate().catch(() => toast.error("Reprocess failed"));
  };

  const handleRetryFailed = () => {
    reprocessFailed.mutate().catch(() => toast.error("Retry failed"));
  };

  const anyPending = reprocessAll.isPending || reprocessFailed.isPending;

  return (
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Pipeline Logs</h2>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleRetryFailed}
            disabled={anyPending || errorCount === 0}
          >
            {reprocessFailed.isPending ? "Retrying..." : "Retry Failed"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleReprocessAll}
            disabled={anyPending}
          >
            {reprocessAll.isPending ? "Reprocessing..." : "Reprocess All"}
          </Button>
        </div>
      </div>

      {/* Progress display */}
      <ReprocessProgress label="Reprocessing all memories..." stream={reprocessAll} />
      <ReprocessProgress label="Retrying failed memories..." stream={reprocessFailed} />
      {(reprocessAll.isPending || reprocessFailed.isPending) && <div className="mb-6" />}

      {/* Status summary */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-1">
              <ServiceDot ok={!!health?.pipeline} />
              <span className="text-xs uppercase tracking-wider text-muted-foreground font-medium">Pipeline</span>
            </div>
            <div className="text-2xl font-bold">{health?.pipeline ? "Active" : "Inactive"}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3 text-sm">
              <span className="flex items-center gap-1.5"><ServiceDot ok={!!health?.services.qdrant} /> Qdrant</span>
              <span className="flex items-center gap-1.5"><ServiceDot ok={!!health?.services.neo4j} /> Neo4j</span>
              <span className="flex items-center gap-1.5"><ServiceDot ok={!!health?.services.llm} /> LLM</span>
            </div>
            <div className="text-xs text-muted-foreground mt-2">Service Health</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-green-500">{successCount}</div>
            <div className="text-xs text-muted-foreground">Successful Runs</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className={`text-2xl font-bold ${errorCount > 0 ? "text-destructive" : "text-muted-foreground"}`}>{errorCount}</div>
            <div className="text-xs text-muted-foreground">Failed / Partial</div>
          </CardContent>
        </Card>
      </div>

      {/* Log entries */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Recent Pipeline Executions</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <p className="text-muted-foreground text-sm">Loading...</p>}
          {!isLoading && !logs?.length && (
            <p className="text-muted-foreground text-sm">No pipeline logs yet. Create a memory to trigger the pipeline.</p>
          )}
          {logs && logs.length > 0 && (
            <div className="space-y-2">
              {logs.map((log) => {
                const d = log.details;
                const hasError = !!d.error;
                return (
                  <div
                    key={log.id}
                    className={`border rounded-lg p-3 text-sm ${hasError ? "border-destructive/30 bg-destructive/5" : "border-border"}`}
                  >
                    <div className="flex items-center justify-between mb-2">
                      <span className="font-mono text-xs text-muted-foreground">
                        {log.memory_id?.slice(0, 8)}...
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex items-center gap-2 flex-wrap">
                      <span className="text-xs text-muted-foreground">Embed:</span>
                      <StatusBadge value={String(d.embed ?? "—")} />
                      <span className="text-xs text-muted-foreground">Extract:</span>
                      <StatusBadge value={String(d.extract ?? "—")} />
                      <span className="text-xs text-muted-foreground">Qdrant:</span>
                      <StatusBadge value={String(d.qdrant ?? "—")} />
                      <span className="text-xs text-muted-foreground">Neo4j:</span>
                      <StatusBadge value={String(d.neo4j ?? "—")} />
                      {(d.entities_count as number) > 0 && (
                        <span className="text-xs text-muted-foreground ml-2">
                          {String(d.entities_count)} entities, {String(d.relations_count)} relations
                        </span>
                      )}
                    </div>
                    {hasError && (
                      <p className="text-xs text-destructive mt-2">{String(d.error)}</p>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
