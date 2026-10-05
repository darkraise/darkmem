import { render, screen } from "@testing-library/react"
import {
  RouterProvider,
  createMemoryHistory,
  createRootRoute,
  createRouter,
} from "@tanstack/react-router"
import { createRef, type ReactNode } from "react"
import { describe, expect, it } from "vitest"
import { registerNavLabels, tanstackRouterAdapter } from "../router-adapter"

const Link = tanstackRouterAdapter.Link as unknown as (
  props: Record<string, unknown> & { to: string; children: ReactNode },
) => ReactNode

function renderInRouter(node: ReactNode) {
  const rootRoute = createRootRoute({ component: () => <>{node}</> })
  const router = createRouter({
    routeTree: rootRoute,
    history: createMemoryHistory({ initialEntries: ["/"] }),
  })
  return render(<RouterProvider router={router} />)
}

describe("AdapterLink", () => {
  it("names a collapsed rail link from the registered nav", async () => {
    registerNavLabels([{ items: [{ href: "/memories", label: "Memories" }] }])
    renderInRouter(
      <Link
        to="/memories"
        data-collapsed="true"
        className="dr-sidebar-nav-link"
      >
        <span />
      </Link>,
    )
    expect(
      await screen.findByRole("link", { name: "Memories" }),
    ).toHaveAttribute("data-collapsed", "true")
  })

  it("forwards the ref and Slot-merged props a tooltip trigger needs", async () => {
    const ref = createRef<HTMLAnchorElement>()
    renderInRouter(
      <Link
        to="/facts"
        ref={ref}
        data-state="closed"
        aria-describedby="tip"
        onPointerEnter={() => {}}
      >
        Facts
      </Link>,
    )
    const link = await screen.findByRole("link", { name: "Facts" })
    expect(ref.current).toBe(link)
    expect(link).toHaveAttribute("data-state", "closed")
    expect(link).toHaveAttribute("aria-describedby", "tip")
  })
})
