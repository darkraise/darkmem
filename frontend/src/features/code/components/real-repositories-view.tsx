import { useState } from "react"
import { useForm } from "@tanstack/react-form"
import { Clock, FolderGit2, Layers, RefreshCw, X } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { EmptyState, listItemClass } from "@/components/darkmem"
import { Button } from "darkraise-ui/components/button"
import { TextField } from "darkraise-ui/forms"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogClose,
} from "darkraise-ui/components/dialog"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "darkraise-ui/components/alert-dialog"
import { toast } from "darkraise-ui/components/sonner"
import { cn } from "darkraise-ui/lib"
import { ListSurface } from "@/features/knowledge/components/list-surface"
import {
  useRepos,
  useUpdateRepo,
  useDeleteRepo,
  useReindexRepo,
  useRepoTasks,
  useCancelTask,
} from "@/hooks/api"
import type { Repo, RepoTask, RepoUpdateParams } from "@/hooks/api"
import { relativeTime } from "@/lib/format"
import {
  editRepoSchema,
  type EditRepoInput,
  type ReindexInput,
} from "../schemas"
import { AddRepoDialog } from "./add-repo-dialog"
import {
  CUSTOM_TOKEN,
  GitAccountSelect,
  NO_ACCOUNT,
} from "./git-account-select"
import { RealReindexDialog } from "./real-reindex-dialog"
import { IndexingModesFields } from "./indexing-modes-fields"

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
      <Clock aria-hidden className="text-warning-text h-4.5 w-4.5 shrink-0" />
      <div className="space-y-1 text-sm">
        <p className="font-semibold">
          Last index failed — showing the last good graph
        </p>
        <p className="text-muted-foreground">
          Cause: {staleCause(repo.status_message)}
        </p>
        <p>Nothing retries automatically — reindex once the cause is fixed.</p>
      </div>
    </div>
  )
}

function ErrorReason({ repo }: { repo: Repo }) {
  if (repo.status !== "error" || !repo.status_message) return null
  return <p className="text-destructive text-sm">{repo.status_message}</p>
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
      <span className="border-warning/55 bg-warning/8 text-warning-text inline-flex items-center gap-1.5 rounded-full border border-dashed px-2.5 py-0.5 text-sm">
        <Layers aria-hidden className="h-3.5 w-3.5" />
        {debt.queued} dependent {debt.queued === 1 ? "file" : "files"} queued
        for reindex
      </span>
      <p className="text-muted-foreground text-sm">
        {debt.last_drain
          ? `last drained ${debt.last_drain.count} ${
              debt.last_drain.count === 1 ? "file" : "files"
            } ${relativeTime(debt.last_drain.at)}`
          : "none drained yet"}
      </p>
    </div>
  )
}

// The live phase label: the backend broadcasts only the current tick's
// label (repo.indexing_progress over the websocket), not a forward-looking
// ticker — this renders what status_message actually carries while
// indexing, honestly, rather than fabricating a multi-step bar. A full
// done/current/pending ticker is buildable from code_pipeline.py's fixed
// 14-phase sequence (phases 2-12 always fire in the same numbered order;
// 13/14 are opt-in) but this step ships the simpler single-label rendering.
function LivePhaseLabel({ repo }: { repo: Repo }) {
  if (repo.status !== "indexing") return null
  return (
    <p className="text-info-text flex items-center gap-1.5 text-sm">
      <RefreshCw aria-hidden className="h-3.5 w-3.5 shrink-0 animate-spin" />
      indexing — {repo.status_message ?? "starting…"}
    </p>
  )
}

// The real auto-provision signal: repo_provision.py's handoff_capture_hint
// upserts status="queued" with a fixed status_message when a captured
// memory's repo_hint clears the SSRF allowlist gate. created_at is an
// explicitly-labelled proxy for "when" — the REST Repo shape carries no
// dedicated auto-provision timestamp.
function AutoProvisionLabel({ repo }: { repo: Repo }) {
  if (repo.status !== "queued") return null
  return (
    <p className="text-muted-foreground text-sm">
      auto-provisioned — queued {relativeTime(repo.created_at)}
    </p>
  )
}

