import { useState } from "react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { DEMO } from "@/lib/demo-flag"
import { useDemoMaintenance } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type { MaintenanceOpKey } from "@/features/settings/types"
import { apiFetch, ApiError } from "@/lib/api"
import { useTriggerJob } from "@/hooks/api"

export type MaintenanceOp = MaintenanceOpKey | "reembed_code_chunks"

export interface MaintenanceTabBinding {
  isLoading: boolean
  fingerprint: string
  reembed: { memories: number; entities: number; codeChunks: number }
  /** Always false: `POST /reembed/code-chunks` exists and returns 202, but
   *  `ReembedService.reembed_code_chunks` is a stub — it never embeds
   *  anything and reports every row as an error with a "not yet
   *  implemented" message (verified by reading the method body, not just
   *  the route). Triggering it would be an honest-looking button wired to
   *  a call that structurally cannot succeed, which is worse than not
   *  offering it. Matches the demo fixture's own disabled state. */
  codeChunksReembedAvailable: boolean
  cleanup: {
    expired: number | null
    expiredDependents: number | null
    failuresMemoryIngest: number
    failuresCodeRepo: number
  }
  dbops: {
    retiredFingerprints: string[] | null
    vacuumTarget: string
    vacuumNote: string
    reindexTarget: string
    reindexNote: string
  }
  lastOpNote: string | null
  /** True in real mode: every trigger this tab exposes journals a
   *  `maintenance_run` event via `record_maintenance_run` (job_runners.py's
   *  three cleanup runners, reembed.py's background tasks and
   *  POST /reembed/prune-cache) — verified with a mutation-proof backend
   *  test per operation (tests/test_maintenance_journaling.py). */
  eventsJournaled: boolean
  run: (op: MaintenanceOp) => void
}

interface ObsoleteCounts {
  memories: number
  entities: number
  code_chunks: number
  current_fingerprint: string
}

interface FailureCounts {
  memory_ingest?: number
  code_index?: number
}

function busyNote(op: string): string {
  return `${op} is already running — this trigger was not queued (HTTP 409); try again once the current run finishes.`
}

export function useMaintenanceTabBinding(): MaintenanceTabBinding {
  const demoMaintenance = useDemoMaintenance()
  const runDemoOp = useDemoStore((s) => s.runMaintenanceOp)
  const qc = useQueryClient()
  const [realLastOpNote, setRealLastOpNote] = useState<string | null>(null)

  const countsQuery = useQuery<ObsoleteCounts>({
    queryKey: ["reembedObsoleteCounts"],
    queryFn: () => apiFetch<ObsoleteCounts>("/reembed/obsolete-counts"),
    enabled: !DEMO,
  })
  const failuresQuery = useQuery<FailureCounts>({
    queryKey: ["pipelineFailureCounts"],
    queryFn: () => apiFetch<FailureCounts>("/pipeline-failures/counts"),
    enabled: !DEMO,
  })

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ["reembedObsoleteCounts"] })
    void qc.invalidateQueries({ queryKey: ["pipelineFailureCounts"] })
  }

  const reembedMemories = useMutation({
    mutationFn: () => apiFetch("/reembed/memories", { method: "POST" }),
    onSuccess: () => {
      setRealLastOpNote("re-embed memories started (POST returned 202)")
      invalidate()
    },
  })
  const reembedEntities = useMutation({
    mutationFn: () => apiFetch("/reembed/entities", { method: "POST" }),
    onSuccess: () => {
      setRealLastOpNote("re-embed entities started (POST returned 202)")
      invalidate()
    },
  })
  const pruneCaches = useMutation({
    mutationFn: () =>
      apiFetch<{ deleted: number }>("/reembed/prune-cache", { method: "POST" }),
    onSuccess: (result) => {
      setRealLastOpNote(
        `${result.deleted} retired cache tables dropped — each rebuilds lazily on next use of its embedder`,
      )
    },
  })
  const triggerJob = useTriggerJob()

  const runJobTrigger = (key: string, label: string) => {
    triggerJob.mutate(key, {
      onSuccess: () => {
        setRealLastOpNote(`${label} ran now — the same job the hourly schedule already runs`)
        invalidate()
      },
      onError: (err) => {
        setRealLastOpNote(
          err instanceof ApiError && err.status === 409 ? busyNote(label) : `${label} failed to trigger`,
        )
      },
    })
  }

  if (DEMO) {
    return {
      isLoading: false,
      fingerprint: demoMaintenance.fingerprint,
      reembed: {
        memories: demoMaintenance.reembed.memories,
        entities: demoMaintenance.reembed.entities,
        codeChunks: demoMaintenance.reembed.code_chunks,
      },
      codeChunksReembedAvailable: false,
      cleanup: {
        expired: demoMaintenance.cleanup.expired,
        expiredDependents: demoMaintenance.cleanup.expired_dependents,
        failuresMemoryIngest: demoMaintenance.cleanup.failures_memory_ingest,
        failuresCodeRepo: demoMaintenance.cleanup.failures_code_repo,
      },
      dbops: {
        retiredFingerprints: demoMaintenance.dbops.retired_fingerprints,
        vacuumTarget: demoMaintenance.dbops.vacuum_target,
        vacuumNote: demoMaintenance.dbops.vacuum_note,
        reindexTarget: demoMaintenance.dbops.reindex_target,
        reindexNote: demoMaintenance.dbops.reindex_note,
      },
      lastOpNote: demoMaintenance.last_op_note,
      eventsJournaled: true,
      run: (op) => {
        if (op === "reembed_code_chunks") return
        runDemoOp(op)
      },
    }
  }

  return {
    isLoading: countsQuery.isLoading || failuresQuery.isLoading,
    fingerprint: countsQuery.data?.current_fingerprint ?? "",
    reembed: {
      memories: countsQuery.data?.memories ?? 0,
      entities: countsQuery.data?.entities ?? 0,
      codeChunks: countsQuery.data?.code_chunks ?? 0,
    },
    codeChunksReembedAvailable: false,
    cleanup: {
      expired: null,
      expiredDependents: null,
      failuresMemoryIngest: failuresQuery.data?.memory_ingest ?? 0,
      failuresCodeRepo: failuresQuery.data?.code_index ?? 0,
    },
    dbops: {
      retiredFingerprints: null,
      vacuumTarget: "memory_embeddings__<active fingerprint>",
      vacuumNote:
        "The GIN index supersession and retrieval filtering both consult (memories.technologies).",
      reindexTarget: "ix_memories_technologies",
      reindexNote:
        "The GIN index supersession and retrieval filtering both consult (memories.technologies).",
    },
    lastOpNote: realLastOpNote,
    eventsJournaled: true,
    run: (op) => {
      switch (op) {
        case "reembed_memories":
          reembedMemories.mutate()
          return
        case "reembed_entities":
          reembedEntities.mutate()
          return
        case "reembed_code_chunks":
          // codeChunksReembedAvailable is always false — see its doc
          // comment. The UI never reaches this arm; kept exhaustive.
          return
        case "prune_caches":
          pruneCaches.mutate()
          return
        case "expired_memory_cleanup":
          runJobTrigger("expired_memory_cleanup", "expired_memory_cleanup")
          return
        case "graph_orphan_cleanup":
          runJobTrigger("graph_orphan_cleanup", "graph_orphan_cleanup")
          return
        case "tag_orphan_cleanup":
          runJobTrigger("tag_orphan_cleanup", "tag_orphan_cleanup")
          return
      }
    },
  }
}
