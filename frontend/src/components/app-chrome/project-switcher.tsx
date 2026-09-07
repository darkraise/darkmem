import { useState } from "react"
import { Globe, Globe2, Check } from "lucide-react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "darkraise-ui/components/popover"
import { cn } from "darkraise-ui/lib"
import { useProjects, type ProjectSummary } from "@/hooks/api"
import {
  ALL_PROJECTS,
  projectLabel,
  useProjectStore,
  type ProjectScope,
} from "@/stores/project-store"

/**
 * The global isolation scope (doc 13 §3). Lives in the app chrome, writes
 * to `projectStore`, and every project-scoped query key (src/lib/
 * query-keys.ts) reads from that same store — switching here is what
 * makes Memories, Knowledge, Review, the timeline, the calendar and the
 * dashboard refetch against the new scope.
 *
 * A solid pill, deliberately styled distinctly from `ContextChip`'s dashed
 * one (Ruling 3): this control sets *scope*, never a session context hint.
 *
 * The list is exactly the corpus's own (`GET /api/v1/projects`) — a scope is
 * offered once a memory, document or checkpoint carries it. There is no free-text field: a
 * project comes into existence by being captured into, so a name typed here
 * would switch every project-scoped view to a scope guaranteed to be empty,
 * which reads as a broken filter rather than as a new project.
 */
/** Items across all three corpora. A document-only project -- which the
 *  corpus import creates -- would read as broken under a memories-only
 *  count, showing "0 memories" for a scope that holds a hundred files. */
function itemHint(row: ProjectSummary): string {
  const total = row.memory_count + row.document_count + row.checkpoint_count
  return `${total} ${total === 1 ? "item" : "items"}`
}

export function ProjectSwitcher() {
  const activeProject = useProjectStore((s) => s.activeProject)
  const setProject = useProjectStore((s) => s.setProject)
  const { data: projects, isLoading } = useProjects()
  const [open, setOpen] = useState(false)

  const switchTo = (project: ProjectScope) => {
    setProject(project)
    setOpen(false)
  }

  const rows = (projects ?? []).filter((p) => p.kind !== "personal")
  const isAll = activeProject === ALL_PROJECTS

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="Project scope"
          className="border-border bg-muted hover:bg-muted/70 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm transition-colors"
        >
          <Globe aria-hidden className="text-muted-foreground h-3.5 w-3.5" />
          project: {projectLabel(activeProject)}
        </button>
      </PopoverTrigger>
      <PopoverContent
        side="bottom"
        align="end"
        className="bg-card border-border w-72 space-y-3 rounded-lg border p-3 shadow-xl"
      >
        <div className="space-y-1.5">
          <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
            Switch project
          </p>
          <p className="text-muted-foreground text-xs">
            The isolation scope — every project-scoped view refetches against
            it. This is not a context declaration.
          </p>
        </div>

        <div className="max-h-64 space-y-0.5 overflow-y-auto">
          <ScopeRow
            label="All projects"
            hint="every scope at once"
            icon={Globe2}
            active={isAll}
            onSelect={() => switchTo(ALL_PROJECTS)}
          />

          {isLoading && (
            <div className="space-y-1 py-1">
              <Skeleton className="h-8 w-full rounded-md" />
              <Skeleton className="h-8 w-full rounded-md" />
            </div>
          )}

          {!isLoading &&
            rows.map((row) => (
              <ScopeRow
                key={row.name}
                label={row.name}
                hint={itemHint(row)}
                active={activeProject === row.name}
                onSelect={() => switchTo(row.name)}
              />
            ))}

          {!isLoading && rows.length === 0 && (
            <p className="text-muted-foreground px-2 py-3 text-center text-xs">
              No project holds anything yet.
            </p>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}

function ScopeRow({
  label,
  hint,
  icon: Icon,
  active,
  onSelect,
}: {
  label: string
  hint: string
  icon?: typeof Globe2
  active: boolean
  onSelect: () => void
}) {
  return (
    <button
      type="button"
      aria-pressed={active}
      onClick={onSelect}
      className={cn(
        "flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-sm transition-colors",
        active
          ? "bg-primary/10 text-foreground"
          : "text-muted-foreground hover:bg-muted/50 hover:text-foreground",
      )}
    >
      {Icon && <Icon aria-hidden className="h-3.5 w-3.5 shrink-0" />}
      <span className="min-w-0 flex-1 truncate">{label}</span>
      <span className="text-muted-foreground/70 shrink-0 text-xs">{hint}</span>
      {active && <Check aria-hidden className="text-primary h-3.5 w-3.5 shrink-0" />}
    </button>
  )
}
