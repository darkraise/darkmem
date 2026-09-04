import { useState } from "react"
import { Brain, FileText, Link2, Loader2, Trash2 } from "lucide-react"
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
import { Badge } from "darkraise-ui/components/badge"
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
  useRelatedMemories,
  useDocumentLift,
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
    <div className="grid gap-3.5 pt-3.5 sm:grid-cols-2 xl:grid-cols-3">
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

      <RelatedMemoriesCard documentId={documentId} />
    </div>
  )
}

/** Memories that assert what this document asserts, and what to do about them.
 *
 * A maintenance surface, which is the owner's stated purpose for it. Two
 * things it deliberately does not do: it renders no prose about what a
 * document and a memory share (that would be unbadged synthesis, which doc 09
 * owns with grounding and a ladder), and it shows the shared entity names
 * rather than a similarity score, because the count is evidence and a
 * normalised number would read as a measurement nobody made.
 *
 * An UNLIFTED document is not an empty list. Rendering both the same way tells
 * a reader "nothing relates to this" when the truth is "nobody has asked yet",
 * so the unlifted state says so and offers the lift.
 */
function RelatedMemoriesCard({ documentId }: { documentId: string }) {
  const related = useRelatedMemories(documentId)
  const lift = useDocumentLift(documentId)

  return (
    <Card elevation="low">
      <CardHeader className="space-y-1 pb-3">
        <p className="flex items-center gap-1.5 text-sm font-semibold">
          <Brain className="size-4" />
          Related memories
        </p>
        <p className="text-muted-foreground text-sm">
          Memories asserting what this document's lift asserted — ordered by
          shared entities, which is evidence rather than a score.
        </p>
      </CardHeader>
      <CardContent>
        {related.isLoading ? (
          <Skeleton className="h-16 w-full rounded-md" />
        ) : !related.data?.lifted ? (
          <div className="space-y-2">
            <p className="text-muted-foreground text-sm italic">
              this document has not been lifted, so it asserts nothing yet —
              which is different from having no relations
            </p>
            <Button
              size="sm"
              variant="outline"
              onClick={() => lift.mutate()}
              disabled={lift.isPending}
            >
              {lift.isPending ? "Lifting…" : "Lift this document"}
            </Button>
            <p className="text-muted-foreground text-sm">
              Lifting spends a model call per block and mints ordinary
              memories. It is idempotent: lifting again replaces the previous
              lift rather than doubling it.
            </p>
          </div>
        ) : (related.data?.items ?? []).length === 0 ? (
          <p className="text-muted-foreground text-sm italic">
            lifted, and no other memory asserts the same entities
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {(related.data?.items ?? []).map((memory) => (
              <div key={memory.memory_id} className="text-sm">
                <div className="flex items-start gap-1.5">
                  <span className="line-clamp-2">{memory.content}</span>
                  {memory.status !== "active" && (
                    <Badge variant="outline" className="shrink-0 text-[10px]">
                      {memory.status}
                    </Badge>
                  )}
                </div>
                <span className="text-muted-foreground font-mono text-sm">
                  {memory.shared_entities.join(" · ")}
                </span>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
