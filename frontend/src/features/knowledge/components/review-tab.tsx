import { useState } from "react"
import {
  SegmentGroup,
  SegmentGroupIndicator,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import { HelpTip } from "@/components/darkmem"
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
        <SegmentGroup
          aria-label="Triage mode"
          value={mode}
          onValueChange={(value) => {
            if (value === "review" || value === "hygiene") setMode(value)
          }}
        >
          <SegmentGroupIndicator />
          <SegmentGroupItem value="review">Review — truth</SegmentGroupItem>
          <SegmentGroupItem value="hygiene">Hygiene — housekeeping</SegmentGroupItem>
        </SegmentGroup>
        <HelpTip label="About review actions">
          Ratify and reject are available only here, in the signed-in app; no
          MCP tool can reach them, whatever scopes a key holds.
        </HelpTip>
      </div>
      {mode === "review" ? (
        <ReviewQueue project={project} />
      ) : (
        <HygieneQueue project={project} />
      )}
    </div>
  )
}
