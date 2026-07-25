import { createFileRoute } from "@tanstack/react-router"
import { PageHeader } from "darkraise-ui/layout"
import { ClipboardCheck, FileText, ListChecks, Tags } from "lucide-react"
import {
  PlaceholderTabs,
  type PlaceholderTab,
} from "@/components/placeholder-tabs"

export const Route = createFileRoute("/_authenticated/knowledge")({
  component: KnowledgePage,
})

const TABS: PlaceholderTab[] = [
  {
    value: "facts",
    label: "Facts",
    icon: <ListChecks />,
    title: "The fact ledger lands here",
    description:
      "L2 knowledge triples with the verification ladder, sources, and context scopes. Built in Wave 2.",
  },
  {
    value: "articles",
    label: "Articles",
    icon: <FileText />,
    title: "Synthesised articles land here",
    description:
      "L3 living documents with citations back to the facts and memories that support them. Built in Wave 2.",
  },
  {
    value: "topics",
    label: "Topics",
    icon: <Tags />,
    title: "Topic communities land here",
    description:
      "Clustered themes across the vault, with per-topic drill-down. Built in Wave 2.",
  },
  {
    value: "review",
    label: "Review",
    icon: <ClipboardCheck />,
    title: "The review queue lands here",
    description:
      "Disputed and candidate facts awaiting a human decision — ratify, dispute, or archive. Built in Wave 2.",
  },
]

function KnowledgePage() {
  return (
    <div className="space-y-4 p-6">
      <PageHeader
        title="Knowledge"
        description="The verified vault: facts, articles, topics, and the review queue."
      />
      <PlaceholderTabs tabs={TABS} />
    </div>
  )
}
