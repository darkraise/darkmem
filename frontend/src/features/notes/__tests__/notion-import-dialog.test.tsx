import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import { beforeEach, describe, expect, it, vi } from "vitest"

import { NotionImportDialog } from "../notion-import-dialog"

const importNotionExport = vi.fn()
vi.mock("../lib/notion-import", () => ({
  importNotionExport: (...args: unknown[]) => importNotionExport(...args),
}))

function open(onImported = vi.fn()) {
  render(
    <NotionImportDialog
      project="notes"
      open
      onOpenChange={vi.fn()}
      onImported={onImported}
    />,
  )
  return onImported
}

function pick(name = "export.zip") {
  const input = document.querySelector('input[type="file"]') as HTMLInputElement
  const file = new File([new Uint8Array([1, 2, 3])], name, { type: "application/zip" })
  Object.defineProperty(input, "files", { value: [file] })
  fireEvent.change(input)
  return file
}

beforeEach(() => {
  importNotionExport.mockReset()
})

describe("NotionImportDialog", () => {
  it("shows the export instructions while idle", () => {
    open()
    expect(screen.getByText(/Markdown & CSV/i)).toBeInTheDocument()
  })

  it("accepts only zip files", () => {
    open()
    const input = document.querySelector('input[type="file"]') as HTMLInputElement
    expect(input.accept).toContain(".zip")
  })

  it("reports progress while the body uploads", async () => {
    let report!: (fraction: number) => void
    importNotionExport.mockImplementation(
      (_p: string, _f: File, onProgress: (n: number) => void) =>
        new Promise(() => {
          report = onProgress
        }),
    )
    open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    await waitFor(() => expect(importNotionExport).toHaveBeenCalled())
    report(0.5)
    await waitFor(() =>
      expect(screen.getByRole("progressbar")).toHaveAttribute("aria-valuenow", "50"),
    )
  })

  it("goes indeterminate once the body is sent", async () => {
    let report!: (fraction: number) => void
    importNotionExport.mockImplementation(
      (_p: string, _f: File, onProgress: (n: number) => void) =>
        new Promise(() => {
          report = onProgress
        }),
    )
    open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    await waitFor(() => expect(importNotionExport).toHaveBeenCalled())
    report(1)
    await waitFor(() =>
      expect(screen.getByRole("progressbar")).not.toHaveAttribute("aria-valuenow"),
    )
  })

  it("says a committed import is not cancelled by closing", async () => {
    let report!: (fraction: number) => void
    importNotionExport.mockImplementation(
      (_p: string, _f: File, onProgress: (n: number) => void) =>
        new Promise(() => {
          report = onProgress
        }),
    )
    open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    await waitFor(() => expect(importNotionExport).toHaveBeenCalled())
    report(1)
    await waitFor(() =>
      expect(screen.getByText(/closing this does not cancel/i)).toBeInTheDocument(),
    )
  })

  it("shows the counts on success", async () => {
    importNotionExport.mockResolvedValue({
      root_page_id: "r1", pages_created: 12, databases: 2,
      attachments_stored: 3, attachment_bytes: 900, warnings: [], warnings_omitted: 0,
    })
    open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    expect(await screen.findByText(/12/)).toBeInTheDocument()
  })

  it("lists warnings and their omitted count", async () => {
    importNotionExport.mockResolvedValue({
      root_page_id: "r1", pages_created: 1, databases: 0,
      attachments_stored: 0, attachment_bytes: 0,
      warnings: [{ path: "A.md", kind: "missing_file", detail: "x.png is not in the export" }],
      warnings_omitted: 4,
    })
    open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    fireEvent.click(await screen.findByRole("button", { name: /warning/i }))
    expect(await screen.findByText(/x\.png is not in the export/)).toBeInTheDocument()
    expect(screen.getByText(/4 more/)).toBeInTheDocument()
  })

  it("hands the root page id back on Go to imported pages", async () => {
    importNotionExport.mockResolvedValue({
      root_page_id: "root-123", pages_created: 1, databases: 0,
      attachments_stored: 0, attachment_bytes: 0, warnings: [], warnings_omitted: 0,
    })
    const onImported = open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    fireEvent.click(await screen.findByRole("button", { name: /go to imported pages/i }))
    expect(onImported).toHaveBeenCalledWith("root-123")
  })

  it("renders a refusal in the dialog, not as a toast", async () => {
    importNotionExport.mockRejectedValue(
      Object.assign(new Error("re-export from Notion as Markdown & CSV"), {
        name: "ApiError", status: 422,
      }),
    )
    open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    expect(
      await screen.findByText(/re-export from Notion as Markdown & CSV/),
    ).toBeInTheDocument()
  })

  it("lets the operator retry after a refusal", async () => {
    importNotionExport.mockRejectedValueOnce(new Error("nope"))
    open()
    pick()
    fireEvent.click(screen.getByRole("button", { name: /import/i }))
    await screen.findByText(/nope/)
    expect(screen.getByRole("button", { name: /import/i })).toBeEnabled()
  })

  it("reopens onto a fresh picker after a success was dismissed", async () => {
    importNotionExport.mockResolvedValue({
      root_page_id: "root-123", pages_created: 1, databases: 0,
      attachments_stored: 0, attachment_bytes: 0, warnings: [], warnings_omitted: 0,
    })
    const { rerender } = render(
      <NotionImportDialog
        project="notes"
        open
        onOpenChange={vi.fn()}
        onImported={vi.fn()}
      />,
    )
    pick()
    fireEvent.click(screen.getByRole("button", { name: /^import$/i }))
    await screen.findByRole("button", { name: /go to imported pages/i })

    rerender(
      <NotionImportDialog
        project="notes"
        open={false}
        onOpenChange={vi.fn()}
        onImported={vi.fn()}
      />,
    )
    rerender(
      <NotionImportDialog
        project="notes"
        open
        onOpenChange={vi.fn()}
        onImported={vi.fn()}
      />,
    )

    await waitFor(() =>
      expect(
        screen.queryByRole("button", { name: /go to imported pages/i }),
      ).not.toBeInTheDocument(),
    )
    expect(screen.getByRole("button", { name: /^import$/i })).toBeDisabled()
  })

  it("disables the import button with no file chosen", () => {
    open()
    expect(screen.getByRole("button", { name: /import/i })).toBeDisabled()
  })
})
