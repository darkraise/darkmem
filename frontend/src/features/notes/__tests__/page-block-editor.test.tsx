import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { useState, type ReactNode } from "react"
import { describe, expect, it, vi, beforeEach } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => {
  class ApiError extends Error {
    status: number
    constructor(message: string, status: number) {
      super(message)
      this.status = status
    }
  }
  return { apiFetch: vi.fn(), apiFetchWithHeaders: vi.fn(), ApiError }
})

import { apiFetch, ApiError } from "@/lib/api"
import type { BlockRow } from "@/hooks/api"
import { PageBlockEditor, promote } from "../page-block-editor"

function wrapper({ children }: { children: ReactNode }) {
  const [qc] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      }),
  )
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const BLOCKS: BlockRow[] = [
  {
    block_id: "b1",
    type: "paragraph",
    text: "hello",
    order_index: 0,
    char_span: [0, 5],
    parent_id: null,
    properties: null,
    source: "hello",
  },
]

/** The queue's hash re-read goes through `pageQuery`, which normalises a WHOLE
 *  page. A stub answering every call with a write response throws inside the
 *  normaliser and every edit below rejects before it is sent, so the GET arm
 *  is routed separately. */
function route(_path: string, init?: RequestInit) {
  if (!init?.body) {
    return Promise.resolve({
      id: "p1",
      project: "personal",
      parent_id: null,
      order_index: 0,
      title: "Notes",
      content_hash: "h1",
      properties: null,
      content: null,
      blocks: [],
    })
  }
  return Promise.resolve({ page_id: "p1", content_hash: "h2" })
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(apiFetch).mockImplementation(route as never)
})

describe("promote", () => {
  it("reads the markers the serialiser emits", () => {
    expect(promote("## Sub")).toEqual({
      type: "heading",
      text: "Sub",
      properties: { level: 2 },
    })
    expect(promote("- item")).toEqual({
      type: "list",
      text: "item",
      properties: { marker: "-" },
    })
    expect(promote("> quoted")).toEqual({ type: "quote", text: "quoted" })
    expect(promote("---")).toEqual({ type: "divider", text: "" })
    expect(promote("plain")).toEqual({ type: "paragraph", text: "plain" })
  })

  it("preserves an html block's type, which has no marker to read back", () => {
    expect(promote("<b>bold</b> text", "html")).toEqual({
      type: "html",
      text: "<b>bold</b> text",
    })
  })
})

describe("PageBlockEditor", () => {
  it("edits the block's source and sends the promoted type", async () => {
    render(
      <PageBlockEditor pageId="p1" blocks={BLOCKS} onStatus={vi.fn()} />,
      { wrapper },
    )
    fireEvent.click(screen.getByRole("button", { name: /hello/ }))
    const area = screen.getByLabelText("block source")
    expect(area).toHaveValue("hello")
    fireEvent.change(area, { target: { value: "## Head" } })
    fireEvent.blur(area)
    await waitFor(() => {
      const call = vi
        .mocked(apiFetch)
        .mock.calls.find((c) => String(c[0]).includes("/blocks/b1"))
      expect(call).toBeTruthy()
      expect(JSON.parse(String((call![1] as RequestInit).body))).toMatchObject({
        type: "heading",
        text: "Head",
        properties: { level: 2 },
      })
    })
  })

  it("reports Saving then Saved", async () => {
    const onStatus = vi.fn()
    render(<PageBlockEditor pageId="p1" blocks={BLOCKS} onStatus={onStatus} />, {
      wrapper,
    })
    fireEvent.click(screen.getByRole("button", { name: /hello/ }))
    fireEvent.change(screen.getByLabelText("block source"), {
      target: { value: "changed" },
    })
    fireEvent.blur(screen.getByLabelText("block source"))
    await waitFor(() =>
      expect(onStatus.mock.calls.map(([s]) => s.kind)).toContain("saving"),
    )
    await waitFor(() =>
      expect(onStatus.mock.calls.map(([s]) => s.kind)).toContain("saved"),
    )
  })

  it("reports the server's own message when a write is refused", async () => {
    vi.mocked(apiFetch).mockImplementation(((path: string, init?: RequestInit) =>
      init?.body
        ? Promise.reject(new ApiError("expected_hash a does not match b", 409))
        : route(path)) as never)
    const onStatus = vi.fn()
    render(<PageBlockEditor pageId="p1" blocks={BLOCKS} onStatus={onStatus} />, {
      wrapper,
    })
    fireEvent.click(screen.getByRole("button", { name: /hello/ }))
    fireEvent.change(screen.getByLabelText("block source"), {
      target: { value: "changed" },
    })
    fireEvent.blur(screen.getByLabelText("block source"))
    await waitFor(() => {
      const blocked = onStatus.mock.calls
        .map(([s]) => s)
        .find((s) => s.kind === "blocked")
      expect(blocked?.message).toBe("expected_hash a does not match b")
    })
  })

  it("does not write when the source is unchanged", async () => {
    render(<PageBlockEditor pageId="p1" blocks={BLOCKS} onStatus={vi.fn()} />, {
      wrapper,
    })
    fireEvent.click(screen.getByRole("button", { name: /hello/ }))
    fireEvent.blur(screen.getByLabelText("block source"))
    await waitFor(() => expect(screen.queryByLabelText("block source")).toBeNull())
    expect(
      vi.mocked(apiFetch).mock.calls.filter(
        (c) => (c[1] as RequestInit | undefined)?.body,
      ),
    ).toHaveLength(0)
  })
})
