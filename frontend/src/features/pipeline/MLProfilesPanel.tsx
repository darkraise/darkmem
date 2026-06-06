import { useState } from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import {
  NumberInput,
  NumberInputControl,
  NumberInputField,
  NumberInputTriggerGroup,
  NumberInputIncrementTrigger,
  NumberInputDecrementTrigger,
} from "darkraise-ui/components/number-input"
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
import { Skeleton } from "darkraise-ui/components/skeleton"
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
  const [confirmDeleteName, setConfirmDeleteName] = useState<string | null>(
    null,
  )

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="bg-foreground/5 border-border rounded-t-[calc(var(--radius)-1px)] border-b pb-4">
          <CardTitle className="text-lg tracking-wide uppercase">
            Darkmem ML Profiles
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <Skeleton className="h-32 rounded" />
        </CardContent>
      </Card>
    )
  }

  const profiles = data?.profiles ?? {}
  const names = Object.keys(profiles).sort()

  const handleSaveTtl = (name: string, ttl: number) => {
    const existing = profiles[name]
    if (!existing) return
    const next: Record<string, MlProfile> = {
      ...profiles,
      [name]: { ...existing, ttl_seconds: ttl },
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
    setConfirmDeleteName(name)
  }

  const confirmDelete = (name: string) => {
    remove.mutate(
      { name },
      {
        onSuccess: () => toast.success(`${name} deleted`),
        onError: (err) => toast.error(`Delete failed: ${err.message}`),
      },
    )
  }

  return (
    <>
      <Card>
        <CardHeader className="bg-foreground/5 border-border rounded-t-[calc(var(--radius)-1px)] border-b pb-4">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <div className="min-w-0">
              <CardTitle className="text-lg tracking-wide uppercase">
                Darkmem ML Profiles
              </CardTitle>
              <CardDescription>
                HuggingFace classifiers loaded into the backend for in-process
                inference. CPU-only. TTL of 0 means "never unload until backend
                stops".
              </CardDescription>
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
          </div>
        </CardHeader>
        <CardContent className="p-0">
          {names.length === 0 ? (
            <p className="text-muted-foreground px-4 py-3 text-base">
              No ML profiles yet. Add one above.
            </p>
          ) : (
            <div className="divide-border divide-y">
              {names.map((name) => {
                const profile = profiles[name]
                if (!profile) return null
                return (
                  <MlProfileRow
                    key={name}
                    name={name}
                    profile={profile}
                    onSaveTtl={(ttl) => handleSaveTtl(name, ttl)}
                    onDelete={() => handleDelete(name)}
                    disabled={update.isPending || remove.isPending}
                  />
                )
              })}
            </div>
          )}
        </CardContent>
      </Card>

      <AlertDialog
        open={!!confirmDeleteName}
        onOpenChange={(o) => !o && setConfirmDeleteName(null)}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Delete ML profile &ldquo;{confirmDeleteName}&rdquo;?
            </AlertDialogTitle>
            <AlertDialogDescription>
              The profile will be removed and unloaded from memory.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (confirmDeleteName) confirmDelete(confirmDeleteName)
                setConfirmDeleteName(null)
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
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
          <span className="truncate text-base font-bold">{name}</span>
          <Badge
            variant="outline"
            className="max-w-full truncate font-mono text-sm"
          >
            {profile.model_repo}
          </Badge>
          <Badge variant="secondary" className="text-sm">
            CPU
          </Badge>
        </div>
        <div className="text-muted-foreground mt-0.5 text-base">
          {profile.ttl_seconds === 0
            ? "TTL: ∞ (never unload)"
            : `TTL: ${profile.ttl_seconds}s`}
        </div>
      </div>
      <div className="flex items-center gap-2">
        <NumberInput
          min={0}
          value={ttl}
          onValueChange={(d) =>
            setTtl(Number.isNaN(d.valueAsNumber) ? 0 : d.valueAsNumber)
          }
          className="h-9 w-28"
        >
          <NumberInputControl>
            <NumberInputField className="text-base" />
            <NumberInputTriggerGroup>
              <NumberInputIncrementTrigger />
              <NumberInputDecrementTrigger />
            </NumberInputTriggerGroup>
          </NumberInputControl>
        </NumberInput>
        <span className="text-muted-foreground text-sm">s</span>
        <Button
          variant="ghost"
          size="sm"
          className="h-9 px-2 text-base"
          onClick={() => onSaveTtl(ttl)}
          disabled={!dirty || disabled}
        >
          Save
        </Button>
        <Button
          variant="ghost"
          size="sm"
          className="text-destructive hover:text-destructive h-9 px-2 text-base"
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
        <Label className="text-muted-foreground text-base">Profile name</Label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. default-classifier"
          required
        />
      </div>
      <div>
        <Label className="text-muted-foreground text-base">
          HuggingFace model repo
        </Label>
        <Input
          value={repo}
          onChange={(e) => setRepo(e.target.value)}
          placeholder="user/model-name"
          className="font-mono"
          required
        />
        <p className="text-muted-foreground mt-1 text-sm">
          Public HF Hub repos only — no token configuration in this iteration.
        </p>
      </div>
      <div>
        <Label className="text-muted-foreground text-base">TTL (seconds)</Label>
        <NumberInput
          min={0}
          value={ttl}
          onValueChange={(d) =>
            setTtl(Number.isNaN(d.valueAsNumber) ? 0 : d.valueAsNumber)
          }
        >
          <NumberInputControl>
            <NumberInputField />
            <NumberInputTriggerGroup>
              <NumberInputIncrementTrigger />
              <NumberInputDecrementTrigger />
            </NumberInputTriggerGroup>
          </NumberInputControl>
        </NumberInput>
        <p className="text-muted-foreground mt-1 text-sm">
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
