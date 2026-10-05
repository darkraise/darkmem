import { useState } from "react"
import { useNavigate } from "@tanstack/react-router"
import { Brain, Pencil, Trash2 } from "lucide-react"
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
import { toast } from "darkraise-ui/components/sonner"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Card, CardContent, CardHeader } from "darkraise-ui/components/card"
import { EmptyState } from "@/components/darkmem"
import { Separator } from "darkraise-ui/components/separator"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import {
  useDeleteMemory,
  useMemory,
  type Memory,
  type MemoryLineageEntry,
} from "@/hooks/api/use-memory-api"
import { LifecycleBadge } from "./lifecycle-badge"
import { MemoryEditorDialog } from "./memory-editor-dialog"
import { MemoryEventTimeline } from "./memory-event-timeline"
import { MemoryExcerptLink } from "./memory-excerpt-link"
import { shortId } from "@/lib/short-id"

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  })
}

function LineageLink({ id, content }: { id: string; content: string }) {
  return (
    <MemoryExcerptLink
      memoryId={id}
      excerpt={content.length > 160 ? `${content.slice(0, 160)}…` : content}
    />
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-muted-foreground mb-1.5 text-xs font-semibold tracking-wide uppercase">
      {children}
    </p>
  )
}

function PredecessorRow({ entry }: { entry: MemoryLineageEntry }) {
  return (
    <div className="flex items-start gap-2.5">
      <LifecycleBadge status={entry.status} />
      <LineageLink id={entry.id} content={entry.content} />
    </div>
  )
}

/**
 * Forward direction (what replaced this memory) reads `superseded_by`
 * straight off the row and resolves it through `GET /memories/{id}` — an
 * ID-addressed read, so it reaches the successor regardless of the
 * successor's own status (content_surfaces.py's ID_ADDRESSED exemption).
 *
 * The reverse direction (what this memory replaced) reads `predecessors`
 * (T1.47), which the backend populates only on this same single-get read —
 * `undefined` means "not computed for this read" (e.g. a row reused from a
 * search result), never "confirmed empty." That is a third, distinct state
 * from "has predecessors" and "replaced nothing" (`[]`), and conflating it
 * with either would misreport what the database actually knows.
 */
