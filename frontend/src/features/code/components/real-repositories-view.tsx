import { Clock, FolderGit2, Layers } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { cn } from "darkraise-ui/lib"
import { ListSurface } from "@/features/knowledge/components/list-surface"
import { useRepos } from "@/hooks/api"
import type { Repo } from "@/hooks/api"
import { relativeTime } from "@/lib/format"

const STALE_CAUSE_MARKER = "Cause: "

function staleCause(statusMessage: string | null): string {
  if (!statusMessage) return "unknown cause"
  const idx = statusMessage.indexOf(STALE_CAUSE_MARKER)
  return idx === -1
    ? statusMessage
    : statusMessage.slice(idx + STALE_CAUSE_MARKER.length)
}

// T1.38: a stale-but-queryable graph is honest; a silently-empty one is
// not. `last_indexed_commit`/`last_indexed_at` are untouched by a failed
// run, so they still name the exact last-good graph being served.
function StaleBanner({ repo }: { repo: Repo }) {
  if (repo.status !== "stale") return null
  return (
    <div className="border-warning/50 bg-warning/8 flex gap-2.5 rounded-md border p-3">
      <Clock aria-hidden className="text-warning h-4.5 w-4.5 shrink-0" />
      <div className="space-y-1 text-sm">
        <p className="font-semibold">
          Last index failed — serving the last-good graph, marked stale
        </p>
        <p className="text-muted-foreground">
          Cause: {staleCause(repo.status_message)}
        </p>
        <p>
          The graph indexed{" "}
          {repo.last_indexed_at
            ? relativeTime(repo.last_indexed_at)
            : "previously"}{" "}
          (HEAD{" "}
          <span className="font-mono">
            {repo.last_indexed_commit ?? "unknown"}
          </span>
          ) is still served to every code tool, labelled <b>stale</b>, until
          the next run succeeds.
        </p>
      </div>
    </div>
  )
}

// T1.39: the queued count alone cannot say whether the debt is draining or
// stuck — `last_drain` is the evidence. Its timestamp advances across a
// refetch (WS-triggered on every repo.indexing_completed) when a real drain
// lands, so watching this line over time is what reads as "draining."
function IndexDebtIndicator({ repo }: { repo: Repo }) {
  const debt = repo.index_debt
  if (!debt || (debt.queued === 0 && debt.deferred_total === 0)) return null

  return (
    <div className="space-y-1">
      <span className="border-warning/55 bg-warning/8 text-warning inline-flex items-center gap-1.5 rounded-full border border-dashed px-2.5 py-0.5 text-sm">
        <Layers aria-hidden className="h-3.5 w-3.5" />
        {debt.queued} dependent {debt.queued === 1 ? "file" : "files"} queued
        for re-trace
      </span>
      <p className="text-muted-foreground text-sm">
        {debt.last_drain
          ? `draining — last drained ${debt.last_drain.count} ${
              debt.last_drain.count === 1 ? "file" : "files"
            } ${relativeTime(debt.last_drain.at)} (commit ${
              debt.last_drain.commit
            })${
              debt.last_drain.vanished > 0
                ? `, ${debt.last_drain.vanished} vanished — no longer referenced`
                : ""
            }`
          : `no drain recorded yet — ${debt.deferred_total} deferred, 0 drained so far`}
      </p>
    </div>
  )
}

function RepoRow({ repo }: { repo: Repo }) {
  return (
    <div
      className={cn(
        "border-border space-y-2 rounded-md border p-3",
        repo.status === "stale" && "border-warning/40 bg-warning/3",
      )}
    >
      <div className="flex flex-wrap items-center gap-2.5">
        <FolderGit2
          aria-hidden
          className="text-muted-foreground h-4 w-4 shrink-0"
        />
        <span className="text-sm font-semibold">{repo.name}</span>
        <Badge
          variant="outline"
          size="sm"
          className={cn(
            "gap-1 font-mono uppercase",
            repo.status === "stale" &&
              "border-warning/60 border-dashed bg-warning/10 text-warning",
            repo.status === "error" &&
              "border-destructive/50 bg-destructive/10 text-destructive",
          )}
        >
          {repo.status}
        </Badge>
        <span className="text-muted-foreground ml-auto font-mono text-sm whitespace-nowrap">
          {repo.status === "stale"
            ? `last-good HEAD ${repo.last_indexed_commit ?? "unknown"}`
            : repo.last_indexed_commit
              ? `HEAD ${repo.last_indexed_commit}`
              : "no HEAD yet"}
        </span>
      </div>

      {repo.last_indexed_at && (
        <p className="text-muted-foreground text-sm">
          branch <span className="font-mono">{repo.default_branch}</span> ·
          last indexed {relativeTime(repo.last_indexed_at)}
        </p>
      )}

      <IndexDebtIndicator repo={repo} />
      <StaleBanner repo={repo} />
    </div>
  )
}

// The real-backend counterpart of the demo Code section's RepositoriesTab
// (component-level DEMO ? demo : real split, per RealMemoriesView). This
// task binds only the two new signals — stale banner and index-debt — not
// the reindex dialog or live phase ticker, which is T1.59's.
export function RealRepositoriesView() {
  const { data: repos, isLoading } = useRepos()

  return (
    <ListSurface
      title="Repositories"
      populated={(repos?.length ?? 0) > 0}
      meta={isLoading ? undefined : `${repos?.length ?? 0} tracked`}
    >
      {isLoading ? (
        <p className="text-muted-foreground p-3 text-sm">
          Loading repositories…
        </p>
      ) : repos && repos.length > 0 ? (
        repos.map((repo) => <RepoRow key={repo.id} repo={repo} />)
      ) : (
        <p className="text-muted-foreground p-3 text-sm">
          No repositories yet.
        </p>
      )}
    </ListSurface>
  )
}
