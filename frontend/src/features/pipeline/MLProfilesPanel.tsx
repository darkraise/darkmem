import { useState } from "react"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { Badge } from "darkraise-ui/components/badge"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "darkraise-ui/components/dialog"
import { toast } from "darkraise-ui/components/sonner"
import { Plus, Trash2 } from "lucide-react"
import {
  useMlProfiles,
  useUpdateMlProfiles,
  useDeleteMlProfile,
  type MlProfile,
} from "@/hooks/api"

export function MLProfilesPanel() {
  const { data, isLoading } = useMlProfiles()
  const update = useUpdateMlProfiles()
  const remove = useDeleteMlProfile()

  const [addOpen, setAddOpen] = useState(false)

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Darkmem ML Profiles</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="bg-muted h-32 animate-pulse rounded" />
        </CardContent>
      </Card>
    )
  }

  const profiles = data?.profiles ?? {}
  const names = Object.keys(profiles).sort()

  const handleSaveTtl = (name: string, ttl: number) => {
    const next: Record<string, MlProfile> = {
      ...profiles,
      [name]: { ...profiles[name], ttl_seconds: ttl },
    }
    update.mutate(
      { profiles: next },
      {
        onSuccess: () => toast.success(`${name} TTL saved`),
        onError: (err) => toast.error(`Save failed: ${err.message}`),
      },
    )
  }

  const handleDelete = (name: string) => {
    if (!window.confirm(`Delete ML profile "${name}"?`)) return
    remove.mutate(
      { name },
      {
        onSuccess: () => toast.success(`${name} deleted`),
        onError: (err) => toast.error(`Delete failed: ${err.message}`),
      },
    )
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <div>
          <CardTitle className="text-sm">Darkmem ML Profiles</CardTitle>
          <p className="text-muted-foreground mt-1 text-xs">
            HuggingFace classifiers loaded into the backend for in-process
            inference. CPU-only. TTL of 0 means "never unload until backend
            stops".
          </p>
        </div>
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="mr-1 h-3.5 w-3.5" />
              Add ML Profile
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Add ML Profile</DialogTitle>
            </DialogHeader>
            <AddMlProfileForm
              existingNames={names}
              onClose={() => setAddOpen(false)}
              onCreate={(name, repo, ttl) => {
                const next: Record<string, MlProfile> = {
                  ...profiles,
                  [name]: { model_repo: repo, ttl_seconds: ttl },
                }
                update.mutate(
                  { profiles: next },
                  {
                    onSuccess: () => {
                      toast.success(`${name} created`)
                      setAddOpen(false)
                    },
                    onError: (err) =>
                      toast.error(`Create failed: ${err.message}`),
                  },
                )
              }}
            />
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent className="p-0">
        {names.length === 0 ? (
          <p className="text-muted-foreground px-4 py-3 text-xs">
            No ML profiles yet. Add one above.
          </p>
        ) : (
          <div className="divide-border divide-y">
            {names.map((name) => (
              <MlProfileRow
                key={name}
                name={name}
                profile={profiles[name]}
                onSaveTtl={(ttl) => handleSaveTtl(name, ttl)}
                onDelete={() => handleDelete(name)}
                disabled={update.isPending || remove.isPending}
              />
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function MlProfileRow({
  name,
  profile,
  onSaveTtl,
  onDelete,
  disabled,
}: {
  name: string
  profile: MlProfile
  onSaveTtl: (ttl: number) => void
  onDelete: () => void
  disabled: boolean
}) {
  const [ttl, setTtl] = useState<number>(profile.ttl_seconds)
  const dirty = ttl !== profile.ttl_seconds
  return (
    <div className="flex items-center gap-3 px-4 py-3">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <span className="truncate text-sm font-bold">{name}</span>
          <Badge variant="outline" className="font-mono text-[10px]">
            {profile.model_repo}
          </Badge>
          <Badge variant="secondary" className="text-[10px]">
            CPU
          </Badge>
        </div>
        <div className="text-muted-foreground mt-0.5 text-xs">
          {profile.ttl_seconds === 0
            ? "TTL: ∞ (never unload)"
            : `TTL: ${profile.ttl_seconds}s`}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <Input
          type="number"
          min={0}
          value={ttl}
          onChange={(e) => setTtl(Number(e.target.value))}
          className="h-8 w-24 text-xs"
        />
        <span className="text-muted-foreground text-[10px]">s</span>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2 text-xs"
          onClick={() => onSaveTtl(ttl)}
          disabled={!dirty || disabled}
        >
          Save
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="text-destructive hover:text-destructive h-7 px-2 text-xs"
          onClick={onDelete}
          disabled={disabled}
          aria-label={`Delete ML profile ${name}`}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  )
}

function AddMlProfileForm({
  existingNames,
  onClose,
  onCreate,
}: {
  existingNames: string[]
  onClose: () => void
  onCreate: (name: string, repo: string, ttl: number) => void
}) {
  const [name, setName] = useState("")
  const [repo, setRepo] = useState("darkraise/darkmem-classifier-v1")
  const [ttl, setTtl] = useState<number>(0)

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    if (existingNames.includes(name.trim())) {
      toast.error(`Profile "${name.trim()}" already exists`)
      return
    }
    if (!repo.trim()) {
      toast.error("Model repo is required")
      return
    }
    onCreate(name.trim(), repo.trim(), Math.max(0, ttl))
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div>
        <Label className="text-muted-foreground text-xs">Profile name</Label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. default-classifier"
          required
        />
      </div>
      <div>
        <Label className="text-muted-foreground text-xs">
          HuggingFace model repo
        </Label>
        <Input
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="user/model-name"
          className="font-mono"
          required
        />
        <p className="text-muted-foreground mt-1 text-[10px]">
          Public HF Hub repos only — no token configuration in this iteration.
        </p>
      </div>
      <div>
        <Label className="text-muted-foreground text-xs">TTL (seconds)</Label>
        <Input
          type="number"
          min={0}
          value={ttl}
          onChange={(e) => setTtl(Number(e.target.value))}
        />
        <p className="text-muted-foreground mt-1 text-[10px]">
          0 = never unload until backend restart. Otherwise the model is evicted
          after that many idle seconds.
        </p>
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit">Add</Button>
      </div>
    </form>
  )
}
