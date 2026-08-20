import { LayoutGrid, List } from "lucide-react"
import { create } from "zustand"
import { persist } from "zustand/middleware"
import type { IconSegmentedOption } from "@/components/darkmem"

export type LlmLayout = "list" | "grid"

interface LlmLayoutState {
  layout: LlmLayout
  setLayout: (layout: LlmLayout) => void
}

/** Same icons and labels as the jobs layout switch, so one control does not
 *  mean two different things in two places. The label is the tooltip and the
 *  accessible name both — an icon-only segment has no other name. */
export const LLM_LAYOUT_OPTIONS: ReadonlyArray<IconSegmentedOption<LlmLayout>> =
  [
    { value: "list", label: "List layout", icon: List },
    { value: "grid", label: "Grid layout", icon: LayoutGrid },
  ]

function layoutStore(storageKey: string) {
  return create<LlmLayoutState>()(
    persist(
      (set) => ({ layout: "grid", setLayout: (layout) => set({ layout }) }),
      { name: storageKey },
    ),
  )
}

// Two stores rather than one: the panels hold different-shaped rows, so an
// operator who wants providers dense and purposes roomy is expressing a real
// preference rather than an inconsistency. `grid` is each panel's existing
// look, so a first visit after this lands renders unchanged.
export const useProvidersLayout = layoutStore("darkmem-llm-providers-layout")
export const usePurposesLayout = layoutStore("darkmem-llm-purposes-layout")
