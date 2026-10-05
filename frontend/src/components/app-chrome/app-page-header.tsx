import { useEffect, useRef, useState } from "react"
import { Link } from "@tanstack/react-router"
import { ArrowLeft } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import { splitNavHref } from "@/providers/router-adapter"
import { usePageChrome } from "./page-chrome"

/**
 * Page identity block for the app header bar (rendered via the layout's
 * `headerSlot`): an optional back button, then icon + title + description +
 * actions. darkraise-ui's PageHeader has no icon slot and renders
 * in-content, so this is a custom component fed by the page-chrome store.
 *
 * The back button is icon-only and names its destination in a tooltip. It
 * used to render the label as text beside the arrow, which the top-nav
 * layout then hid in CSS -- so that layout already showed a bare arrow with
 * nothing anywhere saying where it went. One treatment everywhere, and the
 * destination is always reachable.
 */
export function AppPageHeader() {
  const { icon: Icon, title, description, parent, actions } = usePageChrome()

  if (!title) return null

  const back = parent ? splitNavHref(parent.href) : null

  return (
    <div className="flex min-w-0 flex-1 items-center gap-2.5 text-left">
      {parent && back && (
        <TooltipProvider delayDuration={150}>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                asChild
                className="text-muted-foreground hover:text-foreground -ml-1 shrink-0"
              >
                <Link
                  to={back.to}
                  search={back.search}
                  aria-label={`Back to ${parent.label}`}
                >
                  <ArrowLeft aria-hidden className="size-4" />
                </Link>
              </Button>
            </TooltipTrigger>
            <TooltipContent>Back to {parent.label}</TooltipContent>
          </Tooltip>
        </TooltipProvider>
      )}
      {/* The icon repeats the sidebar's; below md the title needs its width
          (a detail page's title was cut to "Memory…" at 390px). The title
          truncates rather than holding its full width, so a crowded bar
          ellipsises it instead of letting the actions paint over the
          controls; the description gives way first. */}
      {Icon && (
        <span className="bg-primary/10 text-primary-text hidden h-7 w-7 shrink-0 items-center justify-center rounded-md md:flex">
          <Icon aria-hidden className="h-4 w-4" />
        </span>
      )}
      <h1 className="min-w-0 truncate text-sm font-semibold">{title}</h1>
      {description && <HeaderDescription text={description} />}
      {actions && (
        <div className="dm-header-actions ml-auto flex shrink-0 items-center gap-2 pl-2">
          {actions}
        </div>
      )}
    </div>
  )
}

/** One line, truncated; when it does not fit, the full text is a tooltip
 *  away. Measured on the box rather than assumed from the string length,
 *  because what fits depends on the header's other contents. */
function HeaderDescription({ text }: { text: string }) {
  const boxRef = useRef<HTMLDivElement>(null)
  const [truncated, setTruncated] = useState(false)
  const [hovered, setHovered] = useState(false)

  useEffect(() => {
    const line = boxRef.current?.querySelector("p")
    if (!line) return
    const measure = () => setTruncated(line.scrollWidth > line.clientWidth)
    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(line)
    return () => observer.disconnect()
  }, [text])

  return (
    <div
      ref={boxRef}
      className="dm-chrome-desc border-border hidden min-w-0 shrink-[20] border-l pl-2.5 lg:block"
    >
      <TooltipProvider delayDuration={300}>
        <Tooltip open={truncated && hovered} onOpenChange={setHovered}>
          <TooltipTrigger asChild>
            <p
              tabIndex={truncated ? 0 : undefined}
              // Radix opens on its own pointer/focus handling, but this
              // tooltip is controlled so that it opens only when the line
              // actually overflows; the trigger therefore reports hover and
              // focus itself.
              onPointerEnter={() => setHovered(true)}
              onPointerLeave={() => setHovered(false)}
              onFocus={() => setHovered(true)}
              onBlur={() => setHovered(false)}
              className="text-muted-foreground truncate text-sm"
            >
              {text}
            </p>
          </TooltipTrigger>
          <TooltipContent className="max-w-md">{text}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    </div>
  )
}
