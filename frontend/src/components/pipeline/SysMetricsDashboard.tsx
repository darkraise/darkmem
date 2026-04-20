import { Badge } from "darkraise-ui/components/badge"
import { Label } from "darkraise-ui/components/label"
import { useMLMetrics, useMLModelsHealth, type PipelineState } from "@/hooks/api"

interface Props {
  ml: PipelineState["ml"]
  active: boolean
}

export function SysMetricsDashboard({ ml, active }: Props) {
  const { data: metrics } = useMLMetrics(active)
  const { data: health } = useMLModelsHealth(active)

  if (!active) {
    return (
      <div className="border-t border-border pt-3 mt-2">
        <div className="flex justify-between text-[10px] text-muted-foreground mb-2">
          <span>HARDWARE METRICS</span><span>paused</span>
        </div>
        <div className="bg-background rounded-md px-3 py-4 text-center">
          <p className="text-xs text-muted-foreground">
            Monitoring is off while the LLM stack is handling every stage.
          </p>
          <p className="text-[10px] text-muted-foreground mt-1">
            Enable any stage on the Darkmem ML stack to resume live CPU/GPU readings.
          </p>
        </div>
      </div>
    )
  }

  const effective = ml.effective_device
  const isGpu = effective ? effective.startsWith("cuda") : false

  const tile1 = isGpu
    ? { label: "GPU LOAD", value: metrics?.gpu_util_percent, unit: "%", fallback: "—" }
    : { label: "CPU LOAD", value: metrics?.cpu_percent, unit: "%", fallback: "—" }

  const tile2 = isGpu
    ? {
        label: "VRAM",
        used: metrics?.vram_used_mb,
        total: metrics?.vram_total_mb,
        allocatedFallback: health?.vram_allocated_mb,
      }
    : {
        label: "RAM",
        used: metrics?.ram_used_mb,
        total: metrics?.ram_total_mb,
      }

  return (
    <div className="border-t border-border pt-3 mt-2">
      <div className="flex justify-between text-[10px] text-muted-foreground mb-2">
        <span>{isGpu ? "GPU" : "CPU"} METRICS</span><span>5s</span>
      </div>

      <div className="grid grid-cols-2 gap-2 mb-2">
        <div className="bg-background rounded-md px-2 py-1.5">
          <div className="text-[9px] text-muted-foreground">{tile1.label}</div>
          <div className="text-sm font-semibold">
            {tile1.value != null ? `${tile1.value.toFixed(0)}${tile1.unit}` : tile1.fallback}
          </div>
          <ProgressBar value={tile1.value ?? 0} max={100} />
        </div>
        <div className="bg-background rounded-md px-2 py-1.5">
          <div className="text-[9px] text-muted-foreground">{tile2.label}</div>
          <MemoryValue
            used={tile2.used}
            total={tile2.total}
            allocatedFallback={(tile2 as any).allocatedFallback}
          />
        </div>
      </div>

      <Label className="text-[10px] text-muted-foreground">Loaded groups</Label>
      <div className="flex gap-1 mt-1">
        {(["extraction", "classification", "retriever"] as const).map((g) => {
          const row = metrics?.groups?.[g]
          const loaded = row?.loaded ?? false
          const idle = row?.idle_seconds
          return (
            <Badge
              key={g}
              variant={loaded ? "default" : "outline"}
              className="text-[10px]"
            >
              {g} {loaded ? `· ${idle ?? 0}s` : ""}
            </Badge>
          )
        })}
      </div>
    </div>
  )
}

function ProgressBar({ value, max }: { value: number; max: number }) {
  const pct = Math.max(0, Math.min(100, (value / max) * 100))
  return (
    <div className="h-1 bg-muted rounded-sm mt-1" role="progressbar" aria-valuenow={value} aria-valuemax={max}>
      <div className="h-full bg-primary rounded-sm" style={{ width: `${pct}%` }} />
    </div>
  )
}

function MemoryValue({ used, total, allocatedFallback }: { used?: number | null; total?: number | null; allocatedFallback?: number | null }) {
  if (used != null && total != null) {
    const usedGb = (used / 1024).toFixed(1)
    const totalGb = (total / 1024).toFixed(1)
    return (
      <>
        <div className="text-sm font-semibold">{usedGb} / {totalGb} GB</div>
        <ProgressBar value={used} max={total} />
      </>
    )
  }
  if (allocatedFallback != null) {
    return (
      <>
        <div className="text-sm font-semibold" title="process only (pynvml unavailable)">
          {(allocatedFallback / 1024).toFixed(1)} GB <span className="text-[9px] text-muted-foreground">process only</span>
        </div>
      </>
    )
  }
  return <div className="text-sm font-semibold text-muted-foreground">—</div>
}
