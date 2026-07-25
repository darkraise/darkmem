import { useEffect } from "react"

/**
 * Opt a route into a full-bleed content area: while the page is mounted it
 * cancels the darkraise-ui layout shell's `p-6` content padding (via a body
 * class + a rule in globals.css), so a full-height canvas (graph pages) can
 * spread edge-to-edge. Padding is restored on unmount for normal pages.
 */
export function useFullBleedContent(enabled = true) {
  useEffect(() => {
    if (!enabled) return
    document.body.classList.add("content-full-bleed")
    return () => document.body.classList.remove("content-full-bleed")
  }, [enabled])
}