function SupersessionLineage({ memory }: { memory: Memory }) {
  const successorId =
    memory.status === "superseded" && memory.superseded_by
      ? memory.superseded_by
      : ""
  const successor = useMemory(successorId)

  return (
    <div className="space-y-3">
      <div>
        <SectionLabel>Replaced by</SectionLabel>
        {memory.status === "superseded" ? (
          <div className="flex items-start gap-2.5">
            {/* The successor's own status: it sits beside the successor's
                link, and the successor is normally the active version. */}
            {successor.data?.status ? (
              <LifecycleBadge status={successor.data.status} />
            ) : null}
            {!memory.superseded_by ? (
              <span className="text-muted-foreground text-sm italic">
                successor pointer missing
              </span>
            ) : successor.isLoading ? (
              <Skeleton className="h-4 w-48" />
            ) : successor.data ? (
              <LineageLink
                id={successor.data.id}
                content={successor.data.content}
              />
            ) : (
              <span className="text-muted-foreground text-sm italic">
                successor memory {shortId(memory.superseded_by)} could not be
                loaded
              </span>
            )}
          </div>
        ) : memory.status === "deprecated" ? (
          <div className="flex flex-wrap items-center gap-2.5">
            <LifecycleBadge status="deprecated" />
            <span className="text-muted-foreground text-sm italic">
              The memory that replaced this one was later deleted.
            </span>
          </div>
        ) : (
          <p className="text-muted-foreground text-sm italic">
            Not superseded — this is the current version.
          </p>
        )}
      </div>

      <Separator />

      <div>
        <SectionLabel>Replaced</SectionLabel>
        {memory.predecessors === undefined ? (
          <p className="text-muted-foreground text-sm italic">Unknown.</p>
        ) : memory.predecessors.length === 0 ? (
          <p className="text-muted-foreground text-sm italic">
            Replaced nothing.
          </p>
        ) : (
          <div className="space-y-1.5">
            {memory.predecessors.map((entry) => (
              <PredecessorRow key={entry.id} entry={entry} />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

export function RealMemoryDetailView({ memoryId }: { memoryId: string }) {
  const { data: memory, isLoading, isError } = useMemory(memoryId)
  const [editOpen, setEditOpen] = useState(false)
  const [deleteOpen, setDeleteOpen] = useState(false)
  const deleteMemory = useDeleteMemory()
  const navigate = useNavigate()

  const confirmDelete = () =>
    deleteMemory.mutate(memoryId, {
      onSuccess: () => {
        toast.success("Memory deleted")
        void navigate({ to: "/memories" })
      },
      onError: (error) => toast.error(`Delete failed: ${error.message}`),
    })

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4">
        <PageChrome icon={Brain} title="Memory detail" />
        <Skeleton className="h-40 w-full rounded-lg" />
        <Skeleton className="h-32 w-full rounded-lg" />
      </div>
    )
  }

  if (isError || !memory) {
    return (
      <>
        <PageChrome icon={Brain} title="Memory detail" />
        <EmptyState
          kind="missing"
          scope="page"
          title="Memory not found"
          description="This memory does not exist, or the request failed."
        />
      </>
    )
  }

  return (
    <div className="mx-auto max-w-3xl space-y-4">
      <PageChrome
        icon={Brain}
        title="Memory detail"
        parent={{ label: "Memories", href: "/memories" }}
        actions={
          <div className="flex items-center gap-2">
            <Button variant="outline" onClick={() => setEditOpen(true)}>
              <Pencil className="mr-2 size-4" />
              Edit
            </Button>
            <Button
              variant="outline"
              className="text-destructive"
              onClick={() => setDeleteOpen(true)}
            >
              <Trash2 className="mr-2 size-4" />
              Delete
            </Button>
          </div>
        }
      />
      <Card elevation="low">
        <CardHeader className="space-y-3 pb-3">
          <div className="flex flex-wrap items-center gap-2">
            <LifecycleBadge status={memory.status} />
            <span className="text-muted-foreground ml-auto font-mono text-sm">
              memory {shortId(memory.id)}
            </span>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-base leading-relaxed whitespace-pre-wrap">
            {memory.content}
          </p>
          {memory.summary ? (
            <p className="text-muted-foreground text-sm">{memory.summary}</p>
          ) : null}
          {memory.tags.length > 0 ? (
            <div className="flex flex-wrap gap-1.5">
              {memory.tags.map((tag) => (
                <Badge key={tag} variant="outline" size="sm">
                  {tag}
                </Badge>
              ))}
            </div>
          ) : null}
          <Separator />
          <div className="text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 font-mono text-sm">
            <span>
              captured{" "}
              <b className="text-foreground font-medium">
                {formatDateTime(memory.created_at)}
              </b>
            </span>
            <span>
              via <b className="text-foreground font-medium">{memory.source}</b>
            </span>
            {memory.project ? (
              <span>
                project{" "}
                <b className="text-foreground font-medium">{memory.project}</b>
              </span>
            ) : null}
            {memory.classified_type || memory.memory_type ? (
              <span>
                type{" "}
                <b className="text-foreground font-medium">
                  {memory.classified_type ?? memory.memory_type}
                </b>
              </span>
            ) : null}
            {memory.technologies?.length ? (
              <span className="flex items-center gap-1.5">
                {memory.technologies.map((tech) => (
                  <Badge
                    key={tech}
                    variant="outline"
                    size="sm"
                    className="rounded-sm font-mono"
                  >
                    {tech}
                  </Badge>
                ))}
              </span>
            ) : null}
          </div>
        </CardContent>
      </Card>

      <Card elevation="low">
        <CardHeader className="pb-3">
          <h2 className="text-sm font-semibold">Supersession lineage</h2>
        </CardHeader>
        <CardContent>
          <SupersessionLineage memory={memory} />
        </CardContent>
      </Card>

      <Card elevation="low">
        <CardHeader className="pb-3">
          <h2 className="text-sm font-semibold">Timeline</h2>
        </CardHeader>
        <CardContent>
          <MemoryEventTimeline memoryId={memory.id} />
        </CardContent>
      </Card>

      <MemoryEditorDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        memory={memory}
        projects={[]}
      />

      <AlertDialog open={deleteOpen} onOpenChange={setDeleteOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete this memory?</AlertDialogTitle>
            <AlertDialogDescription>
              The memory goes, with its embeddings, tags and graph
              contributions. This is not a content purge: the activity journal
              and any fact lifted from it keep text derived from it.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              // The library hard-codes the primary variant; a delete is
              // destructive.
              data-variant="destructive"
              disabled={deleteMemory.isPending}
              onClick={confirmDelete}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
