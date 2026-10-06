import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, act, waitFor, fireEvent } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useState, type ReactNode } from "react"
import { ApiError } from "@/lib/api"

const mockUseConversations = vi.fn()
const mockUseConversation = vi.fn()
const mockUseDeleteConversation = vi.fn()

vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useConversations: () => mockUseConversations(),
  useConversation: (id: string | null) => mockUseConversation(id),
  useDeleteConversation: () => mockUseDeleteConversation(),
}))

import { RealChatPage } from "../components/real-chat-page"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

// The route holds the open conversation in ?id=; this stands in for it, and
// records every navigation the page asks for.
const navigations = vi.fn()
function Routed({ initial = null }: { initial?: string | null }) {
  const [id, setId] = useState<string | null>(initial)
  return (
    <RealChatPage
      conversationId={id}
      onSelect={(next, options) => {
        navigations(next, options)
        setId(next)
      }}
    />
  )
}

const conversation = (id: string, title: string) => ({
  id,
  title,
  created_at: "",
  updated_at: "",
  is_archived: false,
})

function listing(...rows: ReturnType<typeof conversation>[]) {
  mockUseConversations.mockReturnValue({
    data: { conversations: rows },
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  })
}

function streamingFetch() {
  let controller!: ReadableStreamDefaultController<Uint8Array>
  const body = new ReadableStream<Uint8Array>({
    start(streamController) {
      controller = streamController
    },
  })
  const fetchMock = vi.fn().mockResolvedValue({ ok: true, body })
  vi.stubGlobal("fetch", fetchMock)
  const emit = async (event: object) => {
    await act(async () => {
      controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify(event)}\n\n`))
    })
  }
  const finish = async (event: object) => {
    await act(async () => {
      controller.enqueue(new TextEncoder().encode(`data: ${JSON.stringify(event)}\n\n`))
      controller.close()
    })
  }
  return { fetchMock, emit, finish }
}

async function send(text: string) {
  fireEvent.change(screen.getByPlaceholderText(/Ask about your memories/), {
    target: { value: text },
  })
  await userEvent.click(screen.getByRole("button", { name: "Send message" }))
}

// T1.60 Step 7: RealChatPage assembles already-tested primitives
// (ChatSidebar, ChatMessages + ChatInput, useChatStream + useConversation)
// into the three-column layout DemoChatPage already has. No mutation proof
// required here (the plan's own text) — this step is assembly, not a new
// invariant; Step 8 is what makes the third column honest.
const realMatchMedia = window.matchMedia

describe("RealChatPage", () => {
  beforeEach(() => {
    // The wide layout, where all three panes are on screen at once; below lg
    // the thread list is an inactive tab and its buttons are hidden.
    window.matchMedia = vi.fn().mockImplementation((query: string) => ({
      matches: true,
      media: query,
      onchange: null,
      addEventListener: vi.fn(),
      removeEventListener: vi.fn(),
      addListener: vi.fn(),
      removeListener: vi.fn(),
      dispatchEvent: vi.fn(),
    }))
    mockUseConversations.mockReset()
    mockUseConversation.mockReset()
    mockUseDeleteConversation.mockReset()
    navigations.mockReset()
    mockUseDeleteConversation.mockReturnValue({ mutate: vi.fn() })
    mockUseConversation.mockReturnValue({ data: undefined })
    listing()
  })
  afterEach(() => {
    window.matchMedia = realMatchMedia
    vi.unstubAllGlobals()
  })

  it("follows mounted route changes", async () => {
    const view = render(<RealChatPage conversationId="first" onSelect={vi.fn()} />, { wrapper })
    view.rerender(<RealChatPage conversationId="second" onSelect={vi.fn()} />)
    await waitFor(() => expect(mockUseConversation).toHaveBeenLastCalledWith("second"))
  })

  it("hides another conversation's live turn and does not navigate on its completion", async () => {
    listing(conversation("second", "Second"))
    const { finish, emit } = streamingFetch()
    render(<Routed />, { wrapper })
    await send("original draft")
    await emit({ type: "token", content: "old live answer" })
    await userEvent.click(screen.getByText("Second"))
    expect(screen.queryByText("old live answer")).not.toBeInTheDocument()
    expect(screen.queryByText("original draft")).not.toBeInTheDocument()
    await finish({ type: "done", conversation_id: "created" })
    expect(navigations).toHaveBeenCalledTimes(1)
    expect(mockUseConversation).toHaveBeenLastCalledWith("second")
  })

  it("announces a rejected send and restores its retryable draft", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 403, text: async () => "Read only" }))
    render(<Routed />, { wrapper })
    await send("keep this draft")
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Read only"))
    expect(screen.getByRole("textbox")).toHaveValue("keep this draft")
    expect(navigations).not.toHaveBeenCalled()
  })

  it("preserves an uncertain send for copying without putting it in the resend composer", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("connection lost")))
    render(<Routed />, { wrapper })
    await send("possibly stored")
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/may already be saved/))
    expect(screen.getByRole("textbox", { name: "Unconfirmed message" })).toHaveValue("possibly stored")
    expect(screen.getByPlaceholderText(/Ask about your memories/)).toHaveValue("")
  })

  it("renders the sidebar, message pane, and context-panel columns", () => {
    listing(conversation("c1", "First"))

    render(<Routed />, { wrapper })

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
    render(<Routed />, { wrapper })

    expect(screen.getByText("Ask about your memories")).toBeInTheDocument()
  })

  it("selecting a different conversation re-fetches via useConversation with the new id, not stale", async () => {
    const user = userEvent.setup()
    listing(conversation("c1", "First"), conversation("c2", "Second"))

    render(<Routed />, { wrapper })

    await user.click(screen.getByText("Second"))

    expect(mockUseConversation).toHaveBeenLastCalledWith("c2")
  })

  // ── audit O11 ─────────────────────────────────────────────────────

  it("puts a picked conversation in the URL as a new history entry", async () => {
    listing(conversation("c1", "First"), conversation("c2", "Second"))
    render(<Routed initial="c1" />, { wrapper })

    await userEvent.click(screen.getByText("Second"))
    // Picking the open one again is not another history entry.
    await userEvent.click(screen.getByText("Second"))

    expect(navigations.mock.calls).toEqual([["c2", undefined]])
  })

  it("opens a draft on New and stores nothing, however often it is pressed", async () => {
    // Each press used to POST an empty conversation, so three presses left
    // three "Untitled" rows behind.
    const fetchMock = vi.fn()
    vi.stubGlobal("fetch", fetchMock)
    listing(conversation("c1", "First"))
    render(<Routed initial="c1" />, { wrapper })

    const newButton = screen.getByRole("button", { name: /New/ })
    await userEvent.click(newButton)
    await userEvent.click(newButton)
    await userEvent.click(newButton)

    expect(fetchMock).not.toHaveBeenCalled()
    // Leaving the open conversation is one history entry; a draft has no id.
    expect(navigations.mock.calls).toEqual([[null, undefined]])
    expect(mockUseConversation).toHaveBeenLastCalledWith(null)
    expect(screen.getByText("Ask about your memories")).toBeInTheDocument()
  })

  it("adopts the conversation a draft's first turn creates, replacing the draft's entry", async () => {
    const { fetchMock, finish } = streamingFetch()
    render(<Routed />, { wrapper })

    await send("first question")
    expect(JSON.parse(fetchMock.mock.calls[0]![1].body)).toMatchObject({
      conversation_id: null,
      content: "first question",
    })
    await finish({ type: "done", conversation_id: "created" })

    expect(navigations.mock.calls).toEqual([["created", { replace: true }]])
    expect(mockUseConversation).toHaveBeenLastCalledWith("created")
  })

  it("keeps a draft's in-flight turn out of the next draft, which adopts nothing", async () => {
    const { emit, finish } = streamingFetch()
    render(<Routed />, { wrapper })

    await send("from the first draft")
    await emit({ type: "token", content: "first draft's answer" })
    expect(screen.getByText("first draft's answer")).toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: /New/ }))
    expect(screen.queryByText("first draft's answer")).not.toBeInTheDocument()
    expect(screen.queryByText("from the first draft")).not.toBeInTheDocument()
    expect(screen.getByText("Ask about your memories")).toBeInTheDocument()

    await finish({ type: "done", conversation_id: "created" })
    expect(navigations).not.toHaveBeenCalled()
  })

  it("shows a loading conversation as loading, not as the new-conversation hero", () => {
    listing(conversation("c1", "First"))
    mockUseConversation.mockImplementation((id: string | null) =>
      id ? { data: undefined, isLoading: true } : { data: undefined },
    )

    render(<Routed initial="c1" />, { wrapper })

    expect(screen.getByRole("status", { name: "Loading conversation" })).toBeInTheDocument()
    expect(screen.queryByText("Ask about your memories")).not.toBeInTheDocument()
  })

  it("says a conversation in the URL no longer exists, and offers a new one", async () => {
    mockUseConversation.mockImplementation((id: string | null) =>
      id
        ? { data: undefined, isLoading: false, error: new ApiError("Conversation not found", 404) }
        : { data: undefined },
    )

    render(<Routed initial="gone" />, { wrapper })

    expect(screen.getByText("Conversation not found")).toBeInTheDocument()
    expect(screen.queryByText("Ask about your memories")).not.toBeInTheDocument()
    expect(screen.queryByPlaceholderText(/Ask about your memories/)).not.toBeInTheDocument()

    await userEvent.click(screen.getByRole("button", { name: "Start a new conversation" }))
    expect(navigations.mock.calls).toEqual([[null, { replace: true }]])
  })

  it("leaves a deleted open conversation for a draft without a history entry", async () => {
    const mutate = vi.fn()
    mockUseDeleteConversation.mockReturnValue({ mutate })
    listing(conversation("c1", "First"))
    render(<Routed initial="c1" />, { wrapper })

    await userEvent.click(screen.getByRole("button", { name: "Delete conversation First" }))
    await userEvent.click(screen.getByRole("button", { name: "Delete" }))

    expect(mutate).toHaveBeenCalledWith("c1")
    expect(navigations.mock.calls).toEqual([[null, { replace: true }]])
  })
})
