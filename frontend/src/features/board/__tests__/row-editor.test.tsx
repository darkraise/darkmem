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
import { useBoardRecords } from "@/hooks/api"
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

  it("takes a single-line Note, so Enter cannot add the line break the server refuses", async () => {
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
    expect(note.tagName).toBe("INPUT")
    await user.clear(note)
    await user.type(note, "waiting{Enter}")
    expect(note).toHaveValue("waiting")
  })

  it("disables Move while the edit is in flight", async () => {
    const user = userEvent.setup()
    const prompt = { record: byTitle("Alpha"), state: "deferred" }
    const { rerender } = render(
      <NoteDialog prompt={prompt} onCancel={vi.fn()} onConfirm={vi.fn()} />,
    )
    await user.clear(screen.getByLabelText("Note"))
    await user.type(screen.getByLabelText("Note"), "waiting")
    expect(screen.getByRole("button", { name: "Move" })).toBeEnabled()
    rerender(
      <NoteDialog
        prompt={prompt}
        pending
        onCancel={vi.fn()}
        onConfirm={vi.fn()}
      />,
    )
    expect(screen.getByRole("button", { name: "Move" })).toBeDisabled()
  })

  it("cannot be cancelled while its edit is in flight", async () => {
    const onCancel = vi.fn()
    const user = userEvent.setup()
    render(
      <NoteDialog
        prompt={{ record: byTitle("Alpha"), state: "deferred" }}
        pending
        onCancel={onCancel}
        onConfirm={vi.fn()}
      />,
    )
    expect(screen.getByRole("button", { name: "Cancel" })).toBeDisabled()
    await user.keyboard("{Escape}")
    expect(onCancel).not.toHaveBeenCalled()
    expect(screen.getByRole("dialog")).toBeInTheDocument()
  })
})

function deferred<T>() {
  let resolve!: (value: T) => void
  let reject!: (error: unknown) => void
  const promise = new Promise<T>((res, rej) => {
    resolve = res
    reject = rej
  })
  return { promise, resolve, reject }
}

