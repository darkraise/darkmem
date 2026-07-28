import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen } from "@testing-library/react"
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
