import { useEffect, useState } from "react"
import { ArrowUp } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { useLayoutStore } from "darkraise-ui/layout"

const SHOW_AFTER_PX = 320

/**
 * Floating scroll-to-top button for the main content area. All darkraise-ui
 * layouts scroll inside `#main-content` (the shell itself is h-screen
 * overflow-hidden), so the listener binds there rather than on the window.
 * Re-binds when the layout variant changes because the main element is
 * remounted by the layout switch.
 */
export function BackToTop() {
  const layout = useLayoutStore((s) => s.layout)
  const [visible, setVisible] = useState(false)

  useEffect(() => {
    const el = document.getElementById("main-content")
    if (!el) return
    const onScroll = () => setVisible(el.scrollTop > SHOW_AFTER_PX)
    onScroll()
    el.addEventListener("scroll", onScroll, { passive: true })
    return () => el.removeEventListener("scroll", onScroll)
  }, [layout])

  if (!visible) return null

  const scrollToTop = () => {
    const el = document.getElementById("main-content")
    if (!el) return
    const reduced = window.matchMedia(
      "(prefers-reduced-motion: reduce)",
    ).matches
    el.scrollTo({ top: 0, behavior: reduced ? "auto" : "smooth" })
  }

  return (
    <Button
      variant="secondary"
      size="icon"
      aria-label="Back to top"
      onClick={scrollToTop}
      className="border-border fixed right-5 bottom-5 z-40 rounded-full border shadow-lg"
    >
      <ArrowUp aria-hidden className="h-4 w-4" />
    </Button>
  )
}
