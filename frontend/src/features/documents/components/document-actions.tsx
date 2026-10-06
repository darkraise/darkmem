import { useState } from "react"
import {
  BookOpen,
  Brain,
  FileText,
  History,
  Link2,
  Loader2,
  Pencil,
  Trash2,
} from "lucide-react"
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
import { Card, CardContent, CardHeader } from "darkraise-ui/components/card"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import { IconButton } from "@/components/darkmem"
import { MemoryPeekDialog } from "@/features/memories/components/memory-peek-dialog"
import {
  useDocumentConnections,
  useRelatedMemories,
  useDocumentDelete,
  useDocumentSummarize,
  useDocumentSummary,
  type DocumentListItem,
} from "@/hooks/api"
import { RevisionsSheet } from "./revisions-sheet"
import { plainText } from "@/lib/plain-text"

export type ReaderMode = "read" | "edit"

/** The document-level controls: edit, summarize, revisions, delete.
 *
 * Icon-only with a tooltip that is also the accessible name -- `IconButton`
 * makes that label mandatory, so the row is compact without becoming a row of
 * unnamed glyphs. It has to be compact: this bar is sticky over a scrolling
 * document and shares its line with the path.
 *
 * Edit is a BUTTON, not a read/edit segmented pair. A two-state toggle spends
 * a control on "read", which is where every selection already lands, and
 * offers a choice where there is really one action. Pressed state carries the
 * mode instead (`aria-pressed`, a filled variant and the inverse glyph), so
 * the way back out is the same control.
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
  const [revisionsOpen, setRevisionsOpen] = useState(false)
  const summarize = useDocumentSummarize(document.id)
  const remove = useDocumentDelete()
  const editing = mode === "edit"

  return (
    <div className="flex items-center gap-1">
      <IconButton
        icon={editing ? BookOpen : Pencil}
        label={editing ? "Read" : "Edit"}
        variant={editing ? "default" : "ghost"}
        aria-pressed={editing}
        onClick={() => onModeChange(editing ? "read" : "edit")}
      />

      <IconButton
        icon={summarize.isPending ? Loader2 : FileText}
        label="Summarize"
        variant="ghost"
        disabled={summarize.isPending}
        className={summarize.isPending ? "[&_svg]:animate-spin" : undefined}
        onClick={() =>
          summarize.mutate(undefined, {
            onSuccess: () => toast.success("Summary generated"),
            // Named, not swallowed: a 422 here means the document has no
            // blocks to summarise, which is a different thing from a failure.
            onError: (error) =>
              toast.error(`Summary could not be generated — ${error.message}`),
          })
        }
      />

      <IconButton
        icon={History}
        label="Revisions"
        variant="ghost"
        onClick={() => setRevisionsOpen(true)}
      />

      <IconButton
        icon={Trash2}
        label="Delete"
        variant="ghost"
        className="text-destructive hover:text-destructive"
        onClick={() => setConfirmOpen(true)}
      />

      <AlertDialog open={confirmOpen} onOpenChange={setConfirmOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete {document.title ?? document.uri ?? "this document"}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This removes the document. This cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              // The library hard-codes `data-variant="default"` (the primary
              // green) and spreads props after it; a delete is destructive.
              data-variant="destructive"
              onClick={() => {
                remove.mutate(document.id, {
                  onSuccess: () => {
                    toast.success("Document deleted")
                    setConfirmOpen(false)
                    onDeleted()
                  },
                  onError: (error) =>
                    toast.error(
                      `The document could not be deleted — ${error.message}`,
                    ),
                })
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
      <RevisionsSheet
        // DocumentActions stays mounted across selections; without the key a
        // pick on one document would ask for its revision under the next.
        key={document.id}
        documentId={document.id}
        open={revisionsOpen}
        onOpenChange={setRevisionsOpen}
      />
    </div>
  )
}

/** Summary and connections, side by side under the reader.
 *
 * Both are honest about being empty rather than absent: no summary has been
 * generated until someone spends the call, and a connections read that could
 * not be made says so rather than rendering as an empty list.
 */
