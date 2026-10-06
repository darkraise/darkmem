import { afterEach, describe, expect, it, vi } from "vitest"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ChatOverlay } from "../components/chat-overlay"

vi.mock("@tanstack/react-router", () => ({ useNavigate: () => vi.fn() }))
vi.mock("@/hooks/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/hooks/api")>()),
  useConversation: () => ({ data: undefined }),
}))

afterEach(() => vi.unstubAllGlobals())

describe("ChatOverlay send failures", () => {
  it("announces rejection and retains the draft across closing and reopening", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 403, text: async () => "Read only" }))
    render(<QueryClientProvider client={new QueryClient()}><ChatOverlay /></QueryClientProvider>)
    await userEvent.click(screen.getByRole("button", { name: "Open chat panel" }))
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "overlay draft" } })
    await userEvent.click(screen.getByRole("button", { name: "Send message" }))
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("Read only"))
    expect(screen.getByRole("textbox")).toHaveValue("overlay draft")
    await userEvent.click(screen.getByRole("button", { name: "Close chat panel" }))
    await userEvent.click(screen.getByRole("button", { name: "Open chat panel" }))
    expect(screen.getByRole("textbox")).toHaveValue("overlay draft")
  })

  it("does not refill the composer after an ambiguously delivered message", async () => {
    const fetchMock = vi.fn().mockRejectedValue(new Error("offline"))
    vi.stubGlobal("fetch", fetchMock)
    render(<QueryClientProvider client={new QueryClient()}><ChatOverlay /></QueryClientProvider>)
    await userEvent.click(screen.getByRole("button", { name: "Open chat panel" }))
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "possibly stored" } })
    await userEvent.click(screen.getByRole("button", { name: "Send message" }))
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent(/may already be saved/))
    expect(screen.getByRole("textbox", { name: "Unconfirmed message" })).toHaveValue("possibly stored")
    expect(screen.getByPlaceholderText("Ask about selection...")).toHaveValue("")
    await userEvent.click(screen.getByRole("button", { name: "Send message" }))
    expect(fetchMock).toHaveBeenCalledTimes(1)
  })
})

describe("ChatOverlay selection context", () => {
  async function sendWith(clear: boolean) {
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 403, text: async () => "stop" })
    vi.stubGlobal("fetch", fetchMock)
    render(
      <QueryClientProvider client={new QueryClient()}>
        <ChatOverlay selectedNodeId="01a10d4c-f2f7-7498-bda7-c3973130a5d5" />
      </QueryClientProvider>,
    )
    await userEvent.click(screen.getByRole("button", { name: "Open chat panel" }))
    expect(screen.getByText(/Context: Memory: 3130a5d5/)).toBeInTheDocument()
    if (clear) await userEvent.click(screen.getByRole("button", { name: "Clear context" }))
    fireEvent.change(screen.getByRole("textbox"), { target: { value: "about this" } })
    await userEvent.click(screen.getByRole("button", { name: "Send message" }))
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    return JSON.parse(String((fetchMock.mock.calls[0]![1] as RequestInit).body))
  }

  it("sends the selected memory as context", async () => {
    const body = await sendWith(false)
    expect(body.context).toEqual({ selected_node_id: "01a10d4c-f2f7-7498-bda7-c3973130a5d5" })
  })

  it("sends no selection once the context chip is cleared", async () => {
    // Clearing used to hide the label only; the request still carried it.
    const body = await sendWith(true)
    expect(body.context ?? {}).toEqual({})
  })
})
