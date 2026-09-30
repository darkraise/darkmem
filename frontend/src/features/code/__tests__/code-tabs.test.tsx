import { render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"

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

import { RepositoriesTab } from "../components/repositories-tab"
import { CodeGraphTab } from "../components/code-graph-tab"
import { WikiTab } from "../components/wiki-tab"

describe("RepositoriesTab", () => {
  it("renders every repo state honestly", () => {
    render(<RepositoriesTab onOpenGraph={vi.fn()} />)
    expect(screen.queryByText("gated by repository, not project")).toBeNull()
    expect(screen.queryByText("not applied here")).toBeNull()
    // T1 fail-stale banner — last-good graph served, never wiped
    expect(
      screen.getByText("Last index failed — showing the last good graph"),
    ).toBeInTheDocument()
    // T2 index-debt indicator
    expect(
      screen.getByText(/168 dependent files queued/),
    ).toBeInTheDocument()
    // auto-provision registration state
    expect(screen.getByText("auto-provisioned 2026-07-22")).toBeInTheDocument()
    // live phase ticker for the mid-index repo
    expect(
      screen.getAllByText(/Call tracing/).length,
    ).toBeGreaterThan(0)
    // error banner surfaces the raw failure message
    expect(
      screen.getByText(/Permission denied \(publickey\)/),
    ).toBeInTheDocument()
  })

  it("routes 'Open code graph' through the callback", () => {
    const onOpenGraph = vi.fn()
    render(<RepositoriesTab onOpenGraph={onOpenGraph} />)
    const buttons = screen.getAllByRole("button", { name: /Open code graph/ })
    expect(buttons.length).toBeGreaterThan(0)
    buttons[0]?.click()
    expect(onOpenGraph).toHaveBeenCalledWith("repo-backend")
  })
})

describe("CodeGraphTab", () => {
  it("renders chrome, the explorer/filters rail, and analysis panels for a ready repo", () => {
    render(
      <CodeGraphTab
        repoId="repo-backend"
        onRepoChange={vi.fn()}
        onOpenRepositories={vi.fn()}
      />,
    )
    expect(screen.queryByText("scope: repository, not project")).toBeNull()
    expect(screen.getByRole("tab", { name: "Explorer" })).toBeInTheDocument()
    expect(screen.getByRole("tab", { name: "Filters" })).toBeInTheDocument()
    // The explorer opens on the repo's tracked tree, not a flat symbol list.
    expect(screen.getByText("services")).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: "Run Blast Radius" }),
    ).toBeDisabled()
    expect(screen.getByText("memory ingestion pipeline")).toBeInTheDocument()
    expect(screen.getByText("Community navigator")).toBeInTheDocument()
    expect(screen.getAllByText(/ingestion & pipeline/).length).toBeGreaterThan(
      0,
    )
  })

  it("shows the never-indexed empty state pointing at Repositories", () => {
    const onOpenRepositories = vi.fn()
    render(
      <CodeGraphTab
        repoId="repo-storefront"
        onRepoChange={vi.fn()}
        onOpenRepositories={onOpenRepositories}
      />,
    )
    expect(screen.getByText("No graph yet")).toBeInTheDocument()
    screen
      .getByRole("button", { name: /Open reindex dialog on Repositories/ })
      .click()
    expect(onOpenRepositories).toHaveBeenCalled()
  })

  it("shows the live phase for an indexing repo, not a bare spinner", () => {
    render(
      <CodeGraphTab
        repoId="repo-billing"
        onRepoChange={vi.fn()}
        onOpenRepositories={vi.fn()}
      />,
    )
    expect(
      screen.getByText(/Building the code graph for legacy-billing-service/),
    ).toBeInTheDocument()
    expect(screen.getByText(/phase 06/)).toBeInTheDocument()
  })

  it("marks a stale repo's served graph in the toolbar", () => {
    render(
      <CodeGraphTab
        repoId="repo-payments"
        onRepoChange={vi.fn()}
        onOpenRepositories={vi.fn()}
      />,
    )
    expect(
      screen.getByText(/showing last good graph \(4b7e120\)/),
    ).toBeInTheDocument()
  })
})

describe("WikiTab", () => {
  it("renders the generated wiki with toc and generation metadata", () => {
    render(<WikiTab repoId="repo-backend" onRepoChange={vi.fn()} />)
    expect(screen.getByText("Contents")).toBeInTheDocument()
    expect(
      screen.getAllByText("Ingestion pipeline").length,
    ).toBeGreaterThan(0)
    expect(screen.getByText("2026-07-20 04:12")).toBeInTheDocument()
    expect(
      screen.queryByText("repo-scoped — not the project switcher"),
    ).toBeNull()
  })

  it("empty state points at the reindex dialog, never implicitly generates", () => {
    render(<WikiTab repoId="repo-frontend" onRepoChange={vi.fn()} />)
    expect(
      screen.getByText("No wiki generated yet for this repository"),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: /Open reindex dialog/ }),
    ).toBeInTheDocument()
  })
})
