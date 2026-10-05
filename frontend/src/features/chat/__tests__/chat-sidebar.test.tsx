import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { describe, expect, it, vi } from "vitest"
import { ChatSidebar } from "../components/chat-sidebar"
import type { ChatConversation } from "@/hooks/api"

const conversations: ChatConversation[] = [
  {
    id: "c1",
    title: "Reranker defaults",
    created_at: "2026-10-01T00:00:00Z",
    updated_at: "2026-10-01T00:00:00Z",
    is_archived: false,
    message_count: 4,
  },
]

describe("ChatSidebar delete", () => {
  it("asks before deleting a conversation", async () => {
    const onDelete = vi.fn()
    render(
      <ChatSidebar
        conversations={conversations}
        activeId={null}
        onSelect={vi.fn()}
        onCreate={vi.fn()}
        onDelete={onDelete}
      />,
    )
    await userEvent.click(
      screen.getByRole("button", {
        name: "Delete conversation Reranker defaults",
      }),
    )
    // The trash button only opens the confirmation.
    expect(onDelete).not.toHaveBeenCalled()
    const dialog = await screen.findByRole("alertdialog")
    await userEvent.click(
      within(dialog).getByRole("button", { name: "Cancel" }),
    )
    expect(onDelete).not.toHaveBeenCalled()

    await userEvent.click(
      screen.getByRole("button", {
        name: "Delete conversation Reranker defaults",
      }),
    )
    await userEvent.click(
      within(await screen.findByRole("alertdialog")).getByRole("button", {
        name: "Delete",
      }),
    )
    expect(onDelete).toHaveBeenCalledWith("c1")
  })

  it("Enter on the delete button does not select the row", async () => {
    const onSelect = vi.fn()
    render(
      <ChatSidebar
        conversations={conversations}
        activeId={null}
        onSelect={onSelect}
        onCreate={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    screen
      .getByRole("button", { name: "Delete conversation Reranker defaults" })
      .focus()
    await userEvent.keyboard("{Enter}")
    expect(onSelect).not.toHaveBeenCalled()
    expect(await screen.findByRole("alertdialog")).toBeInTheDocument()
  })
})
