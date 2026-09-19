import { render, screen } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@tanstack/react-router", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@tanstack/react-router")>()),
  Link: ({ children, className }: { children?: ReactNode; className?: string }) => (
    <a className={className}>{children}</a>
  ),
}))

import { ArticlesTab } from "../components/articles-tab"
import { useProjectStore } from "@/stores/project-store"

describe("Articles list", () => {
  it("gives every row the same badge-column width so titles align", () => {
    useProjectStore.setState({ activeProject: null, missingProject: null })
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ArticlesTab />
      </QueryClientProvider>,
    )
    const columns = screen.getAllByTestId("article-badges")
    expect(columns.length).toBeGreaterThan(0)
    for (const column of columns) expect(column).toHaveClass("w-40", "shrink-0")
  })
})