function RepoTaskList({ repo }: { repo: Repo }) {
  const { data: tasks } = useRepoTasks(
    repo.status === "cloning" || repo.status === "indexing" ? repo.id : null,
  )
  const cancelTask = useCancelTask()

  if (!tasks || tasks.length === 0) return null

  return (
    <div className="space-y-1">
      {tasks.map((task: RepoTask) => (
        <div
          key={task.id}
          className="text-muted-foreground bg-muted/30 flex items-center gap-2 rounded px-2 py-1 text-sm"
        >
          <span className="h-1.5 w-1.5 shrink-0 animate-pulse rounded-full bg-blue-500" />
          <Badge variant="outline" className="px-1 py-0 text-sm">
            {task.kind}
          </Badge>
          <span className="flex-1 truncate">{task.message}</span>
          <span className="shrink-0">{relativeTime(task.created_at)}</span>
          <Button
            variant="ghost"
            size="icon"
            className="text-muted-foreground hover:text-destructive h-7 w-7 shrink-0"
            aria-label={`Cancel ${task.kind} task`}
            onClick={() =>
              cancelTask.mutate(
                { repoId: repo.id, taskId: task.id },
                {
                  onSuccess: () => toast.success(`Task ${task.kind} cancelled`),
                  onError: () => toast.error("Failed to cancel task"),
                },
              )
            }
          >
            <X className="h-3 w-3" aria-hidden="true" />
          </Button>
        </div>
      ))}
    </div>
  )
}

