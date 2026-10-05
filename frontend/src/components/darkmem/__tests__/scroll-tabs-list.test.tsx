import { render, screen } from "@testing-library/react"
import { afterEach, describe, expect, it, vi } from "vitest"
import { Tabs, TabsTrigger } from "darkraise-ui/components/tabs"
import { ScrollTabsList } from "../scroll-tabs-list"

function renderTabs(active: string) {
  return render(
    <Tabs value={active}>
      <ScrollTabsList activeValue={active}>
        {["one", "two", "three"].map((v) => (
          <TabsTrigger key={v} value={v}>
            {v}
          </TabsTrigger>
        ))}
      </ScrollTabsList>
    </Tabs>,
  )
}

afterEach(() => {
  vi.mocked(Element.prototype.scrollIntoView).mockClear()
})

describe("ScrollTabsList", () => {
  it("scrolls the active tab into view", () => {
    renderTabs("three")
    const calls = vi.mocked(Element.prototype.scrollIntoView).mock
    expect(calls.contexts).toContain(screen.getByRole("tab", { name: "three" }))
  })

  it("sizes the strip to its tabs so none is clipped", () => {
    renderTabs("one")
    expect(screen.getByRole("tablist")).toHaveClass("w-max", "min-w-full")
  })

  it("marks the edge that has more tabs past it", () => {
    const scroll = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollWidth")
    const client = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "clientWidth")
    Object.defineProperty(HTMLElement.prototype, "scrollWidth", { configurable: true, get: () => 900 })
    Object.defineProperty(HTMLElement.prototype, "clientWidth", { configurable: true, get: () => 300 })
    try {
      renderTabs("one")
      const strip = screen.getByRole("tablist").parentElement!
      expect(strip).toHaveAttribute("data-fade-end")
      expect(strip).not.toHaveAttribute("data-fade-start")
    } finally {
      if (scroll) Object.defineProperty(HTMLElement.prototype, "scrollWidth", scroll)
      if (client) Object.defineProperty(HTMLElement.prototype, "clientWidth", client)
    }
  })

  it("offers scroll chevrons only when asked and only while the strip overflows", () => {
    const scroll = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "scrollWidth")
    const client = Object.getOwnPropertyDescriptor(HTMLElement.prototype, "clientWidth")
    Object.defineProperty(HTMLElement.prototype, "scrollWidth", { configurable: true, get: () => 900 })
    Object.defineProperty(HTMLElement.prototype, "clientWidth", { configurable: true, get: () => 300 })
    try {
      const { unmount } = renderTabs("one")
      expect(screen.queryByLabelText("Scroll tabs right")).toBeNull()
      unmount()
      render(
        <Tabs value="one">
          <ScrollTabsList activeValue="one" scrollButtons>
            <TabsTrigger value="one">one</TabsTrigger>
          </ScrollTabsList>
        </Tabs>,
      )
      expect(screen.getByLabelText("Scroll tabs right")).not.toBeDisabled()
      // At the start edge there is nothing to scroll back to.
      expect(screen.getByLabelText("Scroll tabs left")).toBeDisabled()
    } finally {
      if (scroll) Object.defineProperty(HTMLElement.prototype, "scrollWidth", scroll)
      if (client) Object.defineProperty(HTMLElement.prototype, "clientWidth", client)
    }
  })
})
