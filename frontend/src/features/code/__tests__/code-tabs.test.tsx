import { fireEvent, render, screen } from "@testing-library/react"
import { describe, it, expect, vi } from "vitest"
import { CodeGlowCanvasStub } from "@/test/code-glow-canvas-stub"
import type { CodeGlowCanvasProps } from "@/features/code/components/code-glow-canvas"

vi.hoisted(() => {
  const g = globalThis as Record<string, unknown>
  g.WebGL2RenderingContext ??= class {}
  g.WebGLRenderingContext ??= class {}
})

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
// The stub imports drawnGraph from the mocked module, so the factory must not
// import the stub itself (it would wait on its own mock); the component looks
// the stub up at render time instead.
vi.mock("@/features/code/components/code-glow-canvas", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/features/code/components/code-glow-canvas")>()),
  CodeGlowCanvas: (props: CodeGlowCanvasProps) => <CodeGlowCanvasStub {...props} />,
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
    expect(screen.getByText(/168 dependent files queued/)).toBeInTheDocument()
    // auto-provision registration state
    expect(screen.getByText("auto-provisioned 2026-07-22")).toBeInTheDocument()
    // live phase ticker for the mid-index repo
    expect(screen.getAllByText(/Call tracing/).length).toBeGreaterThan(0)
    // error banner surfaces the raw failure message
    expect(
      screen.getByText(/Permission denied \(publickey\)/),
    ).toBeInTheDocument()
  })

  it("summarises an indexing repo and keeps the full ticker behind a toggle", () => {
    render(<RepositoriesTab onOpenGraph={vi.fn()} />)
    expect(screen.getByText(/phase 06 of 14, \d+ skipped/)).toBeInTheDocument()
    const toggle = screen.getByRole("button", { name: /Show all 14 phases/ })
    expect(toggle).toHaveAttribute("aria-expanded", "false")
    fireEvent.click(toggle)
    expect(toggle).toHaveAttribute("aria-expanded", "true")
    expect(screen.getByText("File discovery")).toBeVisible()
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
  it("offers one layout: no Layout switch and no Play/Pause", () => {
    render(
      <CodeGraphTab
        repoId="repo-backend"
        onRepoChange={vi.fn()}
        onOpenRepositories={vi.fn()}
      />,
    )
    expect(screen.queryByRole("group", { name: "Graph layout" })).toBeNull()
    expect(screen.queryByRole("button", { name: /Play layout|Pause layout/ })).toBeNull()
    expect(screen.getByRole("group", { name: /^Code graph — \d+ nodes, \d+ edges$/ })).toBeInTheDocument()
  })

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
    // Same wording as the Repositories card: every phase in the
    // denominator, skipped ones named rather than dropped from the count.
    expect(screen.getByText(/phase 06 of 14, \d+ skipped/)).toBeInTheDocument()
  })

  it("keeps the depth filter disabled until a node is selected", () => {
    render(
      <CodeGraphTab
        repoId="repo-backend"
        onRepoChange={vi.fn()}
        onOpenRepositories={vi.fn()}
      />,
    )
    const depth = screen.getByRole("radiogroup", {
      name: /Neighbourhood depth/,
    })
    for (const item of depth.querySelectorAll("button")) {
      expect(item).toBeDisabled()
    }
    fireEvent.click(screen.getByRole("button", { name: /^dedup_entities/ }))
    for (const item of depth.querySelectorAll("button")) {
      expect(item).not.toBeDisabled()
    }
    // The toolbar spells its count out rather than "18 n 18 e".
    expect(screen.getByText(/nodes ·/)).toBeInTheDocument()
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
    expect(screen.getAllByText("Ingestion pipeline").length).toBeGreaterThan(0)
    expect(screen.getByText("2026-07-20 04:12")).toBeInTheDocument()
    expect(
      screen.queryByText("repo-scoped — not the project switcher"),
    ).toBeNull()
  })

  it("an errored repo explains the failure instead of inviting a reindex", () => {
    render(<WikiTab repoId="repo-tools" onRepoChange={vi.fn()} />)
    expect(
      screen.getByText(/Permission denied \(publickey\)/),
    ).toBeInTheDocument()
    expect(
      screen.getByRole("link", { name: /Fix on Repositories/ }),
    ).toHaveAttribute("href", "/code/repositories")
    expect(
      screen.queryByRole("button", { name: /Open reindex dialog/ }),
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
