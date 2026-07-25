import { createFileRoute } from "@tanstack/react-router"
import { ClipboardCheck } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { ReviewTab } from "@/features/knowledge/components/review-tab"

export const Route = createFileRoute("/_authenticated/knowledge_/review")({
  component: KnowledgeReviewPage,
})

function KnowledgeReviewPage() {
  return (
    <div className="space-y-4">
      <PageChrome
        icon={ClipboardCheck}
        title="Review"
        description="The triage queue — Review adjudicates truth, Hygiene curates housekeeping."
      />
      <ReviewTab />
    </div>
  )
}
