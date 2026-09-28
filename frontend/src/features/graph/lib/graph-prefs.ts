import { create } from "zustand"
import { persist } from "zustand/middleware"
import {
  DEFAULT_DETAIL_PANEL_WIDTH,
  DETAIL_PANEL_MIN_WIDTH,
} from "./panel-resize"

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

/** How many memories the graph asks for. The ceiling is the server's. */
export const NODE_LIMIT_DEFAULT = 200
export const NODE_LIMIT_MIN = 50
export const NODE_LIMIT_MAX = 50_000
export const NODE_LIMIT_STEP = 100

interface GraphPrefsState {
  selectionColor: SelectionColor
  /** Opacity of everything outside the focused node's neighbourhood, percent. */
  dimUnrelated: number
  /** Width of the graph's detail panel, px. The canvas floor is applied
   *  against the live container width, which only the page knows. */
  detailPanelWidth: number
  /** Memories to plot, newest first, while `allNodes` is off. */
  nodeLimit: number
  /** Plot every in-scope memory, up to the server's ceiling. */
  allNodes: boolean
  setSelectionColor: (color: SelectionColor) => void
  setDimUnrelated: (percent: number) => void
  setDetailPanelWidth: (px: number) => void
  setNodeLimit: (n: number) => void
  setAllNodes: (all: boolean) => void
}

export const useGraphPrefs = create<GraphPrefsState>()(
  persist(
    (set) => ({
      selectionColor: DEFAULT_SELECTION_COLOR,
      dimUnrelated: DEFAULT_DIM,
      detailPanelWidth: DEFAULT_DETAIL_PANEL_WIDTH,
      nodeLimit: NODE_LIMIT_DEFAULT,
      allNodes: false,

      setSelectionColor: (selectionColor) => set({ selectionColor }),

      setDimUnrelated: (percent) => {
        if (!Number.isFinite(percent)) return
        set({ dimUnrelated: Math.max(DIM_MIN, Math.min(DIM_MAX, percent)) })
      },

      // Only the panel's own floor is applied here. The canvas floor needs the
      // container width, so it is enforced where the panel is laid out — and a
      // stored width wider than today's window is clamped on render rather than
      // rewritten, so the panel returns to its full width on a wider screen.
      setDetailPanelWidth: (px) => {
        if (!Number.isFinite(px)) return
        set({ detailPanelWidth: Math.max(DETAIL_PANEL_MIN_WIDTH, px) })
      },

      setNodeLimit: (n) => {
        if (!Number.isFinite(n)) return
        set({
          nodeLimit: Math.min(NODE_LIMIT_MAX, Math.max(NODE_LIMIT_MIN, Math.round(n))),
        })
      },

      setAllNodes: (allNodes) => set({ allNodes }),
    }),
    { name: "darkmem-graph-prefs" },
  ),
)
