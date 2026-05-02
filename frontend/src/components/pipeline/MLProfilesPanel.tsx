import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
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
import { toast } from "sonner"
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
          <div className="h-32 bg-muted rounded animate-pulse" />
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
      <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
        <div>
          <CardTitle className="text-sm">Darkmem ML Profiles</CardTitle>
          <p className="text-xs text-muted-foreground mt-1">
            HuggingFace classifiers loaded into the backend for in-process inference.
            CPU-only. TTL of 0 means "never unload until backend stops".
          </p>
        </div>
        <Dialog open={addOpen} onOpenChange={setAddOpen}>
          <DialogTrigger asChild>
            <Button size="sm">
              <Plus className="h-3.5 w-3.5 mr-1" />
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
                    onError: (err) => toast.error(`Create failed: ${err.message}`),
                  },
                )
              }}
            />
          </DialogContent>
        </Dialog>
      </CardHeader>
      <CardContent className="p-0">
        {names.length === 0 ? (
          <p className="text-muted-foreground text-xs px-4 py-3">
            No ML profiles yet. Add one above.
          </p>
        ) : (
          <div className="divide-y divide-border">
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
    <div className="px-4 py-3 flex items-center gap-3">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-sm font-bold truncate">{name}</span>
          <Badge variant="outline" className="text-[10px] font-mono">
            {profile.model_repo}
          </Badge>
          <Badge variant="secondary" className="text-[10px]">CPU</Badge>
        </div>
        <div className="text-xs text-muted-foreground mt-0.5">
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
        <span className="text-[10px] text-muted-foreground">s</span>
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
          className="h-7 px-2 text-xs text-destructive hover:text-destructive"
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
        <Label className="text-xs text-muted-foreground">Profile name</Label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. default-classifier"
          required
        />
      </div>
      <div>
        <Label className="text-xs text-muted-foreground">HuggingFace model repo</Label>
        <Input
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="user/model-name"
          className="font-mono"
          required
        />
        <p className="text-[10px] text-muted-foreground mt-1">
          Public HF Hub repos only — no token configuration in this iteration.
        </p>
      </div>
      <div>
        <Label className="text-xs text-muted-foreground">
          TTL (seconds)
        </Label>
        <Input
          type="number"
          min={0}
          value={ttl}
          onChange={(e) => setTtl(Number(e.target.value))}
        />
        <p className="text-[10px] text-muted-foreground mt-1">
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
