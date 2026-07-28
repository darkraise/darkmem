import { create } from "zustand"

/**
 * The closed axis vocabulary the backend's `applies_when` slot compares on
 * (`app/services/rank_fusion.py::CONTEXT_AXES`, doc 07 §6). `env` and
 * `situation` can produce an explicit conflict; `version` is a free string
 * compared app-side and only ever neutral — but all three are declared the
 * same way here, since that distinction lives in the matching logic
 * (T1.34), not in what the caller is allowed to state.
 */
export type ContextAxis = "env" | "situation" | "version"
export const CONTEXT_AXES: readonly ContextAxis[] = ["env", "situation", "version"]

export interface DeclaredContext {
  axes: Partial<Record<ContextAxis, string>>
}

interface ContextState {
  /**
   * The session's declared `applies_when` hint (doc 07 §6, doc 12 §5 tier
   * 1) — a retrieval boost/exclusion signal, never the isolation boundary
   * `projectStore` owns. `null` is the ONLY representation of "nothing
   * declared" (mirrors the backend's `DeclaredContext | None` and
   * `_AxisSet.__post_init__`, which raises on an empty axis set): a
   * declaration with every axis cleared collapses back to `null` rather
   * than surviving as a live-but-vacuous object, so an undeclared context
   * can never render like a real one.
   *
   * Deliberately NOT persisted — this is a *session* declaration
   * (doc 13 §3), so a reload starts undeclared rather than replaying
   * yesterday's `env=prod` silently. `projectStore` persists precisely
   * because it is a different kind of thing (see that file).
   */
  declared: DeclaredContext | null
  /**
   * T3.14 owns the `declareContext` verb that actually sends this over the
   * wire (the `X-Darkmem-Context` header / `MemorySearchRequest.context`,
   * doc 12 §5). This store only has to expose a setter shaped like that
   * verb so T3.14 has something to call — it does not itself call any
   * API (Ruling 5).
   */
  declareContext: (
    axes: Partial<Record<ContextAxis, string | null | undefined>>,
  ) => void
  clearContext: () => void
}

function normalizeAxes(
  axes: Partial<Record<ContextAxis, string | null | undefined>>,
): Partial<Record<ContextAxis, string>> {
  const normalized: Partial<Record<ContextAxis, string>> = {}
  for (const axis of CONTEXT_AXES) {
    const raw = axes[axis]
    if (raw == null) continue
    const trimmed = raw.trim().toLowerCase()
    if (trimmed) normalized[axis] = trimmed
  }
  return normalized
}

export const useContextStore = create<ContextState>()((set) => ({
  declared: null,

  declareContext: (axes) => {
    const normalized = normalizeAxes(axes)
    set({
      declared: Object.keys(normalized).length > 0 ? { axes: normalized } : null,
    })
  },

  clearContext: () => set({ declared: null }),
}))
