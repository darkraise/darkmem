import { describe, it, expect, beforeEach, vi, afterEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import {
  CODE_SCOPE_REASON,
  ProjectScopeReconciler,
  ProjectSwitcher,
  projectScopeDisabledReason,
} from "../project-switcher"
import {
  useProjectStore,
  DEFAULT_PROJECT,
  ALL_PROJECTS,
  STALE_SCOPE_NOTICE,
} from "@/stores/project-store"
import { useContextStore } from "@/stores/context-store"

const mockUseProjects = vi.fn()
vi.mock("@/hooks/api", () => ({
  useProjects: () => mockUseProjects(),
}))

function renderSwitcher() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  const wrapper = ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
  return render(<ProjectSwitcher />, { wrapper })
}

describe("ProjectSwitcher", () => {
  beforeEach(() => {
    useProjectStore.setState({
      activeProject: DEFAULT_PROJECT,
      missingProject: null,
    })
    useContextStore.setState({ declared: null })
    mockUseProjects.mockReturnValue({ data: [], isLoading: false })
  })

  afterEach(() => {
    mockUseProjects.mockReset()
  })

  it("shows the active project, always visible without opening anything", () => {
    useProjectStore.getState().setProject("acme")
    renderSwitcher()
    expect(
      screen.getByRole("button", { name: /project scope/i }),
    ).toHaveTextContent("project: acme")
  })

  it("switching projects updates the store", async () => {
    mockUseProjects.mockReturnValue({
      data: [{ name: "acme", memory_count: 3 }],
      isLoading: false,
    })
    const user = userEvent.setup()
    renderSwitcher()

    await user.click(screen.getByRole("button", { name: /project scope/i }))
    await user.click(await screen.findByRole("button", { name: /^acme/ }))

    expect(useProjectStore.getState().activeProject).toBe("acme")
  })

  // A scope exists only once a memory carries it, so the switcher offers no
  // way to name one: a typed project would scope every view to a guaranteed
  // empty corpus.
  it("offers no free-text way to name a project", async () => {
    useProjectStore.getState().setProject("acme")
    const user = userEvent.setup()
    renderSwitcher()

    await user.click(screen.getByRole("button", { name: /project scope/i }))

    expect(screen.queryByRole("textbox")).not.toBeInTheDocument()
    expect(
      screen.queryByRole("button", { name: /^switch$/i }),
    ).not.toBeInTheDocument()
  })

  // A scope this browser once visited is not evidence the corpus still holds
  // it — the server list is the only source, so a project whose last memory
  // was deleted leaves the switcher.
  it("does not offer a visited project the corpus no longer holds", async () => {
    useProjectStore.getState().setProject("beta")
    mockUseProjects.mockReturnValue({
      data: [{ name: "darkmem", memory_count: 4 }],
      isLoading: false,
    })
    const user = userEvent.setup()
    renderSwitcher()

    await user.click(screen.getByRole("button", { name: /project scope/i }))
    await screen.findByRole("button", { name: /^darkmem/ })

    expect(screen.queryByRole("button", { name: /^beta/ })).not.toBeInTheDocument()
  })

  // The switcher used to offer only what this browser had visited, so a
  // project captured by another client was reachable solely by typing its
  // name exactly right.
  it("offers every project the corpus holds, with its size", async () => {
    mockUseProjects.mockReturnValue({
      data: [
        {
          name: "darkmem", memory_count: 18, document_count: 2,
          checkpoint_count: 0, page_count: 0, last_checkpoint_at: null,
          last_event_day: null,
        },
        {
          name: "acme", memory_count: 1, document_count: 0,
          checkpoint_count: 0, page_count: 0, last_checkpoint_at: null,
          last_event_day: null,
        },
      ],
      isLoading: false,
    })
    const user = userEvent.setup()
    renderSwitcher()

    await user.click(screen.getByRole("button", { name: /project scope/i }))

    // Items across all three corpora, not memories: 18 + 2 + 0.
    expect(
      await screen.findByRole("button", { name: /darkmem.*20 items/ }),
    ).toBeInTheDocument()
    // Singular, so a one-item project does not read as "1 items".
    expect(
      screen.getByRole("button", { name: /acme.*1 item$/ }),
    ).toBeInTheDocument()
  })

  it("counts a document-only project rather than showing it as empty", async () => {
    // The corpus import creates exactly this shape. Under a memories-only
    // hint it read "0 memories" for a scope holding a hundred files.
    mockUseProjects.mockReturnValue({
      data: [
        {
          name: "docs-only", memory_count: 0, document_count: 42,
          checkpoint_count: 0, page_count: 0, last_checkpoint_at: null,
          last_event_day: null,
        },
      ],
      isLoading: false,
    })
    const user = userEvent.setup()
    renderSwitcher()

    await user.click(screen.getByRole("button", { name: /project scope/i }))

    expect(
      await screen.findByRole("button", { name: /docs-only.*42 items/ }),
    ).toBeInTheDocument()
  })

  it("counts pages in a project's item total", async () => {
    mockUseProjects.mockReturnValue({
      data: [
        {
          name: "darkmem",
          kind: "project" as const,
          memory_count: 1,
          document_count: 2,
          checkpoint_count: 3,
          page_count: 4,
          last_checkpoint_at: null,
          last_event_day: null,
        },
      ],
      isLoading: false,
    })
    const user = userEvent.setup()
    renderSwitcher()

    await user.click(screen.getByRole("button", { name: /project scope/i }))

    // 1 + 2 + 3 + 4. Under the three-corpus total it read "6 items".
    expect(
      await screen.findByRole("button", { name: /darkmem.*10 items/ }),
    ).toBeInTheDocument()
  })

  it("switches to a server-listed project the browser has never visited", async () => {
    mockUseProjects.mockReturnValue({
      data: [{ name: "darkmem", memory_count: 20 }],
      isLoading: false,
    })
    const user = userEvent.setup()
    renderSwitcher()

    await user.click(screen.getByRole("button", { name: /project scope/i }))
    await user.click(await screen.findByRole("button", { name: /^darkmem/ }))

    expect(useProjectStore.getState().activeProject).toBe("darkmem")
  })

  // The wide scope is the absence of one, so it must not read back as a
  // project named anything.
  it("selects every project at once without minting a project", async () => {
    const user = userEvent.setup()
    renderSwitcher()

    await user.click(screen.getByRole("button", { name: /project scope/i }))
    await user.click(await screen.findByRole("button", { name: /All projects/ }))

    expect(useProjectStore.getState().activeProject).toBe(ALL_PROJECTS)
    expect(
      screen.getByRole("button", { name: /project scope/i }),
    ).toHaveTextContent("project: all projects")
  })

  // Ruling 3: switching the project is a scope change and must never
  // declare a context as a side effect.
  it("never writes to contextStore when switching projects", async () => {
    mockUseProjects.mockReturnValue({
      data: [{ name: "production", memory_count: 9 }],
      isLoading: false,
    })
    const user = userEvent.setup()
    renderSwitcher()

    await user.click(screen.getByRole("button", { name: /project scope/i }))
    await user.click(await screen.findByRole("button", { name: /^production/ }))

    expect(useProjectStore.getState().activeProject).toBe("production")
    expect(useContextStore.getState().declared).toBeNull()
  })

  it("omits the personal notes space from the scope list", async () => {
    // The notes space has its own route and its own workspace. Offering it
    // here would open it in a surface built for project artifacts.
    mockUseProjects.mockReturnValue({
      data: [
        { name: "darkmem", kind: "project", memory_count: 3,
          document_count: 0, checkpoint_count: 0, page_count: 0,
          last_checkpoint_at: null, last_event_day: null },
        { name: "notes", kind: "personal", memory_count: 0,
          document_count: 12, checkpoint_count: 0, page_count: 0,
          last_checkpoint_at: null, last_event_day: null },
      ],
      isLoading: false,
    })
    renderSwitcher()
    await userEvent.click(screen.getByRole("button", { name: /project scope/i }))
    expect(screen.getByText("darkmem")).toBeInTheDocument()
    expect(screen.queryByText("notes")).toBeNull()
  })

  it("offers All projects first", async () => {
    mockUseProjects.mockReturnValue({
      data: [{ name: "acme", kind: "project", memory_count: 3, document_count: 0, checkpoint_count: 0, page_count: 0 }],
      isLoading: false,
    })
    const user = userEvent.setup()
    renderSwitcher()
    await user.click(screen.getByRole("button", { name: /project scope/i }))
    const labels = screen
      .getAllByRole("button")
      .filter((b) => b.hasAttribute("aria-pressed"))
      .map((row) => row.textContent ?? "")
    expect(labels[0]).toMatch(/^All projects/)
    expect(labels.findIndex((l) => l.startsWith("All projects"))).toBeLessThan(
      labels.findIndex((l) => l.startsWith("acme")),
    )
  })

  it("says so when a saved project was not found", () => {
    useProjectStore.setState({ activeProject: ALL_PROJECTS, missingProject: "gone" })
    renderSwitcher()
    expect(screen.getByText(STALE_SCOPE_NOTICE)).toBeInTheDocument()
    expect(
      screen.getByRole("button", { name: /project scope/i }),
    ).toHaveTextContent("project: all projects")
  })
})

