import { useMemo, useState } from "react"
import { Link } from "@tanstack/react-router"
import {
  ArrowRight,
  ChevronLeft,
  ChevronRight,
  FolderGit2,
  RefreshCw,
  BookOpen,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { EmptyState } from "@/components/darkmem"
import { cn } from "darkraise-ui/lib"
import { useDemoCodeRepos, useDemoCodeGraph } from "@/demo/hooks"
import type { DemoWikiSection } from "@/demo/types"
import {
  buildWikiLinkIndex,
  collectTargets,
  type ProseSegment,
  type WikiCodeTarget,
} from "../lib/wiki-links"
import { ReindexDialog } from "./reindex-dialog"

/** Every code reference is a live link into the graph for this repo. */
function CodeRef({
  target,
  repoId,
  className,
}: {
  target: WikiCodeTarget
  repoId: string
  className?: string
}) {
  return (
    <Link
      to="/code/graph"
      search={{
        repo: repoId,
        ...(target.symbolId ? { symbol: target.symbolId } : {}),
        ...(target.file ? { file: target.file } : {}),
      }}
      className={cn(
        "border-border bg-muted/40 hover:border-primary/50 hover:text-primary-text rounded border px-1 py-px font-mono text-[0.85em] transition-colors",
        className,
      )}
      title={`Open ${target.text} in the code graph`}
    >
      {target.text}
    </Link>
  )
}

function Prose({
  segments,
  repoId,
  className,
}: {
  segments: ProseSegment[]
  repoId: string
  className?: string
}) {
  return (
    <p className={className}>
      {segments.map((segment, i) =>
        segment.type === "text" ? (
          <span key={i}>{segment.text}</span>
        ) : (
          <CodeRef key={i} target={segment.target} repoId={repoId} />
        ),
      )}
    </p>
  )
}

function ProvenanceStat({
  label,
  value,
  note,
  tone = "neutral",
}: {
  label: string
  value: string
  note?: string
  tone?: "neutral" | "warn"
}) {
  return (
    <div className="bg-card px-3.5 py-2.5">
      <p className="text-muted-foreground font-mono text-xs tracking-[0.18em] uppercase">
        {label}
      </p>
      <p className="mt-1 font-mono text-sm font-semibold">{value}</p>
      {note && (
        <p
          className={cn(
            "mt-0.5 text-xs",
            tone === "warn" ? "text-warning-text" : "text-muted-foreground",
          )}
        >
          {note}
        </p>
      )}
    </div>
  )
}

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
  const graph = useDemoCodeGraph(repo?.id)
  // Keyed by repo so switching repos falls back to the first section
  // without an effect that resets it after a render on the wrong wiki.
  const [activeSection, setActiveSection] = useState<{
    repo: string
    id: string
  } | null>(null)
  const [reindexOpen, setReindexOpen] = useState(false)

  const links = useMemo(
    () => buildWikiLinkIndex(repo?.files ?? [], graph),
    [repo?.files, graph],
  )

  const wiki = repo?.wiki ?? null
  const sections: DemoWikiSection[] = wiki?.sections ?? []
  const index = Math.max(
    0,
    activeSection && activeSection.repo === repo?.id
      ? sections.findIndex((s) => s.id === activeSection.id)
      : 0,
  )
  const currentSection = sections[index]

  const paragraphs = useMemo(
    () => (currentSection?.paragraphs ?? []).map(links.linkify),
    [currentSection, links],
  )
  const referenced = useMemo(() => {
    const fromBullets = (currentSection?.bullets ?? []).map((b) =>
      links.resolve(b.code),
    )
    const fromProse = collectTargets(paragraphs)
    const seen = new Set<string>()
    return [...fromBullets, ...fromProse].filter((target) => {
      const key = target.symbolId ?? target.file ?? target.text
      if (seen.has(key)) return false
      seen.add(key)
      return true
    })
  }, [currentSection, paragraphs, links])

  if (!repo) return null

  const behindHead =
    wiki !== null && repo.head !== null && wiki.head !== repo.head

  return (
    <div className="space-y-4">
      <header className="border-border bg-card overflow-hidden rounded-lg border">
        <div className="border-border flex flex-wrap items-center gap-2.5 border-b px-3 py-2.5">
          <Select value={repo.id} onValueChange={onRepoChange}>
            <SelectTrigger className="w-56" aria-label="Repository">
              <SelectValue>
                <span className="flex items-center gap-2">
                  <FolderGit2 aria-hidden className="h-3.5 w-3.5" />
                  <span className="text-muted-foreground font-mono text-xs uppercase">
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
            branch{" "}
            <b className="text-foreground font-semibold">{repo.branch}</b>
            {repo.head && (
              <>
                {" "}
                · HEAD <span className="font-mono">{repo.head}</span>
              </>
            )}
          </span>
        </div>

        {wiki && (
          <div className="bg-border grid gap-px sm:grid-cols-2">
            <ProvenanceStat label="generated" value={wiki.generated_at} />
            <ProvenanceStat
              label="commit"
              value={wiki.head}
              note={
                behindHead ? `repo has moved to ${repo.head} since` : undefined
              }
              tone={behindHead ? "warn" : "neutral"}
            />
          </div>
        )}
      </header>

      {wiki && currentSection ? (
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[13rem_minmax(0,1fr)]">
          {/* contents — a spine, so position in the document is legible */}
          <nav className="top-2 h-fit lg:sticky" aria-label="Wiki contents">
            <p className="text-muted-foreground mb-2 font-mono text-xs tracking-[0.18em] uppercase">
              Contents
            </p>
            <ol className="border-border ml-[3px] border-l">
              {sections.map((section) => {
                const active = section.id === currentSection.id
                return (
                  <li key={section.id} className="relative">
                    <button
                      type="button"
                      onClick={() =>
                        setActiveSection({ repo: repo.id, id: section.id })
                      }
                      aria-current={active ? "true" : undefined}
                      className={cn(
                        "group flex w-full items-center py-1.5 pl-4 text-left text-sm transition-colors",
                        active
                          ? "text-foreground font-medium"
                          : "text-muted-foreground hover:text-foreground",
                      )}
                    >
                      <span
                        aria-hidden
                        className={cn(
                          "absolute top-1/2 -left-[4px] h-[7px] w-[7px] -translate-y-1/2 rounded-full border transition-colors",
                          active
                            ? "border-primary bg-primary"
                            : "border-border bg-background group-hover:border-primary/60",
                        )}
                      />
                      <span className="truncate">{section.label}</span>
                    </button>
                  </li>
                )
              })}
            </ol>
          </nav>

          <article className="min-w-0">
            <p className="text-muted-foreground font-mono text-xs tracking-[0.18em] uppercase">
              Section {index + 1} of {sections.length}
            </p>
            <h2 className="mt-1.5 text-2xl font-semibold tracking-tight">
              {currentSection.label}
            </h2>
            <div className="border-border mt-3 border-t" />

            <div className="mt-4 max-w-[70ch] space-y-4">
              {paragraphs.map((segments, i) => (
                <Prose
                  key={i}
                  segments={segments}
                  repoId={repo.id}
                  className={cn(
                    "leading-7",
                    i === 0
                      ? "text-foreground/90 text-[15px]"
                      : "text-muted-foreground text-sm",
                  )}
                />
              ))}
            </div>

            {currentSection.bullets && (
              <dl className="mt-5 max-w-[70ch] space-y-2">
                {currentSection.bullets.map((bullet) => (
                  <div
                    key={bullet.code}
                    className="border-border/70 border-l-2 pl-3"
                  >
                    <dt>
                      <CodeRef
                        target={links.resolve(bullet.code)}
                        repoId={repo.id}
                      />
                    </dt>
                    <dd className="text-muted-foreground mt-0.5 text-sm">
                      {bullet.text}
                    </dd>
                  </div>
                ))}
              </dl>
            )}

            {referenced.length > 0 && (
              <section className="border-border bg-muted/20 mt-6 max-w-[70ch] rounded-md border p-3">
                <p className="text-muted-foreground font-mono text-xs tracking-[0.18em] uppercase">
                  Referenced code
                </p>
                <div className="mt-2 flex flex-wrap gap-1.5">
                  {referenced.map((target) => (
                    <CodeRef
                      key={target.symbolId ?? target.file ?? target.text}
                      target={target}
                      repoId={repo.id}
                      className="bg-card py-0.5"
                    />
                  ))}
                </div>
              </section>
            )}

            <nav
              className="border-border mt-6 flex items-center gap-2 border-t pt-3"
              aria-label="Section navigation"
            >
              {index > 0 && (
                <Button
                  variant="ghost"
                  className="text-muted-foreground hover:text-foreground -ml-2"
                  onClick={() =>
                    setActiveSection({
                      repo: repo.id,
                      id: sections[index - 1]!.id,
                    })
                  }
                >
                  <ChevronLeft aria-hidden className="mr-1 h-3.5 w-3.5" />
                  {sections[index - 1]!.label}
                </Button>
              )}
              {index < sections.length - 1 && (
                <Button
                  variant="ghost"
                  className="text-muted-foreground hover:text-foreground ml-auto"
                  onClick={() =>
                    setActiveSection({
                      repo: repo.id,
                      id: sections[index + 1]!.id,
                    })
                  }
                >
                  {sections[index + 1]!.label}
                  <ChevronRight aria-hidden className="ml-1 h-3.5 w-3.5" />
                </Button>
              )}
            </nav>
          </article>
        </div>
      ) : (
        <div className="border-border bg-card rounded-lg border">
          <EmptyState
            kind="empty"
          icon={BookOpen}
            title="No wiki generated yet for this repository"
            description="Run a reindex with Generate wiki on to build one."
            action={
              <div className="flex flex-wrap justify-center gap-2">
                <Button onClick={() => setReindexOpen(true)}>
                  <RefreshCw aria-hidden className="mr-1.5 h-3.5 w-3.5" />
                  Open reindex dialog
                </Button>
                {repo.status === "ready" && (
                  <Button variant="outline" asChild>
                    <Link to="/code/graph" search={{ repo: repo.id }}>
                      Browse the code graph
                      <ArrowRight aria-hidden className="ml-1.5 h-3.5 w-3.5" />
                    </Link>
                  </Button>
                )}
              </div>
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
