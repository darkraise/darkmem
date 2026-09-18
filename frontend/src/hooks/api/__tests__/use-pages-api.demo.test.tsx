import { describe, expect, it, vi } from "vitest"
import { renderHook } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: true }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import { usePage, usePages, usePagesTrash } from "../use-pages-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

// A demo read 401s, and `handleUnauthorized` answers a 401 with a hard
// navigation to /login — one unguarded query takes the whole demo down.
describe("the page reads make no request in demo mode", () => {
  it("leaves every query idle", () => {
    const list = renderHook(() => usePages("personal"), { wrapper })
    const one = renderHook(() => usePage("p1"), { wrapper })
    const trash = renderHook(() => usePagesTrash("personal", true), { wrapper })
    expect(list.result.current.fetchStatus).toBe("idle")
    expect(one.result.current.fetchStatus).toBe("idle")
    expect(trash.result.current.fetchStatus).toBe("idle")
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })
})
