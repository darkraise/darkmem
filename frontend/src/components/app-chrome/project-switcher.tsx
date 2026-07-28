import { useState } from "react"
import { Globe } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "darkraise-ui/components/popover"
import { useProjectStore } from "@/stores/project-store"

/**
 * The global isolation scope (doc 13 §3). Lives in the app chrome, writes
 * to `projectStore`, and every project-scoped query key (src/lib/
 * query-keys.ts) reads from that same store — switching here is what
 * makes Memories, Knowledge, Review, the timeline, the calendar and the
 * dashboard refetch against the new scope.
 *
 * A solid pill, deliberately styled distinctly from `ContextChip`'s dashed
 * one (Ruling 3): this control sets *scope*, never a session context hint.
 */
export function ProjectSwitcher() {
  const activeProject = useProjectStore((s) => s.activeProject)
  const knownProjects = useProjectStore((s) => s.knownProjects)
  const setProject = useProjectStore((s) => s.setProject)
  const [draft, setDraft] = useState("")
  const [open, setOpen] = useState(false)

  const switchTo = (project: string) => {
    setProject(project)
    setDraft("")
    setOpen(false)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <button
          type="button"
          aria-label="Project scope"
          className="border-border bg-muted hover:bg-muted/70 inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-sm transition-colors"
        >
          <Globe aria-hidden className="text-muted-foreground h-3.5 w-3.5" />
          project: {activeProject}
        </button>
      </PopoverTrigger>
      <PopoverContent
        side="bottom"
        align="end"
        className="bg-card border-border w-64 space-y-3 rounded-lg border p-3 shadow-xl"
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
        <form
          className="flex gap-1.5"
          onSubmit={(e) => {
            e.preventDefault()
            if (draft.trim()) switchTo(draft)
          }}
        >
          <Input
            aria-label="New project name"
            placeholder={activeProject}
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            groupClassName="flex-1"
          />
          <Button type="submit" size="sm" disabled={!draft.trim()}>
            Switch
          </Button>
        </form>
        {knownProjects.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {knownProjects.map((project) => (
              <Button
                key={project}
                type="button"
                size="sm"
                variant={project === activeProject ? "secondary" : "ghost"}
                onClick={() => switchTo(project)}
              >
                {project}
              </Button>
            ))}
          </div>
        )}
      </PopoverContent>
    </Popover>
  )
}
