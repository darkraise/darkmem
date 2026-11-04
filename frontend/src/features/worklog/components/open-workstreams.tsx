import { useMemo } from "react"
import { Link } from "@tanstack/react-router"
import { ScrollText } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { EmptyState, listItemClass } from "@/components/darkmem"
import { ModuleSurface } from "@/features/activity/components/module-surface"
import {
  useProjects,
  useWorklogResume,
  useWorkstreams,
  type WorklogEntry,
  type Workstream,
} from "@/hooks/api"
import { formatWhen } from "@/lib/format"
import { firstLine } from "./entry-timeline"

/** The newest of what resume carries: the checkpoint, the notes and the
 *  ledger tail are each bounded, and the newest entry is among them. */
function latestEntry(resume: {
  checkpoint: WorklogEntry | null
  notes: WorklogEntry[]
  ledger: WorklogEntry[]
}): WorklogEntry | null {
  const candidates = [resume.checkpoint, ...resume.notes, ...resume.ledger].filter(
    (e): e is WorklogEntry => e !== null,
  )
  return candidates.reduce<WorklogEntry | null>(
    (newest, e) => (newest === null || e.seq > newest.seq ? e : newest),
    null,
  )
}

function OpenWorkstreamRow({ workstream }: { workstream: Workstream }) {
  const resume = useWorklogResume(workstream.project, workstream.key)
  const latest = resume.data ? latestEntry(resume.data) : null
  let summary = "no entry yet"
  if (latest) summary = `${latest.kind}: ${firstLine(latest.body)}`
  else if (resume.isPending) summary = "…"
  else if (resume.isError) summary = "could not read the latest entry"

  return (
    <Link
      to="/projects/$project"
      params={{ project: workstream.project }}
      search={{ tab: "progress", workstream: workstream.key }}
      className={listItemClass({
        interactive: true,
        className: "bg-card flex flex-wrap items-center gap-2.5 p-3",
      })}
    >
      <ScrollText aria-hidden className="text-primary-text h-4 w-4 shrink-0" />
      <span className="flex min-w-0 flex-1 basis-56 flex-col gap-0.5">
        <span className="text-sm font-semibold">{workstream.title ?? workstream.key}</span>
        <span className="text-muted-foreground font-mono text-xs">
          {workstream.project} · {workstream.key}
        </span>
      </span>
      <span className="text-muted-foreground min-w-0 flex-1 basis-56 truncate text-sm">
        {summary}
      </span>
      <span className="text-muted-foreground font-mono text-sm whitespace-nowrap">
        {formatWhen(workstream.last_entry_at)}
      </span>
    </Link>
  )
}

function ProjectOpenWorkstreams({ project }: { project: string }) {
  const open = useWorkstreams(project, "open")
  const items = useMemo(
    () => open.data?.pages.flatMap((page) => page.items) ?? [],
    [open.data],
  )
  if (open.isError) {
    return (
      <p className="text-destructive-text text-sm">
        Could not read {project}'s work log: {open.error.message}
      </p>
    )
  }
  return (
    <>
      {items.map((w) => (
        <OpenWorkstreamRow key={w.id} workstream={w} />
      ))}
      {open.hasNextPage ? (
        <Button
          variant="ghost"
          size="sm"
          disabled={open.isFetchingNextPage}
          onClick={() => void open.fetchNextPage()}
        >
          More open workstreams in {project}
        </Button>
      ) : null}
    </>
  )
}

/** Every project's open workstreams (spec §8). There is no cross-project list
 *  route, so the project catalogue names the projects worth asking. */
export function OpenWorkstreams() {
  const projects = useProjects()
  const withOpen = (projects.data ?? []).filter(
    (p) => p.kind !== "personal" && p.open_workstream_count > 0,
  )

  if (projects.isError) {
    return (
      <EmptyState
        kind="failed"
        title="Could not read the project catalogue"
        description={projects.error.message}
      />
    )
  }
  if (projects.isPending) return <Skeleton className="h-32 w-full" />
  if (withOpen.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={ScrollText}
        title="No open workstreams"
        description="A workstream appears here when a coding client starts logging work, until it is closed."
      />
    )
  }
  return (
    <ModuleSurface
      title="Open workstreams"
      state="populated"
      meta={`${withOpen.length} ${withOpen.length === 1 ? "project" : "projects"}`}
    >
      {withOpen.map((p) => (
        <ProjectOpenWorkstreams key={p.name} project={p.name} />
      ))}
    </ModuleSurface>
  )
}
