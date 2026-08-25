import { useState } from "react"
import { useForm } from "@tanstack/react-form"
import { Clock, FolderGit2, Layers, RefreshCw, X } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { EmptyState, listItemClass } from "@/components/darkmem"
import { Button } from "darkraise-ui/components/button"
import { TextField, SwitchField } from "darkraise-ui/forms"
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
          ) is still served to every code tool, labelled <b>stale</b>, until the
          next run succeeds.
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
    <p className="text-info flex items-center gap-1.5 text-sm">
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
      {repo.status_message ? ` (${repo.status_message})` : ""}
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
      auto_sync: repo?.auto_sync ?? true,
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
      if (v.auto_sync !== repo.auto_sync) data.auto_sync = v.auto_sync

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
          <form.Field name="auto_sync">
            {(field) => (
              <SwitchField
                name={field.name}
                label="Auto-sync"
                value={field.state.value}
                onChange={(v) => field.handleChange(v)}
                onBlur={field.handleBlur}
              />
            )}
          </form.Field>
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
              "border-warning/60 bg-warning/10 text-warning border-dashed",
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
    </div>
  )
}

// The real-backend counterpart of the demo Code section's RepositoriesTab
// (component-level DEMO ? demo : real split, per RealMemoriesView). T1.46
// bound the two truth signals (stale banner, index-debt); T1.59 adds the
// reindex dialog, live phase label, create/edit/delete, auto-provision
// state, and the task list — the full doc-13 §4.2 Repositories surface.
export function RealRepositoriesView() {
  const { data: repos, isLoading } = useRepos()
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

      {isLoading ? (
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
          description="Add one and darkmem clones it, parses it with tree-sitter, and makes its symbols searchable."
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

      <EditRepoDialog
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
