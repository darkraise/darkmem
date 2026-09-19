import { useState } from "react"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import { useProjectStore } from "@/stores/project-store"
import { ReviewQueue } from "./review-queue"
import { HygieneQueue } from "./hygiene-queue"

type TriageMode = "review" | "hygiene"

// One shared triage shell, two visibly distinct modes: Review adjudicates
// truth over facts/articles, Hygiene curates housekeeping over L0 memories —
// disjoint tables by construction (app/services/hygiene_queue.py), so the
// two queues can never share a row. Switching the tab swaps the query, not
// the URL; both queues take the header switcher's project scope and apply it
// to their own backend routes.
export function ReviewTab() {
  const [mode, setMode] = useState<TriageMode>("review")
  const project = useProjectStore((s) => s.activeProject) ?? undefined

  return (
    <div className="space-y-4">
      <div className="border-border flex flex-wrap items-center gap-2.5 border-b border-dashed pb-3">
        <ToggleGroup
          type="single"
          size="sm"
          value={mode}
          onValueChange={(value) => {
            if (value === "review" || value === "hygiene") setMode(value)
          }}
          aria-label="Triage mode"
        >
          <ToggleGroupItem value="review">Review — truth</ToggleGroupItem>
          <ToggleGroupItem value="hygiene">Hygiene — housekeeping</ToggleGroupItem>
        </ToggleGroup>
        <span className="text-muted-foreground font-mono text-sm">
          /knowledge · {mode}
        </span>
      </div>
      {mode === "review" ? (
        <ReviewQueue project={project} />
      ) : (
        <HygieneQueue project={project} />
      )}
    </div>
  )
}
