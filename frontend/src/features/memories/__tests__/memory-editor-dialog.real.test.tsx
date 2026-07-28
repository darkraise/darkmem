import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

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
  tags: [],
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
  expires_at: null,
  is_archived: false,
  status: "active",
}

describe("MemoryEditorDialog (DEMO off — editing isn't wired to the backend yet)", () => {
  it("prefills the fetched real memory's content but disables Save", () => {
    render(
      <MemoryEditorDialog
        open
        onOpenChange={vi.fn()}
        memory={REAL_MEMORY}
        projects={[]}
      />,
    )

    expect(screen.getByLabelText("Content")).toHaveValue(REAL_MEMORY.content)
    const save = screen.getByRole("button", { name: "Save changes" })
    expect(save).toBeDisabled()
    expect(save).toHaveAttribute("title", "Editing isn't wired to the backend yet")
  })

  it("names the reason inline, not only on the disabled button's title", () => {
    render(
      <MemoryEditorDialog
        open
        onOpenChange={vi.fn()}
        memory={REAL_MEMORY}
        projects={[]}
      />,
    )

    expect(
      screen.getByText(/editing isn't wired to the backend yet/i),
    ).toBeInTheDocument()
  })
})
