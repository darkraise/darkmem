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
      <CardContent className={`space-y-3 ${applyDevice.isPending ? "pointer-events-none opacity-70" : ""}`}>
        <MLDeviceSection ml={state.ml} />
        <PersistenceModeToggle ml={state.ml} />
        <SysMetricsDashboard ml={state.ml} />
        <UnloadControls state={state} />
      </CardContent>
    </Card>
  )
}
