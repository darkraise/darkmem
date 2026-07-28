import { createFileRoute, redirect } from "@tanstack/react-router"

// The real implementation that used to live at this path was relocated to
// /memory-graph (T1.60, Step 1) — the sidebar nav already pointed there.
// This redirect preserves any external bookmark/link to the old path
// rather than 404ing it.
export const Route = createFileRoute("/_authenticated/unified-graph")({
  beforeLoad: () => {
    throw redirect({ to: "/memory-graph" })
  },
})
