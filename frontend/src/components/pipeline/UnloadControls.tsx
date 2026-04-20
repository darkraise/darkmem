import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import { toast } from "sonner"
import { useMLMetrics, useUnloadPipeline, type PipelineState } from "@/hooks/api"
import { UnloadConfirmDialog } from "./UnloadConfirmDialog"

interface Props {
  state: PipelineState
}

export function UnloadControls({ state }: Props) {
  const unload = useUnloadPipeline()
  const { data: metrics } = useMLMetrics()
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [advancedOpen, setAdvancedOpen] = useState(false)

  const anyLoaded = Object.values(metrics?.groups ?? {}).some((g) => g?.loaded)

  const runUnload = (group?: "extraction" | "classification" | "retriever") => {
    unload.mutate(
      { group },
      {
        onSuccess: (r) => toast.success(
          group
            ? `Unloaded ${group}`
            : r.unloaded.length ? `Unloaded ${r.unloaded.join(", ")}` : "Nothing to unload",
        ),
        onError: (err) => toast.error(`Unload failed: ${err.message}`),
      },
    )
  }

  return (
    <>
      <Button
        variant="destructive"
        size="sm"
        onClick={() => setConfirmOpen(true)}
        disabled={!anyLoaded || unload.isPending}
      >
        Unload all models
      </Button>

      <div className="mt-2">
        <Button variant="ghost" size="sm" className="text-[10px] h-5 px-1" onClick={() => setAdvancedOpen((o) => !o)}>
          Advanced — per-group {advancedOpen ? "▴" : "▾"}
        </Button>
        {advancedOpen && (
          <div className="flex gap-1 mt-1">
            {(["extraction", "classification", "retriever"] as const).map((g) => {
              const loaded = metrics?.groups?.[g]?.loaded ?? false
              return (
                <Button
                  key={g}
                  variant="outline"
                  size="sm"
                  className="text-[10px]"
                  disabled={!loaded || unload.isPending}
                  onClick={() => runUnload(g)}
                >
                  Unload {g}
                </Button>
              )
            })}
          </div>
        )}
      </div>

      <UnloadConfirmDialog
        open={confirmOpen}
        shadowModeOn={state.shadow_mode}
        pending={unload.isPending}
        onCancel={() => setConfirmOpen(false)}
        onConfirm={() => {
          setConfirmOpen(false)
          runUnload()
        }}
      />
    </>
  )
}
