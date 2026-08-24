import { useEffect, useState } from "react"

/** Subscribes to a CSS media query from JS.
 *
 *  Needed where a breakpoint has to change the *tree* rather than the styling
 *  — Tailwind's `lg:` prefix cannot swap one container component for another.
 *  Reads `false` on the server and in tests (the suite stubs `matchMedia` with
 *  `matches: false`), so a caller must render its narrow branch as the
 *  fallback rather than treating the wide one as the default.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() => {
    if (typeof window === "undefined" || !window.matchMedia) return false
    return window.matchMedia(query).matches
  })

  useEffect(() => {
    if (typeof window === "undefined" || !window.matchMedia) return
    const list = window.matchMedia(query)
    setMatches(list.matches)
    const onChange = (event: MediaQueryListEvent) => setMatches(event.matches)
    list.addEventListener("change", onChange)
    return () => list.removeEventListener("change", onChange)
  }, [query])

  return matches
}
