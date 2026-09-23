import { useCallback, useRef, useState } from "react"

// Library gap (darkraise-ui 6.6.0): ComboboxContent renders inline as
// `absolute top-full` with no portal and no collision handling, so inside a
// scrolling dialog body its list is clipped by the scroll container and reads as
// sliding under the footer. A portal is not an option: Combobox closes on a
// DOM-containment click-outside check, so a portaled item click would close the
// list before it selects. Retire this once the library flips or portals.
const LIST_HEIGHT = 300

function clippingBounds(el: HTMLElement) {
  let top = 0
  let bottom = window.innerHeight
  for (let node = el.parentElement; node; node = node.parentElement) {
    const overflowY = getComputedStyle(node).overflowY
    if (overflowY === "visible") continue
    const rect = node.getBoundingClientRect()
    top = Math.max(top, rect.top)
    bottom = Math.min(bottom, rect.bottom)
  }
  return { top, bottom }
}

/** Opens a combobox list upward when the space below its anchor, inside every
 * clipping ancestor, is too short and the space above is larger. Put `ref` on
 * an element wrapping the Combobox, pass `onOpenChange` to it and
 * `contentClassName` to its ComboboxContent. */
export function useDropdownPlacement() {
  const ref = useRef<HTMLDivElement>(null)
  const [up, setUp] = useState(false)
  const onOpenChange = useCallback((open: boolean) => {
    if (!open || !ref.current) return
    const rect = ref.current.getBoundingClientRect()
    const bounds = clippingBounds(ref.current)
    const below = bounds.bottom - rect.bottom
    const above = rect.top - bounds.top
    setUp(below < LIST_HEIGHT && above > below)
  }, [])
  return {
    ref,
    onOpenChange,
    contentClassName: up ? "top-auto bottom-full mt-0 mb-1" : undefined,
  }
}
