import { create } from "zustand"
import { persist } from "zustand/middleware"

/** Mirrors the backend's own default (`memories.project` column default,
 *  doc 04 §3), so a fresh session's scope already matches where an
 *  unscoped capture lands. */
export const DEFAULT_PROJECT = "default"

const MAX_KNOWN_PROJECTS = 8

interface ProjectState {
  /**
   * The global isolation/scope boundary (doc 13 §3) — the project switcher
   * writes here, and it rides into every project-scoped query key via
   * `src/lib/query-keys.ts`. This is NOT the session `applies_when`
   * context declaration; see `context-store.ts` for that, and never let
   * the two read from or write into each other.
   */
  activeProject: string
  /**
   * Most-recently-used projects, newest first, `activeProject` always
   * included. No backend project-list endpoint exists yet (T1.65's own
   * scope is frontend-only), so the switcher offers what this session has
   * actually visited rather than a fabricated catalog.
   */
  knownProjects: string[]
  setProject: (project: string) => void
}

export const useProjectStore = create<ProjectState>()(
  persist(
    (set, get) => ({
      activeProject: DEFAULT_PROJECT,
      knownProjects: [DEFAULT_PROJECT],

      setProject: (project: string) => {
        const trimmed = project.trim()
        if (!trimmed) return
        const known = [
          trimmed,
          ...get().knownProjects.filter((p) => p !== trimmed),
        ].slice(0, MAX_KNOWN_PROJECTS)
        set({ activeProject: trimmed, knownProjects: known })
      },
    }),
    { name: "darkmem-project" },
  ),
)
