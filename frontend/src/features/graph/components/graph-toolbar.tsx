import { Toggle } from "darkraise-ui/components/toggle"
import { Switch } from "darkraise-ui/components/switch"
import { Spinner } from "darkraise-ui/components/spinner"
import {
  SegmentGroup,
  SegmentGroupIndicator,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "darkraise-ui/components/popover"
import { Slider } from "darkraise-ui/components/slider"
import { Button } from "darkraise-ui/components/button"
import { Label } from "darkraise-ui/components/label"
import { Settings, RotateCcw } from "lucide-react"
import { cn } from "darkraise-ui/lib"
import type React from "react"
import type { SizeMode } from "@/features/graph/lib/graph-utils"
import type { ColorMode } from "@/features/graph/lib/graph-colors"
import type { HullMode } from "@/features/graph/lib/graph-geometry"
import { SelectionSettings } from "./selection-settings"

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
  /** A graph refetch is in flight. Reported beside the switch that started it
   *  rather than only on the canvas, so the control answers when you use it. */
  entityLayerLoading?: boolean
  sharedEntitiesOnly: boolean
  onSharedEntitiesOnlyChange: (v: boolean) => void
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
  /** Rendered at the end of the button row. The details-panel toggle lives
   *  here rather than positioning itself over the canvas: two absolutely
   *  positioned clusters competing for the same corner is how they ended up
   *  stacked on each other, and an offset picked to clear one is a number
   *  that rots the moment the row changes. */
  trailing?: React.ReactNode
}

/** The mono-uppercase section header the settings cards use, so the popover
 *  reads as the same product rather than as a stray widget. */
function SectionLabel({
  children,
  className,
}: {
  children: React.ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        "text-muted-foreground mb-2 font-mono text-[10px] font-semibold tracking-[0.14em] uppercase",
        className,
      )}
    >
      {children}
    </div>
  )
}

function SegmentRow({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: { value: string; label: string }[]
}) {
  return (
    <div className="text-muted-foreground flex items-center gap-2 text-sm">
      <Label className="w-16 shrink-0 text-right font-normal">{label}</Label>
      <SegmentGroup
        color="accent"
        value={value}
        onValueChange={(v) => {
          if (v) onChange(v)
        }}
        className="min-w-0 flex-1"
      >
        <SegmentGroupIndicator />
        {options.map((o) => (
          <SegmentGroupItem key={o.value} value={o.value}>
            {o.label}
          </SegmentGroupItem>
        ))}
      </SegmentGroup>
    </div>
  )
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
    <div className="text-muted-foreground flex items-center gap-2 text-sm">
      <Label className="w-16 shrink-0 text-right font-normal">{label}</Label>
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
      <span className="text-foreground w-10 shrink-0 text-right font-mono tabular-nums">
        {value}
      </span>
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
  entityLayerLoading = false,
  sharedEntitiesOnly,
  onSharedEntitiesOnlyChange,
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
  trailing,
}: GraphToolbarProps) {
  return (
    // Top-right, not centred: the graph is the page, and a bar across its
    // middle competes with the thing it controls. Two buttons is all that
    // sits over the canvas now -- everything else moved into the panel.
    <div className="pointer-events-none absolute top-3 right-3 z-20 flex items-center gap-1.5">
      <Popover>
        <PopoverTrigger asChild>
          <Toggle
            aria-label="Toggle graph settings"
            className="bg-card/80 border-border data-[pressed]:bg-primary/20 data-[pressed]:text-primary pointer-events-auto h-8 w-8 rounded-md border p-0 shadow-lg backdrop-blur-sm"
          >
            <Settings className="h-3.5 w-3.5" />
          </Toggle>
        </PopoverTrigger>
        <PopoverContent
          side="bottom"
          align="end"
          className="bg-card/95 border-border max-h-[min(70vh,32rem)] w-[384px] overflow-y-auto rounded-lg border px-4 py-3 shadow-xl backdrop-blur-sm"
        >
          <SectionLabel>View</SectionLabel>
          <div className="space-y-3">
            <SegmentRow
              label="Render"
              value={viewMode}
              onChange={(v) => onViewModeChange(v as ViewMode)}
              options={[
                { value: "2d", label: "2D" },
                { value: "3d", label: "3D" },
              ]}
            />
            <SegmentRow
              label="Colour"
              value={colorMode}
              onChange={(v) => onColorModeChange(v as ColorMode)}
              options={[
                { value: "type", label: "Type" },
                { value: "cluster", label: "Cluster" },
                { value: "tag", label: "Tag" },
              ]}
            />
            <SegmentRow
              label="Regions"
              value={hullMode}
              onChange={(v) => onHullModeChange(v as HullMode)}
              options={[
                { value: "none", label: "None" },
                { value: "cluster", label: "Cluster" },
                { value: "tag", label: "Tag" },
                { value: "source", label: "Source" },
              ]}
            />
            <div className="text-muted-foreground flex items-center gap-2 text-sm">
              <Label className="w-16 shrink-0 text-right font-normal">
                Entities
              </Label>
              <Switch
                checked={entityLayer}
                onCheckedChange={onEntityLayerChange}
                aria-label="Entity layer"
              />
              {entityLayerLoading && <Spinner size="sm" />}
            </div>
            {entityLayer && (
              <div className="text-muted-foreground flex items-center gap-2 text-sm">
                <Label className="w-16 shrink-0 text-right font-normal">
                  Shared only
                </Label>
                <Switch
                  checked={sharedEntitiesOnly}
                  onCheckedChange={onSharedEntitiesOnlyChange}
                  aria-label="Shared entities only"
                />
                <span className="text-sm opacity-60">2+ memories</span>
              </div>
            )}
          </div>

          <SectionLabel className="mt-4">Selection</SectionLabel>
          <div className="space-y-3">
            {/* Same component as Settings > Appearance, over the same store,
                so the two surfaces cannot drift. */}
            <SelectionSettings compact />
          </div>

          <SectionLabel className="mt-4">Layout</SectionLabel>
          <div className="space-y-3">
            <SegmentRow
              label="Size"
              value={sizeMode}
              onChange={(v) => onSizeModeChange(v as SizeMode)}
              options={[
                { value: "connections", label: "Links" },
                { value: "importance", label: "Weight" },
                { value: "uniform", label: "Equal" },
              ]}
            />
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
        className="bg-card/80 border-border text-muted-foreground hover:bg-muted hover:text-foreground pointer-events-auto inline-flex h-8 w-8 items-center justify-center rounded-md border shadow-lg backdrop-blur-sm transition-colors"
        onClick={onReset}
        aria-label="Reset graph view"
      >
        <RotateCcw className="h-3.5 w-3.5" />
      </Button>

      {trailing}
    </div>
  )
}
