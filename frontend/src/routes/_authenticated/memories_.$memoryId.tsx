import { useMemo, useState } from "react"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft, ArrowRight, Brain, Link2, Pencil } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { EmptyState } from "@/components/darkmem"
import { Separator } from "darkraise-ui/components/separator"
import { useSetPageChrome } from "@/components/app-chrome"
import { DEMO } from "@/lib/demo-flag"
import { useDemoMemories } from "@/demo/hooks"
import { deriveTimeline, distinctProjects } from "@/demo/memories"
import type { DemoMemory, MemoryTimelineEvent } from "@/features/memories/types"
import {
  VerificationBadge,
  type VerificationStatus,
} from "@/components/darkmem"
import { LifecycleBadge } from "@/features/memories/components/lifecycle-badge"
import { MemoryEditorDialog } from "@/features/memories/components/memory-editor-dialog"
import { RealMemoryDetailView } from "@/features/memories/components/real-memory-detail-view"

// DEMO is fixed for the process lifetime (import.meta.env, not runtime
// state), so branching at the component level never violates the rules of
// hooks — mirrors the /memories list route's DEMO ? demo : real split
// (real-memories-view.tsx). The demo page keeps its own store-backed
// lineage rendering untouched; RealMemoryDetailView is the real-backend
// rebuild this task owns.
export const Route = createFileRoute("/_authenticated/memories_/$memoryId")({
  component: () => (DEMO ? <MemoryDetailPage /> : <RealMemoryDetailRoute />),
})

function RealMemoryDetailRoute() {
  const { memoryId } = Route.useParams()
  return <RealMemoryDetailView memoryId={memoryId} />
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  })
}

