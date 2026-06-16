import { useCallback, useEffect, useRef, useState } from "react"
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
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
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
import { toast } from "darkraise-ui/components/sonner"

function ServiceDot({ ok }: { ok: boolean }) {
  const label = ok ? "online" : "offline"
  return (
    <span className="inline-flex items-center">
      <span
        className={`inline-block h-2 w-2 rounded-full ${ok ? "bg-green-500" : "bg-red-500"}`}
        role="img"
        aria-label={label}
      />
      <span className="sr-only">{label}</span>
    </span>
  )
}

function StatusBadge({ value }: { value: string }) {
  const variant =
    value === "ok" ? "default" : value === "error" ? "destructive" : "secondary"
  return (
    <Badge variant={variant}>
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
    <div className="bg-muted/30 space-y-2 rounded-lg border p-3">
      <div className="flex items-center justify-between text-sm">
        <span className="font-medium">{label}</span>
        <span className="text-muted-foreground tabular-nums">
          {progress.current} / {progress.total}
        </span>
      </div>
      <Progress value={pct} />
      <div className="text-muted-foreground flex gap-3 text-sm">
        <span className="text-green-500">{progress.processed} succeeded</span>
        {progress.errors > 0 && (
          <span className="text-destructive">{progress.errors} failed</span>
        )}
        {progress.memoryId && (
          <span className="ml-auto font-mono">
            {progress.memoryId.slice(0, 8)}...
          </span>
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
  const { data: failuresData } = usePipelineFailures({
    pipeline_name: pipelineName,
  })
  const { data: counts } = usePipelineFailureCounts()
  const retry = useRetryFailure()
  const forget = useForgetFailure()
  const retryAll = useRetryAllFailures()
  const { data: batchProgress } = useRetryBatchProgress(activeBatchId)

  const totalCount = counts
    ? Object.values(counts).reduce((a, b) => a + b, 0)
    : 0
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
    retryAll.mutate(filter === "all" ? undefined : { pipeline_name: filter }, {
      onSuccess: (data) => {
        if (data.total === 0) {
          toast.info("No unresolved failures to retry")
          return
        }
        setActiveBatchId(data.batch_id)
        toast.info(`Retrying ${data.total} failures...`)
      },
      onError: () => toast.error("Bulk retry failed to dispatch"),
    })
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
      <CardHeader className="bg-foreground/5 rounded-t-[calc(var(--radius)-1px)] border-border border-b pb-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-lg uppercase tracking-wide">
            Unresolved Failures
          </CardTitle>
          <Button
            variant="outline"
            onClick={handleRetryAll}
            disabled={
              retryAll.isPending || activeBatchId !== null || totalCount === 0
            }
          >
            {activeBatchId !== null ? "Retrying..." : "Retry all"}
          </Button>
        </div>
        <CardDescription>
          Memories and repos that failed or degraded during processing. Retry
          to reprocess just these; a clean run clears the entry automatically.
        </CardDescription>
        <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div className="border-border flex w-fit flex-wrap gap-1 rounded-md border p-0.5">
            <Button
              variant="ghost"
              onClick={() => setFilter("all")}
              className={`rounded px-3 py-1 font-medium transition-colors ${
                filter === "all"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              All ({totalCount})
            </Button>
            <Button
              variant="ghost"
              onClick={() => setFilter("memory_ingest")}
              className={`rounded px-3 py-1 font-medium transition-colors ${
                filter === "memory_ingest"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Memory ({memoryCount})
            </Button>
            <Button
              variant="ghost"
              onClick={() => setFilter("code_index")}
              className={`rounded px-3 py-1 font-medium transition-colors ${
                filter === "code_index"
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              Code ({codeCount})
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="pt-4">
        {batchProgress &&
          activeBatchId !== null &&
          batchProgress.state !== "done" && (
            <div className="bg-muted/30 mb-4 space-y-2 rounded-lg border p-3">
              <div className="flex items-center justify-between text-sm">
                <span className="font-medium">Retrying failures...</span>
                <span className="text-muted-foreground tabular-nums">
                  {batchProgress.current} / {batchProgress.total}
                </span>
              </div>
              <Progress
                value={
                  batchProgress.total > 0
                    ? (batchProgress.current / batchProgress.total) * 100
                    : 0
                }
              />
              <div className="text-muted-foreground flex gap-3 text-sm">
                <span className="text-green-500">
                  {batchProgress.processed} succeeded
                </span>
                {batchProgress.errors > 0 && (
                  <span className="text-destructive">
                    {batchProgress.errors} failed
                  </span>
                )}
              </div>
            </div>
          )}

        {items.length === 0 && (
          <p className="text-muted-foreground py-4 text-center text-sm">
            No unresolved failures
          </p>
        )}

        {items.length > 0 && (
          <div className="divide-border border-border divide-y rounded-md border">
            {items.map((f) => {
              const isRetrying = retryingIds.has(f.id)
              return (
                <div key={f.id} className="space-y-2 p-3">
                  <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-sm">
                      <Badge variant="outline">{f.entity_type}</Badge>
                      {f.failed_step === "extraction_partial" && (
                        <Badge
                          variant="outline"
                          className="border-warning/40 bg-warning/10 text-warning"
                        >
                          degraded
                        </Badge>
                      )}
                      <span className="text-muted-foreground font-mono">
                        {f.failed_step}
                      </span>
                      <span className="text-muted-foreground">
                        · {f.attempts} attempts
                      </span>
                    </div>
                    <div className="flex gap-1">
                      <Button
                        variant="outline"
                        onClick={() => handleRetry(f.id)}
                        disabled={isRetrying || retry.isPending}
                      >
                        {isRetrying ? "Retrying..." : "Retry"}
                      </Button>
                      <Button
                        variant="ghost"
                        onClick={() => handleForget(f.id)}
                        disabled={forget.isPending}
                      >
                        Forget
                      </Button>
                    </div>
                  </div>
                  {f.entity_preview && (
                    <p className="text-foreground line-clamp-1 text-sm">
                      {f.entity_preview}
                    </p>
                  )}
                  {f.error_message && (
                    <p className="text-destructive line-clamp-2 text-sm">
                      {f.error_message}
                    </p>
                  )}
                  <p className="text-muted-foreground text-sm">
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
  onDone,
}: {
  batchId: string | null
  category: ReembedCategory
  onDone?: (category: ReembedCategory) => void
}) {
  const { data: progress } = useReembedBatchProgress(batchId, category)
  const isDone = progress?.state === "done"
  // Clear the parent's running state when the batch finishes; otherwise
  // batchIds[category] never resets and every re-embed button stays disabled
  // until a full page reload.
  useEffect(() => {
    if (batchId && isDone && onDone) {
      const timer = setTimeout(() => onDone(category), 2000)
      return () => clearTimeout(timer)
    }
  }, [batchId, isDone, onDone, category])
  if (!progress || progress.state === "done") return null
  const pct = progress.total > 0 ? (progress.current / progress.total) * 100 : 0
  return (
    <div className="mt-2 space-y-1">
      <Progress value={pct} />
      <p className="text-muted-foreground text-sm">
        {progress.current} / {progress.total}
        {progress.errors > 0 && (
          <span className="text-destructive ml-2">
            ({progress.errors} errors)
          </span>
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

  const [batchIds, setBatchIds] = useState<
    Record<ReembedCategory, string | null>
  >({
    memories: null,
    code_chunks: null,
    entities: null,
  })

  const clearCategory = useCallback((category: ReembedCategory) => {
    setBatchIds((prev) => ({ ...prev, [category]: null }))
  }, [])

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
      onError: (err) =>
        toast.error(`Re-embed ${category} failed: ${(err as Error).message}`),
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
      onError: (err) =>
        toast.error(`Re-embed all failed: ${(err as Error).message}`),
    })
  }

  const handlePruneCache = () => {
    pruneCache.mutate(undefined, {
      onSuccess: (data) =>
        toast.success(`Pruned ${data.deleted} old cache entries`),
      onError: (err) => toast.error(`Prune failed: ${(err as Error).message}`),
    })
  }

  return (
    <Card>
      <CardHeader className="bg-foreground/5 rounded-t-[calc(var(--radius)-1px)] border-border border-b pb-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <CardTitle className="text-lg uppercase tracking-wide">
            Obsolete Embeddings
          </CardTitle>
          <div className="flex flex-wrap gap-2">
            <Button
              variant="outline"
              onClick={handleReembedAll}
              disabled={
                reembedAll.isPending || anyRunning || totalObsolete === 0
              }
            >
              Re-embed all obsolete
            </Button>
            <Button
              variant="ghost"
              onClick={handlePruneCache}
              disabled={pruneCache.isPending}
            >
              Prune old cache entries
            </Button>
          </div>
        </div>
        <CardDescription className="font-mono">
          Current: {counts.current_fingerprint}
        </CardDescription>
      </CardHeader>
      <CardContent className="pt-4">
        <div className="divide-border border-border divide-y rounded-md border">
          <div className="flex items-center justify-between px-3 py-2">
            <div className="flex-1">
              <span className="text-sm font-medium">Memories</span>
              <p className="text-muted-foreground text-sm">
                {counts.memories} obsolete
              </p>
              <CategoryProgressBar
                batchId={batchIds.memories}
                category="memories"
                onDone={clearCategory}
              />
            </div>
            <Button
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
              <p className="text-muted-foreground text-sm">
                {counts.entities} obsolete
              </p>
              <CategoryProgressBar
                batchId={batchIds.entities}
                category="entities"
                onDone={clearCategory}
              />
            </div>
            <Button
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
              <p className="text-muted-foreground text-sm">
                {counts.code_chunks} obsolete
              </p>
              <CategoryProgressBar
                batchId={batchIds.code_chunks}
                category="code_chunks"
                onDone={clearCategory}
              />
            </div>
            <Button
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

export function MaintenancePanel() {
  const { data: health } = useHealth()
  const { data: logs, isLoading, isError, error } = usePipelineLogs(50)
  const reprocessAll = useReprocessStream("/analytics/reprocess/stream")

  const totalRuns = logs?.length ?? 0
  const successCount = logs?.filter((l) => !l.details?.error).length ?? 0
  const errorCount = totalRuns - successCount

  const prevAllPending = useRef(false)

  useEffect(() => {
    if (
      prevAllPending.current &&
      !reprocessAll.isPending &&
      reprocessAll.progress
    ) {
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
    <div>
      <div className="mb-4 flex items-center justify-end gap-2">
        <AlertDialog>
          <AlertDialogTrigger asChild>
            <Button variant="outline" disabled={anyPending}>
              {reprocessAll.isPending ? "Reprocessing..." : "Reprocess All"}
            </Button>
          </AlertDialogTrigger>
          <AlertDialogContent>
            <AlertDialogHeader>
              <AlertDialogTitle>Reprocess all memories?</AlertDialogTitle>
              <AlertDialogDescription>
                This will re-run embedding, extraction, and graph steps for
                every memory in the database. On large collections this can take
                several minutes.
              </AlertDialogDescription>
            </AlertDialogHeader>
            <AlertDialogFooter>
              <AlertDialogCancel>Cancel</AlertDialogCancel>
              <AlertDialogAction onClick={handleReprocessAll}>
                Reprocess
              </AlertDialogAction>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialog>
        {reprocessAll.isPending && (
          <Button variant="ghost" onClick={() => reprocessAll.cancel()}>
            Cancel
          </Button>
        )}
      </div>

      <div className="mb-6">
        <ObsoleteEmbeddingsCard />
      </div>

      <div className="mb-6">
        <UnresolvedFailuresCard />
      </div>

      <ReprocessProgress
        label="Reprocessing all memories..."
        stream={reprocessAll}
      />
      {reprocessAll.isPending && <div className="mb-6" />}

      <div className="mb-6 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-4">
            <div className="mb-1 flex items-center gap-2">
              <ServiceDot ok={!!health?.pipeline} />
              <span className="text-muted-foreground text-sm font-medium tracking-wider uppercase">
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
            <div className="text-muted-foreground mt-2 text-sm">
              Service Health
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div className="text-2xl font-bold text-green-500">
              {successCount}
            </div>
            <div className="text-muted-foreground text-sm">
              Successful Runs
            </div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-4">
            <div
              className={`text-2xl font-bold ${errorCount > 0 ? "text-destructive" : "text-muted-foreground"}`}
            >
              {errorCount}
            </div>
            <div className="text-muted-foreground text-sm">
              Failed / Partial
            </div>
          </CardContent>
        </Card>
      </div>

      <Card>
        <CardHeader className="bg-foreground/5 rounded-t-[calc(var(--radius)-1px)] border-border border-b pb-4">
          <CardTitle className="text-lg uppercase tracking-wide">
            Recent Pipeline Executions
          </CardTitle>
          <CardDescription>
            The latest pipeline runs and their per-step status.
          </CardDescription>
        </CardHeader>
        <CardContent className="pt-4">
          {isError && (
            <p className="text-destructive">
              Failed to load pipeline logs: {(error as Error).message}
            </p>
          )}
          {isLoading && (
            <p className="text-muted-foreground text-sm">Loading...</p>
          )}
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
                    className={`rounded-lg border p-3 text-sm ${hasError ? "border-destructive/30 bg-destructive/5" : "border-border"}`}
                  >
                    <div className="mb-2 flex items-center justify-between">
                      <span className="text-muted-foreground font-mono text-sm">
                        {log.memory_id?.slice(0, 8)}...
                      </span>
                      <span className="text-muted-foreground text-sm">
                        {new Date(log.timestamp).toLocaleString()}
                      </span>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="text-muted-foreground text-sm">
                        Embed:
                      </span>
                      <StatusBadge value={String(d.embed ?? "—")} />
                      <span className="text-muted-foreground text-sm">
                        Extract:
                      </span>
                      <StatusBadge value={String(d.extract ?? "—")} />
                      <span className="text-muted-foreground text-sm">
                        Vector:
                      </span>
                      <StatusBadge value={String(d.vector ?? "—")} />
                      <span className="text-muted-foreground text-sm">
                        Graph:
                      </span>
                      <StatusBadge value={String(d.graph ?? "—")} />
                      {(d.entities_count as number) > 0 && (
                        <span className="text-muted-foreground ml-2 text-sm">
                          {String(d.entities_count)} entities,{" "}
                          {String(d.relations_count)} relations
                        </span>
                      )}
                    </div>
                    {hasError && (
                      <p className="text-destructive mt-2 text-sm">
                        {String(d.error)}
                      </p>
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
