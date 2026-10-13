import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, render, renderHook, screen } from "@testing-library/react"
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
}))

import { toast } from "darkraise-ui/components/sonner"
import { ApiError, apiFetch } from "@/lib/api"
import { flattenRecords, type BoardRecord } from "../lib/records"
import { NoteDialog } from "../components/note-dialog"
import { CONFLICT_MESSAGE, useRowEditor } from "../use-row-editor"
import { RECORDS } from "./fixtures"

const records = flattenRecords(RECORDS)
const byTitle = (title: string) =>
  records.find((r) => r.title === title) as BoardRecord

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

beforeEach(() => {
  vi.mocked(apiFetch).mockReset()
  vi.mocked(toast.error).mockReset()
})

describe("NoteDialog", () => {
  it("holds the current Note and stays disabled while it is blank or a dash", async () => {
    const onConfirm = vi.fn()
    const user = userEvent.setup()
    render(
      <NoteDialog
        prompt={{ record: byTitle("Alpha"), state: "deferred" }}
        onCancel={vi.fn()}
        onConfirm={onConfirm}
      />,
    )
    const note = screen.getByLabelText("Note")
    expect(note).toHaveValue("-")
    expect(screen.getByRole("button", { name: "Move" })).toBeDisabled()
    await user.clear(note)
    await user.type(note, "  ")
    expect(screen.getByRole("button", { name: "Move" })).toBeDisabled()
    await user.type(note, "waiting on the owner")
    await user.click(screen.getByRole("button", { name: "Move" }))
    expect(onConfirm).toHaveBeenCalledWith("waiting on the owner")
  })
})

describe("useRowEditor", () => {
  it("asks for a Note before a move into deferred, and patches after it", async () => {
    vi.mocked(apiFetch).mockResolvedValue({
      document_id: "reg",
      content_hash: "h2",
      row: {},
    })
    const { result } = renderHook(() => useRowEditor("darkmem"), { wrapper })
    act(() => result.current.move(byTitle("Alpha"), "deferred"))
    expect(result.current.prompt?.state).toBe("deferred")
    expect(apiFetch).not.toHaveBeenCalled()
    act(() => result.current.confirmPrompt("parked for now"))
    await vi.waitFor(() => expect(apiFetch).toHaveBeenCalled())
    expect(vi.mocked(apiFetch).mock.calls[0]).toEqual([
      "/board/registers/reg/rows/1",
      {
        method: "PATCH",
        body: JSON.stringify({
          expected_hash: "h1",
          state: "deferred",
          note: "parked for now",
        }),
      },
    ])
  })

  it("never patches a plan task", () => {
    const { result } = renderHook(() => useRowEditor("darkmem"), { wrapper })
    act(() => result.current.move(byTitle("One"), "todo"))
    expect(apiFetch).not.toHaveBeenCalled()
    expect(result.current.prompt).toBeNull()
  })

  it("names a conflict as a reload and shows any other refusal's own message", async () => {
    const { result } = renderHook(() => useRowEditor("darkmem"), { wrapper })
    vi.mocked(apiFetch).mockRejectedValueOnce(
      new ApiError("stale", 409, [{ current_hash: "h9" }], "hash_conflict"),
    )
    act(() => result.current.move(byTitle("Alpha"), "doing"))
    await vi.waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(CONFLICT_MESSAGE),
    )
    vi.mocked(apiFetch).mockRejectedValueOnce(
      new ApiError(
        "a row in 'verify' needs a Note",
        422,
        undefined,
        "note_required",
      ),
    )
    act(() => result.current.save(byTitle("Beta"), { note: "" }))
    await vi.waitFor(() =>
      expect(toast.error).toHaveBeenLastCalledWith(
        "a row in 'verify' needs a Note",
      ),
    )
  })
})
