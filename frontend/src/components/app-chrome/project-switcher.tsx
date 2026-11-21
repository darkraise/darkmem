import { useEffect, useState } from "react"
import { Globe, Globe2, Check } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "darkraise-ui/components/popover"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import { cn } from "darkraise-ui/lib"
import { EmptyState } from "@/components/darkmem"
import { useProjects, type ProjectSummary } from "@/hooks/api"
import {
  ALL_PROJECTS,
  STALE_SCOPE_NOTICE,
  projectLabel,
  useProjectStore,
  type ProjectScope,
} from "@/stores/project-store"

export const CODE_SCOPE_REASON = "Code is scoped by repository, not by project"
export const WORKSPACE_SCOPE_REASON =
  "This workspace shows the project named in its address"
export const NOTES_SCOPE_REASON =
  "Notes are your personal space, outside any project"

/** Routes whose subject is fixed by something other than the scope -- a
 *  repository, the project in the URL, the personal space -- where a live
 *  scope would read as a filter that silently does nothing. */
export function projectScopeDisabledReason(
  pathname: string,
): string | undefined {
  if (pathname === "/code" || pathname.startsWith("/code/")) {
    return CODE_SCOPE_REASON
  }
  // `/projects/<name>` only: the `/projects` card grid lists every project
  // and stays scope-free without needing the chip disabled.
  if (/^\/projects\/[^/]+/.test(pathname)) return WORKSPACE_SCOPE_REASON
  if (pathname === "/notes" || pathname.startsWith("/notes/")) {
    return NOTES_SCOPE_REASON
  }
  return undefined
}

const TRIGGER_CLASS =
  "border-border bg-muted hover:bg-muted/70 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm transition-colors"

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
 * offered once a memory, document, workstream or page carries it. There is no free-text field: a
 * project comes into existence by being captured into, so a name typed here
 * would switch every project-scoped view to a scope guaranteed to be empty,
 * which reads as a broken filter rather than as a new project.
 */
/** Items across all four corpora. A document-only project -- which the
 *  corpus import creates -- would read as broken under a memories-only
 *  count, showing "0 memories" for a scope that holds a hundred files. */
function itemHint(row: ProjectSummary): string {
  const total =
    row.memory_count +
    row.document_count +
    row.workstream_count +
    row.page_count
  return `${total} ${total === 1 ? "item" : "items"}`
}

/** Widens a persisted scope the corpus no longer holds. Mounted once in the
 *  authenticated layout rather than inside the switcher, because below `md`
 *  the switcher lives in a popover that is not mounted until opened. */
export function ProjectScopeReconciler() {
  const { data, isSuccess } = useProjects()
  const reconcile = useProjectStore((s) => s.reconcile)

  useEffect(() => {
    if (!isSuccess || !data) return
    reconcile(data.filter((p) => p.kind !== "personal").map((p) => p.name))
  }, [data, isSuccess, reconcile])

  return null
}

export function ProjectSwitcher({
  disabledReason,
}: {
  disabledReason?: string
}) {
  const activeProject = useProjectStore((s) => s.activeProject)
  const setProject = useProjectStore((s) => s.setProject)
  const missingProject = useProjectStore((s) => s.missingProject)
  const projectsQuery = useProjects()
  const [open, setOpen] = useState(false)

  const switchTo = (project: ProjectScope) => {
    setProject(project)
    setOpen(false)
  }

  const rows = (projectsQuery.data ?? []).filter((p) => p.kind !== "personal")
  const isAll = activeProject === ALL_PROJECTS

  if (disabledReason) {
    return (
      <TooltipProvider delayDuration={150}>
        <Tooltip>
          <TooltipTrigger asChild>
            {/* A disabled button receives no pointer events, so the wrapper
                carries the hover and the focus that open the tooltip. */}
            <span
              role="group"
              tabIndex={0}
              aria-label={`Project scope — ${disabledReason}`}
              className="inline-flex rounded-full"
            >
              <button
                type="button"
                disabled
                aria-label="Project scope"
                className={cn(TRIGGER_CLASS, "pointer-events-none opacity-60")}
              >
                <Globe
                  aria-hidden
                  className="text-muted-foreground h-3.5 w-3.5"
                />
                project: {projectLabel(activeProject)}
              </button>
            </span>
          </TooltipTrigger>
          <TooltipContent>{disabledReason}</TooltipContent>
        </Tooltip>
      </TooltipProvider>
    )
  }

  return (
    <span className="inline-flex items-center gap-2">
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <button
            type="button"
            aria-label="Project scope"
            className={TRIGGER_CLASS}
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
          <p className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
            Switch project
          </p>

          <div className="max-h-64 space-y-0.5 overflow-y-auto">
            <ScopeRow
              label="All projects"
              hint="all scopes"
              icon={Globe2}
              active={isAll}
              onSelect={() => switchTo(ALL_PROJECTS)}
            />

            {projectsQuery.isPending ? (
              <div className="space-y-1 py-1">
                <Skeleton className="h-8 w-full rounded-md" />
                <Skeleton className="h-8 w-full rounded-md" />
              </div>
            ) : projectsQuery.isError && !projectsQuery.data ? (
              <EmptyState
                kind="failed"
                className="py-4"
                title="Projects could not be loaded"
                action={
                  <Button size="sm" onClick={() => projectsQuery.refetch()}>
                    Retry
                  </Button>
                }
              />
            ) : rows.length === 0 ? (
              <p className="text-muted-foreground px-2 py-3 text-center text-xs">
                No project holds anything yet.
              </p>
            ) : (
              rows.map((row) => (
                <ScopeRow
                  key={row.name}
                  label={row.name}
                  hint={itemHint(row)}
                  active={activeProject === row.name}
                  onSelect={() => switchTo(row.name)}
                />
              ))
            )}
          </div>
        </PopoverContent>
      </Popover>
      {missingProject && (
        <span
          role="status"
          className="text-muted-foreground text-xs whitespace-nowrap"
        >
          {STALE_SCOPE_NOTICE}
        </span>
      )}
    </span>
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
      {/* The label wins the row: the hint shrinks (and truncates) four times
          faster, so "All projects" is no longer cut to "All pr…" by its own
          hint in the 288px popover. */}
      <span className="min-w-0 flex-auto truncate">{label}</span>
      <span className="text-muted-foreground/70 min-w-0 shrink-[4] truncate text-xs">
        {hint}
      </span>
      {active && (
        <Check aria-hidden className="text-primary-text h-3.5 w-3.5 shrink-0" />
      )}
    </button>
  )
}
