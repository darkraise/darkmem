import { entityTypeColor } from "@/features/graph/lib/graph-colors"
import type { MemoryPalette } from "@/features/graph/lib/graph-colors"

const DIAMOND = "polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)"

/**
 * The legend's echo of an entity node: the type colour on the outline, the
 * shared neutral body inside. Two clipped layers rather than one bordered
 * element, because `clip-path` cuts a border off with the rest of the shape.
 */
export function EntityTypeSwatch({
  entityType,
  palette,
  size = 10,
}: {
  entityType: string
  palette: MemoryPalette
  size?: number
}) {
  return (
    <span
      className="relative inline-block flex-shrink-0"
      style={{ width: size, height: size }}
    >
      <span
        className="absolute inset-0"
        style={{
          backgroundColor: entityTypeColor(entityType, palette),
          clipPath: DIAMOND,
        }}
      />
      <span
        className="absolute"
        style={{
          inset: 1.5,
          backgroundColor: palette.entityFill,
          clipPath: DIAMOND,
        }}
      />
    </span>
  )
}
