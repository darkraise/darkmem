import { createFileRoute } from "@tanstack/react-router"
import { PageHeader } from "darkraise-ui/layout"
import { MemoryGraphExplorer } from "@/features/memory-graph/components/memory-graph-explorer"

export const Route = createFileRoute("/_authenticated/memory-graph")({
  component: MemoryGraphPage,
})

function MemoryGraphPage() {
  return (
    <div className="space-y-4 p-6">
      <PageHeader
        title="Memory Graph"
        description="The L1 candidate entity graph and its detected topics — a browsing surface; retrieval does not consult it."
      />
      <MemoryGraphExplorer />
    </div>
  )
}
