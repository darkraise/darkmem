import { createFileRoute } from "@tanstack/react-router"
import { FileText } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { DocumentsView } from "@/features/documents/components/documents-view"

export const Route = createFileRoute("/_authenticated/documents")({
  component: DocumentsPage,
})

function DocumentsPage() {
  return (
    <div className="space-y-4">
      <PageChrome
        icon={FileText}
        title="Documents"
        description="Horizon: grounded answers, single-document summaries and emergent connections over your filed documents."
      />
      {/* The pin is visible at the call site rather than a default nobody
          reads: this surface is the personal one, scoped to `default`. */}
      <DocumentsView project="default" />
    </div>
  )
}
