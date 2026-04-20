import { useEffect, useRef, useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import {
  usePipelineLogs,
  useHealth,
  useReprocessStream,
  usePipelineFailures,
  usePipelineFailureCounts,
  useRetryFailure,
  useForgetFailure,
  useRetryAllFailures,
  useRetryBatchProgress,
  useObsoleteCounts,
  useReembedMemories,
  useReembedCodeChunks,
  useReembedEntities,
  useReembedAll,
  usePruneObsoleteCache,
  useReembedBatchProgress,
} from "@/hooks/api"
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Progress } from "darkraise-ui/components/progress"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from "darkraise-ui/components/alert-dialog"
import { PageHeader } from "darkraise-ui/layout"
import { toast } from "sonner"

export const Route = createFileRoute("/_authenticated/reindex")({
  component: PipelinePage,
})

function ServiceDot({ ok }: { ok: boolean }) {
  return (
    <span
      className={`inline-block w-2 h-2 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`}
    />
  )
}

function StatusBadge({ value }: { value: string }) {
  const variant =
    value === "ok" ? "default" : value === "error" ? "destructive" : "secondary"
  return (
    <Badge variant={variant} className="text-xs">
      {value}
    </Badge>
  )
}

function ReprocessProgress({
  label,
  stream,
}: {
  label: string
  stream: ReturnType<typeof useReprocessStream>
}) {
  const { progress, isPending } = stream
  if (!isPending || !progress) return null

  const pct = progress.total > 0 ? (progress.current / progress.total) * 100 : 0

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
        {progress.errors > 0 && (
          <span className="text-destructive">{progress.errors} failed</span>
        )}
        {progress.memoryId && (
          <span className="ml-auto font-mono">{progress.memoryId.slice(0, 8)}...</span>
        )}
      </div>
    </div>
  )
}

type FilterTab = "all" | "memory_ingest" | "code_index"

