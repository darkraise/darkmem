import { useEffect } from "react"
import { useLayoutStore } from "darkraise-ui/layout"

/**
 * DOM-level workarounds for darkraise-ui layout gaps (6.x). Each one patches
 * behaviour the library keeps private, from outside, and says which gap it
 * fills so the next upgrade can retire it. Mounted once inside the shell.
 */

export const SIDEBAR_COLLAPSED_KEY = "darkmem.sidebar-collapsed"

/** Gap: `MobileDrawer` is an uncontrolled `Sheet` that neither closes on
 *  navigation nor accepts an `open` prop, so choosing a page left the sheet
 *  open over it. A tap on any link inside the drawer now presses the sheet's
 *  own Close button once the link's own click has been handled. */
function useCloseMobileDrawerOnLinkTap() {
  useEffect(() => {
    const onClick = (event: MouseEvent) => {
      const target = event.target
      if (!(target instanceof Element)) return
      const sheet = target.closest<HTMLElement>(".dr-mobile-drawer-content")
      if (!sheet || !target.closest("a[href]")) return
      // A modified click opens a new tab; the drawer should stay put.
      if (
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.button !== 0
      )
        return
      queueMicrotask(() => {
        sheet
          .querySelector<HTMLButtonElement>(":scope > .dr-overlay-close-btn")
          ?.click()
      })
    }
    document.addEventListener("click", onClick)
    return () => document.removeEventListener("click", onClick)
  }, [])
}

function readCollapsed(): boolean {
  try {
    return localStorage.getItem(SIDEBAR_COLLAPSED_KEY) === "1"
  } catch {
    return false
  }
}

function writeCollapsed(collapsed: boolean) {
  try {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, collapsed ? "1" : "0")
  } catch {
    // Storage blocked: the choice simply does not survive a reload.
  }
}

/** Gap: `SidebarLayout` keeps `collapsed` in a private `useState(false)`, so
 *  a reload always reopened the rail. The aside's `data-collapsed` is the
 *  only public trace of the state: it is mirrored into storage, and on mount
 *  a stored "collapsed" presses the library's own toggle once, with the
 *  width transition suppressed so the page does not animate on load. */
function usePersistSidebarCollapse(layout: string) {
  useEffect(() => {
    if (layout !== "sidebar") return
    const aside = document.querySelector<HTMLElement>(
      ".dr-sidebar-layout-aside",
    )
    if (!aside) return

    if (readCollapsed() && aside.dataset.collapsed !== "true") {
      const toggle = aside.querySelector<HTMLButtonElement>(
        ".dr-sidebar-layout-toggle",
      )
      if (toggle) {
        aside.style.transition = "none"
        toggle.click()
        requestAnimationFrame(() => {
          aside.style.transition = ""
        })
      }
    }

    const observer = new MutationObserver(() => {
      writeCollapsed(aside.dataset.collapsed === "true")
    })
    observer.observe(aside, {
      attributes: true,
      attributeFilter: ["data-collapsed"],
    })
    return () => observer.disconnect()
  }, [layout])
}

/** Gap: the rail's nav scroller overflows at 1440x900 (the Operate group sits
 *  below the fold) with nothing marking that the list continues. Sets
 *  `data-fade-start` / `data-fade-end` on the scroller, which globals.css
 *  turns into an edge mask, the same treatment `ScrollTabsList` uses. */
function useNavScrollFade(layout: string) {
  useEffect(() => {
    const scroller = document.querySelector<HTMLElement>(
      ".dr-sidebar-layout-nav-scroll",
    )
    if (!scroller) return
    const update = () => {
      const { scrollTop, scrollHeight, clientHeight } = scroller
      scroller.toggleAttribute("data-fade-start", scrollTop > 1)
      scroller.toggleAttribute(
        "data-fade-end",
        scrollTop + clientHeight < scrollHeight - 1,
      )
    }
    update()
    scroller.addEventListener("scroll", update, { passive: true })
    const observer = new ResizeObserver(update)
    observer.observe(scroller)
    const content = scroller.firstElementChild
    if (content) observer.observe(content)
    return () => {
      scroller.removeEventListener("scroll", update)
      observer.disconnect()
    }
  }, [layout])
}

export function ShellBehaviours() {
  const layout = useLayoutStore((s) => s.layout)
  useCloseMobileDrawerOnLinkTap()
  usePersistSidebarCollapse(layout)
  useNavScrollFade(layout)
  return null
}
