import { createFileRoute } from "@tanstack/react-router"
import { FileText } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { ArticlesTab } from "@/features/knowledge/components/articles-tab"

export const Route = createFileRoute("/_authenticated/knowledge_/articles")({
  component: KnowledgeArticlesPage,
})

function KnowledgeArticlesPage() {
  return (
    <div className="space-y-4">
      <PageChrome
        icon={FileText}
        title="Articles"
        description="L3 synthesised articles — grounded prose whose every claim links to a verified fact."
      />
      <ArticlesTab />
    </div>
  )
}
