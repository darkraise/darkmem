import { Badge } from "darkraise-ui/components/badge"
import { cn } from "darkraise-ui/lib"

export type KnowledgeLayer = 0 | 1 | 2 | 3

const LAYERS: Record<KnowledgeLayer, { name: string; className: string }> = {
  0: { name: "memory", className: "text-muted-foreground" },
  1: { name: "graph", className: "border-chart-3/40 text-chart-3" },
  2: { name: "fact", className: "border-primary/40 text-primary" },
  3: { name: "article", className: "border-chart-2/40 text-chart-2" },
}

export interface LayerChipProps {
  layer: KnowledgeLayer
  className?: string
}

export function LayerChip({ layer, className }: LayerChipProps) {
  const { name, className: layerClass } = LAYERS[layer]
  return (
    <Badge
      variant="outline"
      size="sm"
      className={cn("rounded-sm font-mono font-semibold", layerClass, className)}
    >
      L{layer} · {name}
    </Badge>
  )
}
