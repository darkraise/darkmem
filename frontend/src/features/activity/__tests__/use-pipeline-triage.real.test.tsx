import { describe, it, expect, vi, beforeEach } from "vitest"
import { renderHook, waitFor, act } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { usePipelineTriage } from "../use-pipeline-triage"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const FAILURE = {
  id: "f1",
  entity_type: "memory",
  entity_id: "11111111-2222-3333-4444-555555555555",
  pipeline_name: "memory_ingest",
  failed_step: "graph_write",
  error_message: "Graph write failed: boom",
  attempts: 2,
  first_failed_at: "2026-07-27T10:00:00Z",
  last_attempt_at: "2026-07-27T18:00:00Z",
  resolved_at: null,
  metadata: {},
  entity_preview: "a captured memory",
}

describe("usePipelineTriage (DEMO off — real /pipeline-failures)", () => {
  beforeEach(() => vi.clearAllMocks())

  it("maps a PipelineFailure row into the shared triage shape", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [FAILURE], total: 1 })
    const { result } = renderHook(() => usePipelineTriage(), { wrapper })

    await waitFor(() => expect(result.current.isLoading).toBe(false))
    expect(apiFetch).toHaveBeenCalledWith(
      expect.stringContaining("/pipeline-failures"),
      expect.objectContaining({ signal: expect.any(AbortSignal) }),
    )
    const [failure] = result.current.failures
    expect(failure!.failed_step).toBe("graph_write")
    expect(failure!.reason).toBe("Graph write failed: boom")
    expect(failure!.attempts).toBe(2)
    expect(failure!.retry_queued).toBe(false)
  })

  it("retry() hits the retry endpoint and marks the row retry_queued optimistically", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path.includes("/retry")) {
        return Promise.resolve({ accepted: true, failure_id: FAILURE.id })
      }
      return Promise.resolve({ items: [FAILURE], total: 1 })
    })
    const { result } = renderHook(() => usePipelineTriage(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    act(() => result.current.retry(FAILURE.id))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/pipeline-failures/${FAILURE.id}/retry`),
        expect.objectContaining({ method: "POST" }),
      ),
    )
    await waitFor(() =>
      expect(result.current.failures.find((f) => f.id === FAILURE.id)?.retry_queued).toBe(
        true,
      ),
    )
  })

  it("forget() hits DELETE /pipeline-failures/{id}", async () => {
    vi.mocked(apiFetch).mockResolvedValue({ items: [FAILURE], total: 1 })
    const { result } = renderHook(() => usePipelineTriage(), { wrapper })
    await waitFor(() => expect(result.current.isLoading).toBe(false))

    act(() => result.current.forget(FAILURE.id))

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        expect.stringContaining(`/pipeline-failures/${FAILURE.id}`),
        expect.objectContaining({ method: "DELETE" }),
      ),
    )
  })
})
