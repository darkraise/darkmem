import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"

export interface ProjectSummary {
  name: string
  /** `personal` is the notes workspace's own scope. It has its own route, so
   *  project-shaped pickers filter it out rather than offering it. */
  kind: "project" | "personal"
  memory_count: number
  document_count: number
  checkpoint_count: number
  page_count: number
  last_checkpoint_at: string | null
  /** UTC day (YYYY-MM-DD), not a timestamp -- see the backend's own comment. */
  last_event_day: string | null
}

/**
 * The projects the corpus actually holds, busiest first.
 *
 * Deliberately NOT project-scoped: this is the catalog the scope picker reads,
 * so scoping it to the active project would leave the switcher able to offer
 * only the scope you are already in.
 */
export function useProjects() {
  return useQuery<ProjectSummary[]>({
    queryKey: ["projects"],
    queryFn: () => apiFetch<ProjectSummary[]>("/projects"),
    // Demo mode runs with no backend at all. This hook mounts in the app
    // chrome, so on every route it was the one request the demo still made —
    // and `handleUnauthorized` turns its 401 into a hard redirect to /login,
    // which made the whole demo unreachable rather than merely unscoped.
    enabled: !DEMO,
  })
}
