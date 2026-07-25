import { useCallback, useEffect, useLayoutEffect, useRef, useState } from "react"
import { useVirtualizer } from "@tanstack/react-virtual"

const MAIN_SCROLL_ID = "main-content"

/** The layout shell's scroll container — the element every page scrolls in. */
export function getMainScrollElement(): HTMLElement | null {
  return document.getElementById(MAIN_SCROLL_ID)
}

export interface MainVirtualizerOptions {
  count: number
  estimateSize: (index: number) => number
  overscan?: number
  getItemKey?: (index: number) => string | number
  /** Vertical gap between rows, folded into each measured row's size. */
  gap?: number
}

/**
 * Virtualize a list that scrolls inside the layout shell's `#main-content`
 * rather than its own overflow box. Pages keep their natural document flow
 * (page header, filters, and the list all scroll together) and only the row
 * range is windowed.
 *
 * `scrollMargin` is the distance from the top of the scroll container's
 * content to the top of the list; without it every offset the virtualizer
 * computes is short by the height of everything above the list. It is
 * re-measured after every render and whenever the scroller or the list's
 * parent resizes, because the filter row above the list wraps at narrow
 * widths.
 */
export function useMainVirtualizer({
  count,
  estimateSize,
  overscan = 8,
  getItemKey,
  gap = 0,
}: MainVirtualizerOptions) {
  const listRef = useRef<HTMLDivElement | null>(null)
  const [scrollMargin, setScrollMargin] = useState(0)

  const getScrollElement = useCallback(() => getMainScrollElement(), [])

  const measureMargin = useCallback(() => {
    const list = listRef.current
    const scroller = getMainScrollElement()
    if (!list || !scroller) return
    const next =
      list.getBoundingClientRect().top -
      scroller.getBoundingClientRect().top +
      scroller.scrollTop
    setScrollMargin((prev) => (Math.abs(prev - next) < 1 ? prev : next))
  }, [])

  useLayoutEffect(measureMargin)

  useEffect(() => {
    if (typeof ResizeObserver === "undefined") return
    const scroller = getMainScrollElement()
    const parent = listRef.current?.parentElement
    if (!scroller && !parent) return
    const observer = new ResizeObserver(measureMargin)
    if (scroller) observer.observe(scroller)
    if (parent) observer.observe(parent)
    return () => observer.disconnect()
  }, [measureMargin])

  const virtualizer = useVirtualizer({
    count,
    getScrollElement,
    estimateSize,
    overscan,
    getItemKey,
    scrollMargin,
    gap,
  })

  return { listRef, virtualizer, scrollMargin }
}
