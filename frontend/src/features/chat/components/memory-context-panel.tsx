import { useState } from "react"
import { Brain, Zap, ChevronDown, ChevronUp, X, Eye, EyeOff } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import type { MemoryLayers } from "@/hooks/api"

interface MemoryContextPanelProps {
  layers: MemoryLayers
  wing: string | undefined
  onClear: () => void
}

export function MemoryContextPanel({ layers, wing, onClear }: MemoryContextPanelProps) {
  const [expanded, setExpanded] = useState(false)
  const [showRaw, setShowRaw] = useState(false)

  return (
    <div
      className="mx-4 mb-2 rounded-xl border border-cyan-500/20 bg-cyan-500/5 overflow-hidden"
      style={{ boxShadow: "0 0 12px rgba(6,182,212,0.06)" }}
    >
      <div className="flex items-center gap-2 px-3 py-2">
        <Brain className="w-3.5 h-3.5 text-cyan-400 shrink-0" />
        <span className="text-xs text-cyan-300 font-medium flex-1">
          Memory context active
          {wing && (
            <span className="text-cyan-500 font-mono ml-1.5">· {wing}</span>
          )}
        </span>
        <span
          className="font-mono text-xs text-cyan-400/70 shrink-0"
          title="Approximate tokens loaded into context"
        >
          ~{layers.token_count} tokens
        </span>
        <div className="flex items-center gap-0.5 ml-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-5 w-5 text-muted-foreground/50 hover:text-cyan-300"
            onClick={() => setExpanded((v) => !v)}
            title={expanded ? "Collapse" : "Expand layers"}
          >
            {expanded ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-5 w-5 text-muted-foreground/50 hover:text-red-400"
            onClick={onClear}
            title="Clear memory context"
          >
            <X className="w-3 h-3" />
          </Button>
        </div>
      </div>

      {expanded && (
        <div className="border-t border-cyan-500/10 px-3 py-2.5 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <LayerBadge label="L0" description="Identity" tokenEstimate={100} />
              <LayerBadge label="L1" description="Story" tokenEstimate={Math.max(0, layers.token_count - 100)} />
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="h-5 w-5 text-muted-foreground/50 hover:text-cyan-300"
              onClick={() => setShowRaw((v) => !v)}
              title={showRaw ? "Hide raw content" : "Show raw content"}
            >
              {showRaw ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
            </Button>
          </div>

          {showRaw && (
            <div className="space-y-2">
              <LayerContent label="L0" content={layers.l0} />
              <LayerContent label="L1" content={layers.l1} />
              {layers.l2_hint && (
                <div className="text-xs text-muted-foreground/40 font-mono border-t border-cyan-500/10 pt-2">
                  {layers.l2_hint}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function LayerBadge({
  label,
  description,
  tokenEstimate,
}: {
  label: string
  description: string
  tokenEstimate: number
}) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="font-mono text-[10px] font-bold text-cyan-400 bg-cyan-500/10 border border-cyan-500/25 px-1.5 py-0.5 rounded">
        {label}
      </span>
      <span className="text-xs text-muted-foreground/60">{description}</span>
      <span className="font-mono text-[10px] text-cyan-500/60">~{tokenEstimate}t</span>
    </div>
  )
}

function LayerContent({ label, content }: { label: string; content: string }) {
  return (
    <div className="space-y-1">
      <span className="font-mono text-[10px] text-cyan-500/60 uppercase tracking-widest">{label}</span>
      <pre className="text-[11px] text-muted-foreground/60 whitespace-pre-wrap font-mono leading-relaxed bg-black/20 rounded-lg p-2 max-h-28 overflow-auto scrollbar-thin">
        {content}
      </pre>
    </div>
  )
}

interface WakeUpButtonProps {
  loading: boolean
  loaded: boolean
  wing: string | undefined
  onWakeUp: () => void
}

export function WakeUpButton({ loading, loaded, wing, onWakeUp }: WakeUpButtonProps) {
  return (
    <Button
      size="sm"
      variant="outline"
      className={[
        "h-7 gap-1.5 text-xs border transition-all duration-300",
        loaded
          ? "border-cyan-500/40 text-cyan-300 bg-cyan-500/8 hover:bg-cyan-500/15 shadow-[0_0_10px_rgba(6,182,212,0.12)]"
          : "border-border text-muted-foreground hover:border-cyan-500/30 hover:text-cyan-300",
      ].join(" ")}
      onClick={onWakeUp}
      disabled={loading}
      title={loaded ? "Reload memory layers" : "Load L0+L1 memory context"}
    >
      {loading ? (
        <Zap className="w-3.5 h-3.5 animate-pulse text-cyan-400" />
      ) : loaded ? (
        <Brain className="w-3.5 h-3.5 text-cyan-400" />
      ) : (
        <Brain className="w-3.5 h-3.5" />
      )}
      {loading ? "Loading…" : loaded ? "Active" : "Wake Up"}
      {loaded && wing && (
        <span className="font-mono text-cyan-500/70 text-[10px]">{wing}</span>
      )}
    </Button>
  )
}

interface WingSelectorProps {
  wings: string[]
  selected: string | undefined
  onChange: (wing: string | undefined) => void
}

export function WingSelector({ wings, selected, onChange }: WingSelectorProps) {
  return (
    <Select
      value={selected ?? "__all__"}
      onValueChange={(v) => onChange(v === "__all__" ? undefined : v)}
    >
      <SelectTrigger
        className="h-7 text-xs bg-transparent border-border text-muted-foreground hover:border-cyan-500/30 hover:text-cyan-300 focus:border-cyan-500/40 w-auto"
        title="Scope memory layers to a project wing"
      >
        <SelectValue placeholder="All wings" />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value="__all__">All wings</SelectItem>
        {wings.map((w) => (
          <SelectItem key={w} value={w}>
            {w}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
