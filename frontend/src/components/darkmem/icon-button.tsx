import { useRef, useState, type ComponentProps } from "react"
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
  // Controlled so a click can close it and keep it closed: the pointer is
  // still over the button afterwards, and a button that disables while its
  // action runs gets a fresh pointerenter when it re-enables, so the tooltip
  // reopened over whatever the action produced (a toast, a dialog). It shows
  // again once the pointer has left, or on the next keyboard focus.
  const [open, setOpen] = useState(false)
  const clicked = useRef(false)
  const { onClick } = props
  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip
        open={open}
        onOpenChange={(next) => {
          if (next && clicked.current) return
          setOpen(next)
        }}
      >
        <TooltipTrigger
          asChild
          onPointerLeave={(event) => {
            // A button that disables gets a pointerleave with the pointer
            // still on it; only a real exit re-arms the tooltip.
            const box = event.currentTarget.getBoundingClientRect()
            const inside =
              event.clientX >= box.left &&
              event.clientX <= box.right &&
              event.clientY >= box.top &&
              event.clientY <= box.bottom
            if (!inside) clicked.current = false
          }}
          // Not on blur: disabling the button blurs it, and the reset would
          // let the re-enable's pointerenter reopen it. Keyboard focus is a
          // fresh intent, so that does reset.
          onFocus={(event) => {
            if (event.currentTarget.matches(":focus-visible")) {
              clicked.current = false
            }
          }}
        >
          <Button
            size="icon"
            aria-label={label}
            {...props}
            onClick={(event) => {
              clicked.current = true
              setOpen(false)
              onClick?.(event)
            }}
          >
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
