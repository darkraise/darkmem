import { createFileRoute } from "@tanstack/react-router"
import { ScrollText } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { FactsTab } from "@/features/knowledge/components/facts-tab"

export const Route = createFileRoute("/_authenticated/knowledge_/facts")({
  component: KnowledgeFactsPage,
})

function KnowledgeFactsPage() {
  return (
    <div className="space-y-4">
      <PageChrome
        icon={ScrollText}
        title="Facts"
      />
      <FactsTab />
    </div>
  )
}
