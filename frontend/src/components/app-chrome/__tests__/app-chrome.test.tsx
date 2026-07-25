import { fireEvent, render, screen, within } from "@testing-library/react"
import { describe, it, expect, beforeEach, vi } from "vitest"
import { Brain } from "lucide-react"
import { AppPageHeader } from "../app-page-header"
import { BackToTop } from "../back-to-top"
import { PageChrome, usePageChrome } from "../page-chrome"

beforeEach(() => {
  usePageChrome.setState({
    icon: null,
    title: "",
    description: "",
    breadcrumbs: [],
    actions: null,
  })
})

describe("PageChrome / AppPageHeader", () => {
  it("renders nothing when no page has published chrome", () => {
    const { container } = render(<AppPageHeader />)
    expect(container).toBeEmptyDOMElement()
  })

  it("publishes title, description, and actions into the header", () => {
    render(
      <>
        <PageChrome
          icon={Brain}
          title="Memories"
          description="the L0 surface"
          actions={<button type="button">Create memory</button>}
        />
        <AppPageHeader />
      </>,
    )
    expect(
      screen.getByRole("heading", { name: "Memories" }),
    ).toBeInTheDocument()
    expect(screen.getByText("the L0 surface")).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: "Create memory" }),
    ).toBeInTheDocument()
  })

  it("renders a breadcrumb trail ending in the current page", () => {
    render(
      <>
        <PageChrome title="Memory detail" breadcrumbs={[{ label: "Memories" }]} />
        <AppPageHeader />
      </>,
    )
    const nav = screen.getByRole("navigation", { name: "Breadcrumb" })
    expect(nav).toHaveTextContent("Memories")
    // "Memory detail" also renders as the h1; scope to the crumb trail.
    const { getByText } = within(nav)
    expect(getByText("Memory detail")).toHaveAttribute("aria-current", "page")
  })

  it("clears the chrome when the page unmounts", () => {
    const { unmount } = render(<PageChrome title="Memories" />)
    expect(usePageChrome.getState().title).toBe("Memories")
    unmount()
    expect(usePageChrome.getState().title).toBe("")
  })
})

describe("BackToTop", () => {
  it("appears after scrolling the main content and scrolls back to top", () => {
    const main = document.createElement("main")
    main.id = "main-content"
    main.scrollTo = vi.fn()
    document.body.appendChild(main)
    try {
      render(<BackToTop />)
      expect(
        screen.queryByRole("button", { name: "Back to top" }),
      ).not.toBeInTheDocument()

      Object.defineProperty(main, "scrollTop", {
        configurable: true,
        value: 800,
      })
      fireEvent.scroll(main)
      const button = screen.getByRole("button", { name: "Back to top" })

      fireEvent.click(button)
      expect(main.scrollTo).toHaveBeenCalledWith({
        top: 0,
        behavior: "smooth",
      })
    } finally {
      main.remove()
    }
  })
})
