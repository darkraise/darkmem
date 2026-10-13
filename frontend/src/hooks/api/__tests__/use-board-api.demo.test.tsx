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
import {
  useBoardRecords,
  useBoardViews,
  useRegisterRowEdit,
} from "../use-board-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe("the board in demo mode", () => {
  it("serves records and the built-in views without a request", () => {
    const records = renderHook(() => useBoardRecords("darkmem"), { wrapper })
    expect(
      records.result.current.data?.registers[0]?.rows.length,
    ).toBeGreaterThan(0)
    expect(records.result.current.data?.plans[0]?.tasks.length).toBeGreaterThan(
      0,
    )
    const other = renderHook(() => useBoardRecords("acme-storefront"), {
      wrapper,
    })
    expect(other.result.current.data?.registers).toEqual([])
    const views = renderHook(() => useBoardViews("darkmem"), { wrapper })
    expect(views.result.current.data?.map((v) => v.id)).toEqual([
      "builtin:open-register-items",
      "builtin:plans-in-flight",
    ])
    expect(apiFetch).not.toHaveBeenCalled()
  })

  it("refuses a row edit without a request", async () => {
    const edit = renderHook(() => useRegisterRowEdit("darkmem"), { wrapper })
    await expect(
      edit.result.current.mutateAsync({
        documentId: "d",
        number: 1,
        expectedHash: "h",
        state: "done",
      }),
    ).rejects.toThrow(/read-only/)
    expect(apiFetch).not.toHaveBeenCalled()
  })
})
