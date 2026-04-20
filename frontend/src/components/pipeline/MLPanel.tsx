import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import { Badge } from "darkraise-ui/components/badge"
import { useApplyMLDevice, type PipelineState } from "@/hooks/api"
import { MLDeviceSection } from "./MLDeviceSection"
import { PersistenceModeToggle } from "./PersistenceModeToggle"
import { SysMetricsDashboard } from "./SysMetricsDashboard"
import { UnloadControls } from "./UnloadControls"

interface Props {
  state: PipelineState
}

export function MLPanel({ state }: Props) {
  const applyDevice = useApplyMLDevice()
  const mlStages = Object.values(state.stages).filter((v) => v === "ml").length
  const status = mlStages === 3 ? "active" : mlStages === 0 ? "inactive" : "mixed"
  const active = mlStages > 0
  const switching = applyDevice.isPending

  return (
    <Card className={status === "inactive" ? "opacity-60" : ""}>
      <CardHeader className="pb-2 flex flex-row items-start justify-between">
        <div>
          <CardTitle className="text-sm">Darkmem ML stack</CardTitle>
          <p className="text-muted-foreground text-xs">Local fine-tuned heads</p>
        </div>
        <Badge variant={status === "active" ? "default" : "outline"} className="text-[10px]">
          {status} · {mlStages}/3
        </Badge>
      </CardHeader>
      <CardContent className="space-y-3">
        <MLDeviceSection ml={state.ml} />
        {switching ? <MLPanelSkeleton /> : (
          <>
            <PersistenceModeToggle ml={state.ml} />
            <SysMetricsDashboard ml={state.ml} active={active} />
            <UnloadControls state={state} active={active} />
          </>
        )}
      </CardContent>
    </Card>
  )
}

function MLPanelSkeleton() {
  return (
    <div className="space-y-3" aria-busy="true" aria-label="switching device">
      <div className="h-7 w-48 bg-muted rounded animate-pulse" />
      <div className="border-t border-border pt-3 mt-2 space-y-2">
        <div className="flex justify-between text-[10px] text-muted-foreground mb-2">
          <span>SWITCHING DEVICE</span><span>—</span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <div className="h-12 bg-muted rounded-md animate-pulse" />
          <div className="h-12 bg-muted rounded-md animate-pulse" />
        </div>
        <div className="flex gap-1 mt-1">
          <div className="h-5 w-20 bg-muted rounded animate-pulse" />
          <div className="h-5 w-24 bg-muted rounded animate-pulse" />
          <div className="h-5 w-20 bg-muted rounded animate-pulse" />
        </div>
      </div>
      <div className="h-8 w-40 bg-muted rounded animate-pulse" />
    </div>
  )
}
