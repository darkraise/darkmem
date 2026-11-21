export interface LabelBox {
  id: string
  /** The node centre; the label sits to its right, or its left when flipped. */
  x: number
  y: number
  text: string
}

export type LabelSide = "right" | "left"

// The explorer's label: 10.5px monospace at x±12, baseline y+4, in viewBox
// units. A monospace glyph is ~0.6em wide; the extents carry a little slack
// so two labels the estimate calls clear do not touch once rendered.
export const LABEL_OFFSET_X = 12
const CHAR_WIDTH = 6.5
const ASCENT = 10
const DESCENT = 4

interface Box {
  x1: number
  x2: number
  y1: number
  y2: number
}

function boxFor(label: LabelBox, side: LabelSide): Box {
  const width = label.text.length * CHAR_WIDTH
  const x1 =
    side === "right"
      ? label.x + LABEL_OFFSET_X
      : label.x - LABEL_OFFSET_X - width
  return { x1, x2: x1 + width, y1: label.y - ASCENT, y2: label.y + DESCENT }
}

/** Which side a label fits on inside [0, width]: right unless that runs
 *  past the right edge and the left side does not run past the left one. */
export function labelSide(label: LabelBox, width: number): LabelSide {
  const right = boxFor(label, "right")
  if (right.x2 <= width) return "right"
  return boxFor(label, "left").x1 >= 0 ? "left" : "right"
}

/** Greedy, in input order: each label takes the side that keeps it inside
 *  the canvas (`width`), and is placed unless its box overlaps one already
 *  placed — in which case the other side is tried before hiding it. The
 *  caller shows a hidden label while its node is hovered, focused or
 *  selected. */
export function placeLabels(
  labels: readonly LabelBox[],
  width = Number.POSITIVE_INFINITY,
): Map<string, LabelSide> {
  const placed: Box[] = []
  const visible = new Map<string, LabelSide>()
  const fits = (box: Box) =>
    box.x1 >= 0 &&
    box.x2 <= width &&
    !placed.some(
      (p) => box.x1 < p.x2 && p.x1 < box.x2 && box.y1 < p.y2 && p.y1 < box.y2,
    )
  for (const label of labels) {
    const preferred = labelSide(label, width)
    const other: LabelSide = preferred === "right" ? "left" : "right"
    for (const side of [preferred, other]) {
      const box = boxFor(label, side)
      if (!fits(box)) continue
      placed.push(box)
      visible.set(label.id, side)
      break
    }
  }
  return visible
}
