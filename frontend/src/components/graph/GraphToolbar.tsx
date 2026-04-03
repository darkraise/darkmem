import { useRef, useEffect } from "react";
import { Toggle } from "@/components/ui/toggle";
import { ToggleGroup, ToggleGroupItem } from "@/components/ui/toggle-group";
import { Settings, RotateCcw } from "lucide-react";
import type { SizeMode } from "@/lib/graph-utils";
import type { ColorMode } from "@/lib/graph-colors";
import type { HullMode } from "@/lib/graph-geometry";

type ViewMode = "2d" | "3d";

interface GraphToolbarProps {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  colorMode: ColorMode;
  onColorModeChange: (mode: ColorMode) => void;
  hullMode: HullMode;
  onHullModeChange: (mode: HullMode) => void;
  entityLayer: boolean;
  onEntityLayerChange: (v: boolean) => void;
  showSettings: boolean;
  onToggleSettings: (pressed: boolean) => void;
  sizeMode: SizeMode;
  onSizeModeChange: (mode: SizeMode) => void;
  similarityThreshold: number;
  onSimilarityChange: (v: number) => void;
  minClusterSize: number;
  onMinClusterSizeChange: (v: number) => void;
  spacing: number;
  onSpacingChange: (v: number) => void;
  clusterTightness: number;
  onClusterTightnessChange: (v: number) => void;
  onReset: () => void;
}

interface SliderProps {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (v: number) => void;
  float?: boolean;
}

