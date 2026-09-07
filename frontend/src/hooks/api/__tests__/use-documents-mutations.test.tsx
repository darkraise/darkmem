import { describe, it, expect, vi } from "vitest"
import { renderHook, act } from "@testing-library/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))

import { apiFetch } from "@/lib/api"
import {
  useDocumentCreate,
  useDocumentSubtreeRename,
  useDocumentSubtreeDelete,
} from "../use-documents-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function mockApiFetch(
  handler: (path: string, init?: RequestInit) => unknown,
) {
  vi.mocked(apiFetch).mockImplementation(
    async (path: string, init?: RequestInit) => handler(path, init) as never,
  )
}

describe("document mutation hooks", () => {
  it("creates a note at the uri it was given", async () => {
    const calls: Array<{ path: string; body: unknown }> = []
    mockApiFetch((path, init) => {
      calls.push({ path, body: init?.body ? JSON.parse(String(init.body)) : null })
      return { document_id: "d1", outcome: "created" }
    })

    const { result } = renderHook(() => useDocumentCreate(), { wrapper })
    await act(async () => {
      await result.current.mutateAsync({
        project: "notes", uri: "untitled.md", title: "Untitled",
      })
    })

    expect(calls[0]!.path).toBe("/documents")
    expect(calls[0]!.body).toMatchObject({
      project: "notes", uri: "untitled.md", content: "# Untitled\n",
    })
  })

  it("renames a subtree through the rename route", async () => {
    const calls: string[] = []
    mockApiFetch((path) => { calls.push(path); return { renamed: 2 } })

    const { result } = renderHook(() => useDocumentSubtreeRename(), { wrapper })
    await act(async () => {
      await result.current.mutateAsync({
        project: "notes", uri_prefix: "a", new_uri_prefix: "b",
      })
    })

    expect(calls[0]).toBe("/documents/rename")
  })

  it("deletes a subtree through the bulk route", async () => {
    const calls: string[] = []
    mockApiFetch((path) => { calls.push(path); return { deleted: 3 } })

    const { result } = renderHook(() => useDocumentSubtreeDelete(), { wrapper })
    await act(async () => {
      await result.current.mutateAsync({ project: "notes", uri_prefix: "gone" })
    })

    expect(calls[0]).toBe("/documents/delete")
  })
})
