import { create } from "zustand"
import { persist } from "zustand/middleware"

export type DetailLevel = "simple" | "advanced"

interface DetailLevelState {
  level: DetailLevel
  setLevel: (level: DetailLevel) => void
}

export const useDetailLevel = create<DetailLevelState>()(
  persist(
    (set) => ({
      level: "advanced",
      setLevel: (level) => set({ level }),
    }),
    { name: "darkmem-detail-level" },
  ),
)
