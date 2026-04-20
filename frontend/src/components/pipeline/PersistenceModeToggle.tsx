import { useState } from "react"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { Button } from "darkraise-ui/components/button"
import { toast } from "sonner"
import { useUpdateFeatureFlags, type PipelineState } from "@/hooks/api"

const LS_KEY = "darkmem.pipeline.lastIdleTtl"

interface Props {
  ml: PipelineState["ml"]
}

export function PersistenceModeToggle({ ml }: Props) {
  const updateFlags = useUpdateFeatureFlags()
  const [advancedOpen, setAdvancedOpen] = useState(false)

  const pickPersistent = () => {
    if (ml.persistence === "persistent") return
    if (ml.idle_ttl_minutes > 0) {
      window.localStorage.setItem(LS_KEY, String(ml.idle_ttl_minutes))
    }
    updateFlags.mutate({ ml_idle_ttl_minutes: 0 }, {
      onError: (err) => toast.error(`Failed: ${err.message}`),
    })
  }

  const pickTtl = () => {
    if (ml.persistence === "ttl") return
    const restored = readLastTtl() ?? 30
    updateFlags.mutate({ ml_idle_ttl_minutes: restored }, {
      onError: (err) => toast.error(`Failed: ${err.message}`),
    })
  }

  const commitMinutes = (raw: string) => {
    const clamped = Math.max(1, Math.min(1440, Number(raw) || 0))
    if (clamped !== ml.idle_ttl_minutes) {
      updateFlags.mutate({ ml_idle_ttl_minutes: clamped })
    }
  }

  const commitInterval = (raw: string) => {
    const clamped = Math.max(10, Math.min(3600, Number(raw) || 0))
    if (clamped !== ml.eviction_check_interval_seconds) {
      updateFlags.mutate({ ml_eviction_check_interval_seconds: clamped })
    }
  }

  return (
    <div>
      <Label className="text-xs text-muted-foreground">Persistence</Label>
      <div className="flex items-center gap-2 mt-1">
        <div className="inline-flex p-0.5 border border-border rounded-md">
          <button
            type="button"
            onClick={pickPersistent}
            disabled={updateFlags.isPending}
            className={`px-3 py-1 text-xs rounded ${
              ml.persistence === "persistent" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
            }`}
          >
            Persistent
          </button>
          <button
            type="button"
            onClick={pickTtl}
            disabled={updateFlags.isPending}
            className={`px-3 py-1 text-xs rounded ${
              ml.persistence === "ttl" ? "bg-primary text-primary-foreground" : "text-muted-foreground"
            }`}
          >
            Idle TTL
          </button>
        </div>
        {ml.persistence === "ttl" && (
          <>
            <Input
              key={ml.idle_ttl_minutes}
              type="number"
              min={1}
              max={1440}
              defaultValue={ml.idle_ttl_minutes}
              onBlur={(e) => commitMinutes(e.target.value)}
              className="w-16 h-7 text-xs text-center"
              disabled={updateFlags.isPending}
            />
            <span className="text-xs text-muted-foreground">min</span>
          </>
        )}
      </div>

      {ml.persistence === "ttl" && (
        <div className="mt-2">
          <Button variant="ghost" size="sm" className="text-[10px] h-5 px-1" onClick={() => setAdvancedOpen((o) => !o)}>
            Advanced {advancedOpen ? "▴" : "▾"}
          </Button>
          {advancedOpen && (
            <div className="flex items-center gap-2 mt-1">
              <Label className="text-[10px] text-muted-foreground">Eviction check</Label>
              <Input
                key={ml.eviction_check_interval_seconds}
                type="number"
                min={10}
                max={3600}
                defaultValue={ml.eviction_check_interval_seconds}
                onBlur={(e) => commitInterval(e.target.value)}
                className="w-16 h-6 text-[10px] text-center"
                disabled={updateFlags.isPending}
              />
              <span className="text-[10px] text-muted-foreground">s</span>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function readLastTtl(): number | null {
  const raw = window.localStorage.getItem(LS_KEY)
  if (!raw) return null
  const n = Number(raw)
  return Number.isFinite(n) && n > 0 ? n : null
}
