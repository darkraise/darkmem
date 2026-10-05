import { useCallback, useEffect, useRef, useState, type ReactNode } from "react"
import { ChevronLeft, ChevronRight } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { TabsList } from "darkraise-ui/components/tabs"
import { cn } from "darkraise-ui/lib"

/**
 * darkraise-ui gap: `TabsList` has no overflow behaviour — a strip with more
 * tabs than fit clips its first and last tab. This keeps the library list and
 * only adds a horizontal scroller around it: the list sizes to its tabs, the
 * edge with more tabs past it fades, and the active tab scrolls into view.
 *
 * `scrollButtons` adds a chevron on each edge that has tabs past it. The fade
 * alone left a pointer user guessing that a ten-tab strip scrolled at all
 * (Settings hid its last tab at 1440px with the sidebar open).
 */
export function ScrollTabsList({
  activeValue,
  className,
  scrollButtons = false,
  children,
}: {
  activeValue: string
  className?: string
  scrollButtons?: boolean
  children: ReactNode
}) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [edges, setEdges] = useState({ start: false, end: false })

  const measure = useCallback(() => {
    const el = scrollRef.current
    if (!el) return
    setEdges({
      start: el.scrollLeft > 1,
      end: el.scrollLeft + el.clientWidth < el.scrollWidth - 1,
    })
  }, [])

  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    el.addEventListener("scroll", measure, { passive: true })
    return () => {
      observer.disconnect()
      el.removeEventListener("scroll", measure)
    }
  }, [measure])

  // Chevrons appear once the strip is found to overflow, which narrows it;
  // re-run then so the active tab is not left under the right chevron.
  const chevronsShown = scrollButtons && (edges.start || edges.end)
  useEffect(() => {
    scrollRef.current
      ?.querySelector<HTMLElement>('[role="tab"][data-state="active"]')
      ?.scrollIntoView({ block: "nearest", inline: "nearest" })
  }, [activeValue, chevronsShown])

  const scrollBy = (direction: -1 | 1) => {
    const el = scrollRef.current
    if (!el) return
    el.scrollBy({ left: direction * el.clientWidth * 0.8, behavior: "smooth" })
  }

  const strip = (
    <div
      ref={scrollRef}
      className={cn("dm-tab-scroll", scrollButtons && "min-w-0 flex-1")}
      data-fade-start={edges.start || undefined}
      data-fade-end={edges.end || undefined}
    >
      <TabsList className={cn("w-max min-w-full", className)}>
        {children}
      </TabsList>
    </div>
  )

  if (!scrollButtons) return strip

  // Both chevrons render whenever the strip overflows at all, each disabled
  // at its own end: showing one only once its edge hides a tab would shrink
  // the strip mid-scroll and push the last tab back out of view. The strip
  // keeps its child slot either way, so its ref and observers survive.
  const overflows = edges.start || edges.end

  return (
    <div className="flex items-center gap-1">
      {overflows && (
        <Button
          variant="ghost"
          size="icon"
          className="shrink-0"
          aria-label="Scroll tabs left"
          disabled={!edges.start}
          onClick={() => scrollBy(-1)}
        >
          <ChevronLeft aria-hidden className="size-4" />
        </Button>
      )}
      {strip}
      {overflows && (
        <Button
          variant="ghost"
          size="icon"
          className="shrink-0"
          aria-label="Scroll tabs right"
          disabled={!edges.end}
          onClick={() => scrollBy(1)}
        >
          <ChevronRight aria-hidden className="size-4" />
        </Button>
      )}
    </div>
  )
}
