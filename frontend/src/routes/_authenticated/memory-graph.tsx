import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { PageHeader } from "darkraise-ui/layout"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { Button } from "darkraise-ui/components/button"
import { Waypoints } from "lucide-react"

export const Route = createFileRoute("/_authenticated/memory-graph")({
  component: MemoryGraphPage,
})

function MemoryGraphPage() {
  const navigate = useNavigate()
  return (
    <div className="space-y-4 p-6">
      <PageHeader
        title="Memory Graph"
        description="Entities and relations across the vault, in force, tree, and circles layouts."
      />
      <EmptyState
        icon={<Waypoints />}
        title="The memory graph moves here"
        description="The unified entity/relation explorer is reshaped into this destination in Wave 3."
        action={
          <Button
            variant="outline"
            onClick={() => navigate({ to: "/unified-graph" })}
          >
            Open the current Memory Graph page
          </Button>
        }
      />
    </div>
  )
}
