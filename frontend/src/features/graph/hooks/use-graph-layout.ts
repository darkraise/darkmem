import { useState } from "react"
import {
  DEFAULT_SIZE_MODE,
  type SizeMode,
} from "@/features/graph/lib/graph-utils"
import {
  DEFAULT_HULL_MODE,
  type HullMode,
} from "@/features/graph/lib/graph-geometry"

export function useGraphLayout() {
  const [sizeMode, setSizeMode] = useState<SizeMode>(DEFAULT_SIZE_MODE)
  const [hullMode, setHullMode] = useState<HullMode>(DEFAULT_HULL_MODE)
  const [spacing3D, setSpacing3D] = useState(50)

  return {
    sizeMode,
    setSizeMode,
    hullMode,
    setHullMode,
    spacing3D,
    setSpacing3D,
  }
}
