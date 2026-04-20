import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import { Switch } from "darkraise-ui/components/switch"
import { Label } from "darkraise-ui/components/label"
import { Button } from "darkraise-ui/components/button"
import { Badge } from "darkraise-ui/components/badge"
import { ToggleGroup, ToggleGroupItem } from "darkraise-ui/components/toggle-group"
import { toast } from "sonner"
import {
  useSetPipelineMode,
  useUpdateFeatureFlags,
  type PipelineState,
  type StageMode,
} from "@/hooks/api"

interface Props {
  state: PipelineState
}

export function PipelineModeToggle({ state }: Props) {
  const setMode = useSetPipelineMode()
  const updateFlags = useUpdateFeatureFlags()
  const [advancedOpen, setAdvancedOpen] = useState(false)

  const segValue = state.mode === "mixed" ? "" : state.mode
  const summary = (Object.entries(state.stages) as [keyof PipelineState["stages"], StageMode][])
    .map(([k, v]) => `${cap(k)}: ${v.toUpperCase()}`)
    .join(" · ")

  const pickMode = (v: string) => {
    if (v !== "ml" && v !== "llm") return
    setMode.mutate({ mode: v as StageMode }, {
      onError: (err) => toast.error(`Mode flip failed: ${err.message}`),
    })
  }

  const toggleStage = (stage: keyof PipelineState["stages"], on: boolean) => {
    const key = { extraction: "ml_extraction", classification: "ml_classification", retrieval: "ml_retrieval" }[stage]
    updateFlags.mutate({ [key]: on } as any, {
      onError: (err) => toast.error(`Stage toggle failed: ${err.message}`),
    })
  }

  const toggleShadow = (on: boolean) => {
    updateFlags.mutate({ ml_shadow_mode: on }, {
      onError: (err) => toast.error(`Shadow mode toggle failed: ${err.message}`),
    })
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Default stack</CardTitle>
        <p className="text-muted-foreground text-xs">
          Pick the stack used when adding memories. Applies to all three stages — extraction, classification, retrieval.
        </p>
      </CardHeader>
      <CardContent>
        <div className="flex items-center gap-3 flex-wrap">
          <ToggleGroup
            type="single"
            variant="outline"
            value={segValue}
            onValueChange={pickMode}
            disabled={setMode.isPending}
          >
            <ToggleGroupItem value="ml">Darkmem ML stack</ToggleGroupItem>
            <ToggleGroupItem value="llm">LLM</ToggleGroupItem>
          </ToggleGroup>

          {state.mode === "mixed" && (
            <Badge variant="secondary" className="text-[10px]">Mixed</Badge>
          )}

          <div className="flex items-center gap-2 ml-auto">
            <Label className="text-xs">Shadow mode</Label>
            <Switch checked={state.shadow_mode} onCheckedChange={toggleShadow} />
          </div>

          <Button
            variant="ghost"
            size="sm"
            className="text-xs"
            onClick={() => setAdvancedOpen((o) => !o)}
          >
            Advanced {advancedOpen ? "▴" : "▾"}
          </Button>
        </div>

        <p className="text-muted-foreground text-xs mt-2">{summary}</p>

        {advancedOpen && (
          <div className="mt-3 grid grid-cols-3 gap-2 border-t border-border pt-3">
            {(["extraction", "classification", "retrieval"] as const).map((stage) => (
              <div key={stage} className="flex items-center justify-between">
                <Label className="text-xs capitalize">{stage}</Label>
                <Switch
                  checked={state.stages[stage] === "ml"}
                  onCheckedChange={(v) => toggleStage(stage, v)}
                />
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function cap(s: string) {
  return s[0].toUpperCase() + s.slice(1)
}
