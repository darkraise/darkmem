import { useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
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
  onToggleSettings: () => void;
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

function SegmentedControl<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { label: string; value: T }[];
  value: T;
  onChange: (v: T) => void;
}) {
  return (
    <div className="flex items-center rounded-sm overflow-hidden border border-border">
      {options.map((opt) => (
        <Button
          key={opt.value}
          variant="ghost"
          size="sm"
          className={`h-7 text-xs rounded-none px-2.5 ${
            value === opt.value
              ? "bg-primary/20 text-primary"
              : "text-muted-foreground"
          }`}
          onClick={() => onChange(opt.value)}
        >
          {opt.label}
        </Button>
      ))}
    </div>
  );
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
        onToggleSettings();
      }
    }
    const timer = setTimeout(() => document.addEventListener("click", handleClick), 0);
    return () => {
      clearTimeout(timer);
      document.removeEventListener("click", handleClick);
    };
  }, [showSettings, onToggleSettings]);

  return (
    <div className="absolute top-3 left-0 right-0 z-10 flex flex-col items-center pointer-events-none">
      <div className="flex items-center gap-2 bg-card/80 backdrop-blur-sm rounded-md border border-border shadow-lg px-3 py-1.5 pointer-events-auto flex-wrap justify-center">
        <SegmentedControl
          options={[
            { label: "2D", value: "2d" as ViewMode },
            { label: "3D", value: "3d" as ViewMode },
          ]}
          value={viewMode}
          onChange={onViewModeChange}
        />

        <div className="w-px h-4 bg-border" />

        <SegmentedControl
          options={[
            { label: "Type", value: "type" as ColorMode },
            { label: "Cluster", value: "cluster" as ColorMode },
            { label: "Tag", value: "tag" as ColorMode },
          ]}
          value={colorMode}
          onChange={onColorModeChange}
        />

        <SegmentedControl
          options={[
            { label: "None", value: "none" as HullMode },
            { label: "Cluster", value: "cluster" as HullMode },
            { label: "Tag", value: "tag" as HullMode },
            { label: "Source", value: "source" as HullMode },
          ]}
          value={hullMode}
          onChange={onHullModeChange}
        />

        <div className="w-px h-4 bg-border" />

        <Button
          variant="ghost"
          size="sm"
          className={`h-7 text-xs ${entityLayer ? "bg-primary/20 text-primary" : "text-muted-foreground"}`}
          onClick={() => onEntityLayerChange(!entityLayer)}
        >
          Entities
        </Button>

        <Button
          variant="ghost"
          size="sm"
          className={`h-7 text-xs ${showSettings ? "bg-primary/20 text-primary" : "text-muted-foreground"}`}
          onClick={onToggleSettings}
        >
          <Settings className="w-3.5 h-3.5" />
        </Button>

        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-muted-foreground"
          onClick={onReset}
        >
          <RotateCcw className="w-3.5 h-3.5" />
        </Button>
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
              <SegmentedControl
                options={[
                  { label: "Connections", value: "connections" as SizeMode },
                  { label: "Importance", value: "importance" as SizeMode },
                  { label: "Uniform", value: "uniform" as SizeMode },
                ]}
                value={sizeMode}
                onChange={onSizeModeChange}
              />
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
