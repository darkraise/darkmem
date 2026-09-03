import { useState } from "react"
import { FileText, Link2, Loader2, Trash2 } from "lucide-react"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "darkraise-ui/components/alert-dialog"
import { Button } from "darkraise-ui/components/button"
import { Card, CardContent, CardHeader } from "darkraise-ui/components/card"
import {
  SegmentGroup,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import {
  useDocumentConnections,
  useDocumentDelete,
  useDocumentSummarize,
  useDocumentSummary,
  type DocumentListItem,
} from "@/hooks/api"

export type ReaderMode = "read" | "edit"

/** The document-level controls the workspace was missing: mode, summarize,
 *  delete. Every route behind these already shipped -- except the summarize
 *  POST, which did not exist at all, so the summary panel could never fill.
 */
export function DocumentActions({
  document,
  mode,
  onModeChange,
  onDeleted,
}: {
  document: DocumentListItem
  mode: ReaderMode
  onModeChange: (mode: ReaderMode) => void
  onDeleted: () => void
}) {
  const [confirmOpen, setConfirmOpen] = useState(false)
  const summarize = useDocumentSummarize(document.id)
  const remove = useDocumentDelete()

  return (
    <div className="flex flex-wrap items-center gap-2 pb-2">
      <SegmentGroup
        value={mode}
        onValueChange={(value) => onModeChange(value as ReaderMode)}
      >
        <SegmentGroupItem value="read">Read</SegmentGroupItem>
        <SegmentGroupItem value="edit">Edit</SegmentGroupItem>
      </SegmentGroup>

      <div className="flex-1" />

      <Button
        variant="outline"
        size="sm"
        disabled={summarize.isPending}
        onClick={() =>
          summarize.mutate(undefined, {
            onSuccess: () => toast.success("Summary generated"),
            // Named, not swallowed: a 422 here means the document has no
            // blocks to summarise, which is a different thing from a failure.
            onError: (error) => toast.error(error.message),
          })
        }
      >
        {summarize.isPending ? (
          <Loader2 className="size-4 animate-spin" />
        ) : (
          <FileText className="size-4" />
        )}
        Summarize
      </Button>

      <Button
        variant="destructive"
        size="sm"
        onClick={() => setConfirmOpen(true)}
      >
        <Trash2 className="size-4" />
        Delete
      </Button>

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete {document.title ?? document.uri ?? "this document"}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This does more than remove the row. Deleting withdraws every
              block of this document as a source of evidence, and any fact
              left with no surviving source is expired. Facts still sourced
              some other way keep their rung. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                remove.mutate(document.id, {
                  onSuccess: () => {
                    toast.success("Document deleted")
                    setConfirmOpen(false)
                    onDeleted()
                  },
                  onError: (error) => toast.error(error.message),
                })
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

/** Summary and connections, side by side under the reader.
 *
 * Both are honest about being empty rather than absent: no summary has been
 * generated until someone spends the call, and connections stay empty for
 * every document until lifting runs, because they are emergent from shared
 * entities and this corpus has none.
 */
export function DocumentDetail({ documentId }: { documentId: string }) {
  const summary = useDocumentSummary(documentId)
  const connections = useDocumentConnections(documentId)

  return (
    <div className="grid gap-3.5 pt-3.5 sm:grid-cols-2">
      <Card elevation="low">
        <CardHeader className="space-y-1 pb-3">
          <p className="flex items-center gap-1.5 text-sm font-semibold">
            <FileText className="size-4" />
            Summary
          </p>
          <p className="text-muted-foreground text-sm">
            A report over this document — not a verified claim, and never
            badged.
          </p>
        </CardHeader>
        <CardContent>
          {summary.isLoading ? (
            <Skeleton className="h-16 w-full rounded-md" />
          ) : summary.data ? (
            <p className="text-sm">{summary.data.text}</p>
          ) : (
            <p className="text-muted-foreground text-sm italic">
              no summary has been generated — generating one is an explicit act
            </p>
          )}
        </CardContent>
      </Card>

      <Card elevation="low">
        <CardHeader className="space-y-1 pb-3">
          <p className="flex items-center gap-1.5 text-sm font-semibold">
            <Link2 className="size-4" />
            Connections
          </p>
          <p className="text-muted-foreground text-sm">
            Emergent from shared entities after lifting — not a synthesis.
          </p>
        </CardHeader>
        <CardContent>
          {connections.isLoading ? (
            <Skeleton className="h-16 w-full rounded-md" />
          ) : (connections.data?.items ?? []).length === 0 ? (
            <p className="text-muted-foreground text-sm italic">
              no shared entities with another document
            </p>
          ) : (
            <div className="flex flex-col gap-1.5">
              {(connections.data?.items ?? []).map((connection) => (
                <div key={connection.document_id} className="text-sm">
                  <span className="font-medium">
                    {connection.title ?? "untitled document"}
                  </span>
                  <span className="text-muted-foreground ml-2 font-mono text-sm">
                    {connection.shared_entities.join(" · ")}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  )
}
