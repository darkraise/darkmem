import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { useState, type ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn(), apiFetchWithHeaders: vi.fn() }))

const binding = vi.hoisted(() => ({
  status: { kind: "idle" } as { kind: string; reason?: string; message?: string },
  discard: vi.fn(),
  generations: [] as number[],
}))

vi.mock("../use-page-sync", () => ({
  usePageSync: (_page: unknown, generation: number) => {
    binding.generations.push(generation)
    return {
      initialBlocks: [],
      status: binding.status,
      onDocumentChange: () => {},
      flushNow: () => {},
      discard: binding.discard,
    }
  },
}))

vi.mock("../page-editor", () => ({
  PageEditor: ({ editable }: { editable: boolean }) => <div>editor {editable ? "editable" : "read-only"}</div>,
}))

import { apiFetch } from "@/lib/api"
import type { PageView } from "@/hooks/api"
import { PagePane } from "../page-pane"

function wrapper({ children }: { children: ReactNode }) {
  const [qc] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } }),
  )
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const PAGE: PageView = {
  id: "p1",
  project: "personal",
  parent_id: null,
  order_index: 0,
  title: "Notes",
  content_hash: "h1",
  blocks: [],
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetch).mockResolvedValue({ id: "p1" })
  binding.status = { kind: "idle" }
  binding.discard.mockReset()
  binding.generations.length = 0
})

describe("PagePane", () => {
  it("renders the title in an editable field and the editor below it", async () => {
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    expect(screen.getByLabelText("Page title")).toHaveValue("Notes")
    expect(await screen.findByText("editor editable")).toBeInTheDocument()
  })

  it("shows the fallback for an untitled page without sending it as a title", () => {
    render(<PagePane page={{ ...PAGE, title: null }} autoFocusTitle={false} />, { wrapper })
    const field = screen.getByLabelText("Page title")
    expect(field).toHaveValue("")
    expect(field).toHaveAttribute("placeholder", "Untitled")
  })

  it("renames on blur, and not when the title is unchanged", async () => {
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    const field = screen.getByLabelText("Page title")
    fireEvent.blur(field)
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
    fireEvent.change(field, { target: { value: "Renamed" } })
    fireEvent.blur(field)
    await waitFor(() =>
      expect(vi.mocked(apiFetch)).toHaveBeenCalledWith("/pages/p1", {
        method: "PATCH",
        body: JSON.stringify({ title: "Renamed" }),
      }),
    )
  })

  it("focuses the title when asked", () => {
    render(<PagePane page={PAGE} autoFocusTitle />, { wrapper })
    expect(screen.getByLabelText("Page title")).toHaveFocus()
  })

  it.each([
    ["idle", null],
    ["saving", "Saving…"],
    ["saved", "Saved"],
    ["retrying", "Unsaved — retrying"],
  ])("labels the %s state", (kind, label) => {
    binding.status = { kind }
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    for (const text of ["Saving…", "Saved", "Unsaved — retrying"]) {
      if (text === label) expect(screen.getByText(text)).toBeInTheDocument()
      else expect(screen.queryByText(text)).not.toBeInTheDocument()
    }
  })

  it("shows a stopped engine as a banner, locks the editor, and reloads", async () => {
    binding.status = { kind: "stopped", reason: "refused", message: "a paragraph block cannot hold a list block" }
    vi.mocked(apiFetch).mockResolvedValue({ ...PAGE, properties: null, content: null, blocks: [] })
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    expect(screen.getByText("This edit was refused — a paragraph block cannot hold a list block")).toBeInTheDocument()
    expect(await screen.findByText("editor read-only")).toBeInTheDocument()
    fireEvent.click(screen.getByRole("button", { name: "Reload page" }))
    expect(binding.discard).toHaveBeenCalledOnce()
    await waitFor(() => expect(binding.generations).toContain(1))
  })

  it("shows a conflict in the engine's own words", () => {
    binding.status = { kind: "stopped", reason: "conflict", message: "This page was changed somewhere else." }
    render(<PagePane page={PAGE} autoFocusTitle={false} />, { wrapper })
    expect(screen.getByText("This page was changed somewhere else.")).toBeInTheDocument()
  })
})