export function DocumentDetail({
  documentId,
  hasSummary,
  onOpenDocument,
}: {
  documentId: string
  /** The list row's `has_summary`; `false` skips the summary read, whose
   *  answer would be a 404. Omitted where no list row is in hand. */
  hasSummary?: boolean
  /** Open a connected document in the same reader, focused on the passage
   *  that made it a connection. Omitted where the surface has no reader to
   *  steer, and the rows stay inert there rather than offering a navigation
   *  that would go nowhere. */
  onOpenDocument?: (documentId: string, blockId: string) => void
}) {
  const summary = useDocumentSummary(documentId, hasSummary)
  const connections = useDocumentConnections(documentId)

  return (
    <div className="grid gap-3.5 pt-3.5 sm:grid-cols-2 xl:grid-cols-3">
      <Card elevation="low">
        <CardHeader className="space-y-1 pb-3">
          <p className="flex items-center gap-1.5 text-sm font-semibold">
            <FileText className="size-4" />
            Summary
          </p>
        </CardHeader>
        <CardContent>
          {summary.isLoading ? (
            <Skeleton className="h-16 w-full rounded-md" />
          ) : summary.data ? (
            <p className="text-sm">{summary.data.text}</p>
          ) : (
            <p className="text-muted-foreground text-sm italic">
              no summary yet — use Summarize to generate one
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
              connections could not be read
            </p>
          ) : connections.data?.comparable_documents === 0 ? (
            // Tested before `embedded`, because `embedded` is false in this
            // state too: a project with one document resolves no fingerprint
            // holding both sides, and the "still being embedded" copy below
            // would then never come true — nothing embeds a document that
            // does not exist. The count is fingerprint-independent, so it is
            // the arm that can tell the two apart.
            <p className="text-muted-foreground text-sm italic">
              no other documents in this project to compare against
            </p>
          ) : !connections.data?.embedded ? (
            <p className="text-muted-foreground text-sm italic">
              not ready yet — documents are still being indexed
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
              no similar documents found
            </p>
          ) : (
            <div className="flex flex-col gap-1">
              {connections.data.items.map((connection) => {
                // `other_block_id` is the passage in the OTHER document, which
                // is the one worth landing on -- `block_id` is the passage in
                // the document already open.
                const open = onOpenDocument
                  ? () =>
                      onOpenDocument(
                        connection.document_id,
                        connection.other_block_id,
                      )
                  : undefined
                const Row = open ? "button" : "div"
                return (
                  <Row
                    key={connection.document_id}
                    {...(open
                      ? {
                          type: "button" as const,
                          onClick: open,
                          className:
                            "group hover:bg-muted/50 focus-visible:ring-primary/40 -mx-1.5 cursor-pointer rounded-sm px-1.5 py-1 text-left text-sm transition-colors focus-visible:ring-2 focus-visible:outline-none",
                        }
                      : { className: "text-sm" })}
                  >
                    <div className="flex items-start gap-1.5">
                      <span
                        className={
                          open
                            ? "text-primary-text font-medium underline-offset-2 group-hover:underline"
                            : "font-medium"
                        }
                      >
                        {connection.title ?? "untitled document"}
                      </span>
                      <span className="text-muted-foreground shrink-0 font-mono text-sm">
                        {connection.score.toFixed(3)}
                      </span>
                    </div>
                    <p className="text-muted-foreground line-clamp-2">
                      {plainText(connection.block_text)}
                    </p>
                    <p className="text-muted-foreground line-clamp-2 italic">
                      {plainText(connection.other_block_text)}
                    </p>
                  </Row>
                )
              })}
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
 * a zero comparable count render distinctly — and the count is tested first,
 * because `embedded` is false in both states. Neither offers an action, but
 * they are not resolved by the same thing and neither is resolved by this
 * card: a pending embed is ordinarily finished by the filing path, which
 * embeds a document's blocks at filing time, and by the pipeline's Phase 1
 * at buffer flush on the memory side — the hourly `block_embedding_refresh`
 * is a backstop for gaps and the `reembed` POST is an operator action after
 * a rotation, neither the normal route. `comparable_memories = 0` is
 * resolved only by capturing a memory in this project. Nothing resolves it
 * on its own.
 */
function RelatedMemoriesCard({ documentId }: { documentId: string }) {
  const related = useRelatedMemories(documentId)
  /** The memory a row opened, read in a dialog rather than by leaving the
   *  page: this card is a maintenance surface beside an open document, and
   *  routing away from that document to read one memory loses the context
   *  that made the memory interesting. */
  const [peek, setPeek] = useState<string | null>(null)

  return (
    <Card elevation="low">
      <CardHeader className="space-y-1 pb-3">
        <p className="flex items-center gap-1.5 text-sm font-semibold">
          <Brain className="size-4" />
          Related memories
        </p>
        <p className="text-muted-foreground text-sm">
          Memories near a passage of this document.
        </p>
      </CardHeader>
      <CardContent>
        {related.isLoading ? (
          <Skeleton className="h-16 w-full rounded-md" />
        ) : related.isError ? (
          <p className="text-destructive text-sm italic">
            related memories could not be read
          </p>
        ) : related.data?.comparable_memories === 0 ? (
          // Tested before `embedded`, for the reason the connections card
          // above gives: a project holding no memory resolves no shared
          // fingerprint either, so `!embedded` would swallow this state and
          // render "still being embedded" about a memory that will never be
          // captured.
          <p className="text-muted-foreground text-sm italic">
            no memories in this project to compare against
          </p>
        ) : !related.data?.embedded ? (
          <p className="text-muted-foreground text-sm italic">
            not ready yet — memories are still being indexed
          </p>
        ) : related.data.items.length === 0 ? (
          // Defensive: unreachable while `comparable_memories > 0`. The read
          // applies no similarity floor and inner-joins every comparable
          // memory to this document's best block in the shared partition, so
          // a comparable memory always yields a row.
          <p className="text-muted-foreground text-sm italic">
            no related memories found
          </p>
        ) : (
          <div className="flex flex-col gap-1">
            {related.data.items.map((memory) => (
              <button
                key={memory.memory_id}
                type="button"
                onClick={() => setPeek(memory.memory_id)}
                className="hover:bg-muted/50 focus-visible:ring-primary/40 -mx-1.5 cursor-pointer rounded-sm px-1.5 py-1 text-left text-sm transition-colors focus-visible:ring-2 focus-visible:outline-none"
              >
                {/* Text alone on the first lines; the status and score ride
                    a meta line below. Beside a two-line clamp they squeezed
                    the content down to a word or two. */}
                <span className="line-clamp-2">{memory.content}</span>
                <span className="text-muted-foreground mt-0.5 flex items-center gap-1.5 font-mono text-xs">
                  {memory.status !== "active" && (
                    <Badge variant="outline" className="text-xs">
                      {memory.status}
                    </Badge>
                  )}
                  {memory.score.toFixed(3)}
                </span>
                <p className="text-muted-foreground line-clamp-2">
                  {plainText(memory.block_text)}
                </p>
              </button>
            ))}
          </div>
        )}
      </CardContent>
      <MemoryPeekDialog memoryId={peek} onClose={() => setPeek(null)} />
    </Card>
  )
}
