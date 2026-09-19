import { useState } from "react"
import {
  Clock,
  FolderGit2,
  Layers,
  TriangleAlert,
  Zap,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { cn } from "darkraise-ui/lib"
import { ListSurface } from "@/features/knowledge/components/list-surface"
import { useDemoCodeRepos } from "@/demo/hooks"
import type { DemoRepo } from "@/demo/types"
import { RepoStatusChip } from "./repo-status-chip"
import { PhaseTicker } from "./phase-ticker"
import { ReindexDialog } from "./reindex-dialog"

function StaleBanner({ repo }: { repo: DemoRepo }) {
  if (!repo.stale) return null
  return (
    <div className="border-warning/50 bg-warning/8 flex gap-2.5 rounded-md border p-3">
      <Clock aria-hidden className="text-warning h-4.5 w-4.5 shrink-0" />
      <div className="space-y-1 text-sm">
        <p className="font-semibold">
          Last index failed — serving the last-good graph, marked stale
        </p>
        <p className="text-muted-foreground">Cause: {repo.stale.cause}</p>
        <p>
          The graph indexed {repo.stale.last_good_at} (HEAD{" "}
          <span className="font-mono">{repo.stale.last_good_head}</span>) is
          still served to every code tool, labelled <b>stale</b>, until the
          next run succeeds.
        </p>
      </div>
    </div>
  )
}

function ErrorBanner({ repo }: { repo: DemoRepo }) {
  if (!repo.error) return null
  return (
    <div className="border-destructive/50 bg-destructive/8 flex gap-2.5 rounded-md border p-3">
      <TriangleAlert
        aria-hidden
        className="text-destructive h-4.5 w-4.5 shrink-0"
      />
      <div className="space-y-1 text-sm">
        <p className="font-semibold">{repo.error.headline}</p>
        <p className="text-muted-foreground">{repo.error.detail}</p>
        <p className="text-destructive font-mono text-sm">
          {repo.error.message}
        </p>
      </div>
    </div>
  )
}

function RepoRow({
  repo,
  onReindex,
  onOpenGraph,
}: {
  repo: DemoRepo
  onReindex: (id: string) => void
  onOpenGraph: (id: string) => void
}) {
  const indexing = repo.status === "indexing"
  const currentPhase = repo.phases?.find((p) => p.state === "current")
  const hasGraph = repo.status === "ready" || repo.status === "stale"

  return (
    <div
      className={cn(
        "border-border space-y-2 rounded-md border p-3",
        (indexing || repo.stale || repo.error) &&
          "border-primary/40 bg-primary/3",
      )}
    >
      <div className="flex flex-wrap items-center gap-2.5">
        <FolderGit2
          aria-hidden
          className="text-muted-foreground h-4 w-4 shrink-0"
        />
        <span className="text-sm font-semibold">{repo.name}</span>
        <RepoStatusChip status={repo.status} />
        <span className="text-muted-foreground ml-auto font-mono text-sm whitespace-nowrap">
          {repo.status === "stale" && repo.stale
            ? `last-good HEAD ${repo.stale.last_good_head}`
            : repo.status === "error"
              ? // A periodic-sync failure disables the indexing lane only —
                // fetch_enabled is left alone on purpose, so this chip must
                // never claim fetching was turned off.
                "indexing disabled"
              : repo.head
                ? `HEAD ${repo.head}`
                : "no HEAD yet"}
        </span>
      </div>

      {(repo.last_indexed_at || repo.status === "registered") && (
        <p className="text-muted-foreground text-sm">
          branch <span className="font-mono">{repo.branch}</span>
          {repo.last_indexed_at && (
            <> · last indexed {repo.last_indexed_at}</>
          )}
          {repo.index_on_commit_enabled && <> · indexing on</>}
        </p>
      )}

      {repo.debt && (
        <span className="border-warning/55 bg-warning/8 text-warning inline-flex items-center gap-1.5 rounded-full border border-dashed px-2.5 py-0.5 text-sm">
          <Layers aria-hidden className="h-3.5 w-3.5" />
          {repo.debt.queued_files} {repo.debt.note}
        </span>
      )}

      {repo.auto_provisioned && (
        <div className="space-y-1">
          <span className="border-info/50 bg-info/10 text-info inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-sm">
            <Zap aria-hidden className="h-3 w-3" />
            auto-provisioned {repo.auto_provisioned.on}
          </span>
          <p className="text-muted-foreground text-sm">
            registered from memory:{" "}
            <span className="text-primary">
              {repo.auto_provisioned.from_memory}
            </span>
          </p>
        </div>
      )}

      {repo.registered_note && (
        <p className="text-muted-foreground text-sm italic">
          {repo.registered_note}
        </p>
      )}

      {indexing && currentPhase && (
        <p className="text-muted-foreground text-sm">
          phase {String(currentPhase.n).padStart(2, "0")} of{" "}
          {repo.phases?.length ?? 14} · {currentPhase.label}
        </p>
      )}
      {indexing && repo.phases && <PhaseTicker phases={repo.phases} />}

      <StaleBanner repo={repo} />
      <ErrorBanner repo={repo} />

      <div className="flex flex-wrap justify-end gap-2">
        {hasGraph && (
          <Button
            variant="outline"
            className="rounded-full"
            onClick={() => onOpenGraph(repo.id)}
          >
            Open code graph{repo.status === "stale" ? " (stale)" : ""}
          </Button>
        )}
        {indexing ? (
          <Button variant="outline" className="rounded-full" disabled>
            Reindex running…
          </Button>
        ) : (
          <Button
            variant="outline"
            className={cn(
              "rounded-full",
              repo.stale || repo.error
                ? "border-warning/60 text-warning bg-warning/8"
                : "border-primary/60 text-primary bg-primary/8",
            )}
            onClick={() => onReindex(repo.id)}
          >
            {repo.stale || repo.error ? "Reindex now" : "Reindex…"}
          </Button>
        )}
      </div>

      {repo.stale && (
        <p className="text-muted-foreground text-sm">
          If a periodic run caused this, it has also disabled indexing on
          commit, so nothing retries automatically — reindex now, or
          re-enable indexing from the Edit Repo dialog once the underlying
          issue is fixed. If a manual reindex caused it instead, don't count
          on an automatic retry — reindex now rather than waiting on one. The
          stale label clears the moment a run succeeds.
        </p>
      )}
    </div>
  )
}

export function RepositoriesTab({
  onOpenGraph,
}: {
  onOpenGraph: (repoId: string) => void
}) {
  const repos = useDemoCodeRepos()
  const [reindexRepoId, setReindexRepoId] = useState<string | null>(null)
  const reindexRepo = repos.find((r) => r.id === reindexRepoId)

  return (
    <div className="space-y-4">
      <ListSurface
        title="Repositories"
        populated={repos.length > 0}
        meta={`${repos.length} tracked`}
      >
        {repos.map((repo) => (
          <RepoRow
            key={repo.id}
            repo={repo}
            onReindex={setReindexRepoId}
            onOpenGraph={onOpenGraph}
          />
        ))}
      </ListSurface>

      {reindexRepo && (
        <ReindexDialog
          repo={reindexRepo}
          open={reindexRepoId !== null}
          onOpenChange={(open) => {
            if (!open) setReindexRepoId(null)
          }}
        />
      )}
    </div>
  )
}
