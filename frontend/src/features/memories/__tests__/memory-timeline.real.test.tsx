import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { apiFetch } from "@/lib/api"
import { MemoryEventTimeline } from "../components/memory-event-timeline"

vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

const MEMORY_ID = "11111111-1111-1111-1111-111111111111"
const LIVE_KEY_ID = "22222222-2222-2222-2222-222222222222"
const REVOKED_KEY_ID = "33333333-3333-3333-3333-333333333333"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function event(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    created_at: "2026-08-16T10:00:00Z",
    event_type: "created",
    object_type: "memory",
    object_id: MEMORY_ID,
    project: "default",
    actor: "webhook-runner",
    api_key_id: LIVE_KEY_ID,
    source: "api",
    payload: {},
    ...overrides,
  }
}

const KEYS = [
  {
    id: LIVE_KEY_ID,
    name: "push-webhook",
    key_id: "abc123",
    scopes: ["capture"],
    created_at: "2026-08-01T00:00:00Z",
    last_used_at: "2026-08-16T10:00:00Z",
    expires_at: null,
    revoked_at: null,
  },
  {
    id: REVOKED_KEY_ID,
    name: "retired-laptop",
    key_id: "def456",
    scopes: ["read"],
    created_at: "2026-07-01T00:00:00Z",
    last_used_at: "2026-07-20T00:00:00Z",
    expires_at: null,
    revoked_at: "2026-08-02T00:00:00Z",
  },
]

function mockApi(items: ReturnType<typeof event>[], keys: unknown = KEYS) {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path.startsWith("/events")) {
      return Promise.resolve({ items, total: items.length })
    }
    if (path === "/api-keys") return Promise.resolve(keys)
    return Promise.reject(new Error(`unexpected apiFetch(${path})`))
  })
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
})

describe("per-memory timeline — who did what, with which key", () => {
  it("reads the journal by object rather than deriving history from the row", async () => {
    mockApi([event()])
    render(<MemoryEventTimeline memoryId={MEMORY_ID} />, { wrapper })

    await waitFor(() =>
      expect(apiFetch).toHaveBeenCalledWith(
        expect.stringContaining(`object_id=${MEMORY_ID}`),
      ),
    )
    expect(apiFetch).toHaveBeenCalledWith(
      expect.stringContaining("object_type=memory"),
    )
  })

  it("shows the key label and the actor on a keyed call", async () => {
    mockApi([event()])
    render(<MemoryEventTimeline memoryId={MEMORY_ID} />, { wrapper })

    await waitFor(() =>
      expect(screen.getByText("key: push-webhook")).toBeInTheDocument(),
    )
    expect(screen.getByText("webhook-runner")).toBeInTheDocument()
    expect(screen.getByText("created")).toBeInTheDocument()
  })

  it("a revoked key still labels the history it made", async () => {
    mockApi([event({ api_key_id: REVOKED_KEY_ID })])
    render(<MemoryEventTimeline memoryId={MEMORY_ID} />, { wrapper })

    await waitFor(() =>
      expect(screen.getByText("key: retired-laptop")).toBeInTheDocument(),
    )
    expect(
      screen.getByText(/revoked — the call it made is still recorded/),
    ).toBeInTheDocument()
  })

  it("an unkeyed call shows its actor and claims no key", async () => {
    mockApi([event({ api_key_id: null, actor: "admin" })])
    render(<MemoryEventTimeline memoryId={MEMORY_ID} />, { wrapper })

    await waitFor(() => expect(screen.getByText("admin")).toBeInTheDocument())
    expect(screen.queryByText(/^key:/)).not.toBeInTheDocument()
  })

  it("a keyed call whose key is gone says so, and is never read as a session call", async () => {
    mockApi([event({ api_key_id: "44444444-4444-4444-4444-444444444444" })], [])
    render(<MemoryEventTimeline memoryId={MEMORY_ID} />, { wrapper })

    await waitFor(() =>
      expect(screen.getByText("key: no longer listed")).toBeInTheDocument(),
    )
  })

  it("an empty journal is not a failed read, and neither renders as the other", async () => {
    mockApi([])
    const { unmount } = render(<MemoryEventTimeline memoryId={MEMORY_ID} />, {
      wrapper,
    })
    await waitFor(() =>
      expect(screen.getByText(/no journal rows for this memory/)).toBeInTheDocument(),
    )
    expect(screen.queryByText(/could not be read/)).not.toBeInTheDocument()
    unmount()

    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path.startsWith("/events")) return Promise.reject(new Error("boom"))
      if (path === "/api-keys") return Promise.resolve(KEYS)
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<MemoryEventTimeline memoryId={MEMORY_ID} />, { wrapper })
    await waitFor(() =>
      expect(
        screen.getByText(/the event journal could not be read/),
      ).toBeInTheDocument(),
    )
    expect(
      screen.queryByText(/no journal rows for this memory/),
    ).not.toBeInTheDocument()
  })

  it("does not flag every keyed row as unresolved while the key list is still loading", async () => {
    vi.mocked(apiFetch).mockImplementation((path: string) => {
      if (path.startsWith("/events")) {
        return Promise.resolve({ items: [event()], total: 1 })
      }
      if (path === "/api-keys") return new Promise(() => {})
      return Promise.reject(new Error(`unexpected apiFetch(${path})`))
    })
    render(<MemoryEventTimeline memoryId={MEMORY_ID} />, { wrapper })

    await waitFor(() => expect(screen.getByText("created")).toBeInTheDocument())
    expect(screen.queryByText("key: no longer listed")).not.toBeInTheDocument()
  })
})
