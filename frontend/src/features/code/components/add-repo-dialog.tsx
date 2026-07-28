import { useState } from "react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
  DialogFooter,
  DialogClose,
} from "darkraise-ui/components/dialog"
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
import { Switch } from "darkraise-ui/components/switch"
import { toast } from "darkraise-ui/components/sonner"
import { Plus } from "lucide-react"
import { useCreateRepo } from "@/hooks/api"
import type { RepoCreateParams } from "@/hooks/api"

// Ported from routes/_authenticated/repos.tsx's AddRepoDialog (T1.59) — same
// POST /repos shape, adapted to the Code section's own trigger/dialog chrome.
export function AddRepoDialog() {
  const [open, setOpen] = useState(false)
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
        setOpen(false)
        setForm({
          name: "",
          url: "",
          provider: "github",
          default_branch: "main",
          auth_token: "",
          auto_sync: true,
        })
      },
      onError: () => toast.error("Failed to add repository"),
    })
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button>
          <Plus aria-hidden className="mr-1 h-4 w-4" />
          Add repository
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Add repository</DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3">
          <div>
            <Label className="text-muted-foreground">Name *</Label>
            <Input
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              required
            />
          </div>
          <div>
            <Label className="text-muted-foreground">URL</Label>
            <Input
              value={form.url ?? ""}
              onChange={(e) => set("url", e.target.value)}
              placeholder="https://github.com/org/repo"
            />
          </div>
          <div>
            <Label className="text-muted-foreground">Provider</Label>
            <Select
              value={form.provider ?? "github"}
              onValueChange={(v) => set("provider", v)}
            >
              <SelectTrigger className="h-9 w-full">
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
            <Label className="text-muted-foreground">Default branch</Label>
            <Input
              value={form.default_branch ?? "main"}
              onChange={(e) => set("default_branch", e.target.value)}
            />
          </div>
          <div>
            <Label className="text-muted-foreground">Auth token</Label>
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
            <div className="text-sm">
              <div>Auto-sync</div>
              <div className="text-muted-foreground text-sm">
                When on, the repo_sync background job fetches and re-indexes
                this repo on every tick. Manual reindex always works
                regardless of this toggle.
              </div>
            </div>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="ghost">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" disabled={createRepo.isPending}>
              {createRepo.isPending ? "Adding..." : "Add Repository"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}
