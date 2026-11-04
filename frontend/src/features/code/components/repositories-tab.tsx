import { useState } from "react"
import {
  ChevronDown,
  Clock,
  FolderGit2,
  Layers,
  TriangleAlert,
  Zap,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "darkraise-ui/components/collapsible"
import { Progress } from "darkraise-ui/components/progress"
import { cn } from "darkraise-ui/lib"
import { formatWhen } from "@/lib/format"
import { phaseProgressLabel, phaseProgressPercent } from "../lib/phase-progress"
import { ListSurface } from "@/features/knowledge/components/list-surface"
import { useDemoCodeRepos } from "@/demo/hooks"
import type { DemoRepo } from "@/demo/types"
import { RepoStatusChip } from "./repo-status-chip"
import { PhaseTicker } from "./phase-ticker"
import { ReindexDialog } from "./reindex-dialog"

export function StaleBanner({ repo }: { repo: DemoRepo }) {
  if (!repo.stale) return null
  return (
    <div className="border-warning-edge/50 bg-warning-solid/8 flex gap-2.5 rounded-md border p-3">
      <Clock aria-hidden className="text-warning-text h-4.5 w-4.5 shrink-0" />
      <div className="min-w-0 space-y-1 text-sm">
        <p className="font-semibold">
          Last index failed — showing the last good graph
        </p>
        <p className="text-muted-foreground">Cause: {repo.stale.cause}</p>
        <p>Nothing retries automatically — reindex once the cause is fixed.</p>
      </div>
    </div>
  )
}

export function ErrorBanner({ repo }: { repo: DemoRepo }) {
  if (!repo.error) return null
  return (
    <div className="border-destructive-edge/50 bg-destructive-solid/8 flex gap-2.5 rounded-md border p-3">
      <TriangleAlert
        aria-hidden
        className="text-destructive-text h-4.5 w-4.5 shrink-0"
      />
      {/* `min-w-0` + `overflow-wrap:anywhere`: an unbreakable git URL in the mono line
          must wrap inside the banner, not push the column past its border. */}
      <div className="min-w-0 space-y-1 text-sm">
        <p className="font-semibold">{repo.error.headline}</p>
        <p className="text-muted-foreground break-words">{repo.error.detail}</p>
        <p className="text-destructive-text font-mono text-sm [overflow-wrap:anywhere]">
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
            <>
              {" "}
              · last indexed{" "}
              <time title={repo.last_indexed_at}>
                {formatWhen(repo.last_indexed_at)}
              </time>
            </>
          )}
          {repo.index_on_commit_enabled && <> · indexing on</>}
        </p>
      )}

      {repo.debt && (
        <span className="border-warning-edge/55 bg-warning-solid/8 text-warning-text inline-flex items-center gap-1.5 rounded-full border border-dashed px-2.5 py-0.5 text-sm">
          <Layers aria-hidden className="h-3.5 w-3.5" />
          {repo.debt.queued_files} {repo.debt.note}
        </span>
      )}

      {repo.auto_provisioned && (
        <div className="space-y-1">
          <span className="border-info-edge/50 bg-info-solid/10 text-info-text inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-sm">
            <Zap aria-hidden className="h-3 w-3" />
            auto-provisioned {repo.auto_provisioned.on}
          </span>
          <p className="text-muted-foreground text-sm">
            registered from memory:{" "}
            <span className="text-primary-text">
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

      {/* Summarised like every other row: the current phase and a progress
          bar, with the full ticker one click away. Inline, 14 rows pushed
          the rest of the list below the fold. */}
      {indexing && repo.phases && (
        <Collapsible className="space-y-2">
          <div className="flex flex-wrap items-center gap-x-3 gap-y-1.5">
            <p className="text-muted-foreground text-sm">
              {phaseProgressLabel(repo.phases) ?? "starting…"}
              {currentPhase && <> · {currentPhase.label}</>}
            </p>
            <Progress
              value={phaseProgressPercent(repo.phases)}
              aria-label={`Indexing progress for ${repo.name}`}
              className="w-40 max-w-full"
            />
            <CollapsibleTrigger className="text-muted-foreground hover:text-foreground group ml-auto inline-flex items-center gap-1 text-sm">
              <ChevronDown
                aria-hidden
                className="h-3.5 w-3.5 transition-transform group-data-[state=open]:rotate-180"
              />
              <span className="group-data-[state=open]:hidden">
                Show all {repo.phases.length} phases
              </span>
              <span className="hidden group-data-[state=open]:inline">
                Hide phases
              </span>
            </CollapsibleTrigger>
          </div>
          <CollapsibleContent>
            <PhaseTicker phases={repo.phases} />
          </CollapsibleContent>
        </Collapsible>
      )}

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
                ? "border-warning-edge/60 text-warning-text bg-warning-solid/8"
                : "border-primary/60 text-primary-text bg-primary/8",
            )}
            onClick={() => onReindex(repo.id)}
          >
            {repo.stale || repo.error ? "Reindex now" : "Reindex…"}
          </Button>
        )}
      </div>
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
