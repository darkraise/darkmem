import { describe, expect, it, vi } from "vitest"
import { render, screen, within } from "@testing-library/react"
import {
  RouterProvider,
  createMemoryHistory,
  createRouter,
} from "@tanstack/react-router"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
// The full route tree imports the graph pages, whose renderer reads WebGL
// globals at module scope; nothing here draws a graph.
vi.hoisted(() => {
  const g = globalThis as Record<string, unknown>
  g.WebGL2RenderingContext ??= class {}
  g.WebGLRenderingContext ??= class {}
})

import { routeTree } from "@/routeTree.gen"

function renderAt(path: string) {
  const router = createRouter({
    routeTree,
    history: createMemoryHistory({ initialEntries: [path] }),
  })
  return render(<RouterProvider router={router} />)
}

// An unknown top-level path used to render the root's bare 404 outside the
// shell, and an unknown path under a real page rendered inside it with no
// title and that page's nav item highlighted. Both are now the one page.
describe.each(["/does-not-exist", "/settings/foo/bar"])("%s", (path) => {
  it("is the shell's not-found page, titled, with nothing highlighted", async () => {
    renderAt(path)
    expect(
      await screen.findByRole("heading", { level: 1, name: "Page not found" }),
    ).toBeInTheDocument()
    const nav = screen.getAllByRole("navigation")[0]!
    expect(
      within(nav).getAllByRole("link", { name: "Settings" }).length,
    ).toBeGreaterThan(0)
    expect(document.querySelector('[data-status="active"]')).toBeNull()
    expect(
      screen.getByRole("link", { name: "Back to the dashboard" }),
    ).toHaveAttribute("href", "/")
  })
})
