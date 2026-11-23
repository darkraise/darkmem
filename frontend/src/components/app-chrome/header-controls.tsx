import { useState } from "react"
import type { ReactNode } from "react"
import { Search, SlidersHorizontal } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "darkraise-ui/components/popover"
import { useLayoutStore } from "darkraise-ui/layout"
import { DetailLevelToggle } from "@/components/darkmem"
import { useMediaQuery } from "@/hooks/use-media-query"
import { MinimalThemeSwitcher } from "./minimal-theme-switcher"
import { ProjectSwitcher } from "./project-switcher"

/** Inline controls need roughly 600px beside the page title, its actions and
 *  the account menu. Below 1280px (header ≈ 1024px with the expanded rail)
 *  they crowded the title until the actions overlapped the project pill and
 *  the account controls went off-screen, so the overflow
 *  popover takes over from here down rather than only below `md`. */
export const HEADER_WIDE_QUERY = "(min-width: 1280px)"

/** Below `md` the sidebar rail (and the palette trigger it hosts) is hidden. */
const RAIL_HIDDEN_QUERY = "(max-width: 767.98px)"

/** Opens the rail's command palette from outside the rail.
 *
 *  darkraise-ui gap (SidebarLayout, 6.x): `SearchCommand` keeps its `open`
 *  state private and the layout hard-codes `showSearch: false` on its header
 *  and passes no search to `MobileDrawer`, so below `md` the only way into
 *  the palette is the Ctrl/⌘ K shortcut a phone does not have. The rail's
 *  `SearchCommand` stays mounted while the rail is `display: none` and
 *  listens for that shortcut on `window`, so this button sends it. Retire it
 *  once the library exposes a search trigger for the drawer. */
function openCommandPalette() {
  window.dispatchEvent(
    new KeyboardEvent("keydown", { key: "k", ctrlKey: true, bubbles: true }),
  )
}

/**
 * The header's view controls. From 1280px up they sit inline beside the page
 * title; below it they share one overflow popover so the title keeps the bar.
 * A JS media query rather than breakpoint classes, because the narrow branch
 * swaps the container rather than restyling it.
 */
export function HeaderControls({
  projectDisabledReason,
}: {
  projectDisabledReason?: string
}) {
  const wide = useMediaQuery(HEADER_WIDE_QUERY)
  const railHidden = useMediaQuery(RAIL_HIDDEN_QUERY)
  const layout = useLayoutStore((s) => s.layout)
  const [open, setOpen] = useState(false)

  if (wide) {
    return (
      <div className="flex min-w-0 shrink-0 items-center gap-2">
        <ProjectSwitcher disabledReason={projectDisabledReason} />
        <DetailLevelToggle />
        <MinimalThemeSwitcher />
      </div>
    )
  }

  return (
    <>
      {/* Only the sidebar layout hides its search with the rail; the other
          two layouts keep the library's trigger in the header. */}
      {railHidden && layout === "sidebar" && (
        <Button
          variant="ghost"
          size="icon"
          aria-label="Go to page"
          onClick={openCommandPalette}
        >
          <Search aria-hidden className="size-4" />
        </Button>
      )}
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button variant="ghost" size="icon" aria-label="View options">
            <SlidersHorizontal aria-hidden className="size-4" />
          </Button>
        </PopoverTrigger>
        <PopoverContent
          side="bottom"
          align="end"
          className="grid w-80 max-w-[calc(100vw-1rem)] grid-cols-[4.5rem_minmax(0,1fr)] items-center gap-x-3 gap-y-3 p-3"
          // The switcher opens a popover of its own, which portals outside
          // this one; a click inside it must not close it.
          onInteractOutside={(event) => {
            const target = event.target
            if (
              target instanceof Element &&
              target.closest(".dr-popover-content")
            ) {
              event.preventDefault()
            }
          }}
        >
          {/* Each control gets a caption row: in this narrow list they read
              as two pills, a pair of icons and a palette with nothing saying
              what any of them governs. */}
          <ControlRow label="Project">
            <ProjectSwitcher disabledReason={projectDisabledReason} />
          </ControlRow>
          <DetailLevelToggle variant="row" />
          <ControlRow label="Theme">
            <MinimalThemeSwitcher />
          </ControlRow>
        </PopoverContent>
      </Popover>
    </>
  )
}

function ControlRow({
  label,
  children,
}: {
  label: string
  children: ReactNode
}) {
  return (
    <>
      <span className="text-muted-foreground text-xs font-medium">{label}</span>
      <div className="flex min-w-0 items-center">{children}</div>
    </>
  )
}
