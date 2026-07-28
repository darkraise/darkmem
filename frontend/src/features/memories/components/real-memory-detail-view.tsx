import { Link } from "@tanstack/react-router"
import { Brain, FileQuestion, Link2 } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import {
  Card,
  CardContent,
  CardHeader,
} from "darkraise-ui/components/card"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { Separator } from "darkraise-ui/components/separator"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import { useMemory, type Memory } from "@/hooks/api/use-memory-api"
import { LifecycleBadge } from "./lifecycle-badge"

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  })
}

function SuccessorLink({ memory }: { memory: Memory }) {
  return (
    <Link
      to="/memories/$memoryId"
      params={{ memoryId: memory.id }}
      className="hover:text-primary flex min-w-0 items-center gap-1.5 text-sm transition-colors"
    >
      <Link2 aria-hidden className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
      <span className="truncate">
        memory {memory.id.slice(0, 8)} — “{memory.content.slice(0, 80)}…”
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

/**
 * Forward direction (what replaced this memory) reads `superseded_by`
 * straight off the row and resolves it through `GET /memories/{id}` — an
 * ID-addressed read, so it reaches the successor regardless of the
 * successor's own status (content_surfaces.py's ID_ADDRESSED exemption).
 *
 * The reverse direction (what this memory replaced) has no backend query to
 * read: `MemorySearchRequest` carries no `superseded_by` filter and no
 * per-memory predecessor list exists on `MemoryResponse`. Deriving it by
 * paging through every superseded row in the project and matching
 * `superseded_by` client-side would be exactly the list-query
 * reconstruction the lineage surface must not do — a derived answer that
 * can silently drift from the database is worse than an honestly labelled
 * gap. This renders the gap instead of a guess.
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
              <SuccessorLink memory={successor.data} />
            ) : (
              <span className="text-muted-foreground text-sm italic">
                successor memory {memory.superseded_by.slice(0, 8)} could not
                be loaded
              </span>
            )}
          </div>
        ) : memory.status === "deprecated" ? (
          <div className="flex flex-wrap items-center gap-2.5">
            <LifecycleBadge status="deprecated" />
            <span className="text-muted-foreground text-sm italic">
              superseded_by: null — the successor memory was later removed;
              this row was demoted, not deleted.
            </span>
          </div>
        ) : (
          <p className="text-muted-foreground text-sm italic">
            not superseded — this is the current, active version of this
            memory; superseded_by is null.
          </p>
        )}
      </div>

      <Separator />

      <div>
        <SectionLabel>Replaced</SectionLabel>
        <p className="text-muted-foreground text-sm italic">
          Not shown — the API has no reverse lookup from a memory to the
          earlier memories it superseded (only the forward{" "}
          <code className="font-mono">superseded_by</code> pointer exists on
          each row). Rendering this honestly needs a backend query capability
          first; a client-side reconstruction from a list of superseded rows
          could disagree with the database.
        </p>
      </div>
    </div>
  )
}

export function RealMemoryDetailView({ memoryId }: { memoryId: string }) {
  const { data: memory, isLoading, isError } = useMemory(memoryId)

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
          icon={<FileQuestion aria-hidden className="h-6 w-6" />}
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
    </div>
  )
}
