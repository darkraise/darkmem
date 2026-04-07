import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import {
  useRepoStats,
  useRepos,
  useCreateRepo,
  useDeleteRepo,
  useReindexRepo,
  useTriggerEnrichment,
  useRepoTasks,
  useCancelTask,
} from "@/hooks/api"
import type { RepoCreateParams, RepoTask, Repo } from "@/hooks/api"
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
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
import { toast } from "sonner"
import { Plus, RefreshCw, Trash2, X } from "lucide-react"

export const Route = createFileRoute("/_authenticated/repos")({
  component: RepositoriesPage,
})

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

const PROVIDER_VARIANT: Record<string, "default" | "secondary" | "outline"> = {
  github: "default",
  gitlab: "secondary",
  local: "outline",
}

function StatValue({ label, value }: { label: string; value: string | number }) {
  return (
    <Card>
      <CardContent className="pt-4">
        <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
          {label}
        </div>
        <div className="text-3xl font-bold mt-1">{value}</div>
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
    sync_interval_minutes: 30,
  })

  const set = (field: keyof RepoCreateParams, value: string | number) =>
    setForm((prev) => ({ ...prev, [field]: value }))

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.name.trim()) return

    const params: RepoCreateParams = { name: form.name.trim() }
    if (form.url) params.url = form.url
    if (form.provider) params.provider = form.provider
    if (form.default_branch) params.default_branch = form.default_branch
    if (form.auth_token) params.auth_token = form.auth_token
    if (form.sync_interval_minutes != null)
      params.sync_interval_minutes = form.sync_interval_minutes

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
        <Label className="text-xs text-muted-foreground">Name *</Label>
        <Input value={form.name} onChange={(e) => set("name", e.target.value)} required />
      </div>
      <div>
        <Label className="text-xs text-muted-foreground">URL</Label>
        <Input
          value={form.url ?? ""}
          onChange={(e) => set("url", e.target.value)}
          placeholder="https://github.com/org/repo"
        />
      </div>
      <div>
        <Label className="text-xs text-muted-foreground">Provider</Label>
        <Select value={form.provider ?? "github"} onValueChange={(v) => set("provider", v)}>
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
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="text-xs text-muted-foreground">Default branch</Label>
          <Input
            value={form.default_branch ?? "main"}
            onChange={(e) => set("default_branch", e.target.value)}
          />
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">Sync interval (min)</Label>
          <Input
            type="number"
            value={form.sync_interval_minutes ?? 30}
            onChange={(e) => set("sync_interval_minutes", Number(e.target.value))}
            min={1}
          />
        </div>
      </div>
      <div>
        <Label className="text-xs text-muted-foreground">Auth token</Label>
        <Input
          type="password"
          value={form.auth_token ?? ""}
          onChange={(e) => set("auth_token", e.target.value)}
          placeholder="Optional"
        />
      </div>
      <Button type="submit" className="w-full" disabled={createRepo.isPending}>
        {createRepo.isPending ? "Adding..." : "Add Repository"}
      </Button>
    </form>
  )
}

