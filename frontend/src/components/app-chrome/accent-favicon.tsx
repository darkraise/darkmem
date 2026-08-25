import { useEffect } from "react"
import { watchAccentFavicon } from "@/lib/accent-favicon"

/**
 * Keeps the browser-tab icon in the accent the operator picked.
 *
 * No dependency list, and no `useTheme()`: the watcher reads the resolved
 * `--primary` off the root element and re-reads it whenever the theme rewrites
 * its tokens. Depending on the theme's state instead would reintroduce the
 * effect-ordering bug this replaced — `ThemeProvider` writes those tokens from
 * its own effect, which runs after every child's.
 */
export function AccentFavicon() {
  useEffect(() => watchAccentFavicon(), [])
  return null
}
