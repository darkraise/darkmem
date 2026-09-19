import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react"
import { TabsList } from "darkraise-ui/components/tabs"
import { cn } from "darkraise-ui/lib"

/**
 * darkraise-ui gap: `TabsList` has no overflow behaviour — a strip with more
 * tabs than fit clips its first and last tab. This keeps the library list and
 * only adds a horizontal scroller around it: the list sizes to its tabs, the
 * edge with more tabs past it fades, and the active tab scrolls into view.
 */
export function ScrollTabsList({
  activeValue,
  className,
  children,
}: {
  activeValue: string
  className?: string
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

  useEffect(() => {
    scrollRef.current
      ?.querySelector<HTMLElement>('[role="tab"][data-state="active"]')
      ?.scrollIntoView({ block: "nearest", inline: "nearest" })
  }, [activeValue])

  return (
    <div
      ref={scrollRef}
      className="dm-tab-scroll"
      data-fade-start={edges.start || undefined}
      data-fade-end={edges.end || undefined}
    >
      <TabsList className={cn("w-max min-w-full", className)}>{children}</TabsList>
    </div>
  )
}