function SectionCard({
  title,
  hint,
  children,
}: {
  title: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">{title}</CardTitle>
        {hint && <CardDescription className="text-sm">{hint}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-2">{children}</CardContent>
    </Card>
  )
}

const LADDER: VerificationStatus[] = [
  "candidate",
  "corroborated",
  "confirmed",
  "disputed",
  "superseded",
]

// A rung-pair side: a real badge when the wire carries one, a plain label
// otherwise — never a fabricated pill.
function RungLabel({ value }: { value: string | null }) {
  if (!value || value === "active") {
    return (
      <span className="text-muted-foreground text-sm">active (no badge)</span>
    )
  }
  if ((LADDER as string[]).includes(value)) {
    return <VerificationBadge status={value as VerificationStatus} />
  }
  return (
    <Badge
      variant="outline"
      size="sm"
      className="border-warning/50 bg-warning/10 text-warning"
    >
      {value}
    </Badge>
  )
}

function TimelineRow({ event }: { event: MemoryTimelineEvent }) {
  return (
    <div className="border-border flex flex-wrap items-start gap-2.5 border-t border-dashed py-2.5 first:border-t-0 first:pt-0">
      <span className="text-muted-foreground w-40 shrink-0 pt-0.5 font-mono text-sm">
        {formatDateTime(event.at)}
      </span>
      <Badge variant="outline" size="sm" className="shrink-0 font-mono">
        {event.kind}
      </Badge>
      <div className="min-w-52 flex-1 space-y-1">
        <p className="text-sm">{event.description}</p>
        {event.transition && (
          <span className="flex items-center gap-2">
            <RungLabel value={event.transition.from} />
            <ArrowRight
              aria-hidden
              className="text-muted-foreground h-3.5 w-3.5"
            />
            <RungLabel value={event.transition.to} />
          </span>
        )}
        {event.note && (
          <p className="text-muted-foreground text-sm">{event.note}</p>
        )}
      </div>
    </div>
  )
}

function MemoryLink({
  memoryId,
  excerpt,
}: {
  memoryId: string
  excerpt: string
}) {
  return (
    <Link
      to="/memories/$memoryId"
      params={{ memoryId }}
      className="hover:text-primary flex min-w-0 items-center gap-1.5 text-sm transition-colors"
    >
      <Link2
        aria-hidden
        className="text-muted-foreground h-3.5 w-3.5 shrink-0"
      />
      <span className="truncate">
        memory {memoryId.slice(0, 8)} — “{excerpt}”
      </span>
    </Link>
  )
}

function SupersessionLineage({
  memory,
  successor,
}: {
  memory: DemoMemory
  successor?: DemoMemory
}) {
  if (memory.status === "superseded") {
    return (
      <div className="flex flex-wrap items-center gap-2.5">
        <LifecycleBadge status="superseded" />
        {memory.superseded_by ? (
          <MemoryLink
            memoryId={memory.superseded_by}
            excerpt={
              successor
                ? `${successor.content.slice(0, 80)}…`
                : "successor memory"
            }
          />
        ) : (
          <span className="text-muted-foreground text-sm italic">
            successor pointer missing
          </span>
        )}
      </div>
    )
  }
  if (memory.status === "deprecated") {
    return (
      <div className="flex flex-wrap items-center gap-2.5">
        <LifecycleBadge status="deprecated" />
        <span className="text-muted-foreground text-sm italic">
          superseded_by: null — the successor memory was later removed; this row
          was demoted, not deleted.
        </span>
      </div>
    )
  }
  return (
    <p className="text-muted-foreground text-sm italic">
      not superseded — this is the current, active version of this memory;
      superseded_by is null.
    </p>
  )
}

function MetaRow({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <>
      <dt className="text-muted-foreground font-mono">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </>
  )
}

function MemoryDetailPage() {
  const { memoryId } = Route.useParams()
  const memories = useDemoMemories()
  const memory = memories.find((m) => m.id === memoryId)
  const successor = memory?.superseded_by
    ? memories.find((m) => m.id === memory.superseded_by)
    : undefined
  const projects = useMemo(() => distinctProjects(memories), [memories])
  const [editOpen, setEditOpen] = useState(false)

  useSetPageChrome({
    icon: Brain,
    title: "Memory detail",
    description: "One memory, its enrichment, and its lineage.",
    parent: { label: "Memories", href: "/memories" },
    actions: memory ? (
      <Button variant="outline" size="sm" onClick={() => setEditOpen(true)}>
        <Pencil className="mr-2 size-4" />
        Edit
      </Button>
    ) : undefined,
  })

  if (!memory) {
    return (
      <div>
        <EmptyState
          kind="missing"
          scope="page"
          title="Memory not found"
          description="This memory does not exist in the demo store — it may have been deleted."
          action={
            <Button variant="outline" asChild>
              <Link to="/memories">
                <ArrowLeft className="mr-2 size-4" />
                Back to Memories
              </Link>
            </Button>
          }
        />
      </div>
    )
  }

  const timeline = deriveTimeline(memory)

  return (
    <div className="mx-auto max-w-6xl">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_19rem] lg:items-start">
        {/* main column — the memory content is the hero */}
        <div className="min-w-0 space-y-4">
          <Card elevation="low">
            <CardHeader className="space-y-3 pb-3">
              <div className="flex flex-wrap items-center gap-2">
                <LifecycleBadge status={memory.status} />
                {memory.verification_status && (
                  <VerificationBadge
                    status={memory.verification_status}
                    detail={memory.verification_detail}
                  />
                )}
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
                  via{" "}
                  <b className="text-foreground font-medium">{memory.source}</b>
                </span>
                <span>
                  project{" "}
                  <b className="text-foreground font-medium">
                    {memory.project}
                  </b>
                </span>
                <span>
                  confidence{" "}
                  <b className="text-foreground font-medium">
                    {memory.confidence.toFixed(2)}
                  </b>
                </span>
              </div>
            </CardContent>
          </Card>

          <SectionCard title="Memory-relations">
            {memory.relations?.length ? (
              <div className="space-y-1.5">
                {memory.relations.map((rel) => (
                  <div
                    key={`${rel.rel_type}-${rel.memory_id}`}
                    className="border-border flex flex-wrap items-center gap-2.5 rounded-md border p-2.5"
                  >
                    <Badge
                      variant="secondary"
                      size="sm"
                      className="shrink-0 font-mono tracking-wide uppercase"
                    >
                      {rel.rel_type}
                    </Badge>
                    <MemoryLink
                      memoryId={rel.memory_id}
                      excerpt={rel.excerpt}
                    />
                  </div>
                ))}
              </div>
            ) : (
              <p className="text-muted-foreground text-sm italic">
                no associative relations recorded yet
              </p>
            )}
          </SectionCard>

          <SectionCard
            title="Per-memory timeline"
            hint="events by object — timestamp, event-type chip, and (for transitions) the from→to rung pair."
          >
            <div>
              {timeline.map((event, i) => (
                <TimelineRow key={i} event={event} />
              ))}
            </div>
          </SectionCard>
        </div>

        {/* aside — the record's metadata and lineage, well out of the way */}
        <div className="space-y-4">
          <SectionCard title="Record">
            <dl className="grid grid-cols-[7rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
              <MetaRow label="id">{memory.id.slice(0, 8)}</MetaRow>
              <MetaRow label="project">{memory.project}</MetaRow>
              <MetaRow label="source">{memory.source}</MetaRow>
              <MetaRow label="status">{memory.status}</MetaRow>
              <MetaRow label="created">
                {formatDateTime(memory.created_at)}
              </MetaRow>
              <MetaRow label="confidence">
                {memory.confidence.toFixed(2)}
              </MetaRow>
              {memory.applies_when && (
                <MetaRow label="applies_when">{memory.applies_when}</MetaRow>
              )}
            </dl>
          </SectionCard>

          <SectionCard title="Enrichment">
            <dl className="grid grid-cols-[7rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
              <MetaRow label="classified_type">
                {memory.classified_type ?? "— pending"}
              </MetaRow>
              <MetaRow label="summary">{memory.summary ?? "—"}</MetaRow>
              <MetaRow label="emotions">
                {memory.emotions?.length ? memory.emotions.join(", ") : "—"}
              </MetaRow>
              <MetaRow label="flags">
                {memory.flags?.length ? (
                  <span className="flex flex-wrap gap-1.5">
                    {memory.flags.map((flag) => (
                      <Badge
                        key={flag}
                        variant="outline"
                        size="sm"
                        className="border-warning/40 text-warning"
                      >
                        {flag}
                      </Badge>
                    ))}
                  </span>
                ) : (
                  "none"
                )}
              </MetaRow>
            </dl>
          </SectionCard>

          <SectionCard title="technologies">
            {memory.technologies?.length ? (
              <div className="flex flex-wrap gap-1.5">
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
              </div>
            ) : (
              <p className="text-muted-foreground text-sm italic">
                none recorded
              </p>
            )}
          </SectionCard>

          <SectionCard title="Supersession lineage">
            <SupersessionLineage memory={memory} successor={successor} />
          </SectionCard>
        </div>
      </div>

      <MemoryEditorDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        memory={memory}
        projects={projects}
      />
    </div>
  )
}
