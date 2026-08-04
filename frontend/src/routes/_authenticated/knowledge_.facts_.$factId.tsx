import { createFileRoute } from "@tanstack/react-router"
import { FactDetail } from "@/features/knowledge/components/fact-detail"

export const Route = createFileRoute("/_authenticated/knowledge_/facts_/$factId")({
  component: FactDetailRoute,
})

function FactDetailRoute() {
  const { factId } = Route.useParams()
  return <FactDetail factId={factId} />
}