function EditRepoDialog({
  repo,
  open,
  onOpenChange,
}: {
  repo: Repo | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const updateRepo = useUpdateRepo()
  const form = useForm({
    defaultValues: {
      name: repo?.name ?? "",
      path: repo?.local_path ?? "",
      branch: repo?.default_branch ?? "main",
      fetch_enabled: repo?.fetch_enabled ?? false,
      fetch_interval_seconds: repo?.fetch_interval_seconds ?? 300,
      index_on_commit_enabled: repo?.index_on_commit_enabled ?? false,
      commit_poll_seconds: repo?.commit_poll_seconds ?? 60,
      index_uncommitted: repo?.index_uncommitted ?? false,
      account: repo?.git_account_id
        ? repo.git_account_id
        : repo?.has_custom_token
          ? CUSTOM_TOKEN
          : NO_ACCOUNT,
      auth_token: "",
    },
    onSubmit: async ({ value }) => {
      if (!repo) return
      const parsed = editRepoSchema.safeParse(value)
      if (!parsed.success) return
      const v: EditRepoInput = parsed.data
      const data: RepoUpdateParams = {}
      if (v.name !== repo.name) data.name = v.name
      if (v.branch !== repo.default_branch) data.default_branch = v.branch
      if (v.fetch_enabled !== repo.fetch_enabled)
        data.fetch_enabled = v.fetch_enabled
      if (v.fetch_interval_seconds !== repo.fetch_interval_seconds)
        data.fetch_interval_seconds = v.fetch_interval_seconds
      if (v.index_on_commit_enabled !== repo.index_on_commit_enabled)
        data.index_on_commit_enabled = v.index_on_commit_enabled
      if (v.commit_poll_seconds !== repo.commit_poll_seconds)
        data.commit_poll_seconds = v.commit_poll_seconds
      if (v.index_uncommitted !== repo.index_uncommitted)
        data.index_uncommitted = v.index_uncommitted

      const wasCustom = repo.has_custom_token && !repo.git_account_id
      const currentChoice = repo.git_account_id ?? (wasCustom ? CUSTOM_TOKEN : NO_ACCOUNT)
      if (v.account === CUSTOM_TOKEN) {
        // A blank token on an already-custom repo means "leave it alone";
        // there is nothing to send.
        if (v.auth_token.trim()) data.auth_token = v.auth_token.trim()
      } else if (v.account !== currentChoice) {
        data.git_account_id = v.account === NO_ACCOUNT ? null : v.account
      }

      if (Object.keys(data).length === 0) {
        toast.info("No changes to save")
        onOpenChange(false)
        return
      }
      await updateRepo.mutateAsync(
        { id: repo.id, data },
        {
          onSuccess: () => toast.success("Repository updated"),
          onError: (err) => toast.error(`Failed to update: ${err.message}`),
        },
      )
      onOpenChange(false)
    },
  })

  if (!repo) return null

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Edit repository</DialogTitle>
        </DialogHeader>
        <form
          onSubmit={(e) => {
            e.preventDefault()
            form.handleSubmit()
          }}
          className="space-y-3"
        >
          <form.Field name="name">
            {(field) => (
              <TextField
                name={field.name}
                label="Name"
                value={field.state.value}
                onChange={(v) => field.handleChange(v)}
                onBlur={field.handleBlur}
              />
            )}
          </form.Field>
          <form.Field name="path">
            {(field) => (
              <TextField
                name={field.name}
                label="Path"
                value={field.state.value}
                onChange={(v) => field.handleChange(v)}
                onBlur={field.handleBlur}
              />
            )}
          </form.Field>
          <form.Field name="branch">
            {(field) => (
              <TextField
                name={field.name}
                label="Branch"
                value={field.state.value}
                onChange={(v) => field.handleChange(v)}
                onBlur={field.handleBlur}
              />
            )}
          </form.Field>
          {repo.provider !== "local" && (
            <form.Field name="account">
              {(field) => (
                <GitAccountSelect
                  value={field.state.value}
                  onChange={(v) => field.handleChange(v)}
                  provider={repo.provider}
                />
              )}
            </form.Field>
          )}
          <form.Subscribe selector={(state) => state.values.account}>
            {(account) =>
              account === CUSTOM_TOKEN ? (
                <form.Field name="auth_token">
                  {(field) => (
                    <TextField
                      name={field.name}
                      label={
                        repo.has_custom_token
                          ? "Replace token (blank keeps the stored one)"
                          : "Auth token"
                      }
                      value={field.state.value}
                      onChange={(v) => field.handleChange(v)}
                      onBlur={field.handleBlur}
                    />
                  )}
                </form.Field>
              ) : null
            }
          </form.Subscribe>
          <form.Subscribe
            selector={(state) => ({
              fetch_enabled: state.values.fetch_enabled,
              fetch_interval_seconds: state.values.fetch_interval_seconds,
              index_on_commit_enabled: state.values.index_on_commit_enabled,
              commit_poll_seconds: state.values.commit_poll_seconds,
              index_uncommitted: state.values.index_uncommitted,
            })}
          >
            {(value) => (
              <IndexingModesFields
                value={value}
                onChange={(next) => {
                  form.setFieldValue("fetch_enabled", next.fetch_enabled)
                  form.setFieldValue(
                    "fetch_interval_seconds",
                    next.fetch_interval_seconds,
                  )
                  form.setFieldValue(
                    "index_on_commit_enabled",
                    next.index_on_commit_enabled,
                  )
                  form.setFieldValue(
                    "commit_poll_seconds",
                    next.commit_poll_seconds,
                  )
                  form.setFieldValue(
                    "index_uncommitted",
                    next.index_uncommitted,
                  )
                }}
              />
            )}
          </form.Subscribe>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="ghost">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit">Save</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function RepoRow({
  repo,
  onReindex,
  onEdit,
  onDelete,
}: {
  repo: Repo
  onReindex: (repo: Repo) => void
  onEdit: (repo: Repo) => void
  onDelete: (repo: Repo) => void
}) {
  return (
    <div
      className={listItemClass({
        className: cn(
          "space-y-2 p-3",
          repo.status === "stale" && "border-warning/40 bg-warning/3",
        ),
      })}
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
              "border-warning/60 bg-warning/10 text-warning-text border-dashed",
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
        <div className="flex shrink-0 gap-1">
          <Button
            variant="ghost"
            disabled={repo.status === "cloning" || repo.status === "indexing"}
            onClick={() => onReindex(repo)}
          >
            <RefreshCw aria-hidden className="mr-1 h-3.5 w-3.5" />
            Reindex
          </Button>
          <Button variant="ghost" onClick={() => onEdit(repo)}>
            Edit
          </Button>
          <Button
            variant="ghost"
            className="text-destructive hover:text-destructive"
            onClick={() => onDelete(repo)}
          >
            Delete
          </Button>
        </div>
      </div>

      {repo.last_indexed_at && (
        <p className="text-muted-foreground text-sm">
          branch <span className="font-mono">{repo.default_branch}</span> · last
          indexed {relativeTime(repo.last_indexed_at)}
        </p>
      )}

      <LivePhaseLabel repo={repo} />
      <AutoProvisionLabel repo={repo} />
      <RepoTaskList repo={repo} />
      <IndexDebtIndicator repo={repo} />
      <StaleBanner repo={repo} />
      <ErrorReason repo={repo} />
    </div>
  )
}

