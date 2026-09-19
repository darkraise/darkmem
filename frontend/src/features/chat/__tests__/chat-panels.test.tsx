import { render } from "@testing-library/react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"
import { ChatPanels, THREADS_MIN_SIZE } from "../components/chat-panels"

const realMatchMedia = window.matchMedia

beforeEach(() => {
  window.localStorage.clear()
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: true,
    media: query,
    onchange: null,
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    addListener: vi.fn(),
    removeListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }))
})
afterEach(() => {
  window.matchMedia = realMatchMedia
})

function threadsWidth(container: HTMLElement): number {
  const pane = container.querySelector<HTMLElement>('[data-panel-id="chat-threads"]')!
  return Number.parseFloat(pane.style.width)
}

describe("ChatPanels", () => {
  it("opens the thread pane at least as wide as its floor", () => {
    const { container } = render(
      <ChatPanels threads={<div />} conversation={<div />} context={<div />} />,
    )
    expect(threadsWidth(container)).toBeGreaterThanOrEqual(THREADS_MIN_SIZE)
  })

  it("ignores a stored layout that squeezed the thread pane below its floor", () => {
    window.localStorage.setItem("darkmem.chat.panel-sizes", JSON.stringify([10, 66, 24]))
    const { container } = render(
      <ChatPanels threads={<div />} conversation={<div />} context={<div />} />,
    )
    expect(threadsWidth(container)).toBeGreaterThanOrEqual(THREADS_MIN_SIZE)
  })
})
