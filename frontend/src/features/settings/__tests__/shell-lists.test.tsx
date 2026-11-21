import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, fireEvent, render, renderHook, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest"

const flags = vi.hoisted(() => ({ demo: false }))
vi.mock("@/lib/demo-flag", () => ({
  get DEMO() {
    return flags.demo
  },
}))
vi.mock("@tanstack/react-router", () => ({
  Link: ({ children }: { children: ReactNode }) => <a>{children}</a>,
}))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn(), warning: vi.fn(), info: vi.fn() },
}))

import { useJobs } from "@/hooks/api"
import { useWebSocket } from "@/lib/websocket"
import { FakeSocket, deferred, json, routeFetch } from "@/lib/__tests__/session-test-kit"
import { LLMTab } from "../components/llm-tab"
import { MaintenanceTab } from "../components/maintenance-tab"
import { ResearchTab } from "../components/research-tab"

function client() {
  return new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
}

function wrapperFor(qc: QueryClient) {
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

const counts = (memories: number) => ({
  memories,
  entities: 0,
  code_chunks: 0,
  current_fingerprint: "qwen3-embedding:0.6b|1024",
})

const research = (findings: number) => ({
  enabled: false,
  max_findings_per_run: findings,
  max_content_chars: 8000,
  default_enabled: false,
})

beforeEach(() => {
  flags.demo = false
  FakeSocket.instances = []
  vi.stubGlobal("WebSocket", FakeSocket)
})

afterEach(() => {
  vi.unstubAllGlobals()
  vi.useRealTimers()
})

describe("shell lists", () => {
  it("the re-embed count follows an embedder change", async () => {
    routeFetch({
      "/reembed/obsolete-counts": [json(counts(0)), json(counts(12))],
      "/pipeline-failures/counts": [json({})],
      "/jobs": [json({ jobs: [] })],
    })
    function Screen() {
      useWebSocket()
      return <MaintenanceTab />
    }
    render(<Screen />, { wrapper: wrapperFor(client()) })
    await waitFor(() => expect(screen.getAllByText("0 missing").length).toBeGreaterThan(0))

    const socket = FakeSocket.latest()
    act(() => socket.open())
    act(() =>
      socket.message({
        event: "pipeline.reembed_batch.progress",
        data: {
          batch_id: "b1",
          category: "memories",
          current: 12,
          total: 12,
          processed: 12,
          errors: 0,
          state: "done",
          error_message: null,
        },
      }),
    )
    expect(await screen.findByText("12 missing a vector")).toBeInTheDocument()
  })

  it("the maintenance tab does not poll jobs", async () => {
    vi.useFakeTimers()
    const net = routeFetch({
      "/reembed/obsolete-counts": [json(counts(0))],
      "/pipeline-failures/counts": [json({})],
      "/jobs": [json({ jobs: [] })],
    })
    render(<MaintenanceTab />, { wrapper: wrapperFor(client()) })
    await act(async () => {
      await vi.advanceTimersByTimeAsync(30_000)
    })
    expect(net.count("/jobs")).toBeLessThanOrEqual(1)
  })

  it("typed research budgets survive a settings reload", async () => {
    const net = routeFetch({
      "/config/auto-research": [json(research(20)), json(research(30)), json(research(7))],
      "/config/auto-research/runs": [json({ items: [] })],
    })
    const qc = client()
    render(<ResearchTab />, { wrapper: wrapperFor(qc) })
    const field = screen.getByLabelText("Max findings per run")
    await waitFor(() => expect(field).toHaveValue("20"))

    fireEvent.change(field, { target: { value: "7" } })
    await act(async () => {
      await qc.refetchQueries({ queryKey: ["autoResearch"] })
      // The query notifies its observers on a later task.
      await new Promise((r) => setTimeout(r, 20))
    })
    expect(qc.getQueryData(["autoResearch"])).toMatchObject({ max_findings_per_run: 30 })
    expect(field).toHaveValue("7")

    fireEvent.click(screen.getByRole("button", { name: /Save budgets/ }))
    await waitFor(() => {
      const put = net.fetchMock.mock.calls
        .map((call) => (call as unknown[])[1] as RequestInit | undefined)
        .find((init) => init?.method === "PUT")
      expect(JSON.parse(String(put?.body))).toMatchObject({ max_findings_per_run: 7 })
    })
  })

  it("demo mode sends no request from the LLM tab", async () => {
    flags.demo = true
    const net = routeFetch({})
    const user = userEvent.setup()
    render(<LLMTab />, { wrapper: wrapperFor(client()) })

    await user.click(screen.getByLabelText("Edit extraction"))
    await screen.findByText("extraction — configuration")
    await user.keyboard("{Escape}")
    await user.click(screen.getByLabelText("System prompt for extraction"))
    await user.keyboard("{Escape}")
    await user.click(screen.getByRole("tab", { name: "Providers" }))
    await act(async () => {
      await new Promise((r) => setTimeout(r, 20))
    })

    expect(net.fetchMock).not.toHaveBeenCalled()
  })

  it("queries pass a cancellation signal", async () => {
    const answer = deferred<Response>()
    const net = routeFetch({ "/jobs": [answer.promise] })
    const hook = renderHook(() => useJobs(), { wrapper: wrapperFor(client()) })
    await waitFor(() => expect(net.count("/jobs")).toBe(1))

    hook.unmount()
    const init = (net.fetchMock.mock.calls[0] as unknown[])[1] as RequestInit | undefined
    expect(init?.signal?.aborted).toBe(true)
    answer.resolve(json({ jobs: [] }))
  })
})