describe("ProjectScopeReconciler", () => {
  beforeEach(() => {
    useProjectStore.setState({ activeProject: "gone", missingProject: null })
  })

  it("widens a saved scope the server list does not hold", () => {
    mockUseProjects.mockReturnValue({
      data: [
        { name: "acme", kind: "project" },
        { name: "notes", kind: "personal" },
      ],
      isLoading: false,
      isSuccess: true,
    })
    render(<ProjectScopeReconciler />)
    expect(useProjectStore.getState().activeProject).toBe(ALL_PROJECTS)
    expect(useProjectStore.getState().missingProject).toBe("gone")
  })

  it("does nothing until the list has loaded", () => {
    mockUseProjects.mockReturnValue({ data: undefined, isLoading: true, isSuccess: false })
    render(<ProjectScopeReconciler />)
    expect(useProjectStore.getState().activeProject).toBe("gone")
  })

  it("treats the personal space as no project scope", () => {
    useProjectStore.setState({ activeProject: "notes", missingProject: null })
    mockUseProjects.mockReturnValue({
      data: [{ name: "notes", kind: "personal" }],
      isLoading: false,
      isSuccess: true,
    })
    render(<ProjectScopeReconciler />)
    expect(useProjectStore.getState().activeProject).toBe(ALL_PROJECTS)
  })
})

describe("project scope on code pages", () => {
  it("names the code routes and nothing else", () => {
    expect(projectScopeDisabledReason("/code/graph")).toBe(CODE_SCOPE_REASON)
    expect(projectScopeDisabledReason("/code/repositories")).toBe(CODE_SCOPE_REASON)
    expect(projectScopeDisabledReason("/code")).toBe(CODE_SCOPE_REASON)
    expect(projectScopeDisabledReason("/codex")).toBeUndefined()
    expect(projectScopeDisabledReason("/memories")).toBeUndefined()
  })

  it("renders the switcher disabled, explaining why", async () => {
    mockUseProjects.mockReturnValue({ data: [], isLoading: false })
    const user = userEvent.setup()
    const qc = new QueryClient()
    render(
      <QueryClientProvider client={qc}>
        <ProjectSwitcher disabledReason={CODE_SCOPE_REASON} />
      </QueryClientProvider>,
    )
    expect(screen.getByRole("button", { name: /project scope/i })).toBeDisabled()
    await user.hover(screen.getByLabelText(`Project scope — ${CODE_SCOPE_REASON}`))
    expect(await screen.findAllByText(CODE_SCOPE_REASON)).not.toHaveLength(0)
  })
})
