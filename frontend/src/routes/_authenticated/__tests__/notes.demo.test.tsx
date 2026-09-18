import { render, screen } from "@testing-library/react"
import type { ComponentType } from "react"
import { expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@tanstack/react-router", async () => ({
  ...(await vi.importActual<Record<string, unknown>>("@tanstack/react-router")),
  createFileRoute: () => (opts: Record<string, unknown>) => opts,
  useSearch: () => ({}),
  useNavigate: () => vi.fn(),
}))
vi.mock("@/features/notes/demo-notes", () => ({ DemoNotes: () => <div>demo notes</div> }))
vi.mock("@/hooks/api", () => ({ useProjects: () => ({ data: undefined, isLoading: false, isError: false }) }))

import { Route } from "../notes"

it("renders the demo page instead of the catalogue branches", () => {
  const Component = (Route.options ?? Route).component as ComponentType
  render(<Component />)
  expect(screen.getByText("demo notes")).toBeInTheDocument()
  expect(screen.queryByText("No personal space yet")).not.toBeInTheDocument()
})
