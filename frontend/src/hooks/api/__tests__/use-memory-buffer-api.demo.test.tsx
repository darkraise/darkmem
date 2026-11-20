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
import { useMemoryBufferItems } from "../use-memory-buffer-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("the memory buffer hooks in demo mode", () => {
  it("sends nothing in demo mode", () => {
    const { result } = renderHook(() => useMemoryBufferItems(), { wrapper })
    expect(result.current.items).toEqual([])
    expect(result.current.total).toBe(0)
    expect(result.current.isLoading).toBe(false)
    expect(apiFetch).not.toHaveBeenCalled()
  })
})