// The real-backend counterpart of the demo Code section's RepositoriesTab
// (component-level DEMO ? demo : real split, per RealMemoriesView). T1.46
// bound the two truth signals (stale banner, index-debt); T1.59 adds the
// reindex dialog, live phase label, create/edit/delete, auto-provision
// state, and the task list — the full doc-13 §4.2 Repositories surface.
export function RealRepositoriesView() {
  const { data: repos, isLoading, isError } = useRepos()
  const deleteRepo = useDeleteRepo()
  const reindexRepo = useReindexRepo()

  const [reindexingRepo, setReindexingRepo] = useState<Repo | null>(null)
  const [editingRepo, setEditingRepo] = useState<Repo | null>(null)
  const [confirmDeleteRepo, setConfirmDeleteRepo] = useState<Repo | null>(null)

  return (
    <ListSurface
      title="Repositories"
      populated={(repos?.length ?? 0) > 0}
      meta={isLoading ? undefined : `${repos?.length ?? 0} tracked`}
    >
      <div className="flex justify-end">
        <AddRepoDialog />
      </div>

      {isError ? (
        // Not the empty state: it invites the operator to add a repository
        // they already have, on a read that merely failed.
        <p className="text-destructive p-3 text-sm">
          Repositories could not be loaded.
        </p>
      ) : isLoading ? (
        <p className="text-muted-foreground p-3 text-sm">
          Loading repositories…
        </p>
      ) : repos && repos.length > 0 ? (
        repos.map((repo) => (
          <RepoRow
            key={repo.id}
            repo={repo}
            onReindex={setReindexingRepo}
            onEdit={setEditingRepo}
            onDelete={setConfirmDeleteRepo}
          />
        ))
      ) : (
        <EmptyState
          kind="empty"
          icon={FolderGit2}
          title="No repositories indexed yet"
          description="Add one to make its code searchable."
        />
      )}

      <RealReindexDialog
        repo={reindexingRepo}
        open={!!reindexingRepo}
        onOpenChange={(o) => !o && setReindexingRepo(null)}
        onConfirm={async (v: ReindexInput) => {
          if (!reindexingRepo) return
          await reindexRepo.mutateAsync(
            { id: reindexingRepo.id, options: v },
            {
              onSuccess: () => toast.success("Reindex triggered"),
              onError: () => toast.error("Reindex failed"),
            },
          )
        }}
      />

      {/* Keyed by repo id: EditRepoDialog's form only re-defaults while
          untouched (TanStack FormApi.update), so switching repos after a
          touched-but-cancelled edit would otherwise serve the previous
          repo's stale values into the next repo's form. */}
      <EditRepoDialog
        key={editingRepo?.id}
        repo={editingRepo}
        open={!!editingRepo}
        onOpenChange={(o) => !o && setEditingRepo(null)}
      />

      <AlertDialog
        open={!!confirmDeleteRepo}
        onOpenChange={(o) => !o && setConfirmDeleteRepo(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete &ldquo;{confirmDeleteRepo?.name}&rdquo;?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This will remove the repository and all its indexed data.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (confirmDeleteRepo) {
                  deleteRepo.mutate(confirmDeleteRepo.id, {
                    onSuccess: () => toast.success("Repository deleted"),
                    onError: () => toast.error("Failed to delete repository"),
                  })
                }
                setConfirmDeleteRepo(null)
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </ListSurface>
  )
}
