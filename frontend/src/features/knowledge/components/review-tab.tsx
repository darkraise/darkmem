import { useState } from "react"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import { ReviewQueue } from "./review-queue"
import { HygieneQueue } from "./hygiene-queue"

type TriageMode = "review" | "hygiene"

// One shared triage shell, two modes: Review adjudicates truth, Hygiene
// curates housekeeping. Switching the tab swaps the query, not the URL.
export function ReviewTab() {
  const [mode, setMode] = useState<TriageMode>("review")

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
          <ToggleGroupItem value="review">Review</ToggleGroupItem>
          <ToggleGroupItem value="hygiene">Hygiene</ToggleGroupItem>
        </ToggleGroup>
        <span className="text-muted-foreground font-mono text-sm">
          /knowledge · review
        </span>
        <span className="text-muted-foreground ml-auto font-mono text-sm">
          project: darkmem
        </span>
      </div>
      {mode === "review" ? <ReviewQueue /> : <HygieneQueue />}
    </div>
  )
}
