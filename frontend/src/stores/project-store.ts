import { create } from "zustand"
import { persist } from "zustand/middleware"

/** Mirrors the backend's own default (`memories.project` column default,
 *  doc 04 §3), so a fresh session's scope already matches where an
 *  unscoped capture lands. */
export const DEFAULT_PROJECT = "default"

/**
 * "Every project" — the absence of a scope, not a project named something.
 *
 * `null` rather than a reserved string because `memories.project` is free
 * text: any sentinel spelling could also be a real project name, and the two
 * would then be indistinguishable at the request boundary. A null scope is
 * simply not sent, and every consuming endpoint already reads an absent
 * `project` as wide (`MemorySearchRequest.project` and `/graph/unified`'s
 * query param are both `str | None`, and the graph service applies no memory
 * filter at all when it is None).
 */
export const ALL_PROJECTS = null

export type ProjectScope = string | typeof ALL_PROJECTS

/** What the scope is called in the chrome. */
export function projectLabel(project: ProjectScope): string {
  return project ?? "all projects"
}

interface ProjectState {
  /**
   * The global isolation/scope boundary (doc 13 §3) — the project switcher
   * writes here, and it rides into every project-scoped query key via
   * `src/lib/query-keys.ts`. This is NOT the session `applies_when`
   * context declaration; see `context-store.ts` for that, and never let
   * the two read from or write into each other.
   *
   * `null` means every project; see `ALL_PROJECTS`.
   */
  activeProject: ProjectScope
  setProject: (project: ProjectScope) => void
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set) => ({
      activeProject: DEFAULT_PROJECT,

      setProject: (project: ProjectScope) => {
        if (project === ALL_PROJECTS) {
          set({ activeProject: ALL_PROJECTS })
          return
        }
        const trimmed = project.trim()
        if (!trimmed) return
        set({ activeProject: trimmed })
      },
    }),
    { name: "darkmem-project" },
  ),
)
