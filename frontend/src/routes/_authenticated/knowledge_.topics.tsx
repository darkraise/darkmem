import { createFileRoute } from "@tanstack/react-router"
import { Tags } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { TopicsTab } from "@/features/knowledge/components/topics-tab"

export const Route = createFileRoute("/_authenticated/knowledge_/topics")({
  component: KnowledgeTopicsPage,
})

function KnowledgeTopicsPage() {
  return (
    <div className="space-y-4">
      <PageChrome
        icon={Tags}
        title="Topics"
        description="Topic clusters across the verified fact base."
      />
      <TopicsTab />
    </div>
  )
}
