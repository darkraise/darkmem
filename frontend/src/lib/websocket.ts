import { useEffect, useRef, useCallback } from "react"
import { useQueryClient } from "@tanstack/react-query"
import { toast } from "darkraise-ui/components/sonner"
import type { WebSocketEventMap, PipelineStatus } from "./websocket-events"
import { describeSkippedFiles } from "./websocket-events"

/**
 * Every query key any pipeline/memory/repo WebSocket event keeps fresh while
 * the socket is open. A dropped connection means broadcasts fired during the
 * gap were never delivered, so `onopen` after a reconnect invalidates this
 * whole set rather than only the keys a live event happens to name — without
 * it, a UI that reconnects silently keeps rendering pre-drop state with no
 * signal anything was missed.
 */
const RECONCILE_QUERY_KEYS: string[] = [
  "memories",
  "memory",
  "memoriesPaginated",
  "stats",
  "overview",
  "tags",
  "pipelineLogs",
  "pipelineFailures",
  "pipelineFailureCounts",
  "repos",
  "repoTasks",
  "repoStats",
]

function showPipelineToast(event: string, data: PipelineStatus) {
  const id = data.memory_id.slice(0, 8)

  if (event === "pipeline.completed") {
    toast.success(`Memory ${id} processed`, {
      description: `${data.entities_count} entities, ${data.relations_count} relations extracted`,
    })
  } else if (event === "pipeline.partial") {
    const failed = [
      data.embed === "error" && "embedding",
      data.extract === "error" && "extraction",
      data.vector === "error" && "vector store",
      data.graph === "error" && "graph store",
    ]
      .filter(Boolean)
      .join(", ")
    toast.warning(`Memory ${id} partially processed`, {
      description: `Failed: ${failed}`,
    })
  } else if (event === "pipeline.failed") {
    toast.error(`Memory ${id} processing failed`, {
      description: data.error || "All pipeline steps failed",
    })
  }
}

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null)
  const retryCount = useRef<number>(0)
  const closedByCaller = useRef<boolean>(false)
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const hasConnectedBefore = useRef<boolean>(false)
  const qc = useQueryClient()

  const connect = useCallback(() => {
    if (closedByCaller.current) return
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:"
    const url = `${protocol}//${window.location.host}/ws`
    ws.current = new WebSocket(url)

    ws.current.onmessage = (event) => {
      const msg = JSON.parse(event.data as string) as {
        [K in keyof WebSocketEventMap]?: {
          event: K
          data: WebSocketEventMap[K]
        }
      }[keyof WebSocketEventMap] & { event?: string; data?: unknown }

      if (!msg.event) return

      if (
        msg.event === "pipeline.completed" ||
        msg.event === "pipeline.partial" ||
        msg.event === "pipeline.failed"
      ) {
        showPipelineToast(msg.event, msg.data as PipelineStatus)
        void qc.invalidateQueries({ queryKey: ["memories"] })
        void qc.invalidateQueries({ queryKey: ["memory"] })
        void qc.invalidateQueries({ queryKey: ["memoriesPaginated"] })
        void qc.invalidateQueries({ queryKey: ["stats"] })
        void qc.invalidateQueries({ queryKey: ["overview"] })
        void qc.invalidateQueries({ queryKey: ["tags"] })
        void qc.invalidateQueries({ queryKey: ["pipelineLogs"] })
      } else if (
        msg.event === "memory.deleted" ||
        msg.event === "memory.bulk_deleted"
      ) {
        // A bulk delete emits one terminal memory.bulk_deleted instead of N
        // per-row memory.deleted events, so the cache invalidates once.
        void qc.invalidateQueries({ queryKey: ["memories"] })
        void qc.invalidateQueries({ queryKey: ["memory"] })
        void qc.invalidateQueries({ queryKey: ["memoriesPaginated"] })
        void qc.invalidateQueries({ queryKey: ["stats"] })
        void qc.invalidateQueries({ queryKey: ["overview"] })
        void qc.invalidateQueries({ queryKey: ["tags"] })
      }

      if (msg.event === "pipeline.failure.updated") {
        void qc.invalidateQueries({ queryKey: ["pipelineFailures"] })
        void qc.invalidateQueries({ queryKey: ["pipelineFailureCounts"] })
        const d = msg.data as WebSocketEventMap["pipeline.failure.updated"]
        if (d.state === "resolved") {
          toast.success(`${d.pipeline_name} retry resolved`)
        } else if (d.state === "recorded") {
          void qc.invalidateQueries({ queryKey: ["pipelineLogs"] })
        }
      }

      if (msg.event === "pipeline.retry_batch.progress") {
        const d = msg.data as WebSocketEventMap["pipeline.retry_batch.progress"]
        qc.setQueryData(["retryBatchProgress", d.batch_id], d)
        if (d.state === "done") {
          void qc.invalidateQueries({ queryKey: ["pipelineFailures"] })
          void qc.invalidateQueries({ queryKey: ["pipelineFailureCounts"] })
          void qc.invalidateQueries({ queryKey: ["stats"] })
          void qc.invalidateQueries({ queryKey: ["pipelineLogs"] })
        }
      }

      if (msg.event === "pipeline.reembed_batch.progress") {
        const d =
          msg.data as WebSocketEventMap["pipeline.reembed_batch.progress"]
        qc.setQueryData(["reembedBatchProgress", d.batch_id, d.category], d)
        if (d.state === "done") {
          void qc.invalidateQueries({ queryKey: ["obsoleteCounts"] })
          if (d.errors > 0) {
            toast.warning(
              `Re-embed ${d.category}: ${d.processed} succeeded, ${d.errors} failed`,
              {
                description: d.error_message || undefined,
              },
            )
          } else if (d.processed > 0) {
            toast.success(
              `Re-embed ${d.category} complete: ${d.processed} updated`,
            )
          }
        }
      }

      if (
        msg.event === "repo.clone_started" ||
        msg.event === "repo.clone_completed" ||
        msg.event === "repo.clone_failed" ||
        msg.event === "repo.indexing_started" ||
        msg.event === "repo.indexing_progress" ||
        msg.event === "repo.indexing_completed" ||
        msg.event === "repo.indexing_failed"
      ) {
        // repo.status_message is rewritten on every indexing-progress tick
        // (code_pipeline._update_status), so [repos] must refetch to show the
        // live phase label. But the task list and aggregate stats only change
        // at the terminal events, so refetching them on each of the ~13 phase
        // ticks per index is pure waste — skip them mid-progress.
        void qc.invalidateQueries({ queryKey: ["repos"] })
        if (msg.event !== "repo.indexing_progress") {
          void qc.invalidateQueries({ queryKey: ["repoTasks"] })
          void qc.invalidateQueries({ queryKey: ["repoStats"] })
        }

        if (msg.event === "repo.clone_completed") {
          const d = msg.data as WebSocketEventMap["repo.clone_completed"]
          toast.success(`Repository ${d.name} cloned`)
        } else if (msg.event === "repo.clone_failed") {
          const d = msg.data as WebSocketEventMap["repo.clone_failed"]
          toast.error(`Clone failed: ${d.error}`)
        } else if (msg.event === "repo.indexing_completed") {
          const d = msg.data as WebSocketEventMap["repo.indexing_completed"]
          const skipped = describeSkippedFiles(d)
          if (d.union_accepted !== undefined && d.files_changed === 0) {
            // A file-scoped run that indexed nothing is the outcome the bucket
            // reporting exists for, and "Indexed 0 files, 0 symbols" answers
            // the wrong question -- it reads as a failed run rather than as
            // "your files were already current". Lead with the disposition and
            // let the buckets say why. Missing or unindexable files are the
            // caller's problem to act on, so those warn; everything already up
            // to date is merely informational.
            const unresolved =
              (d.union_skipped_missing ?? 0) + (d.union_skipped_unindexable ?? 0)
            const notify = unresolved > 0 ? toast.warning : toast.info
            notify("Nothing to index", { description: skipped })
          } else {
            toast.success(
              `Indexed ${d.files_changed} files, ${d.symbols_indexed} symbols`,
              skipped ? { description: skipped } : undefined,
            )
          }
        } else if (msg.event === "repo.indexing_failed") {
          const d = msg.data as WebSocketEventMap["repo.indexing_failed"]
          toast.error(`Indexing failed: ${d.error}`)
        }
      }

      if (msg.event === "enrichment.batch_completed") {
        void qc.invalidateQueries({ queryKey: ["repoStats"] })
      }
    }

    ws.current.onopen = () => {
      if (hasConnectedBefore.current) {
        for (const key of RECONCILE_QUERY_KEYS) {
          void qc.invalidateQueries({ queryKey: [key] })
        }
      }
      hasConnectedBefore.current = true
      retryCount.current = 0
    }

    ws.current.onclose = () => {
      if (closedByCaller.current) return
      const delay = Math.min(1000 * Math.pow(2, retryCount.current), 30000)
      retryCount.current++
      reconnectTimer.current = setTimeout(connect, delay)
    }
  }, [qc])

  useEffect(() => {
    closedByCaller.current = false
    connect()
    return () => {
      closedByCaller.current = true
      if (reconnectTimer.current) {
        clearTimeout(reconnectTimer.current)
        reconnectTimer.current = null
      }
      ws.current?.close()
    }
  }, [connect])
}