function UnresolvedFailuresCard() {
  const [filter, setFilter] = useState<FilterTab>("all")
  const [activeBatchId, setActiveBatchId] = useState<string | null>(null)
  const [retryingIds, setRetryingIds] = useState<Set<string>>(new Set())

  const pipelineName = filter === "all" ? undefined : filter
  const { data: failuresData } = usePipelineFailures({ pipeline_name: pipelineName })
  const { data: counts } = usePipelineFailureCounts()
  const retry = useRetryFailure()
  const forget = useForgetFailure()
  const retryAll = useRetryAllFailures()
  const { data: batchProgress } = useRetryBatchProgress(activeBatchId)

  const totalCount = counts ? Object.values(counts).reduce((a, b) => a + b, 0) : 0
  const memoryCount = counts?.memory_ingest ?? 0
  const codeCount = counts?.code_index ?? 0

  const handleRetry = (id: string) => {
    setRetryingIds((prev) => new Set(prev).add(id))
    retry.mutate(id, {
      onError: () => {
        setRetryingIds((prev) => {
          const next = new Set(prev)
          next.delete(id)
          return next
        })
        toast.error("Retry failed to dispatch")
      },
    })
  }

  const handleForget = (id: string) => {
    forget.mutate(id, {
      onError: () => toast.error("Forget failed"),
    })
  }

  const handleRetryAll = () => {
    retryAll.mutate(
      filter === "all" ? undefined : { pipeline_name: filter },
      {
        onSuccess: (data) => {
          if (data.total === 0) {
            toast.info("No unresolved failures to retry")
            return
          }
          setActiveBatchId(data.batch_id)
          toast.info(`Retrying ${data.total} failures...`)
        },
        onError: () => toast.error("Bulk retry failed to dispatch"),
      },
    )
  }

  useEffect(() => {
    if (batchProgress?.state === "done") {
      const timer = setTimeout(() => setActiveBatchId(null), 2000)
      return () => clearTimeout(timer)
    }
  }, [batchProgress?.state])

  const items = failuresData?.items ?? []

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Unresolved Failures</CardTitle>
          <Button
            variant="outline"
            size="sm"
            onClick={handleRetryAll}
            disabled={retryAll.isPending || activeBatchId !== null || totalCount === 0}
          >
            {activeBatchId !== null ? "Retrying..." : "Retry all"}
          </Button>
        </div>
        <div className="flex gap-1 mt-3 rounded-md border border-border p-0.5 w-fit">
          <button
            onClick={() => setFilter("all")}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              filter === "all"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            All ({totalCount})
          </button>
          <button
            onClick={() => setFilter("memory_ingest")}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              filter === "memory_ingest"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Memory ({memoryCount})
          </button>
          <button
            onClick={() => setFilter("code_index")}
            className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
              filter === "code_index"
                ? "bg-primary text-primary-foreground"
                : "text-muted-foreground hover:text-foreground"
            }`}
          >
            Code ({codeCount})
          </button>
        </div>
      </CardHeader>
      <CardContent>
        {batchProgress && activeBatchId !== null && batchProgress.state !== "done" && (
          <div className="mb-4 p-3 border rounded-lg bg-muted/30 space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Retrying failures...</span>
              <span className="text-muted-foreground tabular-nums">
                {batchProgress.current} / {batchProgress.total}
              </span>
            </div>
            <Progress value={batchProgress.total > 0 ? (batchProgress.current / batchProgress.total) * 100 : 0} />
            <div className="flex gap-3 text-xs text-muted-foreground">
              <span className="text-green-500">{batchProgress.processed} succeeded</span>
              {batchProgress.errors > 0 && (
                <span className="text-destructive">{batchProgress.errors} failed</span>
              )}
            </div>
          </div>
        )}

        {items.length === 0 && (
          <p className="text-muted-foreground text-sm py-4 text-center">
            No unresolved failures
          </p>
        )}

        {items.length > 0 && (
          <div className="divide-y divide-border rounded-md border border-border">
            {items.map((f) => {
              const isRetrying = retryingIds.has(f.id)
              return (
                <div key={f.id} className="p-3 space-y-2">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-xs">
                      <Badge variant="outline">{f.entity_type}</Badge>
                      <span className="font-mono text-muted-foreground">{f.failed_step}</span>
                      <span className="text-muted-foreground">· {f.attempts} attempts</span>
                    </div>
                    <div className="flex gap-1">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => handleRetry(f.id)}
                        disabled={isRetrying || retry.isPending}
                      >
                        {isRetrying ? "Retrying..." : "Retry"}
                      </Button>
                      <Button
                        size="sm"
                        variant="ghost"
                        onClick={() => handleForget(f.id)}
                        disabled={forget.isPending}
                      >
                        Forget
                      </Button>
                    </div>
                  </div>
                  {f.entity_preview && (
                    <p className="text-sm text-foreground line-clamp-1">{f.entity_preview}</p>
                  )}
                  {f.error_message && (
                    <p className="text-xs text-destructive line-clamp-2">{f.error_message}</p>
                  )}
                  <p className="text-xs text-muted-foreground">
                    Last attempt: {new Date(f.last_attempt_at).toLocaleString()}
                  </p>
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

type ReembedCategory = "memories" | "code_chunks" | "entities"

function CategoryProgressBar({
  batchId,
  category,
}: {
  batchId: string | null
  category: ReembedCategory
}) {
  const { data: progress } = useReembedBatchProgress(batchId, category)
  if (!progress || progress.state === "done") return null
  const pct = progress.total > 0 ? (progress.current / progress.total) * 100 : 0
  return (
    <div className="mt-2 space-y-1">
      <Progress value={pct} />
      <p className="text-xs text-muted-foreground">
        {progress.current} / {progress.total}
        {progress.errors > 0 && (
          <span className="text-destructive ml-2">({progress.errors} errors)</span>
        )}
      </p>
    </div>
  )
}

function ObsoleteEmbeddingsCard() {
  const { data: counts } = useObsoleteCounts()
  const reembedMemories = useReembedMemories()
  const reembedCodeChunks = useReembedCodeChunks()
  const reembedEntities = useReembedEntities()
  const reembedAll = useReembedAll()
  const pruneCache = usePruneObsoleteCache()

  const [batchIds, setBatchIds] = useState<Record<ReembedCategory, string | null>>({
    memories: null,
    code_chunks: null,
    entities: null,
  })

  if (!counts) return null

  const totalObsolete = counts.memories + counts.code_chunks + counts.entities
  const anyRunning =
    batchIds.memories !== null ||
    batchIds.code_chunks !== null ||
    batchIds.entities !== null

  if (totalObsolete === 0 && !anyRunning) return null

  const handleReembed = (
    category: ReembedCategory,
    mutation: typeof reembedMemories,
  ) => {
    mutation.mutate(undefined, {
      onSuccess: (data) => {
        if (data.total === 0) {
          toast.info(`No obsolete ${category}`)
          return
        }
        setBatchIds((prev) => ({ ...prev, [category]: data.batch_id }))
        toast.info(`Re-embedding ${data.total} ${category}...`)
      },
      onError: (err) => toast.error(`Re-embed ${category} failed: ${(err as Error).message}`),
    })
  }

  const handleReembedAll = () => {
    reembedAll.mutate(undefined, {
      onSuccess: (data) => {
        setBatchIds({
          memories: data.batch_id,
          code_chunks: data.batch_id,
          entities: data.batch_id,
        })
        toast.info(
          `Re-embedding all obsolete: ${data.totals.memories} memories, ${data.totals.entities} entities, ${data.totals.code_chunks} code chunks`,
        )
      },
      onError: (err) => toast.error(`Re-embed all failed: ${(err as Error).message}`),
    })
  }

  const handlePruneCache = () => {
    pruneCache.mutate(undefined, {
      onSuccess: (data) => toast.success(`Pruned ${data.deleted} old cache entries`),
      onError: (err) => toast.error(`Prune failed: ${(err as Error).message}`),
    })
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm">Obsolete Embeddings</CardTitle>
          <div className="flex gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={handleReembedAll}
              disabled={reembedAll.isPending || anyRunning || totalObsolete === 0}
            >
              Re-embed all obsolete
            </Button>
            <Button
              size="sm"
              variant="ghost"
              onClick={handlePruneCache}
              disabled={pruneCache.isPending}
            >
              Prune old cache entries
            </Button>
          </div>
        </div>
        <p className="text-muted-foreground text-xs font-mono mt-1">
          Current: {counts.current_fingerprint}
        </p>
      </CardHeader>
      <CardContent>
        <div className="divide-y divide-border rounded-md border border-border">
          <div className="flex items-center justify-between px-3 py-2">
            <div className="flex-1">
              <span className="text-sm font-medium">Memories</span>
              <p className="text-muted-foreground text-xs">
                {counts.memories} obsolete
              </p>
              <CategoryProgressBar
                batchId={batchIds.memories}
                category="memories"
              />
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleReembed("memories", reembedMemories)}
              disabled={
                reembedMemories.isPending ||
                batchIds.memories !== null ||
                counts.memories === 0
              }
            >
              Re-embed
            </Button>
          </div>
          <div className="flex items-center justify-between px-3 py-2">
            <div className="flex-1">
              <span className="text-sm font-medium">Entities</span>
              <p className="text-muted-foreground text-xs">
                {counts.entities} obsolete
              </p>
              <CategoryProgressBar
                batchId={batchIds.entities}
                category="entities"
              />
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleReembed("entities", reembedEntities)}
              disabled={
                reembedEntities.isPending ||
                batchIds.entities !== null ||
                counts.entities === 0
              }
            >
              Re-embed
            </Button>
          </div>
          <div className="flex items-center justify-between px-3 py-2">
            <div className="flex-1">
              <span className="text-sm font-medium">Code chunks</span>
              <p className="text-muted-foreground text-xs">
                {counts.code_chunks} obsolete
              </p>
              <CategoryProgressBar
                batchId={batchIds.code_chunks}
                category="code_chunks"
              />
            </div>
            <Button
              size="sm"
              variant="outline"
              onClick={() => handleReembed("code_chunks", reembedCodeChunks)}
              disabled={
                reembedCodeChunks.isPending ||
                batchIds.code_chunks !== null ||
                counts.code_chunks === 0
              }
            >
              Re-embed
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function PipelinePage() {
  const { data: health } = useHealth()
  const { data: logs, isLoading } = usePipelineLogs(50)
  const reprocessAll = useReprocessStream("/analytics/reprocess/stream")

  const totalRuns = logs?.length ?? 0
  const successCount = logs?.filter((l) => !l.details?.error).length ?? 0
  const errorCount = totalRuns - successCount

  const prevAllPending = useRef(false)

  useEffect(() => {
    if (prevAllPending.current && !reprocessAll.isPending && reprocessAll.progress) {
      const p = reprocessAll.progress
      if (p.errors > 0) {
        toast.success(`Reprocessed ${p.processed}/${p.total} memories`, {
          description: `${p.errors} errors`,
        })
      } else {
        toast.success(`Reprocessed ${p.processed}/${p.total} memories`)
      }
    }
    prevAllPending.current = reprocessAll.isPending
  }, [reprocessAll.isPending, reprocessAll.progress])

  const handleReprocessAll = () => {
    reprocessAll.mutate().catch(() => toast.error("Reprocess failed"))
  }

  const anyPending = reprocessAll.isPending

  return (
    <div className="p-6">
      <PageHeader title="Pipeline Logs" />

      <div className="flex items-center justify-end gap-2 mb-4">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline" size="sm" disabled={anyPending}>
              {reprocessAll.isPending ? "Reprocessing..." : "Reprocess All"}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Reprocess all memories?</AlertDialogTitle>
              <AlertDialogDescription>
                This will re-run embedding, extraction, and graph steps for every memory
                in the database. On large collections this can take several minutes.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleReprocessAll}>Reprocess</AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
      </div>

      <div className="mb-6">
        <ObsoleteEmbeddingsCard />
      </div>

      <div className="mb-6">
        <UnresolvedFailuresCard />
      </div>

      <ReprocessProgress label="Reprocessing all memories..." stream={reprocessAll} />
      {reprocessAll.isPending && <div className="mb-6" />}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-2 mb-1">
              <ServiceDot ok={!!health?.pipeline} />
              <span className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
                Pipeline
              </span>
            </div>
            <div className="text-2xl font-bold">
              {health?.pipeline ? "Active" : "Inactive"}
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="flex items-center gap-3 text-sm">
              <span className="flex items-center gap-1.5">
                <ServiceDot ok={!!health?.services.pgvector} /> pgvector
              </span>
              <span className="flex items-center gap-1.5">
                <ServiceDot ok={!!health?.services.llm} /> LLM
              </span>
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
            <div
              className={`text-2xl font-bold ${errorCount > 0 ? "text-destructive" : "text-muted-foreground"}`}
            >
              {errorCount}
            </div>
            <div className="text-xs text-muted-foreground">Failed / Partial</div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Recent Pipeline Executions</CardTitle>
        </CardHeader>
        <CardContent>
          {isLoading && <p className="text-muted-foreground text-sm">Loading...</p>}
          {!isLoading && !logs?.length && (
            <p className="text-muted-foreground text-sm">
              No pipeline logs yet. Create a memory to trigger the pipeline.
            </p>
          )}
          {logs && logs.length > 0 && (
            <div className="space-y-2">
              {logs.map((log) => {
                const d = log.details
                const hasError = !!d.error
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
                      <span className="text-xs text-muted-foreground">Vector:</span>
                      <StatusBadge value={String(d.vector ?? "—")} />
                      <span className="text-xs text-muted-foreground">Graph:</span>
                      <StatusBadge value={String(d.graph ?? "—")} />
                      {(d.entities_count as number) > 0 && (
                        <span className="text-xs text-muted-foreground ml-2">
                          {String(d.entities_count)} entities, {String(d.relations_count)}{" "}
                          relations
                        </span>
                      )}
                    </div>
                    {hasError && (
                      <p className="text-xs text-destructive mt-2">{String(d.error)}</p>
                    )}
                  </div>
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
