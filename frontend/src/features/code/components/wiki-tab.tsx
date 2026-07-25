import { useEffect, useState } from "react"
import { BookOpen, FolderGit2, RefreshCw } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { cn } from "darkraise-ui/lib"
import { useDemoCodeRepos } from "@/demo/hooks"
import { ReindexDialog } from "./reindex-dialog"

// Read-only view over what a prior reindex generated: GET /code/wiki never
// triggers generation on browse — the empty state points at the reindex
// dialog's generate_wiki toggle, the only way a wiki gets built.
export function WikiTab({
  repoId,
  onRepoChange,
}: {
  repoId: string | undefined
  onRepoChange: (id: string) => void
}) {
  const repos = useDemoCodeRepos()
  const repo =
    repos.find((r) => r.id === repoId) ??
    repos.find((r) => r.wiki !== null) ??
    repos.find(() => true)
  const [activeSection, setActiveSection] = useState<string | null>(null)
  const [reindexOpen, setReindexOpen] = useState(false)

  useEffect(() => {
    setActiveSection(null)
  }, [repo?.id])

  if (!repo) return null
  const wiki = repo.wiki
  const currentSection =
    wiki?.sections.find((s) => s.id === activeSection) ??
    wiki?.sections.find(() => true)

  return (
    <div className="space-y-4">
      {/* repo picker — deliberately NOT the project switcher */}
      <div className="border-border bg-muted/25 flex flex-wrap items-center gap-2.5 rounded-md border border-dashed px-2.5 py-2">
        <Select value={repo.id} onValueChange={onRepoChange}>
          <SelectTrigger className="w-56" aria-label="Repository">
            <SelectValue>
              <span className="flex items-center gap-2">
                <FolderGit2 aria-hidden className="h-3.5 w-3.5" />
                <span className="text-muted-foreground font-mono text-[10px] uppercase">
                  repo
                </span>
                {repo.name}
              </span>
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {repos.map((r) => (
              <SelectItem key={r.id} value={r.id}>
                {r.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-muted-foreground font-mono text-sm">
          branch <b className="text-foreground font-semibold">{repo.branch}</b>
          {repo.head && (
            <>
              {" "}
              · HEAD <span className="font-mono">{repo.head}</span>
            </>
          )}
          {!wiki && repo.status === "ready" && <> · indexed, never wiki'd</>}
        </span>
        <span className="text-muted-foreground ml-auto text-sm italic">
          repo-scoped — not the project switcher
        </span>
      </div>

      {wiki && currentSection ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-[12rem_minmax(0,1fr)]">
          <nav
            className="border-border bg-card h-fit space-y-0.5 rounded-md border p-2"
            aria-label="Wiki contents"
          >
            <p className="text-muted-foreground px-1.5 pb-1 font-mono text-sm tracking-wide uppercase">
              Contents
            </p>
            {wiki.sections.map((section) => (
              <button
                key={section.id}
                type="button"
                onClick={() => setActiveSection(section.id)}
                className={cn(
                  "block w-full rounded-sm px-1.5 py-1 text-left text-sm",
                  section.id === currentSection.id
                    ? "bg-primary/12 text-primary font-medium"
                    : "text-muted-foreground hover:bg-muted/50",
                )}
              >
                {section.label}
              </button>
            ))}
          </nav>
          <div className="min-w-0 space-y-3">
            <p className="border-border text-muted-foreground border-b border-dashed pb-2 font-mono text-sm">
              generated{" "}
              <b className="text-foreground font-semibold">
                {wiki.generated_at}
              </b>{" "}
              · at <span className="font-mono">{wiki.head}</span> · symbol
              enrichment{" "}
              <b className="text-foreground font-semibold">
                {wiki.symbol_enrichment}
              </b>{" "}
              · module summaries{" "}
              <b className="text-foreground font-semibold">
                {wiki.module_summaries}
              </b>
            </p>
            <div className="space-y-2">
              <h3 className="text-sm font-semibold">{currentSection.label}</h3>
              {currentSection.paragraphs.map((paragraph, i) => (
                <p key={i} className="text-sm leading-relaxed">
                  {paragraph}
                </p>
              ))}
              {currentSection.bullets && (
                <ul className="text-muted-foreground list-disc space-y-1 pl-5 text-sm">
                  {currentSection.bullets.map((bullet) => (
                    <li key={bullet.code}>
                      <span className="text-foreground font-mono">
                        {bullet.code}
                      </span>{" "}
                      — {bullet.text}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>
        </div>
      ) : (
        <div className="border-border bg-card rounded-lg border">
          <EmptyState
            className="py-10"
            icon={<BookOpen aria-hidden className="h-6 w-6" />}
            title="No wiki generated yet for this repository"
            description={
              repo.status === "registered" || repo.last_indexed_at === null
                ? `${repo.name} has never been indexed, so there is no graph for a wiki to describe. Run a reindex with generate_wiki enabled — browsing this page never triggers generation.`
                : `This repo has been indexed (its code graph and symbols are current as of ${repo.head ?? "the last run"}), but generate_wiki has never been enabled on a reindex, so there is no generated documentation to read yet. GET /code/wiki is read-only — it never spends LLM budget just because a page was opened.`
            }
            action={
              <Button onClick={() => setReindexOpen(true)}>
                <RefreshCw aria-hidden className="mr-1.5 h-3.5 w-3.5" />
                Open reindex dialog
              </Button>
            }
          />
        </div>
      )}

      <ReindexDialog
        repo={repo}
        open={reindexOpen}
        onOpenChange={setReindexOpen}
        emphasizeWiki
      />
    </div>
  )
}