function RepoRow({
  repo,
  onReindex,
  onDelete,
}: {
  repo: Repo
  onReindex: (id: string) => void
  onDelete: (id: string, name: string) => void
}) {
  const { data: tasks } = useRepoTasks(
    repo.status === "cloning" || repo.status === "indexing" ? repo.id : null,
  )
  const cancelTask = useCancelTask()

  return (
    <div className="px-4 py-3 space-y-2">
      <div className="flex items-center gap-3">
        <span
          className={`w-2 h-2 rounded-full shrink-0 ${
            repo.status === "cloning"
              ? "bg-yellow-500 animate-pulse"
              : repo.status === "error"
                ? "bg-red-500"
                : repo.status === "cancelled"
                  ? "bg-orange-500"
                  : repo.status === "indexing"
                    ? "bg-blue-500 animate-pulse"
                    : repo.is_active
                      ? "bg-green-500"
                      : "bg-muted-foreground"
          }`}
          title={repo.status_message ?? repo.status}
        />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="text-sm font-bold truncate">{repo.name}</span>
            <Badge
              variant={PROVIDER_VARIANT[repo.provider.toLowerCase()] ?? "outline"}
              className="text-[10px] px-1.5 py-0 shrink-0"
            >
              {repo.provider}
            </Badge>
            {(repo.status === "cloning" || repo.status === "indexing") && (
              <Badge
                variant="outline"
                className={`text-[10px] px-1.5 py-0 shrink-0 ${
                  repo.status === "cloning"
                    ? "text-yellow-500 border-yellow-500"
                    : "text-blue-500 border-blue-500"
                }`}
              >
                {repo.status_message ??
                  (repo.status === "cloning" ? "Cloning..." : "Indexing...")}
              </Badge>
            )}
            {repo.status === "error" && (
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0 shrink-0 text-destructive border-destructive"
                title={repo.status_message ?? ""}
              >
                Error: {repo.status_message ? repo.status_message.slice(0, 60) : "Unknown"}
              </Badge>
            )}
            {repo.status === "cancelled" && (
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0 shrink-0 text-orange-500 border-orange-500"
              >
                Cancelled
              </Badge>
            )}
          </div>
          <div className="flex items-center gap-2 mt-0.5 text-xs text-muted-foreground">
            <span className="truncate max-w-[300px]">{repo.url ?? repo.local_path ?? "—"}</span>
            <span className="shrink-0">·</span>
            <span className="shrink-0">
              {repo.last_indexed_at ? relativeTime(repo.last_indexed_at) : "Never"}
            </span>
            <span className="shrink-0">·</span>
            <span className="shrink-0">{repo.file_count} files</span>
            <span className="shrink-0">·</span>
            <span className="shrink-0">{repo.symbol_count} symbols</span>
          </div>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs"
            disabled={repo.status === "cloning" || repo.status === "indexing"}
            onClick={() => onReindex(repo.id)}
          >
            <RefreshCw
              className={`w-3.5 h-3.5 mr-1 ${repo.status === "indexing" ? "animate-spin" : ""}`}
            />
            {repo.status === "indexing" ? "Indexing..." : "Reindex"}
          </Button>
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-xs text-destructive hover:text-destructive"
            onClick={() => onDelete(repo.id, repo.name)}
          >
            <Trash2 className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>
      {tasks && tasks.length > 0 && (
        <div className="ml-5 space-y-1">
          {tasks.map((task: RepoTask) => (
            <div
              key={task.id}
              className="flex items-center gap-2 text-xs text-muted-foreground bg-muted/30 rounded px-2 py-1"
            >
              <span className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse shrink-0" />
              <Badge variant="outline" className="text-[9px] px-1 py-0">
                {task.kind}
              </Badge>
              <span className="truncate flex-1">{task.message}</span>
              <span className="shrink-0">{relativeTime(task.created_at)}</span>
              <button
                className="text-muted-foreground hover:text-destructive shrink-0"
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
                <X className="w-3 h-3" />
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

function RepositoriesPage() {
  const { data: stats } = useRepoStats()
  const { data: repos, isLoading } = useRepos()
  const deleteRepo = useDeleteRepo()
  const reindexRepo = useReindexRepo()
  const triggerEnrichment = useTriggerEnrichment()

  const [dialogOpen, setDialogOpen] = useState(false)

  const handleReindex = (id: string) => {
    reindexRepo.mutate(id, {
      onSuccess: () => toast.success("Reindex triggered"),
      onError: () => toast.error("Reindex failed"),
    })
  }

  const handleDelete = (id: string, name: string) => {
    if (!window.confirm(`Delete repository "${name}"?`)) return
    deleteRepo.mutate(id, {
      onSuccess: () => toast.success("Repository deleted"),
      onError: () => toast.error("Failed to delete repository"),
    })
  }

  const enrichmentLabel = stats
    ? `${stats.enrichment_completed}/${stats.enrichment_completed + stats.enrichment_pending}`
    : "—"

  return (
    <div className="p-6 space-y-4">
      <PageHeader title="Repositories" />

      <div className="flex items-center justify-end gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() =>
            triggerEnrichment.mutate(undefined, {
              onSuccess: (data) => toast.success(`Enriched ${data.processed} symbols`),
              onError: () => toast.error("Enrichment failed"),
            })
          }
          disabled={triggerEnrichment.isPending}
        >
          {triggerEnrichment.isPending ? "Enriching..." : "Run Enrichment"}
        </Button>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="w-4 h-4 mr-1" />
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

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <StatValue label="Repos" value={stats?.total_repos ?? "—"} />
        <StatValue label="Files" value={stats?.total_files ?? "—"} />
        <StatValue label="Symbols" value={stats?.total_symbols ?? "—"} />
        <StatValue label="Enrichment" value={enrichmentLabel} />
      </div>

      {isLoading && <p className="text-muted-foreground">Loading...</p>}

      {!isLoading && repos?.length === 0 && (
        <p className="text-muted-foreground">No repositories yet. Add one to get started.</p>
      )}

      {repos && repos.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs uppercase tracking-wider text-muted-foreground font-medium">
              Repositories
            </CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            <div className="divide-y divide-border">
              {repos.map((repo) => (
                <RepoRow
                  key={repo.id}
                  repo={repo}
                  onReindex={handleReindex}
                  onDelete={handleDelete}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}
