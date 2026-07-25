import { useMemo, useState } from "react"
import { createFileRoute, Link } from "@tanstack/react-router"
import {
  ArrowLeft,
  ArrowRight,
  Brain,
  FileQuestion,
  Link2,
  Pencil,
} from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { useSetPageChrome } from "@/components/app-chrome"
import { useDemoMemories } from "@/demo/hooks"
import { deriveTimeline, distinctProjects } from "@/demo/memories"
import type { DemoMemory, MemoryTimelineEvent } from "@/demo/types"
import { VerificationBadge, type VerificationStatus } from "@/components/darkmem"
import { LifecycleBadge } from "@/features/memories/components/lifecycle-badge"
import { MemoryEditorDialog } from "@/features/memories/components/memory-editor-dialog"

export const Route = createFileRoute("/_authenticated/memories_/$memoryId")({
  component: MemoryDetailPage,
})

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  })
}

function Module({
  title,
  hint,
  children,
}: {
  title: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <section className="border-border space-y-2 border-t pt-4 first:border-t-0 first:pt-0">
      <h3 className="text-sm font-semibold">{title}</h3>
      {hint && <p className="text-muted-foreground text-sm">{hint}</p>}
      {children}
    </section>
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
      <Link2 aria-hidden className="text-muted-foreground h-3.5 w-3.5 shrink-0" />
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
          superseded_by: null — the successor memory was later removed; this
          row was demoted, not deleted.
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
    breadcrumbs: [{ label: "Memories", href: "/memories" }],
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
          icon={<FileQuestion aria-hidden className="h-6 w-6" />}
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
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2.5">
        <LifecycleBadge status={memory.status} />
        {memory.verification_status && (
          <VerificationBadge
            status={memory.verification_status}
            detail={memory.verification_detail}
          />
        )}
      </div>

      <div className="border-border bg-card space-y-4 rounded-lg border p-5">
        <Module title="Content">
          <div className="text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 font-mono text-sm">
            <span>
              id: <b className="text-foreground">{memory.id.slice(0, 8)}</b>
            </span>
            <span>
              project: <b className="text-foreground">{memory.project}</b>
            </span>
            <span>
              source: <b className="text-foreground">{memory.source}</b>
            </span>
            <span>
              status: <b className="text-foreground">{memory.status}</b>
            </span>
            <span>
              created:{" "}
              <b className="text-foreground">
                {formatDateTime(memory.created_at)}
              </b>
            </span>
            <span>
              confidence:{" "}
              <b className="text-foreground">{memory.confidence.toFixed(2)}</b>
            </span>
            {memory.applies_when && (
              <span>
                applies_when:{" "}
                <b className="text-foreground">{memory.applies_when}</b>
              </span>
            )}
          </div>
          <blockquote className="border-border bg-muted/25 rounded-r-md border-l-2 px-3.5 py-3 text-sm leading-relaxed">
            {memory.content}
          </blockquote>
        </Module>

        <Module title="Enrichment">
          <dl className="grid grid-cols-[8rem_1fr] gap-x-4 gap-y-1.5 text-sm">
            <dt className="text-muted-foreground font-mono">classified_type</dt>
            <dd>{memory.llm_classified_type ?? "— pending"}</dd>
            <dt className="text-muted-foreground font-mono">summary</dt>
            <dd>{memory.llm_summary ?? "—"}</dd>
            <dt className="text-muted-foreground font-mono">emotions</dt>
            <dd>
              {memory.llm_emotions?.length
                ? memory.llm_emotions.join(", ")
                : "—"}
            </dd>
            <dt className="text-muted-foreground font-mono">flags</dt>
            <dd className="flex flex-wrap gap-1.5">
              {memory.llm_flags?.length
                ? memory.llm_flags.map((flag) => (
                    <Badge
                      key={flag}
                      variant="outline"
                      size="sm"
                      className="border-warning/40 text-warning"
                    >
                      {flag}
                    </Badge>
                  ))
                : "none"}
            </dd>
          </dl>
        </Module>

        <Module title="technologies">
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
        </Module>

        <Module title="Supersession lineage">
          <SupersessionLineage memory={memory} successor={successor} />
        </Module>

        <Module title="Memory-relations">
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
                  <MemoryLink memoryId={rel.memory_id} excerpt={rel.excerpt} />
                </div>
              ))}
            </div>
          ) : (
            <p className="text-muted-foreground text-sm italic">
              no associative relations recorded yet
            </p>
          )}
        </Module>

        <Module
          title="Per-memory timeline"
          hint="events by object — timestamp, event-type chip, and (for transitions) the from→to rung pair."
        >
          <div>
            {timeline.map((event, i) => (
              <TimelineRow key={i} event={event} />
            ))}
          </div>
        </Module>
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
