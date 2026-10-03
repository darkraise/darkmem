import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, act, waitFor, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

const mockUseConversations = vi.fn()
const mockUseConversation = vi.fn()
const mockUseCreateConversation = vi.fn()
const mockUseDeleteConversation = vi.fn()

vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useConversations: () => mockUseConversations(),
  useConversation: (id: string | null) => mockUseConversation(id),
  useCreateConversation: () => mockUseCreateConversation(),
  useDeleteConversation: () => mockUseDeleteConversation(),
}))

import { RealChatPage } from "../components/real-chat-page"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

// T1.60 Step 7: RealChatPage assembles already-tested primitives
// (ChatSidebar, ChatMessages + ChatInput, useChatStream + useConversation)
// into the three-column layout DemoChatPage already has. No mutation proof
// required here (the plan's own text) — this step is assembly, not a new
// invariant; Step 8 is what makes the third column honest.
describe("RealChatPage", () => {
  it("follows mounted route changes", async () => {
    mockUseConversations.mockReturnValue({ data: { conversations: [] } })
    const view = render(<RealChatPage initialId="first" />, { wrapper })
    view.rerender(<RealChatPage initialId="second" />)
    await waitFor(() => expect(mockUseConversation).toHaveBeenLastCalledWith("second"))
  })

  it("hides another conversation's live turn and does not navigate on its completion", async () => {
    mockUseConversations.mockReturnValue({ data: { conversations: [{ id: "second", title: "Second", created_at: "", updated_at: "" }] } })
    let controller!: ReadableStreamDefaultController<Uint8Array>
    const body = new ReadableStream<Uint8Array>({ start(streamController) { controller = streamController } })
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, body }))
    render(<RealChatPage />, { wrapper })
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "original draft" } })
    await userEvent.click(screen.getByRole("button", { name: "Send message" }))
    await act(async () => { controller.enqueue(new TextEncoder().encode('data: {"type":"token","content":"old live answer"}\n\n')) })
    await userEvent.click(screen.getByText("Second"))
    expect(screen.queryByText("old live answer")).not.toBeInTheDocument()
    expect(screen.queryByText("original draft")).not.toBeInTheDocument()
    await act(async () => {
      controller.enqueue(new TextEncoder().encode('data: {"type":"done","conversation_id":"created"}\n\n'))
      controller.close()
    })
    expect(mockUseConversation).toHaveBeenLastCalledWith("second")
    vi.unstubAllGlobals()
  })

  it("announces a rejected send and restores its retryable draft", async () => {
    mockUseConversations.mockReturnValue({ data: { conversations: [] } })
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 403, text: async () => "Read only" }))
    render(<RealChatPage />, { wrapper })
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "keep this draft" } })
    await userEvent.click(screen.getByRole("button", { name: "Send message" }))
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Read only"))
    expect(screen.getByRole("textbox")).toHaveValue("keep this draft")
    vi.unstubAllGlobals()
  })

  it("preserves an uncertain send for copying without putting it in the resend composer", async () => {
    mockUseConversations.mockReturnValue({ data: { conversations: [] } })
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connection lost")))
    render(<RealChatPage />, { wrapper })
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "possibly stored" } })
    await userEvent.click(screen.getByRole("button", { name: "Send message" }))
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/may already be saved/))
    expect(screen.getByRole("textbox", { name: "Unconfirmed message" })).toHaveValue("possibly stored")
    expect(screen.getByPlaceholderText(/Ask about your memories/)).toHaveValue("")
    vi.unstubAllGlobals()
  })
  beforeEach(() => {
    mockUseConversations.mockReset()
    mockUseConversation.mockReset()
    mockUseCreateConversation.mockReset()
    mockUseDeleteConversation.mockReset()
    mockUseCreateConversation.mockReturnValue({ mutateAsync: vi.fn() })
    mockUseDeleteConversation.mockReturnValue({ mutate: vi.fn() })
    mockUseConversation.mockReturnValue({ data: undefined })
  })

  it("renders the sidebar, message pane, and context-panel columns", () => {
    mockUseConversations.mockReturnValue({
      data: {
        conversations: [
          {
            id: "c1",
            title: "First",
            created_at: "",
            updated_at: "",
            is_archived: false,
          },
        ],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    })

    render(<RealChatPage />, { wrapper })

    expect(screen.getByText("Conversations")).toBeInTheDocument()
    expect(screen.getByText("First")).toBeInTheDocument()
    expect(
      screen.getByPlaceholderText(/Ask about your memories/),
    ).toBeInTheDocument()
    expect(screen.getByText("Context used for this turn")).toBeInTheDocument()
    expect(screen.getByText("No context yet")).toBeInTheDocument()
  })

  // The pane used to render an empty scroll region above the input while both
  // columns beside it stated their own absence, so a fresh conversation read
  // as a broken pane rather than an empty one.
  it("states the absence in the message pane when no turn has run", () => {
    mockUseConversations.mockReturnValue({
      data: { conversations: [] },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    })

    render(<RealChatPage />, { wrapper })

    expect(screen.getByText("Ask about your memories")).toBeInTheDocument()
  })

  it("selecting a different conversation re-fetches via useConversation with the new id, not stale", async () => {
    const user = userEvent.setup()
    mockUseConversations.mockReturnValue({
      data: {
        conversations: [
          {
            id: "c1",
            title: "First",
            created_at: "",
            updated_at: "",
            is_archived: false,
          },
          {
            id: "c2",
            title: "Second",
            created_at: "",
            updated_at: "",
            is_archived: false,
          },
        ],
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    })

    render(<RealChatPage />, { wrapper })

    await user.click(screen.getByText("Second"))

    expect(mockUseConversation).toHaveBeenLastCalledWith("c2")
  })
})
