import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import type { ColumnDef } from "@tanstack/react-table"
import {
  useRepoStats,
  useRepos,
  useCreateRepo,
  useUpdateRepo,
  useDeleteRepo,
  useReindexRepo,
  useTriggerEnrichment,
  useRepoTasks,
  useCancelTask,
} from "@/hooks/api"
import type {
  RepoCreateParams,
  RepoUpdateParams,
  RepoTask,
  Repo,
} from "@/hooks/api"
import { DataTable, DataTableSkeleton } from "darkraise-ui/data-table"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "darkraise-ui/components/select"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "darkraise-ui/components/dialog"
import { PageHeader } from "darkraise-ui/layout"
import { toast } from "darkraise-ui/components/sonner"
import { Switch } from "darkraise-ui/components/switch"
import { Plus, RefreshCw, X } from "lucide-react"
import { EditRepoDialog } from "@/features/repos/components/edit-repo-dialog"
import { relativeTime } from "@/lib/format"
import {
  Stat as StatRoot,
  StatLabel,
  StatValue as StatValueEl,
} from "darkraise-ui/components/stat"
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
import { ReindexDialog } from "@/features/repos/components/reindex-dialog"
import type { EditRepoInput, ReindexInput } from "@/features/repos/schemas"

export const Route = createFileRoute("/_authenticated/repos")({
  component: RepositoriesPage,
})

const PROVIDER_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  github: "default",
  gitlab: "secondary",
  local: "outline",
}

function StatValue({
  label,
  value,
}: {
  label: string
  value: string | number
}) {
  return (
    <Card>
      <CardContent className="pt-4">
        <StatRoot>
          <StatLabel>{label}</StatLabel>
          <StatValueEl>{value}</StatValueEl>
        </StatRoot>
      </CardContent>
    </Card>
  )
}

function AddRepoDialog({ onClose }: { onClose: () => void }) {
  const createRepo = useCreateRepo()
  const [form, setForm] = useState<RepoCreateParams>({
    name: "",
    url: "",
    provider: "github",
    default_branch: "main",
    auth_token: "",
    auto_sync: true,
  })

  const set = <K extends keyof RepoCreateParams>(
    field: K,
    value: RepoCreateParams[K],
  ) => setForm((prev) => ({ ...prev, [field]: value }))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) return

    const params: RepoCreateParams = { name: form.name.trim() }
    if (form.url) params.url = form.url
    if (form.provider) params.provider = form.provider
    if (form.default_branch) params.default_branch = form.default_branch
    if (form.auth_token) params.auth_token = form.auth_token
    if (form.auto_sync != null) params.auto_sync = form.auto_sync

    createRepo.mutate(params, {
      onSuccess: () => {
        toast.success("Repository added")
        onClose()
      },
      onError: () => toast.error("Failed to add repository"),
    })
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-3">
      <div>
        <Label className="text-muted-foreground text-base">Name *</Label>
        <Input
          value={form.name}
          onChange={(e) => set("name", e.target.value)}
          required
        />
      </div>
      <div>
        <Label className="text-muted-foreground text-base">URL</Label>
        <Input
          value={form.url ?? ""}
          onChange={(e) => set("url", e.target.value)}
          placeholder="https://github.com/org/repo"
        />
      </div>
      <div>
        <Label className="text-muted-foreground text-base">Provider</Label>
        <Select
          value={form.provider ?? "github"}
          onValueChange={(v) => set("provider", v)}
        >
          <SelectTrigger className="h-8 w-full">
            <SelectValue placeholder="Select provider" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="github">GitHub</SelectItem>
            <SelectItem value="gitlab">GitLab</SelectItem>
            <SelectItem value="local">Local</SelectItem>
          </SelectContent>
        </Select>
      </div>
      <div>
        <Label className="text-muted-foreground text-base">
          Default branch
        </Label>
        <Input
          value={form.default_branch ?? "main"}
          onChange={(e) => set("default_branch", e.target.value)}
        />
      </div>
      <div>
        <Label className="text-muted-foreground text-base">Auth token</Label>
        <Input
          type="password"
          value={form.auth_token ?? ""}
          onChange={(e) => set("auth_token", e.target.value)}
          placeholder="Optional"
        />
      </div>
      <div className="flex items-start gap-2 rounded-md border px-3 py-2">
        <Switch
          className="mt-0.5"
          checked={form.auto_sync ?? true}
          onCheckedChange={(v) => set("auto_sync", v)}
        />
        <div className="text-base">
          <div>Auto-sync</div>
          <div className="text-muted-foreground text-base">
            When on, the repo_sync background job fetches and re-indexes this
            repo on every tick. Manual reindex always works regardless of this
            toggle.
          </div>
        </div>
      </div>
      <Button type="submit" className="w-full" disabled={createRepo.isPending}>
        {createRepo.isPending ? "Adding..." : "Add Repository"}
      </Button>
    </form>
  )
}

