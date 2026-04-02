import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { SizeMode } from "@/lib/graph-utils";

type ViewMode = "2d" | "3d";

interface GraphToolbarProps {
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  sizeMode: SizeMode;
  onSizeModeChange: (mode: SizeMode) => void;
  similarityThreshold: number;
  onSimilarityChange: (v: number) => void;
  clusterMinScore: number;
  onClusterMinScoreChange: (v: number) => void;
  minClusterSize: number;
  onMinClusterSizeChange: (v: number) => void;
  spacing: number;
  onSpacingChange: (v: number) => void;
  clusterTightness: number;
  onClusterTightnessChange: (v: number) => void;
  hullMode: "clusters" | "tags";
  onHullModeChange: (v: "clusters" | "tags") => void;
  onReset: () => void;
}

interface SliderProps {
  label: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (v: number) => void;
  width?: string;
  displayWidth?: string;
  float?: boolean;
}

function Slider({
  label,
  min,
  max,
  step,
  value,
  onChange,
  width = "w-14",
  displayWidth = "w-5",
  float = false,
}: SliderProps) {
  return (
    <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <label>{label}</label>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) =>
          onChange(float ? parseFloat(e.target.value) : parseInt(e.target.value))
        }
        className={width}
      />
      <span className={`font-mono ${displayWidth}`}>{value}</span>
    </div>
  );
}

export function GraphToolbar({
  viewMode,
  onViewModeChange,
  sizeMode,
  onSizeModeChange,
  similarityThreshold,
  onSimilarityChange,
  clusterMinScore,
  onClusterMinScoreChange,
  minClusterSize,
  onMinClusterSizeChange,
  spacing,
  onSpacingChange,
  clusterTightness,
  onClusterTightnessChange,
  hullMode,
  onHullModeChange,
  onReset,
}: GraphToolbarProps) {
  return (
    <div className="absolute top-3 left-0 right-0 z-10 flex justify-center pointer-events-none">
      <div className="flex items-center gap-2 bg-card/80 backdrop-blur-sm rounded-md border border-border shadow-lg px-3 py-1.5 pointer-events-auto flex-wrap">
        {/* View toggle */}
        <div className="flex items-center rounded-sm overflow-hidden border border-border">
          <Button
            variant="ghost"
            size="sm"
            className={`h-7 text-xs rounded-none px-2.5 ${viewMode === "2d" ? "bg-primary/20 text-primary" : "text-muted-foreground"}`}
            onClick={() => onViewModeChange("2d")}
          >
            2D
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className={`h-7 text-xs rounded-none px-2.5 ${viewMode === "3d" ? "bg-primary/20 text-primary" : "text-muted-foreground"}`}
            onClick={() => onViewModeChange("3d")}
          >
            3D
          </Button>
        </div>

        <div className="w-px h-4 bg-border" />

        {/* Shared: size mode */}
        <Select value={sizeMode} onValueChange={(v) => onSizeModeChange(v as SizeMode)}>
          <SelectTrigger className="w-36 h-7 text-xs border-0 bg-transparent p-0 pr-2">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="connections">Size: Connections</SelectItem>
            <SelectItem value="importance">Size: Importance</SelectItem>
            <SelectItem value="uniform">Size: Uniform</SelectItem>
          </SelectContent>
        </Select>

        {/* Shared: API param sliders */}
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
          label="Cluster"
          min={0.2}
          max={0.8}
          step={0.05}
          value={clusterMinScore}
          onChange={onClusterMinScoreChange}
          float
        />
        <Slider
          label="Min"
          min={2}
          max={10}
          step={1}
          value={minClusterSize}
          onChange={onMinClusterSizeChange}
          width="w-10"
          displayWidth="w-3"
        />

        {/* Shared: space slider — range differs by view */}
        {viewMode === "2d" ? (
          <>
            <Slider
              label="Tight"
              min={30}
              max={300}
              step={10}
              value={clusterTightness}
              onChange={onClusterTightnessChange}
            />
            <Slider
              label="Space"
              min={100}
              max={500}
              step={25}
              value={spacing}
              onChange={onSpacingChange}
            />
            <div className="flex items-center rounded-sm overflow-hidden border border-border">
              <Button
                variant="ghost"
                size="sm"
                className={`h-7 text-xs rounded-none px-2.5 ${hullMode === "clusters" ? "bg-primary/20 text-primary" : "text-muted-foreground"}`}
                onClick={() => onHullModeChange("clusters")}
              >
                Clusters
              </Button>
              <Button
                variant="ghost"
                size="sm"
                className={`h-7 text-xs rounded-none px-2.5 ${hullMode === "tags" ? "bg-primary/20 text-primary" : "text-muted-foreground"}`}
                onClick={() => onHullModeChange("tags")}
              >
                Tags
              </Button>
            </div>
          </>
        ) : (
          <Slider
            label="Space"
            min={30}
            max={200}
            step={10}
            value={spacing}
            onChange={onSpacingChange}
          />
        )}

        {/* Reset */}
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-muted-foreground"
          onClick={onReset}
        >
          Reset
        </Button>
      </div>
    </div>
  );
}
