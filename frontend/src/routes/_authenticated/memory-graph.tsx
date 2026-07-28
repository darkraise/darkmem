import { createFileRoute } from "@tanstack/react-router"
import { DEMO } from "@/lib/demo-flag"
import { MemoryGraphExplorer } from "@/features/memory-graph/components/memory-graph-explorer"
import { RealMemoryGraphPage } from "@/features/memory-graph/components/real-memory-graph-page"

// DEMO is fixed for the process lifetime (import.meta.env, not runtime
// state), so branching at the component level never violates the rules
// of hooks — mirrors /memories's DEMO ? demo : real idiom exactly. The
// real branch (T1.60, Step 1) is the already-real implementation
// relocated from the orphaned /unified-graph route: the sidebar nav has
// always pointed at /memory-graph, which served only demo data before
// this move.
export const Route = createFileRoute("/_authenticated/memory-graph")({
  component: () => (DEMO ? <MemoryGraphExplorer /> : <RealMemoryGraphPage />),
})
