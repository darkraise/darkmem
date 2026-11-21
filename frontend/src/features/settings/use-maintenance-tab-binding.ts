import { useState } from "react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { DEMO } from "@/lib/demo-flag"
import { useDemoMaintenance } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type { MaintenanceOpKey } from "@/features/settings/types"
import { apiFetch, ApiError } from "@/lib/api"
import { useObsoleteCounts, usePipelineFailureCounts, useTriggerJob } from "@/hooks/api"
import { toast } from "darkraise-ui/components/sonner"

export interface MaintenanceTabBinding {
  reembed: { memories: number; entities: number }
  cleanup: {
    expired: number | null
    expiredDependents: number | null
    failuresMemoryIngest: number
    failuresCodeRepo: number
  }
  dbops: {
    retiredFingerprints: string[] | null
  }
  lastOpNote: string | null
  /** The note reports a refusal or failure, not a completed operation. */
  lastOpFailed: boolean
  run: (op: MaintenanceOpKey) => void
}

function busyNote(op: string): string {
  return `${op} is already running — try again once it finishes.`
}

export function useMaintenanceTabBinding(): MaintenanceTabBinding {
  const demoMaintenance = useDemoMaintenance()
  const runDemoOp = useDemoStore((s) => s.runMaintenanceOp)
  const qc = useQueryClient()
  const [realLastOp, setRealLastOp] = useState<{
    text: string
    failed: boolean
  } | null>(null)
  const setRealLastOpNote = (text: string, failed = false) =>
    setRealLastOp({ text, failed })

  const countsQuery = useObsoleteCounts()
  const failuresQuery = usePipelineFailureCounts()

  const invalidate = () => {
    void qc.invalidateQueries({ queryKey: ["obsoleteCounts"] })
    void qc.invalidateQueries({ queryKey: ["pipelineFailureCounts"] })
  }

  // A refusal (a 409 from the cache prune, a 503 from an unreachable
  // embedder) used to leave the previous operation's note standing. It now
  // replaces the note, and a toast carries it too: the note is drawn at the
  // top of the tab, off screen from the buttons further down.
  const failed = (label: string) => (error: unknown) => {
    const reason = error instanceof Error ? error.message : String(error)
    setRealLastOpNote(`${label} failed: ${reason}`, true)
    toast.error(`${label} failed: ${reason}`)
  }

  const reembedMemories = useMutation({
    mutationFn: () => apiFetch("/reembed/memories", { method: "POST" }),
    onSuccess: () => {
      setRealLastOpNote("re-embed memories started")
      invalidate()
    },
    onError: failed("Re-embed memories"),
  })
  const reembedEntities = useMutation({
    mutationFn: () => apiFetch("/reembed/entities", { method: "POST" }),
    onSuccess: () => {
      setRealLastOpNote("re-embed entities started")
      invalidate()
    },
    onError: failed("Re-embed entities"),
  })
  const pruneCaches = useMutation({
    mutationFn: () =>
      apiFetch<{ deleted: number }>("/reembed/prune-cache", { method: "POST" }),
    onSuccess: (result) => {
      setRealLastOpNote(
        `${result.deleted} unused caches dropped`,
      )
    },
    onError: failed("Prune caches"),
  })
  const triggerJob = useTriggerJob()

  const runJobTrigger = (key: string, label: string) => {
    triggerJob.mutate(key, {
      onSuccess: () => {
        setRealLastOpNote(`${label} ran`)
        invalidate()
      },
      onError: (err) => {
        setRealLastOpNote(
          err instanceof ApiError && err.status === 409 ? busyNote(label) : `${label} failed to trigger`,
          true,
        )
      },
    })
  }

  if (DEMO) {
    return {
      reembed: {
        memories: demoMaintenance.reembed.memories,
        entities: demoMaintenance.reembed.entities,
      },
      cleanup: {
        expired: demoMaintenance.cleanup.expired,
        expiredDependents: demoMaintenance.cleanup.expired_dependents,
        failuresMemoryIngest: demoMaintenance.cleanup.failures_memory_ingest,
        failuresCodeRepo: demoMaintenance.cleanup.failures_code_repo,
      },
      dbops: {
        retiredFingerprints: demoMaintenance.dbops.retired_fingerprints,
      },
      lastOpNote: demoMaintenance.last_op_note,
      lastOpFailed: false,
      run: runDemoOp,
    }
  }

  return {
    reembed: {
      memories: countsQuery.data?.memories ?? 0,
      entities: countsQuery.data?.entities ?? 0,
    },
    cleanup: {
      expired: null,
      expiredDependents: null,
      failuresMemoryIngest: failuresQuery.data?.memory_ingest ?? 0,
      failuresCodeRepo: failuresQuery.data?.code_index ?? 0,
    },
    dbops: {
      retiredFingerprints: null,
    },
    lastOpNote: realLastOp?.text ?? null,
    lastOpFailed: realLastOp?.failed ?? false,
    run: (op) => {
      switch (op) {
        case "reembed_memories":
          reembedMemories.mutate()
          return
        case "reembed_entities":
          reembedEntities.mutate()
          return
        case "prune_caches":
          pruneCaches.mutate()
          return
        case "expired_memory_cleanup":
          runJobTrigger("expired_memory_cleanup", "Expired-memory cleanup")
          return
        case "graph_orphan_cleanup":
          runJobTrigger("graph_orphan_cleanup", "Orphaned-entity cleanup")
          return
        case "tag_orphan_cleanup":
          runJobTrigger("tag_orphan_cleanup", "Unused-tag cleanup")
          return
      }
    },
  }
}
