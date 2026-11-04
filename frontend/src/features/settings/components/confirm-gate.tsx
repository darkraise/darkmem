import { useState, type ReactNode } from "react"
import { TriangleAlert } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { cn } from "darkraise-ui/lib"

// The inline armed-confirmation shape (S29): every destructive or costly
// trigger opens this panel before it runs — never a bare destructive click.
// tone="caution" confirms cost/duration only; tone="danger" confirms data
// loss, so the two consequences read distinctly.
export function ConfirmGate({
  trigger,
  headline,
  desc,
  confirmLabel,
  tone,
  disabled,
  onConfirm,
}: {
  trigger: ReactNode
  headline: string
  desc: ReactNode
  confirmLabel: string
  tone: "caution" | "danger" | "primary"
  disabled?: boolean
  onConfirm: () => void
}) {
  const [armed, setArmed] = useState(false)
  const danger = tone === "danger"

  return (
    <div className="flex flex-col gap-2">
      {/* The inner trigger stays the interactive, focusable element: a native
          button turns Enter/Space into a click that bubbles here, so the gate
          arms from the keyboard too. Never give a trigger tabIndex={-1}; that
          drops it from the Tab order and strands keyboard users. */}
      <div
        className={cn("w-fit", disabled && "pointer-events-none opacity-55")}
        onClick={() => !disabled && setArmed(true)}
      >
        {trigger}
      </div>
      {armed && (
        <div
          className={cn(
            "flex gap-2.5 rounded-md border p-3",
            danger
              ? "border-destructive-edge/55 bg-destructive-solid/8"
              : "border-warning-edge/55 bg-warning-solid/10",
          )}
        >
          <TriangleAlert
            aria-hidden
            className={cn(
              "h-4 w-4 shrink-0",
              danger ? "text-destructive-text" : "text-warning-text",
            )}
          />
          <div className="flex flex-col gap-1.5">
            <span className="text-sm font-semibold">{headline}</span>
            <span className="text-muted-foreground text-sm">{desc}</span>
            <div className="mt-0.5 flex gap-2">
              <Button variant="ghost" onClick={() => setArmed(false)}>
                Cancel
              </Button>
              <Button
                variant="outline"
                className={cn(
                  danger
                    ? "border-destructive-edge/60 text-destructive-text"
                    : tone === "caution"
                      ? "border-warning-edge/60 text-warning-text"
                      : "border-primary/60 text-primary-text",
                )}
                onClick={() => {
                  onConfirm()
                  setArmed(false)
                }}
              >
                {confirmLabel}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
