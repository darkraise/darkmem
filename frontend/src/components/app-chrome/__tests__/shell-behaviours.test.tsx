import { render } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { ShellBehaviours, SIDEBAR_COLLAPSED_KEY } from "../shell-behaviours"

/** A stand-in for the library's DOM: these behaviours patch the shell from
 *  outside, so the contract under test is the markup they read and press. */
function mountShell({ collapsed = false } = {}) {
  document.body.innerHTML = `
    <aside class="dr-sidebar-layout-aside" ${collapsed ? 'data-collapsed="true"' : ""}>
      <button class="dr-sidebar-layout-toggle"></button>
      <div class="dr-sidebar-layout-nav-scroll"><nav></nav></div>
    </aside>
    <div class="dr-mobile-drawer-content" data-state="open">
      <a href="/memories">Memories</a>
      <button class="dr-overlay-close-btn" aria-label="Close"></button>
    </div>`
  const toggle = document.querySelector<HTMLButtonElement>(
    ".dr-sidebar-layout-toggle",
  )!
  const aside = document.querySelector<HTMLElement>(".dr-sidebar-layout-aside")!
  toggle.addEventListener("click", () => {
    if (aside.dataset.collapsed === "true") delete aside.dataset.collapsed
    else aside.dataset.collapsed = "true"
  })
  return { toggle, aside }
}

beforeEach(() => {
  localStorage.clear()
  vi.stubGlobal(
    "ResizeObserver",
    class {
      observe() {}
      disconnect() {}
    },
  )
})
afterEach(() => {
  document.body.innerHTML = ""
  vi.unstubAllGlobals()
})

describe("ShellBehaviours", () => {
  it("closes the mobile drawer when one of its links is tapped", async () => {
    mountShell()
    render(<ShellBehaviours />)
    const close = document.querySelector<HTMLButtonElement>(
      ".dr-overlay-close-btn",
    )!
    const pressed = vi.fn()
    close.addEventListener("click", pressed)
    document
      .querySelector<HTMLAnchorElement>(".dr-mobile-drawer-content a")!
      .addEventListener("click", (e) => e.preventDefault())
    document
      .querySelector<HTMLAnchorElement>(".dr-mobile-drawer-content a")!
      .click()
    await Promise.resolve()
    expect(pressed).toHaveBeenCalledTimes(1)
  })

  it("restores a collapsed rail stored from an earlier visit", () => {
    localStorage.setItem(SIDEBAR_COLLAPSED_KEY, "1")
    const { aside } = mountShell()
    render(<ShellBehaviours />)
    expect(aside.dataset.collapsed).toBe("true")
  })

  it("remembers the rail's state when the user toggles it", async () => {
    const { toggle } = mountShell()
    render(<ShellBehaviours />)
    toggle.click()
    await new Promise((resolve) => setTimeout(resolve, 0))
    expect(localStorage.getItem(SIDEBAR_COLLAPSED_KEY)).toBe("1")
  })
})
