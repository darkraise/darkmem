import { createFileRoute } from "@tanstack/react-router"
import { Waypoints } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { useFullBleedContent } from "@/hooks/use-full-bleed-content"
import { MemoryGraphExplorer } from "@/features/memory-graph/components/memory-graph-explorer"

export const Route = createFileRoute("/_authenticated/memory-graph")({
  component: MemoryGraphPage,
})

function MemoryGraphPage() {
  // Full-bleed: the graph explorer owns the content area edge-to-edge —
  // toolbar on top, canvas filling the rest, inspector as a side column.
  useFullBleedContent()
  return (
    <div className="h-full min-h-0">
      <PageChrome
        icon={Waypoints}
        title="Memory Graph"
        description="The L1 candidate entity graph and its detected topics — a browsing surface; retrieval does not consult it."
      />
      <MemoryGraphExplorer />
    </div>
  )
}
