import { fireEvent, render, screen } from "@testing-library/react"
import { describe, it, expect, beforeEach, vi } from "vitest"
import { Brain } from "lucide-react"

vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({
    to,
    children,
    ...rest
  }: { to: string; children: React.ReactNode } & Record<string, unknown>) => (
    <a href={to} {...rest}>
      {children}
    </a>
  ),
}))

import { AppPageHeader } from "../app-page-header"
import { BackToTop } from "../back-to-top"
import { PageChrome, usePageChrome } from "../page-chrome"

beforeEach(() => {
  usePageChrome.setState({
    icon: null,
    title: "",
    description: "",
    parent: null,
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

  it("renders a back link for a page that declares a parent", () => {
    render(
      <>
        <PageChrome
          title="Memory detail"
          parent={{ label: "Memories", href: "/memories" }}
        />
        <AppPageHeader />
      </>,
    )
    const back = screen.getByRole("link", { name: "Back to Memories" })
    expect(back).toHaveAttribute("href", "/memories")
  })

  it("omits the back link on a page with no parent", () => {
    render(
      <>
        <PageChrome title="Memories" />
        <AppPageHeader />
      </>,
    )
    expect(screen.queryByRole("link")).not.toBeInTheDocument()
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
