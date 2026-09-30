import { describe, expect, it, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

import { apiFetch } from "@/lib/api"
import { toast } from "darkraise-ui/components/sonner"
import { MemoryEditorDialog } from "@/features/memories/components/memory-editor-dialog"
import type { Memory } from "@/hooks/api/use-memory-api"

const REAL_MEMORY: Memory = {
  id: "mem-1",
  content: "we use nomic-embed-text for embeddings",
  source: "mcp",
  source_agent: null,
  memory_type: "fact",
  importance: 5,
  metadata: {},
  tags: ["embeddings"],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  expires_at: null,
  is_archived: false,
  status: "active",
}

function wrapper({ children }: { children: ReactNode }) {
  return (
    <QueryClientProvider client={new QueryClient()}>
      {children}
    </QueryClientProvider>
  )
}

describe("MemoryEditorDialog (DEMO off)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("hides the fields the update route cannot save", () => {
    render(
      <MemoryEditorDialog
        open
        onOpenChange={vi.fn()}
        memory={REAL_MEMORY}
        projects={[]}
      />,
      { wrapper },
    )

    expect(screen.getByLabelText("Content")).toHaveValue(REAL_MEMORY.content)
    expect(screen.queryByText("Project")).toBeNull()
    expect(screen.queryByLabelText(/Context/)).toBeNull()
  })

  it("saves content, type and tags through PUT and closes", async () => {
    vi.mocked(apiFetch).mockResolvedValue(REAL_MEMORY)
    const onOpenChange = vi.fn()
    const user = userEvent.setup()
    render(
      <MemoryEditorDialog
        open
        onOpenChange={onOpenChange}
        memory={REAL_MEMORY}
        projects={[]}
      />,
      { wrapper },
    )

    const content = screen.getByLabelText("Content")
    await user.clear(content)
    await user.type(content, "we use qwen3-embedding for embeddings")
    await user.click(screen.getByRole("button", { name: "Save changes" }))

    await vi.waitFor(() => expect(onOpenChange).toHaveBeenCalledWith(false))
    expect(apiFetch).toHaveBeenCalledWith("/memories/mem-1", {
      method: "PUT",
      body: JSON.stringify({
        content: "we use qwen3-embedding for embeddings",
        memory_type: "fact",
        tags: ["embeddings"],
      }),
    })
    expect(toast.success).toHaveBeenCalledWith("Memory updated")
  })

  it("keeps the dialog open and says so when the save fails", async () => {
    vi.mocked(apiFetch).mockRejectedValue(new Error("500"))
    const onOpenChange = vi.fn()
    const user = userEvent.setup()
    render(
      <MemoryEditorDialog
        open
        onOpenChange={onOpenChange}
        memory={REAL_MEMORY}
        projects={[]}
      />,
      { wrapper },
    )

    await user.click(screen.getByRole("button", { name: "Save changes" }))

    await vi.waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("Could not save the memory"),
    )
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
  })
})
