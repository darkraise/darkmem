export interface LabelBox {
  id: string
  /** The node centre; the label starts to its right. */
  x: number
  y: number
  text: string
}

// The explorer's label: 10.5px monospace at x+12, baseline y+4, in viewBox
// units. A monospace glyph is ~0.6em wide.
const LABEL_OFFSET_X = 12
const CHAR_WIDTH = 6.3
const ASCENT = 8
const DESCENT = 4

/** Greedy, in input order: a label is placed unless its box overlaps a box
 *  already placed. The caller shows a hidden label while its node is
 *  hovered, focused or selected. */
export function visibleLabelIds(labels: readonly LabelBox[]): Set<string> {
  const placed: Array<{ x1: number; x2: number; y1: number; y2: number }> = []
  const visible = new Set<string>()
  for (const label of labels) {
    const box = {
      x1: label.x + LABEL_OFFSET_X,
      x2: label.x + LABEL_OFFSET_X + label.text.length * CHAR_WIDTH,
      y1: label.y - ASCENT,
      y2: label.y + DESCENT,
    }
    const collides = placed.some(
      (p) => box.x1 < p.x2 && p.x1 < box.x2 && box.y1 < p.y2 && p.y1 < box.y2,
    )
    if (collides) continue
    placed.push(box)
    visible.add(label.id)
  }
  return visible
}
