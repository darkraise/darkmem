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
  useDocumentMetadataUpdate,
  useDocumentSubtreeRename,
  useDocumentSubtreeDelete,
} from "../use-documents-api"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function makeWrapper(qc: QueryClient) {
  return function ClientWrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  }
}

function mockApiFetch(
  handler: (path: string, init?: RequestInit) => unknown,
) {
  vi.mocked(apiFetch).mockImplementation(
    async (path: string, init?: RequestInit) => handler(path, init) as never,
  )
}

interface Call {
  path: string
  method?: string
  body: unknown
}

/** Records path, method and parsed body for every apiFetch call, so a test
 *  can assert all three instead of just the path -- a hook that issued the
 *  wrong verb or dropped a field from the body would still pass a
 *  path-only assertion. */
function captureCalls(response: unknown): Call[] {
  const calls: Call[] = []
  mockApiFetch((path, init) => {
    calls.push({
      path,
      method: init?.method,
      body: init?.body ? JSON.parse(String(init.body)) : null,
    })
    return response
  })
  return calls
}

/** Seeds both list keys the brief says every mutation must invalidate, runs
 *  one mutation against a fresh client, and asserts both came back
 *  invalidated -- `invalidateDocumentLists` could be a no-op and every
 *  other test in this file would stay green without this check. */
async function assertInvalidatesLists<TVars>(
  useHook: () => { mutateAsync: (vars: TVars) => Promise<unknown> },
  variables: TVars,
) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  qc.setQueryData(["documentsAll", "notes"], { items: [], truncated: false })
  qc.setQueryData(["documents", "notes"], { items: [], horizon: false })

  const { result } = renderHook(() => useHook(), { wrapper: makeWrapper(qc) })
  await act(async () => {
    await result.current.mutateAsync(variables)
  })

  expect(qc.getQueryState(["documentsAll", "notes"])?.isInvalidated).toBe(true)
  expect(qc.getQueryState(["documents", "notes"])?.isInvalidated).toBe(true)
}

describe("document mutation hooks", () => {
  it("creates a note at the uri it was given", async () => {
    const calls = captureCalls({ document_id: "d1", outcome: "created" })

    const { result } = renderHook(() => useDocumentCreate(), { wrapper })
    await act(async () => {
      await result.current.mutateAsync({
        project: "notes", uri: "untitled.md", title: "Untitled",
      })
    })

    expect(calls[0]!.path).toBe("/documents")
    expect(calls[0]!.method).toBe("POST")
    expect(calls[0]!.body).toMatchObject({
      project: "notes", uri: "untitled.md", content: "# Untitled\n",
    })
  })

  it("updates metadata without leaking documentId onto the wire", async () => {
    const calls = captureCalls({ document_id: "d1" })

    const { result } = renderHook(() => useDocumentMetadataUpdate(), { wrapper })
    await act(async () => {
      await result.current.mutateAsync({
        documentId: "d1", title: "New title", pinned: true,
      })
    })

    expect(calls[0]!.path).toBe("/documents/d1")
    expect(calls[0]!.method).toBe("PATCH")
    // `documentId` rides the path, never the body: PATCH's request model
    // forbids extra fields, so a leaked `documentId` is a 422 in production.
    expect(calls[0]!.body).toEqual({ title: "New title", pinned: true })
    expect(calls[0]!.body).not.toHaveProperty("documentId")
  })

  it("renames a subtree through the rename route", async () => {
    const calls = captureCalls({ renamed: 2 })

    const { result } = renderHook(() => useDocumentSubtreeRename(), { wrapper })
    await act(async () => {
      await result.current.mutateAsync({
        project: "notes", uri_prefix: "a", new_uri_prefix: "b",
      })
    })

    expect(calls[0]!.path).toBe("/documents/rename")
    expect(calls[0]!.method).toBe("POST")
    expect(calls[0]!.body).toEqual({
      project: "notes", uri_prefix: "a", new_uri_prefix: "b",
    })
  })

  it("deletes a subtree through the bulk route", async () => {
    const calls = captureCalls({ deleted: 3 })

    const { result } = renderHook(() => useDocumentSubtreeDelete(), { wrapper })
    await act(async () => {
      await result.current.mutateAsync({ project: "notes", uri_prefix: "gone" })
    })

    expect(calls[0]!.path).toBe("/documents/delete")
    expect(calls[0]!.method).toBe("POST")
    expect(calls[0]!.body).toEqual({ project: "notes", uri_prefix: "gone" })
  })
})

describe("document mutation hooks invalidate the document lists", () => {
  it("useDocumentCreate invalidates documentsAll and documents", async () => {
    mockApiFetch(() => ({ document_id: "d1", outcome: "created" }))
    await assertInvalidatesLists(useDocumentCreate, {
      project: "notes", uri: "untitled.md", title: "Untitled",
    })
  })

  it("useDocumentMetadataUpdate invalidates documentsAll and documents", async () => {
    mockApiFetch(() => ({ document_id: "d1" }))
    await assertInvalidatesLists(useDocumentMetadataUpdate, {
      documentId: "d1", title: "New title",
    })
  })

  it("useDocumentSubtreeRename invalidates documentsAll and documents", async () => {
    mockApiFetch(() => ({ renamed: 2 }))
    await assertInvalidatesLists(useDocumentSubtreeRename, {
      project: "notes", uri_prefix: "a", new_uri_prefix: "b",
    })
  })

  it("useDocumentSubtreeDelete invalidates documentsAll and documents", async () => {
    mockApiFetch(() => ({ deleted: 3 }))
    await assertInvalidatesLists(useDocumentSubtreeDelete, {
      project: "notes", uri_prefix: "gone",
    })
  })
})
