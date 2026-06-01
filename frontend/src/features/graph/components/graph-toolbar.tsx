import { Toggle } from "darkraise-ui/components/toggle"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "darkraise-ui/components/popover"
import { Slider } from "darkraise-ui/components/slider"
import { Button } from "darkraise-ui/components/button"
import { Label } from "darkraise-ui/components/label"
import { Settings, RotateCcw } from "lucide-react"
import type { SizeMode } from "@/features/graph/lib/graph-utils"
import type { ColorMode } from "@/features/graph/lib/graph-colors"
import type { HullMode } from "@/features/graph/lib/graph-geometry"

type ViewMode = "2d" | "3d"

interface GraphToolbarProps {
  viewMode: ViewMode
  onViewModeChange: (mode: ViewMode) => void
  colorMode: ColorMode
  onColorModeChange: (mode: ColorMode) => void
  hullMode: HullMode
  onHullModeChange: (mode: HullMode) => void
  entityLayer: boolean
  onEntityLayerChange: (v: boolean) => void
  sizeMode: SizeMode
  onSizeModeChange: (mode: SizeMode) => void
  similarityThreshold: number
  onSimilarityChange: (v: number) => void
  minClusterSize: number
  onMinClusterSizeChange: (v: number) => void
  spacing: number
  onSpacingChange: (v: number) => void
  clusterTightness: number
  onClusterTightnessChange: (v: number) => void
  onReset: () => void
}

interface SliderRowProps {
  label: string
  min: number
  max: number
  step: number
  value: number
  onChange: (v: number) => void
  float?: boolean
}

function SliderRow({
  label,
  min,
  max,
  step,
  value,
  onChange,
  float = false,
}: SliderRowProps) {
  return (
    <div className="text-muted-foreground flex items-center gap-2 text-base">
      <Label className="w-14 shrink-0 text-right">{label}</Label>
      <Slider
        value={[value]}
        onValueChange={([v]) => {
          const next = v ?? value
          onChange(float ? next : Math.round(next))
        }}
        min={min}
        max={max}
        step={step}
        className="flex-1"
      />
      <span className="w-8 text-right font-mono">{value}</span>
    </div>
  )
}