describe("useRowEditor", () => {
  it("sends the hash the last edit answered before the board re-reads", async () => {
    const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
    qc.setQueryData(["boardRecords", "darkmem"], RECORDS)
    const answers = ["h2", "h3"]
    vi.mocked(apiFetch).mockImplementation((path: string) =>
      path.startsWith("/board/records")
        ? new Promise(() => {})
        : Promise.resolve({
            document_id: "reg",
            content_hash: answers.shift(),
            row: {},
          }),
    )
    const { result } = renderHook(
      () => ({
        records: useBoardRecords("darkmem"),
        editor: useRowEditor("darkmem"),
      }),
      {
        wrapper: ({ children }) => (
          <QueryClientProvider client={qc}>{children}</QueryClientProvider>
        ),
      },
    )
    const alpha = () =>
      flattenRecords(result.current.records.data!).find(
        (r) => r.title === "Alpha",
      ) as BoardRecord
    act(() => result.current.editor.save(alpha(), { note: "first" }))
    await vi.waitFor(() => expect(alpha().contentHash).toBe("h2"))
    act(() => result.current.editor.save(alpha(), { note: "second" }))
    await vi.waitFor(() => expect(alpha().contentHash).toBe("h3"))
    const patches = vi
      .mocked(apiFetch)
      .mock.calls.filter(([, init]) => init?.method === "PATCH")
      .map(([, init]) => JSON.parse(String(init?.body)).expected_hash)
    expect(patches).toEqual(["h1", "h2"])
  })

  it("lets a late success close only the prompt it was sent for", async () => {
    const landing = deferred<unknown>()
    vi.mocked(apiFetch).mockReturnValueOnce(landing.promise as Promise<never>)
    const { result } = renderHook(() => useRowEditor("darkmem"), { wrapper })
    act(() => result.current.move(byTitle("Alpha"), "deferred"))
    act(() => result.current.confirmPrompt("parked"))
    await vi.waitFor(() => expect(result.current.promptPending).toBe(true))
    act(() => result.current.cancelPrompt())
    act(() => result.current.move(byTitle("Beta"), "deferred"))
    expect(result.current.prompt?.record.title).toBe("Beta")
    expect(result.current.promptPending).toBe(false)
    await act(async () => {
      landing.resolve({ document_id: "reg", content_hash: "h2", row: {} })
      await landing.promise
    })
    expect(result.current.prompt?.record.title).toBe("Beta")
  })

  it("reports a refusal even when a later edit was sent before it answered", async () => {
    const first = deferred<never>()
    vi.mocked(apiFetch)
      .mockReturnValueOnce(first.promise)
      .mockResolvedValueOnce({ document_id: "reg", content_hash: "h2", row: {} })
    const { result } = renderHook(() => useRowEditor("darkmem"), { wrapper })
    const alpha = byTitle("Alpha")
    act(() => result.current.save(alpha, { note: "x" }))
    act(() => result.current.save(byTitle("Beta"), { note: "y" }))
    await act(async () => {
      first.reject(new ApiError("bad cell", 422, undefined, "invalid_cell"))
      await first.promise.catch(() => {})
    })
    await vi.waitFor(() => expect(toast.error).toHaveBeenCalledWith("bad cell"))
    expect(result.current.editEpoch(alpha.id)).toBe(1)
  })

  it("marks every record with an edit in flight as pending, each until its own answer", async () => {
    const first = deferred<unknown>()
    const second = deferred<unknown>()
    vi.mocked(apiFetch)
      .mockReturnValueOnce(first.promise as Promise<never>)
      .mockReturnValueOnce(second.promise as Promise<never>)
    const { result } = renderHook(() => useRowEditor("darkmem"), { wrapper })
    const alpha = byTitle("Alpha")
    const beta = byTitle("Beta")
    act(() => result.current.save(alpha, { note: "x" }))
    act(() => result.current.save(beta, { note: "y" }))
    expect(result.current.isPending(alpha.id)).toBe(true)
    expect(result.current.isPending(beta.id)).toBe(true)
    await act(async () => {
      second.resolve({ document_id: "reg", content_hash: "h2", row: {} })
      await second.promise
    })
    expect(result.current.isPending(alpha.id)).toBe(true)
    expect(result.current.isPending(beta.id)).toBe(false)
    await act(async () => {
      first.resolve({ document_id: "reg", content_hash: "h3", row: {} })
      await first.promise
    })
    expect(result.current.isPending(alpha.id)).toBe(false)
  })

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

  it("keeps the Note prompt open on a refusal and closes it when the edit lands", async () => {
    const { result } = renderHook(() => useRowEditor("darkmem"), { wrapper })
    vi.mocked(apiFetch).mockRejectedValueOnce(
      new ApiError("bad cell", 422, undefined, "invalid_cell"),
    )
    act(() => result.current.move(byTitle("Alpha"), "deferred"))
    act(() => result.current.confirmPrompt("parked for now"))
    await vi.waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith("bad cell"),
    )
    expect(result.current.prompt?.state).toBe("deferred")

    vi.mocked(apiFetch).mockResolvedValueOnce({
      document_id: "reg",
      content_hash: "h2",
      row: {},
    })
    act(() => result.current.confirmPrompt("parked for now"))
    await vi.waitFor(() => expect(result.current.prompt).toBeNull())
  })

  it("closes the Note prompt on a hash conflict, since its record is stale", async () => {
    const { result } = renderHook(() => useRowEditor("darkmem"), { wrapper })
    vi.mocked(apiFetch).mockRejectedValueOnce(
      new ApiError("stale", 409, [{ current_hash: "h9" }], "hash_conflict"),
    )
    act(() => result.current.move(byTitle("Alpha"), "deferred"))
    act(() => result.current.confirmPrompt("parked for now"))
    await vi.waitFor(() =>
      expect(toast.error).toHaveBeenCalledWith(CONFLICT_MESSAGE),
    )
    await vi.waitFor(() => expect(result.current.prompt).toBeNull())
  })

  it("bumps a record's edit epoch only when its edit is refused", async () => {
    const { result } = renderHook(() => useRowEditor("darkmem"), { wrapper })
    const alpha = byTitle("Alpha")
    expect(result.current.editEpoch(alpha.id)).toBe(0)
    vi.mocked(apiFetch).mockRejectedValueOnce(
      new ApiError("bad", 422, undefined, "invalid_cell"),
    )
    act(() => result.current.save(alpha, { note: "x" }))
    await vi.waitFor(() => expect(result.current.editEpoch(alpha.id)).toBe(1))
    expect(result.current.editEpoch(byTitle("Beta").id)).toBe(0)
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
