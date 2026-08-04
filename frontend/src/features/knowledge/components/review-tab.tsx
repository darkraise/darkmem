import { useState } from "react"
import { Filter } from "lucide-react"
import { Input } from "darkraise-ui/components/input"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import { ReviewQueue } from "./review-queue"
import { HygieneQueue } from "./hygiene-queue"

type TriageMode = "review" | "hygiene"

// One shared triage shell, two visibly distinct modes: Review adjudicates
// truth over facts/articles, Hygiene curates housekeeping over L0 memories —
// disjoint tables by construction (app/services/hygiene_queue.py), so the
// two queues can never share a row. Switching the tab swaps the query, not
// the URL; the project filter is server-side and shared by both queues,
// each of which applies it to its own backend routes independently.
export function ReviewTab() {
  const [mode, setMode] = useState<TriageMode>("review")
  const [project, setProject] = useState("")

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
        <Input
          prefix={<Filter aria-hidden className="h-4 w-4" />}
          placeholder="project — leave blank for all"
          value={project}
          onChange={(e) => setProject(e.target.value)}
          groupClassName="ml-auto w-56"
          aria-label="Project filter"
        />
      </div>
      {mode === "review" ? (
        <ReviewQueue project={project.trim() || undefined} />
      ) : (
        <HygieneQueue project={project.trim() || undefined} />
      )}
    </div>
  )
}
