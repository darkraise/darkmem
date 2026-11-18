import { Toggle } from "darkraise-ui/components/toggle"
import { Switch } from "darkraise-ui/components/switch"
import { Spinner } from "darkraise-ui/components/spinner"
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "darkraise-ui/components/popover"
import { Button } from "darkraise-ui/components/button"
import { Settings, RotateCcw } from "lucide-react"
import { cn } from "darkraise-ui/lib"
import type React from "react"
import type { SizeMode } from "@/features/graph/lib/graph-utils"
import type { ColorMode } from "@/features/graph/lib/graph-colors"
import type { HullMode } from "@/features/graph/lib/graph-geometry"
import { SelectionSettings } from "./selection-settings"
import {
  SectionLabel,
  SegmentRow,
  SliderRow,
  SwitchRow,
} from "./settings-rows"

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
  onReset: () => void
  /** The node budget control, shown first because it decides what every
   *  other setting acts on. */
  nodes?: React.ReactNode
  /** Rendered at the end of the button row. The details-panel toggle lives
   *  here rather than positioning itself over the canvas: two absolutely
   *  positioned clusters competing for the same corner is how they ended up
   *  stacked on each other, and an offset picked to clear one is a number
   *  that rots the moment the row changes. */
  trailing?: React.ReactNode
}

/** A titled group of rows. `divided` draws the hairline that separates it
 *  from the group above -- headings alone read as one long list. */
function Section({
  title,
  divided = false,
  children,
}: {
  title: string
  divided?: boolean
  children: React.ReactNode
}) {
  return (
    <div className={cn(divided && "border-border/60 mt-3 border-t pt-3")}>
      <SectionLabel>{title}</SectionLabel>
      <div className="space-y-2">{children}</div>
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
  onReset,
  nodes,
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
            className="bg-card/80 border-border data-[pressed]:bg-primary/20 data-[pressed]:text-primary-text pointer-events-auto h-8 w-8 rounded-md border p-0 shadow-lg backdrop-blur-sm"
          >
            <Settings className="h-3.5 w-3.5" />
          </Toggle>
        </PopoverTrigger>
        <PopoverContent
          side="bottom"
          align="end"
          className="bg-card/95 border-border max-h-[min(70vh,32rem)] w-[384px] overflow-y-auto rounded-lg border p-3 shadow-xl backdrop-blur-sm"
        >
          {/* Grouped by the kind of decision each control is, not by where
              it happens to be read. Render gates the rest (Spacing is
              3D-only), encodings say what a mark means, and the layout
              sliders drive the force simulation. */}
          {nodes && <Section title="Nodes">{nodes}</Section>}
          <Section title="Render" divided={!!nodes}>
            <SegmentRow
              label="Mode"
              value={viewMode}
              onChange={(v) => onViewModeChange(v as ViewMode)}
              size="sm"
              ariaLabel="Render mode"
              options={[
                { value: "2d", label: "2D" },
                { value: "3d", label: "3D" },
              ]}
            />
          </Section>

          <Section title="Encoding" divided>
            <SegmentRow
              label="Colour"
              value={colorMode}
              onChange={(v) => onColorModeChange(v as ColorMode)}
              size="sm"
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
              size="sm"
              options={[
                { value: "none", label: "None" },
                { value: "cluster", label: "Cluster" },
                { value: "tag", label: "Tag" },
                { value: "source", label: "Source" },
              ]}
            />
            {/* Node size is an encoding, not a layout parameter: it answers
                the same question Colour and Regions do. */}
            <SegmentRow
              label="Size"
              value={sizeMode}
              onChange={(v) => onSizeModeChange(v as SizeMode)}
              size="sm"
              ariaLabel="Node size"
              options={[
                { value: "connections", label: "Links" },
                { value: "importance", label: "Weight" },
                { value: "uniform", label: "Equal" },
              ]}
            />
          </Section>

          <Section title="Entities" divided>
            <SwitchRow
              label="Show"
              hint={entityLayerLoading ? <Spinner size="sm" /> : undefined}
            >
              <Switch
                checked={entityLayer}
                onCheckedChange={onEntityLayerChange}
                aria-label="Entity layer"
              />
            </SwitchRow>
            {/* Always mounted, disabled when the layer is off: mounting it
                with the layer resized the popover and moved every control
                below it. */}
            <SwitchRow
              label="Shared"
              hint={
                <span
                  className={cn(
                    "text-xs",
                    entityLayer ? "opacity-60" : "opacity-30",
                  )}
                >
                  2+ memories
                </span>
              }
            >
              <Switch
                checked={sharedEntitiesOnly}
                onCheckedChange={onSharedEntitiesOnlyChange}
                disabled={!entityLayer}
                aria-label="Shared entities only"
              />
            </SwitchRow>
          </Section>

          <Section title="Layout" divided>
            <SliderRow
              label="Edges"
              min={0.3}
              max={0.95}
              step={0.05}
              value={similarityThreshold}
              onChange={onSimilarityChange}
              ariaLabel="Edge similarity threshold"
              float
            />
            <SliderRow
              label="Min size"
              min={2}
              max={10}
              step={1}
              value={minClusterSize}
              onChange={onMinClusterSizeChange}
              ariaLabel="Minimum cluster size"
            />
            {viewMode === "3d" && (
              <SliderRow
                label="Spacing"
                min={30}
                max={200}
                step={10}
                value={spacing}
                onChange={onSpacingChange}
              />
            )}
          </Section>

          <Section title="Selection" divided>
            {/* Same component as Settings > Appearance, over the same store,
                so the two surfaces cannot drift. */}
            <SelectionSettings compact />
          </Section>
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
