import { create } from "zustand"
import { persist } from "zustand/middleware"

/**
 * What colour the halo around a focused node is painted in.
 *
 * The halo itself is no longer a choice — it is how selection is drawn. This
 * is only its colour: the accent, or a high-contrast inversion for a crowded
 * canvas where the accent competes with relation edges. Neither repaints the
 * node's fill, which is already carrying cluster or type.
 */
export type SelectionColor = "accent" | "inverted"

export const DEFAULT_SELECTION_COLOR: SelectionColor = "accent"
export const DEFAULT_DIM = 15

/** Below the floor the ground is gone rather than dimmed; above the ceiling
 *  the focus stops reading against it. */
export const DIM_MIN = 5
export const DIM_MAX = 50
export const DIM_STEP = 5

interface GraphPrefsState {
  selectionColor: SelectionColor
  /** Opacity of everything outside the focused node's neighbourhood, percent. */
  dimUnrelated: number
  setSelectionColor: (color: SelectionColor) => void
  setDimUnrelated: (percent: number) => void
}

export const useGraphPrefs = create<GraphPrefsState>()(
  persist(
    (set) => ({
      selectionColor: DEFAULT_SELECTION_COLOR,
      dimUnrelated: DEFAULT_DIM,

      setSelectionColor: (selectionColor) => set({ selectionColor }),

      setDimUnrelated: (percent) => {
        if (!Number.isFinite(percent)) return
        set({ dimUnrelated: Math.max(DIM_MIN, Math.min(DIM_MAX, percent)) })
      },
    }),
    { name: "darkmem-graph-prefs" },
  ),
)
