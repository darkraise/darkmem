import type { ComponentProps } from "react"
import type { LucideIcon } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"

/**
 * An icon-only action button that still says what it does.
 *
 * `size="icon"` drops the label, which is the point — a row of cards each
 * repeating the word "Edit" spends a lot of width saying something a pencil
 * says on its own. What it must not drop is the *name*: without one the
 * control is an unlabelled button to a screen reader and a guess to anyone
 * who does not recognise the glyph. So `label` is required, and it does
 * double duty as the accessible name and the tooltip text.
 *
 * Use it where the icon is unambiguous. An action whose meaning lives in its
 * verb — "Prune caches", "Run now", "Save" — keeps its label instead.
 */
export function IconButton({
  icon: Icon,
  label,
  side = "top",
  ...props
}: {
  icon: LucideIcon
  /** The accessible name AND the tooltip. Not optional. */
  label: string
  side?: "top" | "right" | "bottom" | "left"
} & Omit<ComponentProps<typeof Button>, "size" | "children" | "aria-label">) {
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip>
        <TooltipTrigger asChild>
          <Button size="icon" aria-label={label} {...props}>
            <Icon aria-hidden className="size-[var(--icon-size)]" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side={side} className="text-sm font-normal normal-case">
          {label}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
