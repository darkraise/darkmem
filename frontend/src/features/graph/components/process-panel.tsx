import { Badge } from "darkraise-ui/components/badge"
import { EmptyState } from "@/components/darkmem"
import { Button } from "darkraise-ui/components/button"
import { Workflow } from "lucide-react"
import type { CodeProcess } from "../lib/code-processes"

interface ProcessPanelProps {
  processes: CodeProcess[]
  selectedProcessId?: string | null
  onSelect: (process: CodeProcess) => void
}

export function ProcessPanel({
  processes,
  selectedProcessId,
  onSelect,
}: ProcessPanelProps) {
  if (processes.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={Workflow}
        title="No execution flows"
        description="Flows are traced from call edges during indexing. This repository produced none."
      />
    )
  }

  return (
    <div className="space-y-1">
      {processes.map((p) => {
        const active = p.id === selectedProcessId
        return (
          <Button
            key={p.id}
            variant="ghost"
            onClick={() => onSelect(p)}
            className={`flex h-auto w-full items-start gap-2 rounded-sm px-2 py-2 text-left transition-colors ${
              active
                ? "bg-primary/15 text-primary"
                : "text-foreground hover:bg-accent"
            }`}
          >
            <Workflow
              className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${active ? "text-primary" : "text-muted-foreground"}`}
            />
            <span className="min-w-0 flex-1">
              <span className="flex items-center gap-2">
                <span className="min-w-0 flex-1 truncate font-mono text-sm font-medium">
                  {p.label}
                </span>
                <Badge variant="secondary" size="sm" className="shrink-0">
                  {p.stepCount} {p.stepCount === 1 ? "step" : "steps"}
                </Badge>
              </span>
              {(p.entryKind || p.entryFile) && (
                <span className="mt-0.5 block truncate font-mono text-sm text-muted-foreground">
                  {p.entryKind && (
                    <span className="uppercase tracking-wider">
                      {p.entryKind}
                    </span>
                  )}
                  {p.entryKind && p.entryFile && " · "}
                  {p.entryFile}
                </span>
              )}
            </span>
          </Button>
        )
      })}
    </div>
  )
}
