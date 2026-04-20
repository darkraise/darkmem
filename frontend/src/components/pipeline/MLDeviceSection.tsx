import { Label } from "darkraise-ui/components/label"
import { ToggleGroup, ToggleGroupItem } from "darkraise-ui/components/toggle-group"
import { toast } from "sonner"
import { useApplyMLDevice, type MLDeviceApplyResponse, type PipelineState } from "@/hooks/api"

interface Props {
  ml: PipelineState["ml"]
}

export function MLDeviceSection({ ml }: Props) {
  const applyDevice = useApplyMLDevice()
  const currentId =
    ml.device === "cpu" ? "cpu" : ml.device === "auto" ? "auto" : `cuda:${ml.cuda_index}`

  const pick = (id: string) => {
    if (!id || id === currentId) return
    if (id === "cpu") {
      applyDevice.mutate({ ml_device: "cpu", ml_cuda_index: 0 }, callbacks())
      return
    }
    if (id === "auto") {
      applyDevice.mutate({ ml_device: "auto", ml_cuda_index: 0 }, callbacks())
      return
    }
    const idx = Number(id.replace(/^cuda:/, "")) || 0
    applyDevice.mutate({ ml_device: "cuda", ml_cuda_index: idx }, callbacks())
  }

  return (
    <div>
      <Label className="text-xs text-muted-foreground">Device</Label>
      <ToggleGroup
        type="single"
        variant="outline"
        value={currentId}
        onValueChange={pick}
        disabled={applyDevice.isPending}
        className="flex-wrap justify-start mt-1"
      >
        {ml.available_devices.map((d) => (
          <ToggleGroupItem key={d.id} value={d.id} className="text-xs">
            {d.label}
          </ToggleGroupItem>
        ))}
      </ToggleGroup>
      {applyDevice.isPending && (
        <p className="text-[10px] text-muted-foreground mt-1">Unloading models on the old device…</p>
      )}
    </div>
  )

  function callbacks() {
    return {
      onSuccess: (r: MLDeviceApplyResponse) => {
        toast.success(`Device set to ${r.effective_device} — models will load on demand`)
      },
      onError: (err: Error) => toast.error(`Device apply failed: ${err.message}`),
    }
  }
}
