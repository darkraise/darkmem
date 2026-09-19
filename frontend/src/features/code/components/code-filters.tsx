import { Button } from "darkraise-ui/components/button"
import { Checkbox } from "darkraise-ui/components/checkbox"
import { cn } from "darkraise-ui/lib"
import type { CodeNodeKind } from "@/features/code/types"
import { chartVar } from "./code-canvas"

const KIND_CHART: Record<CodeNodeKind, number> = {
  file: 1,
  module: 1,
  class: 2,
  struct: 2,
  interface: 2,
  trait: 2,
  enum: 2,
  namespace: 2,
  impl: 2,
  type: 2,
  property: 2,
  method: 3,
  function: 3,
  route: 3,
  tool: 3,
}

const KIND_ORDER: CodeNodeKind[] = [
  "file",
  "module",
  "class",
  "struct",
  "interface",
  "trait",
  "enum",
  "namespace",
  "impl",
  "type",
  "method",
  "function",
  "property",
  "route",
  "tool",
]

export function CodeFilters({
  counts,
  hidden,
  onToggle,
  onReset,
}: {
  counts: Map<CodeNodeKind, number>
  hidden: ReadonlySet<CodeNodeKind>
  onToggle: (kind: CodeNodeKind) => void
  onReset: () => void
}) {
  const present = KIND_ORDER.filter((kind) => (counts.get(kind) ?? 0) > 0)
  const shown = present
    .filter((kind) => !hidden.has(kind))
    .reduce((sum, kind) => sum + (counts.get(kind) ?? 0), 0)
  const total = present.reduce((sum, kind) => sum + (counts.get(kind) ?? 0), 0)

  return (
    <div className="min-h-0 flex-1 space-y-2 overflow-auto p-2.5">
      <p className="text-muted-foreground text-sm">
        Node types to draw. Switching one off removes those nodes and every
        edge touching them — it does not re-run the index.
      </p>
      <div className="space-y-1">
        {present.map((kind) => {
          const on = !hidden.has(kind)
          return (
            <div
              key={kind}
              className={cn(
                "flex items-center gap-2 rounded-sm px-1 py-1 text-sm",
                on ? "hover:bg-muted/50" : "text-muted-foreground",
              )}
            >
              <Checkbox
                id={`kind-filter-${kind}`}
                checked={on}
                onCheckedChange={() => onToggle(kind)}
              />
              <span
                aria-hidden
                className="h-2 w-2 shrink-0 rounded-[2px]"
                style={{ background: chartVar(KIND_CHART[kind]) }}
              />
              <label
                htmlFor={`kind-filter-${kind}`}
                className="min-w-0 flex-1 cursor-pointer truncate font-mono"
              >
                {kind}
              </label>
              <span className="shrink-0 font-mono text-xs">
                {counts.get(kind)}
              </span>
            </div>
          )
        })}
      </div>
      <div className="border-border flex items-center gap-2 border-t pt-2">
        <span className="text-muted-foreground font-mono text-sm">
          {shown} of {total} drawn
        </span>
        <Button
          variant="ghost"
          className="ml-auto"
          disabled={hidden.size === 0}
          onClick={onReset}
        >
          Show all
        </Button>
      </div>
    </div>
  )
}
