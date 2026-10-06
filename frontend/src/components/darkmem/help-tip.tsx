import { useEffect, useRef, useState, type ReactNode } from "react"
import { CircleHelp } from "lucide-react"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import { cn } from "darkraise-ui/lib"

export interface HelpTipProps {
  /** Accessible name for the icon button, e.g. "About w_semantic". */
  label: string
  children: ReactNode
  side?: "top" | "right" | "bottom" | "left"
  className?: string
}

// The Settings help affordance: a row is a control + a short label + this
// icon; the long explanation lives here, on demand (hover or focus), so the
// board stays scannable without cutting any information.
//
// Touch has neither hover nor a visible focus, so a tap toggles the tip
// instead, and a tap anywhere else closes it. The tooltip's own handlers
// would close it again on the same tap (pointerdown and pointerleave both
// schedule a close), so a touch or pen pointer is kept away from them.
export function HelpTip({ label, children, side = "top", className }: HelpTipProps) {
  const [open, setOpen] = useState(false)
  const triggerRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    const closeOnTapElsewhere = (event: PointerEvent) => {
      if (event.pointerType === "mouse") return
      if (
        event.target instanceof Node &&
        triggerRef.current?.contains(event.target)
      )
        return
      setOpen(false)
    }
    document.addEventListener("pointerdown", closeOnTapElsewhere, true)
    return () =>
      document.removeEventListener("pointerdown", closeOnTapElsewhere, true)
  }, [open])

  return (
    <TooltipProvider delayDuration={150}>
      <Tooltip open={open} onOpenChange={setOpen}>
        <TooltipTrigger
          ref={triggerRef}
          aria-label={label}
          onPointerDown={(event) => {
            if (event.pointerType === "mouse") return
            event.preventDefault()
            setOpen((wasOpen) => !wasOpen)
          }}
          onPointerLeave={(event) => {
            if (event.pointerType !== "mouse") event.preventDefault()
          }}
          className={cn(
            "text-muted-foreground/70 hover:text-foreground focus-visible:ring-ring inline-flex shrink-0 cursor-help items-center justify-center self-center rounded-sm p-0.5 align-middle transition-colors focus-visible:ring-2 focus-visible:outline-none motion-reduce:transition-none",
            className,
          )}
        >
          <CircleHelp aria-hidden className="h-3.5 w-3.5" />
        </TooltipTrigger>
        <TooltipContent
          side={side}
          className="max-w-sm text-sm leading-relaxed font-normal normal-case"
        >
          {children}
        </TooltipContent>
      </Tooltip>
    </TooltipProvider>
  )
}
