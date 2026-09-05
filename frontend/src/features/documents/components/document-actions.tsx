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
 * generated until someone spends the call, and a connections read that could
 * not be made says so rather than rendering as an empty list.
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
            Nearest documents in this project, by passage similarity.
          </p>
        </CardHeader>
        <CardContent>
          {connections.isLoading ? (
            <Skeleton className="h-16 w-full rounded-md" />
          ) : connections.isError ? (
            <p className="text-destructive text-sm italic">
              connections could not be read — this is a failed read, not an
              empty one
            </p>
          ) : !connections.data?.embedded ? (
            <p className="text-muted-foreground text-sm italic">
              not comparable yet — this document's blocks or this project's
              other documents are still being embedded
            </p>
          ) : connections.data.comparable_documents === 0 ? (
            <p className="text-muted-foreground text-sm italic">
              no other documents in this project to compare against
            </p>
          ) : connections.data.items.length === 0 ? (
            // The probe takes each passage's ten nearest blocks with no
            // project filter and the outer query then drops the foreign ones,
            // so this arm fires when every window was filled by other
            // projects. It cannot mean "nothing is embedded" -- `embedded`
            // already proves a same-project counterpart carries a vector under
            // this fingerprint -- and it cannot mean "nothing is near", since
            // the read applies no similarity floor.
            <p className="text-muted-foreground text-sm italic">
              no other document in this project surfaced — the comparison
              samples each passage's nearest neighbours rather than scanning
              every document, so a distant match can fall outside that window
            </p>
          ) : (
            <div className="flex flex-col gap-2">
              {connections.data.items.map((connection) => (
                <div key={connection.document_id} className="text-sm">
                  <div className="flex items-start gap-1.5">
                    <span className="font-medium">
                      {connection.title ?? "untitled document"}
                    </span>
                    <span className="text-muted-foreground shrink-0 font-mono text-sm">
                      {connection.score.toFixed(3)}
                    </span>
                  </div>
                  <p className="text-muted-foreground line-clamp-2">
                    {connection.block_text}
                  </p>
                  <p className="text-muted-foreground line-clamp-2 italic">
                    {connection.other_block_text}
                  </p>
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

/** Memories whose text sits near a passage of this document.
 *
 * A maintenance surface, which is the owner's stated purpose for it. Two
 * things it deliberately does not do: it renders no prose about what a
 * document and a memory share (that would be unbadged synthesis, which doc 09
 * owns with grounding and a ladder), and it renders the score as a raw number
 * rather than a percentage or a badge, because the distribution is continuous
 * and any banding would assert a precision nobody measured. The matching
 * passage is the evidence, not the score.
 *
 * A read that could not be made is not an empty list, so `embedded: false` and
 * a zero comparable count render distinctly. Neither offers an action: the
 * hourly `block_embedding_refresh` resolves the first on its own.
 */
function RelatedMemoriesCard({ documentId }: { documentId: string }) {
  const related = useRelatedMemories(documentId)

  return (
    <Card elevation="low">
      <CardHeader className="space-y-1 pb-3">
        <p className="flex items-center gap-1.5 text-sm font-semibold">
          <Brain className="size-4" />
          Related memories
        </p>
        <p className="text-muted-foreground text-sm">
          Memories near a passage of this document — the passage is the
          evidence, the score only orders the rows.
        </p>
      </CardHeader>
      <CardContent>
        {related.isLoading ? (
          <Skeleton className="h-16 w-full rounded-md" />
        ) : related.isError ? (
          <p className="text-destructive text-sm italic">
            related memories could not be read — this is a failed read, not an
            empty one
          </p>
        ) : !related.data?.embedded ? (
          <p className="text-muted-foreground text-sm italic">
            not comparable yet — this document's blocks or this project's
            memories are still being embedded
          </p>
        ) : related.data.comparable_memories === 0 ? (
          <p className="text-muted-foreground text-sm italic">
            no memories in this project to compare against
          </p>
        ) : related.data.items.length === 0 ? (
          // Defensive: unreachable while `comparable_memories > 0`. The read
          // applies no similarity floor and inner-joins every comparable
          // memory to this document's best block in the shared partition, so
          // a comparable memory always yields a row.
          <p className="text-muted-foreground text-sm italic">
            no rows came back for this document
          </p>
        ) : (
          <div className="flex flex-col gap-2">
            {related.data.items.map((memory) => (
              <div key={memory.memory_id} className="text-sm">
                <div className="flex items-start gap-1.5">
                  <span className="line-clamp-2">{memory.content}</span>
                  {memory.status !== "active" && (
                    <Badge variant="outline" className="shrink-0 text-[10px]">
                      {memory.status}
                    </Badge>
                  )}
                  <span className="text-muted-foreground shrink-0 font-mono text-sm">
                    {memory.score.toFixed(3)}
                  </span>
                </div>
                <p className="text-muted-foreground line-clamp-2">
                  {memory.block_text}
                </p>
              </div>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}