function RepoTaskList({ repo }: { repo: Repo }) {
  const { data: tasks } = useRepoTasks(
    repo.status === "cloning" || repo.status === "indexing" ? repo.id : null,
  )
  const cancelTask = useCancelTask()

  if (!tasks || tasks.length === 0) return null

  return (
    <div className="mt-1 space-y-1">
      {tasks.map((task: RepoTask) => (
        <div
          key={task.id}
          className="text-muted-foreground bg-muted/30 flex items-center gap-2 rounded px-2 py-1 text-base"
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
            className="text-muted-foreground hover:text-destructive shrink-0"
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

function RepositoriesPage() {
  const { data: stats } = useRepoStats()
  const { data: repos, isLoading } = useRepos()
  const deleteRepo = useDeleteRepo()
  const reindexRepo = useReindexRepo()
  const updateRepo = useUpdateRepo()
  const triggerEnrichment = useTriggerEnrichment()

  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingRepo, setEditingRepo] = useState<Repo | null>(null)
  const [reindexingRepo, setReindexingRepo] = useState<Repo | null>(null)
  const [confirmDeleteRepo, setConfirmDeleteRepo] = useState<Repo | null>(null)

  const handleDelete = (repo: Repo) => {
    setConfirmDeleteRepo(repo)
  }

  const confirmDelete = (id: string) => {
    deleteRepo.mutate(id, {
      onSuccess: () => toast.success("Repository deleted"),
      onError: () => toast.error("Failed to delete repository"),
    })
  }

  const enrichmentLabel = stats
    ? `${stats.enrichment_completed}/${stats.enrichment_completed + stats.enrichment_pending}`
    : "—"

  const columns: ColumnDef<Repo>[] = [
    {
      accessorKey: "name",
      header: "Name",
      cell: ({ row }) => (
        <div>
          <div className="flex items-center gap-2">
            <span
              className={`h-2 w-2 shrink-0 rounded-full ${
                row.original.status === "cloning"
                  ? "animate-pulse bg-yellow-500"
                  : row.original.status === "error"
                    ? "bg-red-500"
                    : row.original.status === "cancelled"
                      ? "bg-orange-500"
                      : row.original.status === "indexing"
                        ? "animate-pulse bg-blue-500"
                        : row.original.auto_sync
                          ? "bg-green-500"
                          : "bg-muted-foreground"
              }`}
              title={row.original.status_message ?? row.original.status}
            />
            <span className="text-base font-medium">{row.original.name}</span>
          </div>
          <RepoTaskList repo={row.original} />
        </div>
      ),
    },
    {
      accessorKey: "provider",
      header: "Provider",
      size: 100,
      cell: ({ getValue }) => (
        <Badge
          variant={
            PROVIDER_VARIANT[String(getValue()).toLowerCase()] ?? "outline"
          }
          className="px-1.5 py-0 text-sm"
        >
          {String(getValue())}
        </Badge>
      ),
    },
    {
      accessorKey: "default_branch",
      header: "Branch",
      size: 100,
    },
    {
      id: "location",
      header: "Location",
      cell: ({ row }) => (
        <span className="text-muted-foreground block max-w-[240px] truncate text-base">
          {row.original.url ?? row.original.local_path ?? "—"}
        </span>
      ),
    },
    {
      accessorKey: "status",
      header: "Status",
      size: 110,
      cell: ({ row }) => {
        const { status, status_message } = row.original
        if (status === "error") {
          return (
            <Badge
              variant="outline"
              className="text-destructive border-destructive px-1.5 py-0 text-sm"
              title={status_message ?? ""}
            >
              error
            </Badge>
          )
        }
        if (status === "cancelled") {
          return (
            <Badge
              variant="outline"
              className="border-orange-500 px-1.5 py-0 text-sm text-orange-500"
            >
              cancelled
            </Badge>
          )
        }
        return (
          <Badge variant="outline" className="px-1.5 py-0 text-sm">
            {status}
          </Badge>
        )
      },
    },
    {
      accessorKey: "auto_sync",
      header: "Auto-sync",
      size: 100,
      cell: ({ row }) => (
        <Switch
          checked={row.original.auto_sync}
          onCheckedChange={(v) =>
            updateRepo.mutate({ id: row.original.id, data: { auto_sync: v } })
          }
        />
      ),
    },
    {
      accessorKey: "last_indexed_at",
      header: "Last indexed",
      size: 140,
      cell: ({ getValue }) => {
        const v = getValue()
        return v ? relativeTime(String(v)) : "Never"
      },
    },
    {
      id: "counts",
      header: "Files / Symbols",
      size: 120,
      cell: ({ row }) => (
        <span className="text-muted-foreground text-base">
          {row.original.file_count} / {row.original.symbol_count}
        </span>
      ),
    },
    {
      id: "actions",
      header: "",
      size: 180,
      cell: ({ row }) => (
        <div className="flex gap-1">
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-base"
            disabled={
              row.original.status === "cloning" ||
              row.original.status === "indexing"
            }
            onClick={() => setReindexingRepo(row.original)}
          >
            <RefreshCw
              className={`mr-1 h-3.5 w-3.5 ${row.original.status === "indexing" ? "animate-spin" : ""}`}
            />
            {row.original.status === "indexing" ? "Indexing..." : "Reindex"}
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="h-7 px-2 text-base"
            onClick={() => setEditingRepo(row.original)}
          >
            Edit
          </Button>
          <Button
            size="sm"
            variant="ghost"
            className="text-destructive hover:text-destructive h-7 px-2 text-base"
            onClick={() => handleDelete(row.original)}
          >
            Delete
          </Button>
        </div>
      ),
    },
  ]

  return (
    <div className="space-y-4 p-6">
      <PageHeader title="Repositories" />

      <div className="flex items-center justify-end gap-2">
        <Button
          variant="outline"
          onClick={() =>
            triggerEnrichment.mutate(undefined, {
              onSuccess: (data) =>
                toast.success(`Enriched ${data.processed} symbols`),
              onError: () => toast.error("Enrichment failed"),
            })
          }
          disabled={triggerEnrichment.isPending}
        >
          {triggerEnrichment.isPending ? "Enriching..." : "Run Enrichment"}
        </Button>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button>
              <Plus className="mr-1 h-4 w-4" />
              Add Repo
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add Repository</DialogTitle>
            </DialogHeader>
            <AddRepoDialog onClose={() => setDialogOpen(false)} />
          </DialogContent>
        </Dialog>
      </div>

      <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
        <StatValue label="Repos" value={stats?.total_repos ?? "—"} />
        <StatValue label="Files" value={stats?.total_files ?? "—"} />
        <StatValue label="Symbols" value={stats?.total_symbols ?? "—"} />
        <StatValue label="Enrichment" value={enrichmentLabel} />
      </div>

      <EditRepoDialog
        open={!!editingRepo}
        onOpenChange={(o) => !o && setEditingRepo(null)}
        initial={
          editingRepo
            ? {
                name: editingRepo.name,
                path: editingRepo.local_path ?? "",
                branch: editingRepo.default_branch,
                sync_cron: "0 */6 * * *",
                auto_sync: editingRepo.auto_sync,
                enrich_symbols: true,
                generate_wiki: true,
              }
            : {}
        }
        onSave={async (v: EditRepoInput) => {
          if (!editingRepo) return
          const data: RepoUpdateParams = {}
          if (v.name !== editingRepo.name) data.name = v.name
          if (v.branch !== editingRepo.default_branch)
            data.default_branch = v.branch
          if (v.auto_sync !== editingRepo.auto_sync)
            data.auto_sync = v.auto_sync
          data.enrich_symbols = v.enrich_symbols
          data.generate_wiki = v.generate_wiki
          if (Object.keys(data).length === 0) {
            toast.info("No changes to save")
            return
          }
          await updateRepo.mutateAsync(
            { id: editingRepo.id, data },
            {
              onSuccess: () => toast.success("Repository updated"),
              onError: (err) => toast.error(`Failed to update: ${err.message}`),
            },
          )
        }}
      />
      <ReindexDialog
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
                if (confirmDeleteRepo) confirmDelete(confirmDeleteRepo.id)
                setConfirmDeleteRepo(null)
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      {isLoading ? (
        <DataTableSkeleton columnCount={9} />
      ) : repos?.length === 0 ? (
        <p className="text-muted-foreground">
          No repositories yet. Add one to get started.
        </p>
      ) : (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-muted-foreground text-base font-medium tracking-wider uppercase">
              Repositories
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <DataTable columns={columns} data={repos ?? []} />
          </CardContent>
        </Card>
      )}
    </div>
  )
}