export function GraphToolbar({
  viewMode,
  onViewModeChange,
  colorMode,
  onColorModeChange,
  hullMode,
  onHullModeChange,
  entityLayer,
  onEntityLayerChange,
  sizeMode,
  onSizeModeChange,
  similarityThreshold,
  onSimilarityChange,
  minClusterSize,
  onMinClusterSizeChange,
  spacing,
  onSpacingChange,
  clusterTightness,
  onClusterTightnessChange,
  onReset,
}: GraphToolbarProps) {
  return (
    <div className="pointer-events-none absolute top-3 right-0 left-0 z-20 flex flex-col items-center">
      <div className="bg-card/80 border-border pointer-events-auto flex flex-wrap items-center justify-center gap-2 rounded-md border px-3 py-1.5 shadow-lg backdrop-blur-sm">
        <ToggleGroup
          type="single"
          value={viewMode}
          onValueChange={(v) => {
            if (v) onViewModeChange(v as ViewMode)
          }}
          className="gap-0"
        >
          <ToggleGroupItem
            value="2d"
            variant="outline"
            className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2.5 text-base"
          >
            2D
          </ToggleGroupItem>
          <ToggleGroupItem
            value="3d"
            variant="outline"
            className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2.5 text-base"
          >
            3D
          </ToggleGroupItem>
        </ToggleGroup>

        <div className="bg-border h-4 w-px" />

        <ToggleGroup
          type="single"
          value={colorMode}
          onValueChange={(v) => {
            if (v) onColorModeChange(v as ColorMode)
          }}
          className="gap-0"
        >
          <ToggleGroupItem
            value="type"
            variant="outline"
            className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2.5 text-base"
          >
            Type
          </ToggleGroupItem>
          <ToggleGroupItem
            value="cluster"
            variant="outline"
            className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2.5 text-base"
          >
            Cluster
          </ToggleGroupItem>
          <ToggleGroupItem
            value="tag"
            variant="outline"
            className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2.5 text-base"
          >
            Tag
          </ToggleGroupItem>
        </ToggleGroup>

        <ToggleGroup
          type="single"
          value={hullMode}
          onValueChange={(v) => {
            if (v) onHullModeChange(v as HullMode)
          }}
          className="gap-0"
        >
          <ToggleGroupItem
            value="none"
            variant="outline"
            className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2.5 text-base"
          >
            None
          </ToggleGroupItem>
          <ToggleGroupItem
            value="cluster"
            variant="outline"
            className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2.5 text-base"
          >
            Cluster
          </ToggleGroupItem>
          <ToggleGroupItem
            value="tag"
            variant="outline"
            className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2.5 text-base"
          >
            Tag
          </ToggleGroupItem>
          <ToggleGroupItem
            value="source"
            variant="outline"
            className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2.5 text-base"
          >
            Source
          </ToggleGroupItem>
        </ToggleGroup>

        <div className="bg-border h-4 w-px" />

        <Toggle
          pressed={entityLayer}
          onPressedChange={onEntityLayerChange}
          className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 text-base"
        >
          Entities
        </Toggle>

        <Popover>
          <PopoverTrigger asChild>
            <Toggle
              aria-label="Toggle graph settings"
              className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 text-base"
            >
              <Settings className="h-3.5 w-3.5" />
            </Toggle>
          </PopoverTrigger>
          <PopoverContent
            side="bottom"
            align="end"
            className="bg-card/95 border-border w-[340px] rounded-lg border px-4 py-3 shadow-xl backdrop-blur-sm"
          >
            <div className="mb-3 flex items-center justify-between">
              <span className="text-foreground text-base font-semibold">
                Settings
              </span>
            </div>
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <span className="text-muted-foreground w-14 shrink-0 text-right text-base">
                  Size
                </span>
                <ToggleGroup
                  type="single"
                  value={sizeMode}
                  onValueChange={(v) => {
                    if (v) onSizeModeChange(v as SizeMode)
                  }}
                  className="gap-0"
                >
                  <ToggleGroupItem
                    value="connections"
                    variant="outline"
                    className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2 text-base"
                  >
                    Connections
                  </ToggleGroupItem>
                  <ToggleGroupItem
                    value="importance"
                    variant="outline"
                    className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2 text-base"
                  >
                    Importance
                  </ToggleGroupItem>
                  <ToggleGroupItem
                    value="uniform"
                    variant="outline"
                    className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2 text-base"
                  >
                    Uniform
                  </ToggleGroupItem>
                </ToggleGroup>
              </div>
              <SliderRow
                label="Edges"
                min={0.3}
                max={0.95}
                step={0.05}
                value={similarityThreshold}
                onChange={onSimilarityChange}
                float
              />
              <SliderRow
                label="Min Size"
                min={2}
                max={10}
                step={1}
                value={minClusterSize}
                onChange={onMinClusterSizeChange}
              />
              {viewMode === "2d" && (
                <SliderRow
                  label="Tightness"
                  min={30}
                  max={300}
                  step={10}
                  value={clusterTightness}
                  onChange={onClusterTightnessChange}
                />
              )}
              <SliderRow
                label="Spacing"
                min={viewMode === "2d" ? 100 : 30}
                max={viewMode === "2d" ? 500 : 200}
                step={viewMode === "2d" ? 25 : 10}
                value={spacing}
                onChange={onSpacingChange}
              />
            </div>
          </PopoverContent>
        </Popover>

        <Button
          variant="ghost"
          size="icon"
          type="button"
          className="text-muted-foreground hover:bg-muted hover:text-foreground inline-flex h-7 w-7 items-center justify-center rounded-lg transition-colors"
          onClick={onReset}
          aria-label="Reset graph view"
        >
          <RotateCcw className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}
