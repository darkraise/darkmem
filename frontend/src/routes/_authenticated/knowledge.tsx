import { createFileRoute } from "@tanstack/react-router"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "darkraise-ui/components/tabs"
import { Library } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { FactsTab } from "@/features/knowledge/components/facts-tab"
import { ArticlesTab } from "@/features/knowledge/components/articles-tab"
import { TopicsTab } from "@/features/knowledge/components/topics-tab"
import { ReviewTab } from "@/features/knowledge/components/review-tab"

const TAB_VALUES = ["facts", "articles", "topics", "review"] as const
export type KnowledgeTab = (typeof TAB_VALUES)[number]

export const Route = createFileRoute("/_authenticated/knowledge")({
  validateSearch: (search: Record<string, unknown>) => ({
    tab: TAB_VALUES.includes(search.tab as KnowledgeTab)
      ? (search.tab as KnowledgeTab)
      : undefined,
  }),
  component: KnowledgePage,
})

function KnowledgePage() {
  const { tab } = Route.useSearch()
  const navigate = Route.useNavigate()

  return (
    <div className="space-y-4">
      <PageChrome
        icon={Library}
        title="Knowledge"
        description="The verified vault: facts, articles, topics, and the review queue."
      />
      <Tabs
        value={tab ?? "facts"}
        onValueChange={(value) => {
          if (TAB_VALUES.includes(value as KnowledgeTab)) {
            void navigate({ search: { tab: value as KnowledgeTab } })
          }
        }}
      >
        <div className="overflow-x-auto">
          <TabsList>
            <TabsTrigger value="facts">Facts</TabsTrigger>
            <TabsTrigger value="articles">Articles</TabsTrigger>
            <TabsTrigger value="topics">Topics</TabsTrigger>
            <TabsTrigger value="review">Review</TabsTrigger>
          </TabsList>
        </div>
        <TabsContent value="facts" className="pt-4">
          <FactsTab />
        </TabsContent>
        <TabsContent value="articles" className="pt-4">
          <ArticlesTab />
        </TabsContent>
        <TabsContent value="topics" className="pt-4">
          <TopicsTab />
        </TabsContent>
        <TabsContent value="review" className="pt-4">
          <ReviewTab />
        </TabsContent>
      </Tabs>
    </div>
  )
}
