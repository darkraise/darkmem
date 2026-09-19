import { useState } from "react"
import { Link } from "@tanstack/react-router"
import { Brain, Link2, Pencil } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Card, CardContent, CardHeader } from "darkraise-ui/components/card"
import { EmptyState } from "@/components/darkmem"
import { Separator } from "darkraise-ui/components/separator"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import {
  useMemory,
  type Memory,
  type MemoryLineageEntry,
} from "@/hooks/api/use-memory-api"
import { LifecycleBadge } from "./lifecycle-badge"
import { MemoryEditorDialog } from "./memory-editor-dialog"
import { MemoryEventTimeline } from "./memory-event-timeline"

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  })
}

function LineageLink({ id, content }: { id: string; content: string }) {
  return (
    <Link
      to="/memories/$memoryId"
      params={{ memoryId: id }}
      className="hover:text-primary-text flex min-w-0 items-center gap-1.5 text-sm transition-colors"
    >
      <Link2
        aria-hidden
        className="text-muted-foreground h-3.5 w-3.5 shrink-0"
      />
      <span className="truncate">
        memory {id.slice(0, 8)} — “{content.slice(0, 80)}…”
      </span>
    </Link>
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
    <div className="flex flex-wrap items-center gap-2.5">
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
          <div className="flex flex-wrap items-center gap-2.5">
            <LifecycleBadge status="superseded" />
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
                successor memory {memory.superseded_by.slice(0, 8)} could not be
                loaded
              </span>
            )}
          </div>
        ) : memory.status === "deprecated" ? (
          <div className="flex flex-wrap items-center gap-2.5">
            <LifecycleBadge status="deprecated" />
            <span className="text-muted-foreground text-sm italic">
              superseded_by: null — the successor memory was later removed; this
              row was demoted, not deleted.
            </span>
          </div>
        ) : (
          <p className="text-muted-foreground text-sm italic">
            not superseded — this is the current, active version of this memory;
            superseded_by is null.
          </p>
        )}
      </div>

      <Separator />

      <div>
        <SectionLabel>Replaced</SectionLabel>
        {memory.predecessors === undefined ? (
          <p className="text-muted-foreground text-sm italic">
            unknown — not computed for this read.
          </p>
        ) : memory.predecessors.length === 0 ? (
          <p className="text-muted-foreground text-sm italic">
            replaced nothing — no earlier memory points here through
            superseded_by.
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
        description="One memory, its enrichment, and its supersession lineage."
        parent={{ label: "Memories", href: "/memories" }}
        actions={
          <Button variant="outline" onClick={() => setEditOpen(true)}>
            <Pencil className="mr-2 size-4" />
            Edit
          </Button>
        }
      />
      <Card elevation="low">
        <CardHeader className="space-y-3 pb-3">
          <div className="flex flex-wrap items-center gap-2">
            <LifecycleBadge status={memory.status} />
            <span className="text-muted-foreground ml-auto font-mono text-sm">
              memory {memory.id.slice(0, 8)}
            </span>
          </div>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-base leading-relaxed">{memory.content}</p>
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
          <p className="text-sm font-semibold">Supersession lineage</p>
        </CardHeader>
        <CardContent>
          <SupersessionLineage memory={memory} />
        </CardContent>
      </Card>

      <Card elevation="low">
        <CardHeader className="pb-3">
          <p className="text-sm font-semibold">Per-memory timeline</p>
          <p className="text-muted-foreground text-sm">
            events by object — timestamp, event type, and the actor and API key
            each call was made under.
          </p>
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
    </div>
  )
}