function Slider({ label, min, max, step, value, onChange, float = false }: SliderProps) {
  return (
    <div className="flex items-center gap-2 text-xs text-muted-foreground">
      <label className="w-14 text-right shrink-0">{label}</label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) =>
          onChange(float ? parseFloat(e.target.value) : parseInt(e.target.value))
        }
        className="flex-1"
      />
      <span className="w-8 font-mono text-right">{value}</span>
    </div>
  );
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
  showSettings,
  onToggleSettings,
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
  const popoverRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!showSettings) return;
    function handleClick(e: MouseEvent) {
      if (popoverRef.current && !popoverRef.current.contains(e.target as Node)) {
        onToggleSettings(false);
      }
    }
    const timer = setTimeout(() => document.addEventListener("click", handleClick), 0);
    return () => {
      clearTimeout(timer);
      document.removeEventListener("click", handleClick);
    };
  }, [showSettings, onToggleSettings]);

  return (
    <div className="absolute top-3 left-0 right-0 z-20 flex flex-col items-center pointer-events-none">
      <div className="flex items-center gap-2 bg-card/80 backdrop-blur-sm rounded-md border border-border shadow-lg px-3 py-1.5 pointer-events-auto flex-wrap justify-center">
        <ToggleGroup
          value={[viewMode]}
          onValueChange={(v) => { if (v.length) onViewModeChange(v[0] as ViewMode); }}
          className="gap-0 border border-border rounded-md"
        >
          <ToggleGroupItem value="2d" size="sm" variant="outline" className="h-7 text-xs border-0 px-2.5 first:rounded-l-md last:rounded-r-md data-[pressed]:bg-primary/20 data-[pressed]:text-primary">2D</ToggleGroupItem>
          <ToggleGroupItem value="3d" size="sm" variant="outline" className="h-7 text-xs border-0 px-2.5 first:rounded-l-md last:rounded-r-md data-[pressed]:bg-primary/20 data-[pressed]:text-primary">3D</ToggleGroupItem>
        </ToggleGroup>

        <div className="w-px h-4 bg-border" />

        <ToggleGroup
          value={[colorMode]}
          onValueChange={(v) => { if (v.length) onColorModeChange(v[0] as ColorMode); }}
          className="gap-0 border border-border rounded-md"
        >
          <ToggleGroupItem value="type" size="sm" variant="outline" className="h-7 text-xs border-0 px-2.5 first:rounded-l-md last:rounded-r-md data-[pressed]:bg-primary/20 data-[pressed]:text-primary">Type</ToggleGroupItem>
          <ToggleGroupItem value="cluster" size="sm" variant="outline" className="h-7 text-xs border-0 px-2.5 first:rounded-l-md last:rounded-r-md data-[pressed]:bg-primary/20 data-[pressed]:text-primary">Cluster</ToggleGroupItem>
          <ToggleGroupItem value="tag" size="sm" variant="outline" className="h-7 text-xs border-0 px-2.5 first:rounded-l-md last:rounded-r-md data-[pressed]:bg-primary/20 data-[pressed]:text-primary">Tag</ToggleGroupItem>
        </ToggleGroup>

        <ToggleGroup
          value={[hullMode]}
          onValueChange={(v) => { if (v.length) onHullModeChange(v[0] as HullMode); }}
          className="gap-0 border border-border rounded-md"
        >
          <ToggleGroupItem value="none" size="sm" variant="outline" className="h-7 text-xs border-0 px-2.5 first:rounded-l-md last:rounded-r-md data-[pressed]:bg-primary/20 data-[pressed]:text-primary">None</ToggleGroupItem>
          <ToggleGroupItem value="cluster" size="sm" variant="outline" className="h-7 text-xs border-0 px-2.5 first:rounded-l-md last:rounded-r-md data-[pressed]:bg-primary/20 data-[pressed]:text-primary">Cluster</ToggleGroupItem>
          <ToggleGroupItem value="tag" size="sm" variant="outline" className="h-7 text-xs border-0 px-2.5 first:rounded-l-md last:rounded-r-md data-[pressed]:bg-primary/20 data-[pressed]:text-primary">Tag</ToggleGroupItem>
          <ToggleGroupItem value="source" size="sm" variant="outline" className="h-7 text-xs border-0 px-2.5 first:rounded-l-md last:rounded-r-md data-[pressed]:bg-primary/20 data-[pressed]:text-primary">Source</ToggleGroupItem>
        </ToggleGroup>

        <div className="w-px h-4 bg-border" />

        <Toggle
          size="sm"
          pressed={entityLayer}
          onPressedChange={onEntityLayerChange}
          className="h-7 text-xs data-[pressed]:bg-primary/20 data-[pressed]:text-primary"
        >
          Entities
        </Toggle>

        <Toggle
          size="sm"
          pressed={showSettings}
          onPressedChange={onToggleSettings}
          className="h-7 text-xs data-[pressed]:bg-primary/20 data-[pressed]:text-primary"
        >
          <Settings className="w-3.5 h-3.5" />
        </Toggle>

        <button
          className="inline-flex items-center justify-center h-7 w-7 rounded-lg text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          onClick={onReset}
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </button>
      </div>

      {showSettings && (
        <div
          ref={popoverRef}
          className="mt-2 bg-card/95 backdrop-blur-sm rounded-lg border border-border shadow-xl px-4 py-3 pointer-events-auto"
          style={{ width: 340 }}
        >
          <div className="flex items-center justify-between mb-3">
            <span className="text-xs font-semibold text-foreground">Settings</span>
          </div>

          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <span className="text-xs text-muted-foreground w-14 text-right shrink-0">Size</span>
              <ToggleGroup
                value={[sizeMode]}
                onValueChange={(v) => { if (v.length) onSizeModeChange(v[0] as SizeMode); }}
                className="gap-0 border border-border rounded-md"
              >
                <ToggleGroupItem value="connections" size="sm" variant="outline" className="h-7 text-xs border-0 px-2 first:rounded-l-md last:rounded-r-md data-[pressed]:bg-primary/20 data-[pressed]:text-primary">Connections</ToggleGroupItem>
                <ToggleGroupItem value="importance" size="sm" variant="outline" className="h-7 text-xs border-0 px-2 first:rounded-l-md last:rounded-r-md data-[pressed]:bg-primary/20 data-[pressed]:text-primary">Importance</ToggleGroupItem>
                <ToggleGroupItem value="uniform" size="sm" variant="outline" className="h-7 text-xs border-0 px-2 first:rounded-l-md last:rounded-r-md data-[pressed]:bg-primary/20 data-[pressed]:text-primary">Uniform</ToggleGroupItem>
              </ToggleGroup>
            </div>

            <Slider
              label="Edges"
              min={0.3}
              max={0.95}
              step={0.05}
              value={similarityThreshold}
              onChange={onSimilarityChange}
              float
            />
            <Slider
              label="Min Size"
              min={2}
              max={10}
              step={1}
              value={minClusterSize}
              onChange={onMinClusterSizeChange}
            />
            {viewMode === "2d" && (
              <Slider
                label="Tightness"
                min={30}
                max={300}
                step={10}
                value={clusterTightness}
                onChange={onClusterTightnessChange}
              />
            )}
            <Slider
              label="Spacing"
              min={viewMode === "2d" ? 100 : 30}
              max={viewMode === "2d" ? 500 : 200}
              step={viewMode === "2d" ? 25 : 10}
              value={spacing}
              onChange={onSpacingChange}
            />
          </div>
        </div>
      )}
    </div>
  );
}
