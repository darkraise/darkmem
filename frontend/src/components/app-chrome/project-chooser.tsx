import type { LucideIcon } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "@/components/darkmem"

export interface ChooserProject {
  name: string
  /** How much of this page's subject the project holds. */
  count: number
}

/** For pages that show one project at a time: under the all-projects scope
 *  they have nothing to render, so they offer the projects instead. A pick
 *  sets the same global scope the header switcher does. */
export function ProjectChooser({
  icon,
  heading,
  description,
  projects,
  noun,
  emptyTitle,
  emptyDescription,
  onChoose,
}: {
  icon: LucideIcon
  heading: string
  description: string
  projects: ChooserProject[]
  noun: { one: string; many: string }
  emptyTitle: string
  emptyDescription: string
  onChoose: (project: string) => void
}) {
  if (projects.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={icon}
        title={emptyTitle}
        description={emptyDescription}
      />
    )
  }
  return (
    <section
      aria-labelledby="project-chooser-title"
      className="border-border bg-card mx-auto w-full max-w-xl space-y-3 rounded-lg border p-5"
    >
      <h2 id="project-chooser-title" className="text-sm font-semibold">
        {heading}
      </h2>
      <p className="text-muted-foreground text-sm">{description}</p>
      <div className="flex flex-wrap gap-2">
        {projects.map((p) => (
          <Button key={p.name} variant="outline" onClick={() => onChoose(p.name)}>
            {p.name}
            <span className="text-muted-foreground ml-2 text-xs">
              {p.count} {p.count === 1 ? noun.one : noun.many}
            </span>
          </Button>
        ))}
      </div>
    </section>
  )
}
