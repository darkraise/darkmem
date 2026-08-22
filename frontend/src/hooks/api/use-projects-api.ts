import { useQuery } from "@tanstack/react-query"
import { apiFetch } from "@/lib/api"

export interface ProjectSummary {
  name: string
  memory_count: number
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
  })
}
