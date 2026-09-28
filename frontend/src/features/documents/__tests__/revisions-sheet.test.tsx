import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { render, screen, waitFor } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import type { ReactNode } from "react"
import { beforeEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", async (importOriginal) => ({
  ...(await importOriginal<typeof import("@/lib/api")>()),
  apiFetch: vi.fn(),
}))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
  Toaster: () => null,
}))

import { apiFetch } from "@/lib/api"
import { DocumentActions } from "../components/document-actions"
import { RevisionsSheet } from "../components/revisions-sheet"

function item(id: string, hash: string, created_at: string) {
  return { id, content_hash: hash, actor: "claude-code", api_key_id: null, created_at }
}

const CONTENT: Record<string, string> = {
  r3: "a\nB\nc\n",
  r2: "a\nb\nc\n",
  r1: "a\nc\n",
}

function routeApi() {
  vi.mocked(apiFetch).mockImplementation((path: string) => {
    if (path.startsWith("/documents/d1/revisions?")) {
      return Promise.resolve({
        document_id: "d1",
        items: [
          item("r3", "3333333333", "2026-09-28T10:00:00Z"),
          item("r2", "2222222222", "2026-09-27T10:00:00Z"),
          item("r1", "1111111111", "2026-09-26T10:00:00Z"),
        ],
        next_before: null,
      })
    }
    const one = path.match(/^\/documents\/d1\/revisions\/(r\d)$/)
    if (one) return Promise.resolve({ id: one[1], document_id: "d1", content: CONTENT[one[1]!] })
    return Promise.reject(new Error(`unrouted ${path}`))
  })
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

function changed(change: string): string[] {
  return [...document.querySelectorAll(`[data-change="${change}"] [data-line]`)].map(
    (line) => line.textContent ?? "",
  )
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  routeApi()
})

describe("RevisionsSheet", () => {
  it("compares the two newest revisions by default", async () => {
    render(<RevisionsSheet documentId="d1" open onOpenChange={vi.fn()} />, { wrapper })
    await screen.findByRole("group", { name: "line diff" })
    expect(changed("removed")).toEqual(["b"])
    expect(changed("added")).toEqual(["B"])
  })

  it("compares any two the reader picks", async () => {
    const user = userEvent.setup()
    render(<RevisionsSheet documentId="d1" open onOpenChange={vi.fn()} />, { wrapper })
    await screen.findByRole("group", { name: "line diff" })

    await user.click(screen.getByRole("button", { name: "Compare from 11111111" }))
    await waitFor(() => expect(changed("added")).toEqual(["B"]))
    expect(changed("removed")).toEqual([])
    expect(screen.getByRole("button", { name: "Compare from 11111111" })).toHaveAttribute(
      "aria-pressed",
      "true",
    )
  })

  it("reads nothing while closed", () => {
    render(<RevisionsSheet documentId="d1" open={false} onOpenChange={vi.fn()} />, { wrapper })
    expect(vi.mocked(apiFetch)).not.toHaveBeenCalled()
  })
})

describe("DocumentActions", () => {
  it("opens the revisions sheet", async () => {
    const user = userEvent.setup()
    render(
      <DocumentActions
        document={{
          id: "d1",
          title: "Design",
          uri: "notes/design.md",
          source_type: "md",
          project: "darkmem",
          block_count: 3,
        } as never}
        mode="read"
        onModeChange={vi.fn()}
        onDeleted={vi.fn()}
      />,
      { wrapper },
    )
    await user.click(screen.getByRole("button", { name: "Revisions" }))
    expect(await screen.findByRole("group", { name: "line diff" })).toBeInTheDocument()
  })
})
