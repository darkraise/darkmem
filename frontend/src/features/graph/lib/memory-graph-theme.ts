import { useMemo } from "react"
import { useGraphThemeTokens, type GraphThemeTokens } from "./code-graph-theme"
import { buildMemoryPalette, type MemoryPalette } from "./graph-colors"

export function useMemoryGraphTheme(): {
  tokens: GraphThemeTokens
  palette: MemoryPalette
} {
  const tokens = useGraphThemeTokens()
  const palette = useMemo(() => buildMemoryPalette(tokens), [tokens])
  return { tokens, palette }
}
