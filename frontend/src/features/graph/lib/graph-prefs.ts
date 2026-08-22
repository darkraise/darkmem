import { create } from "zustand"
import { persist } from "zustand/middleware"

/**
 * How the graph announces the node you selected.
 *
 * All three ship and the reader picks; they differ only in what is drawn
 * *around* the focused node. None of them repaints its fill — that fill is
 * already carrying cluster or type, and overwriting it trades one signal for
 * another instead of adding one.
 */
export type SelectionTreatment = "halo" | "keyline" | "invert"

export const DEFAULT_TREATMENT: SelectionTreatment = "halo"
export const DEFAULT_DIM = 15

/** Below the floor the ground is gone rather than dimmed; above the ceiling
 *  the focus stops reading against it. */
export const DIM_MIN = 5
export const DIM_MAX = 50
export const DIM_STEP = 5

interface GraphPrefsState {
  selectionTreatment: SelectionTreatment
  /** Opacity of everything outside the focused node's neighbourhood, percent. */
  dimUnrelated: number
  setSelectionTreatment: (treatment: SelectionTreatment) => void
  setDimUnrelated: (percent: number) => void
}

export const useGraphPrefs = create<GraphPrefsState>()(
  persist(
    (set) => ({
      selectionTreatment: DEFAULT_TREATMENT,
      dimUnrelated: DEFAULT_DIM,

      setSelectionTreatment: (selectionTreatment) => set({ selectionTreatment }),

      setDimUnrelated: (percent) => {
        if (!Number.isFinite(percent)) return
        set({ dimUnrelated: Math.max(DIM_MIN, Math.min(DIM_MAX, percent)) })
      },
    }),
    { name: "darkmem-graph-prefs" },
  ),
)
