import { describe, it, expect, beforeEach, vi, afterEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"
import { ProjectSwitcher } from "../project-switcher"
import {
  useProjectStore,
  DEFAULT_PROJECT,
  ALL_PROJECTS,
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
          checkpoint_count: 0, last_checkpoint_at: null, last_event_day: null,
        },
        {
          name: "acme", memory_count: 1, document_count: 0,
          checkpoint_count: 0, last_checkpoint_at: null, last_event_day: null,
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
          checkpoint_count: 0, last_checkpoint_at: null, last_event_day: null,
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
          document_count: 0, checkpoint_count: 0,
          last_checkpoint_at: null, last_event_day: null },
        { name: "notes", kind: "personal", memory_count: 0,
          document_count: 12, checkpoint_count: 0,
          last_checkpoint_at: null, last_event_day: null },
      ],
      isLoading: false,
    })
    renderSwitcher()
    await userEvent.click(screen.getByRole("button", { name: /project scope/i }))
    expect(screen.getByText("darkmem")).toBeInTheDocument()
    expect(screen.queryByText("notes")).toBeNull()
  })
})
