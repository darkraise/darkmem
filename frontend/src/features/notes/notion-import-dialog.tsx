import { useEffect, useState } from "react"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import {
  type FileRejection,
  FileUpload,
  FileUploadDropzone,
  FileUploadHiddenInput,
  FileUploadItem,
  FileUploadItemGroup,
  FileUploadItemName,
  FileUploadTrigger,
} from "darkraise-ui/components/file-upload"
import { Progress } from "darkraise-ui/components/progress"

import { type ImportReport, importNotionExport } from "./lib/notion-import"

// Mirrors the backend's `notion_import_max_bytes` so the picker refuses an
// oversized zip before it is uploaded rather than after.
const MAX_IMPORT_BYTES = 1_073_741_824

function rejectionMessage({ file, reason }: FileRejection): string {
  if (reason === "TOO_LARGE") {
    return `${file.name} is over the import size ceiling.`
  }
  if (reason === "TOO_MANY_FILES") {
    return "Choose one zip file."
  }
  return `${file.name} is not a .zip file.`
}

type Phase =
  | { kind: "idle" }
  | { kind: "uploading"; fraction: number }
  | { kind: "importing" }
  | { kind: "done"; report: ImportReport }
  | { kind: "failed"; message: string }

export function NotionImportDialog({
  project,
  open,
  onOpenChange,
  onImported,
}: {
  project: string
  open: boolean
  onOpenChange: (open: boolean) => void
  onImported: (rootPageId: string) => void
}) {
  const [file, setFile] = useState<File | null>(null)
  const [phase, setPhase] = useState<Phase>({ kind: "idle" })
  const [showWarnings, setShowWarnings] = useState(false)
  // The parent mounts this dialog persistently, so a dismissed success would
  // otherwise reopen onto the previous run's report.
  useEffect(() => {
    if (!open) return
    setFile(null)
    setPhase({ kind: "idle" })
    setShowWarnings(false)
  }, [open])

  const busy = phase.kind === "uploading" || phase.kind === "importing"

  async function run() {
    if (!file) return
    setPhase({ kind: "uploading", fraction: 0 })
    try {
      const report = await importNotionExport(project, file, (fraction) => {
        // 1 means the body is sent and the server is now working, which has no
        // fraction to report -- so the bar goes indeterminate rather than
        // sitting at 100% for the length of the import.
        setPhase(
          fraction >= 1 ? { kind: "importing" } : { kind: "uploading", fraction },
        )
      })
      setPhase({ kind: "done", report })
    } catch (error) {
      setPhase({
        kind: "failed",
        message: error instanceof Error ? error.message : String(error),
      })
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next && busy) return
        onOpenChange(next)
      }}
      closeOnOutsidePointerDown={!busy}
      closeOnEscape={!busy}
    >
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Import from Notion</DialogTitle>
          <DialogDescription>
            In Notion, open Settings → Export, choose <strong>Markdown &amp; CSV</strong>,
            turn on “Include subpages” and include files. Then upload the zip here.
          </DialogDescription>
        </DialogHeader>

        {phase.kind === "idle" || phase.kind === "failed" ? (
          <FileUpload
            accept=".zip"
            maxFiles={1}
            maxFileSize={MAX_IMPORT_BYTES}
            onFileAccept={({ files }) => {
              setFile(files[0] ?? null)
              setPhase({ kind: "idle" })
            }}
            onFileReject={({ files }) => {
              // The picker drops a refused file without a word of its own, so
              // the dialog says which file and why, where a failed import does.
              const rejection = files[0]
              if (!rejection) return
              setFile(null)
              setPhase({ kind: "failed", message: rejectionMessage(rejection) })
            }}
          >
            <FileUploadHiddenInput />
            <FileUploadDropzone>
              <FileUploadTrigger>Choose a zip</FileUploadTrigger>
            </FileUploadDropzone>
            <FileUploadItemGroup>
              {file ? (
                <FileUploadItem file={file}>
                  <FileUploadItemName />
                </FileUploadItem>
              ) : null}
            </FileUploadItemGroup>
          </FileUpload>
        ) : null}

        {phase.kind === "uploading" ? (
          <Progress
            value={Math.round(phase.fraction * 100)}
            aria-label="Upload progress"
          />
        ) : null}

        {phase.kind === "importing" ? (
          <div className="space-y-2">
            <Progress value={null} aria-label="Import progress" />
            <p className="text-muted-foreground text-sm">
              Importing. Closing this does not cancel an import that has already
              reached the server.
            </p>
          </div>
        ) : null}

        {phase.kind === "failed" ? (
          <p className="text-destructive text-sm">{phase.message}</p>
        ) : null}

        {phase.kind === "done" ? (
          <div className="space-y-3 text-sm">
            <p>
              Imported <strong>{phase.report.pages_created}</strong> pages,{" "}
              <strong>{phase.report.databases}</strong> databases and{" "}
              <strong>{phase.report.attachments_stored}</strong> files.
            </p>
            {phase.report.warnings.length > 0 ? (
              <div>
                <Button
                  type="button"
                  variant="ghost"
                  size="sm"
                  onClick={() => setShowWarnings((shown) => !shown)}
                >
                  {phase.report.warnings.length} warnings
                </Button>
                {showWarnings ? (
                  <ul className="text-muted-foreground mt-2 space-y-1">
                    {phase.report.warnings.map((warning, index) => (
                      <li key={`${warning.kind}-${index}`}>
                        {warning.path ? `${warning.path}: ` : ""}
                        {warning.detail}
                      </li>
                    ))}
                    {phase.report.warnings_omitted > 0 ? (
                      <li>and {phase.report.warnings_omitted} more</li>
                    ) : null}
                  </ul>
                ) : null}
              </div>
            ) : null}
          </div>
        ) : null}

        <DialogFooter>
          {phase.kind === "done" ? (
            <Button
              type="button"
              onClick={() => onImported(phase.report.root_page_id)}
            >
              Go to imported pages
            </Button>
          ) : (
            <Button type="button" disabled={!file || busy} onClick={run}>
              Import
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
