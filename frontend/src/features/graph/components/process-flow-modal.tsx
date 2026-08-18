import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "darkraise-ui/components/dialog"
import { Button } from "darkraise-ui/components/button"
import { Badge } from "darkraise-ui/components/badge"
import { EmptyState } from "@/components/darkmem"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import { toast } from "darkraise-ui/components/sonner"
import { ArrowDown, Copy, Crosshair } from "lucide-react"
import { processToMermaid, type CodeProcess } from "../lib/code-processes"

interface ProcessFlowModalProps {
  process: CodeProcess | null
  open: boolean
  onOpenChange: (open: boolean) => void
  nodeColors: Record<string, string>
  onFocus: (process: CodeProcess) => void
}

export function ProcessFlowModal({
  process,
  open,
  onOpenChange,
  nodeColors,
  onFocus,
}: ProcessFlowModalProps) {
  if (!process) return null
  const p = process

  const handleCopyMermaid = async () => {
    try {
      await navigator.clipboard.writeText(processToMermaid(p))
      toast.success("Mermaid flowchart copied to clipboard")
    } catch {
      toast.error("Could not copy to clipboard")
    }
  }

  const handleFocus = () => {
    onFocus(p)
    onOpenChange(false)
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="flex max-h-[80vh] max-w-lg flex-col">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span className="min-w-0 flex-1 truncate font-mono">{p.label}</span>
            <Badge variant="secondary" size="sm" className="shrink-0">
              {p.stepCount} {p.stepCount === 1 ? "step" : "steps"}
            </Badge>
          </DialogTitle>
          <DialogDescription>
            Ordered execution flow for this process.
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="min-h-0 flex-1">
          {p.steps.length === 0 ? (
            <EmptyState
              kind="empty"
              title="No recorded steps"
              description="This process has no recorded steps."
            />
          ) : (
            <ol className="space-y-0 px-0.5 py-1">
              {p.steps.map((step, i) => (
                <li key={`${step.nodeId}:${i}`}>
                  <div className="border-border bg-card flex items-start gap-3 rounded-sm border px-3 py-2.5">
                    <Badge
                      variant="outline"
                      size="sm"
                      className="h-6 w-6 shrink-0 justify-center rounded-full p-0 font-mono tabular-nums"
                    >
                      {step.index}
                    </Badge>
                    <span
                      aria-hidden="true"
                      className="mt-1.5 h-2 w-2 shrink-0 rounded-full"
                      style={{
                        backgroundColor:
                          nodeColors[step.kind] ??
                          nodeColors[step.kind.toLowerCase()] ??
                          "var(--muted-foreground)",
                      }}
                    />
                    <span className="min-w-0 flex-1">
                      <span className="flex items-baseline gap-2">
                        <span className="text-foreground min-w-0 flex-1 truncate font-mono text-sm font-medium">
                          {step.label}
                        </span>
                        <Badge
                          variant="outline"
                          size="sm"
                          className="shrink-0 font-mono uppercase"
                        >
                          {step.kind}
                        </Badge>
                      </span>
                      {step.file && (
                        <span className="text-muted-foreground mt-0.5 block truncate font-mono text-sm">
                          {step.file}
                        </span>
                      )}
                    </span>
                  </div>
                  {i < p.steps.length - 1 && (
                    <div className="flex justify-center py-1">
                      <ArrowDown
                        aria-hidden="true"
                        className="text-muted-foreground h-3.5 w-3.5"
                      />
                    </div>
                  )}
                </li>
              ))}
            </ol>
          )}
        </ScrollArea>

        <DialogFooter>
          <Button variant="ghost" onClick={handleCopyMermaid}>
            <Copy className="h-3.5 w-3.5" />
            Copy Mermaid
          </Button>
          <Button variant="outline" onClick={handleFocus}>
            <Crosshair className="h-3.5 w-3.5" />
            Focus in graph
          </Button>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
