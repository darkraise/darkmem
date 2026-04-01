import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { RotateCcw } from "lucide-react";
import type { SizeMode } from "@/lib/graph-utils";

interface Graph3DToolbarProps {
  sizeMode: SizeMode;
  onSizeModeChange: (mode: SizeMode) => void;
  spacing: number;
  onSpacingChange: (value: number) => void;
}

export function Graph3DToolbar({
  sizeMode,
  onSizeModeChange,
  spacing,
  onSpacingChange,
}: Graph3DToolbarProps) {
  return (
    <div className="absolute top-3 left-1/2 z-10 flex -translate-x-1/2 items-center gap-3 rounded-lg border border-border bg-card/90 px-4 py-2 shadow-lg backdrop-blur-sm">
      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Size</span>
        <Select value={sizeMode} onValueChange={(v) => onSizeModeChange(v as SizeMode)}>
          <SelectTrigger className="h-7 w-[120px] text-xs">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="connections">Connections</SelectItem>
            <SelectItem value="importance">Importance</SelectItem>
            <SelectItem value="uniform">Uniform</SelectItem>
          </SelectContent>
        </Select>
      </div>

      <div className="h-4 w-px bg-border" />

      <div className="flex items-center gap-2">
        <span className="text-xs text-muted-foreground">Space</span>
        <input
          type="range"
          min={30}
          max={200}
          step={10}
          value={spacing}
          onChange={(e) => onSpacingChange(Number(e.target.value))}
          className="h-1 w-24 cursor-pointer accent-primary"
        />
      </div>

      <div className="h-4 w-px bg-border" />

      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7"
        onClick={() => {
          onSizeModeChange("connections");
          onSpacingChange(50);
        }}
        title="Reset to defaults"
      >
        <RotateCcw className="h-3.5 w-3.5" />
      </Button>
    </div>
  );
}
