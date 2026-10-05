import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
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
  const pane = container.querySelector<HTMLElement>(
    '[data-panel-id="chat-threads"]',
  )!
  return Number.parseFloat(pane.style.width)
}

describe("ChatPanels below lg", () => {
  it("shows one pane at a time and brings the conversation forward on a new thread", async () => {
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))
    const panes = (key: string | null) => (
      <ChatPanels
        activeKey={key}
        threads={<p>threads pane</p>}
        conversation={<p>conversation pane</p>}
        context={<p>context pane</p>}
      />
    )
    const { rerender } = render(panes(null))
    expect(screen.getByText("conversation pane")).toBeVisible()
    expect(screen.getByText("context pane")).not.toBeVisible()

    await userEvent.click(screen.getByRole("tab", { name: "Threads" }))
    expect(screen.getByText("threads pane")).toBeVisible()
    expect(screen.getByText("conversation pane")).not.toBeVisible()

    rerender(panes("thread-2"))
    expect(screen.getByText("conversation pane")).toBeVisible()
  })
})

describe("ChatPanels", () => {
  it("opens the thread pane at least as wide as its floor", () => {
    const { container } = render(
      <ChatPanels threads={<div />} conversation={<div />} context={<div />} />,
    )
    expect(threadsWidth(container)).toBeGreaterThanOrEqual(THREADS_MIN_SIZE)
  })

  it("ignores a stored layout that squeezed the thread pane below its floor", () => {
    window.localStorage.setItem(
      "darkmem.chat.panel-sizes",
      JSON.stringify([10, 66, 24]),
    )
    const { container } = render(
      <ChatPanels threads={<div />} conversation={<div />} context={<div />} />,
    )
    expect(threadsWidth(container)).toBeGreaterThanOrEqual(THREADS_MIN_SIZE)
  })
})
