import { useState } from "react"
import { SlidersHorizontal } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "darkraise-ui/components/popover"
import { DetailLevelToggle } from "@/components/darkmem"
import { useMediaQuery } from "@/hooks/use-media-query"
import { ContextChip } from "./context-chip"
import { MinimalThemeSwitcher } from "./minimal-theme-switcher"
import { ProjectSwitcher } from "./project-switcher"

export const HEADER_WIDE_QUERY = "(min-width: 768px)"

/**
 * The header's view controls. From `md` up they sit inline beside the page
 * title; below it they share one overflow popover so the title keeps the bar.
 * A JS media query rather than `md:` classes, because the narrow branch swaps
 * the container rather than restyling it.
 */
export function HeaderControls({
  projectDisabledReason,
}: {
  projectDisabledReason?: string
}) {
  const wide = useMediaQuery(HEADER_WIDE_QUERY)
  const [open, setOpen] = useState(false)

  const controls = (
    <>
      <ProjectSwitcher disabledReason={projectDisabledReason} />
      <ContextChip />
      <DetailLevelToggle />
      <MinimalThemeSwitcher />
    </>
  )

  if (wide) {
    return <div className="flex shrink-0 items-center gap-2">{controls}</div>
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" size="icon" aria-label="View options">
          <SlidersHorizontal aria-hidden className="size-4" />
        </Button>
      </PopoverTrigger>
      <PopoverContent
        side="bottom"
        align="end"
        className="flex w-72 flex-col items-start gap-3 p-3"
        // The switcher and the context chip open popovers of their own, which
        // portal outside this one; a click inside them must not close it.
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
        {controls}
      </PopoverContent>
    </Popover>
  )
}
