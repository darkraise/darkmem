import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "darkraise-ui/components/popover"
import { cn } from "darkraise-ui/lib"
import { HelpTip } from "@/components/darkmem"
import { CONTEXT_AXES, useContextStore, type ContextAxis } from "@/stores/context-store"

function summarize(axes: Partial<Record<ContextAxis, string>>): string {
  return CONTEXT_AXES.filter((axis) => axes[axis])
    .map((axis) => `${axis}=${axes[axis]}`)
    .join(", ")
}

/**
 * The session `applies_when` declaration (doc 07 §6, doc 13 §3) — a
 * retrieval boost/exclusion hint, never the isolation scope
 * `ProjectSwitcher` owns. Dashed, italic border when undeclared, matching
 * the visual vocabulary the Memories demo mock already established for
 * this exact distinction, so the two controls read as different kinds of
 * thing at a glance (Ruling 3).
 *
 * Ruling 4: with nothing declared, the label is literally "not declared" —
 * never a placeholder axis value that could be mistaken for a real one.
 */
export function ContextChip() {
  const declared = useContextStore((s) => s.declared)
  const declareContext = useContextStore((s) => s.declareContext)
  const clearContext = useContextStore((s) => s.clearContext)
  const [draft, setDraft] = useState<Partial<Record<ContextAxis, string>>>({})
  const [open, setOpen] = useState(false)

  const label = declared ? `context: ${summarize(declared.axes)}` : "context: none"

  return (
    <span className="inline-flex items-center gap-1">
      <Popover
        open={open}
        onOpenChange={(next) => {
          setOpen(next)
          if (next) setDraft(declared?.axes ?? {})
        }}
      >
        <PopoverTrigger asChild>
          <button
            type="button"
            aria-label="Session context"
            className={cn(
              "border-border inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm transition-colors",
              declared
                ? "bg-muted hover:bg-muted/70"
                : "text-muted-foreground hover:bg-muted/40 border-dashed italic",
            )}
          >
            {label}
          </button>
        </PopoverTrigger>
        <PopoverContent
          side="bottom"
          align="end"
          className="bg-card border-border w-72 space-y-3 rounded-lg border p-3 shadow-xl"
        >
          <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
            Declare session context
          </p>
          <div className="space-y-2">
            {CONTEXT_AXES.map((axis) => (
              <div key={axis} className="space-y-1">
                <Label htmlFor={`context-axis-${axis}`} className="text-xs capitalize">
                  {axis}
                </Label>
                <Input
                  id={`context-axis-${axis}`}
                  aria-label={axis}
                  value={draft[axis] ?? ""}
                  onChange={(e) => setDraft((prev) => ({ ...prev, [axis]: e.target.value }))}
                  placeholder={axis === "env" ? "prod" : axis === "situation" ? "incident" : "15.3"}
                />
              </div>
            ))}
          </div>
          <div className="flex justify-end gap-1.5">
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                clearContext()
                setDraft({})
                setOpen(false)
              }}
              disabled={!declared}
            >
              Clear
            </Button>
            <Button
              type="button"
              onClick={() => {
                declareContext(draft)
                setOpen(false)
              }}
            >
              Declare
            </Button>
          </div>
        </PopoverContent>
      </Popover>
      <HelpTip label="About context hints" side="bottom">
        A session context is a retrieval hint, not a filter. Declaring an
        environment, situation or version ranks memories recorded under a
        matching context higher and sets aside ones that conflict with it. The
        project switcher is what limits the data you see.
      </HelpTip>
    </span>
  )
}
