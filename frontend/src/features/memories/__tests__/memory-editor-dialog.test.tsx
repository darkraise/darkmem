import { describe, expect, it, vi } from "vitest"
import { render, screen } from "@testing-library/react"
import userEvent from "@testing-library/user-event"

vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

import { MemoryEditorDialog } from "@/features/memories/components/memory-editor-dialog"
import { useDemoStore } from "@/demo/store"

describe("MemoryEditorDialog", () => {
  it("requires content and keeps the draft on a failed submit", async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    render(
      <MemoryEditorDialog
        open
        onOpenChange={onOpenChange}
        projects={["default", "darkmem"]}
      />,
    )

    await user.click(screen.getByRole("button", { name: "Create memory" }))
    expect(screen.getByRole("alert")).toHaveTextContent("Content is required.")
    expect(onOpenChange).not.toHaveBeenCalledWith(false)
  })

  it("adds a memory to the demo store on submit", async () => {
    const user = userEvent.setup()
    const onOpenChange = vi.fn()
    const before = useDemoStore.getState().memories.length
    render(
      <MemoryEditorDialog
        open
        onOpenChange={onOpenChange}
        projects={["default", "darkmem"]}
        defaultProject="darkmem"
      />,
    )

    await user.type(
      screen.getByLabelText("Content"),
      "Captured from the dialog test",
    )
    await user.click(screen.getByRole("button", { name: "Create memory" }))

    const state = useDemoStore.getState()
    expect(state.memories.length).toBe(before + 1)
    expect(state.memories[0]!.content).toBe("Captured from the dialog test")
    expect(state.memories[0]!.project).toBe("darkmem")
    expect(state.memories[0]!.status).toBe("active")
    expect(onOpenChange).toHaveBeenCalledWith(false)
    useDemoStore.getState().resetMemories()
  })

  it("prefills and patches when editing an existing memory", async () => {
    const user = userEvent.setup()
    const target = useDemoStore.getState().memories[0]!
    render(
      <MemoryEditorDialog
        open
        onOpenChange={vi.fn()}
        memory={target}
        projects={["default", "darkmem"]}
      />,
    )

    const content = screen.getByLabelText("Content")
    expect(content).toHaveValue(target.content)
    await user.clear(content)
    await user.type(content, "Edited content")
    await user.click(screen.getByRole("button", { name: "Save changes" }))

    const updated = useDemoStore
      .getState()
      .memories.find((m) => m.id === target.id)!
    expect(updated.content).toBe("Edited content")
    const lastEvent = updated.timeline?.[updated.timeline.length - 1]
    expect(lastEvent?.kind).toBe("updated")
    useDemoStore.getState().resetMemories()
  })
})
