import { createFileRoute, Link } from "@tanstack/react-router"
import { FolderKanban } from "lucide-react"
import { Card } from "darkraise-ui/components/card"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import { EmptyState } from "@/components/darkmem"
import { useProjects, type ProjectSummary } from "@/hooks/api"
import { relativeTime } from "@/lib/format"

export const Route = createFileRoute("/_authenticated/projects")({
  component: ProjectsIndexPage,
})

/** `last_event_day` is a UTC day string (YYYY-MM-DD), never a timestamp --
 *  the backend says so at the column. Feeding it to `relativeTime` would
 *  claim a precision the value does not carry. */
function dayLabel(day: string | null): string | null {
  if (!day) return null
  const today = new Date().toISOString().slice(0, 10)
  if (day === today) return "active today"
  const days = Math.round(
    (Date.parse(`${today}T00:00:00Z`) - Date.parse(`${day}T00:00:00Z`)) / 86_400_000,
  )
  return days === 1 ? "active yesterday" : `active ${days}d ago`
}

function Stat({ value, label }: { value: number; label: string }) {
  return (
    <span className="flex flex-col">
      <span className="text-lg font-semibold tabular-nums">{value}</span>
      <span className="text-muted-foreground font-mono text-xs tracking-wide uppercase">
        {label}
      </span>
    </span>
  )
}

function ProjectCard({ row }: { row: ProjectSummary }) {
  const activity = dayLabel(row.last_event_day)
  return (
    <Link
      to="/projects/$project"
      params={{ project: row.name }}
      // The workspace validates `tab`, so the link has to name one. Landing
      // on Artifacts is the default the route itself falls back to.
      search={{ tab: "artifacts" as const }}
    >
      <Card className="hover:border-primary/45 h-full space-y-3 p-4 transition-colors">
        <p className="truncate text-sm font-semibold">{row.name}</p>
        <div className="flex gap-5">
          <Stat value={row.memory_count} label="memories" />
          <Stat value={row.document_count} label="documents" />
          <Stat value={row.workstream_count} label="workstreams" />
        </div>
        <p className="text-muted-foreground text-sm">
          {row.last_worklog_at
            ? `last work-log entry ${relativeTime(row.last_worklog_at)}`
            : "no work log yet"}
          {activity ? ` · ${activity}` : ""}
        </p>
      </Card>
    </Link>
  )
}

function ProjectsIndexPage() {
  const { data, isLoading, isError } = useProjects()
  // The notes space has its own route and its own workspace; offering it
  // here would open it in a surface built for project artifacts.
  const rows = (data ?? []).filter((row) => row.kind !== "personal")

  return (
    <div className="space-y-4">
      <PageChrome
        icon={FolderKanban}
        title="Projects"
        description="Every project the corpus holds — memories, documents and work logs."
      />
      {isError ? (
        // Not the empty state: "no project holds anything yet" is a claim
        // about the corpus, and on a failed read it is a false one.
        <p className="text-destructive text-sm">
          Projects could not be loaded — a failed read, not an empty corpus.
        </p>
      ) : isLoading ? (
        <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2 xl:grid-cols-3">
          {[0, 1, 2].map((i) => (
            <Skeleton key={i} className="h-32 w-full" />
          ))}
        </div>
      ) : rows.length === 0 ? (
        <EmptyState
          kind="empty"
          icon={FolderKanban}
          title="No project holds anything yet"
          description="A project appears here as soon as a memory, document or workstream carries its name."
        />
      ) : (
        <div className="grid grid-cols-1 gap-3.5 md:grid-cols-2 xl:grid-cols-3">
          {rows.map((row) => (
            <ProjectCard key={row.name} row={row} />
          ))}
        </div>
      )}
    </div>
  )
}
