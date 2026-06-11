import { useEffect, useMemo, useRef, useState } from "react"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { Button } from "darkraise-ui/components/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { Badge } from "darkraise-ui/components/badge"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
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
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Plus,
  Trash2,
} from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "darkraise-ui/components/dialog"
import { toast } from "darkraise-ui/components/sonner"
import { Switch } from "darkraise-ui/components/switch"
import {
  useLlmProviders,
  useUpdateLlmProviders,
  useDeleteLlmProvider,
  useLlmProfiles,
  type LlmProviderProfile,
} from "@/hooks/api"
import { API_KIND_OPTIONS, apiKindLabel, findApiKind } from "./api-kinds"
import { LLMProviderTestDialog } from "./LLMProviderTestDialog"
import { firstInvalidDirty } from "./dirty-save"

const TOKEN_SENTINEL = "***"

type DraftProfile = LlmProviderProfile & { _isNew?: boolean }
type DraftMap = Record<string, DraftProfile>

export function LLMProvidersPanel() {
  const { data, isLoading } = useLlmProviders()
  const { data: profilesResp } = useLlmProfiles()
  const update = useUpdateLlmProviders()
  const remove = useDeleteLlmProvider()

  const [draft, setDraft] = useState<DraftMap>({})
  const [addOpen, setAddOpen] = useState(false)

  const stored: DraftMap = useMemo(() => {
    const out: DraftMap = {}
    for (const [name, profile] of Object.entries(data?.profiles ?? {})) {
      out[name] = { ...profile }
    }
    return out
  }, [data])

  const merged: DraftMap = useMemo(
    () => ({ ...stored, ...draft }),
    [stored, draft],
  )
  const profileNames = Object.keys(merged).sort()

  // Which Profiles reference each Provider — surfaced in the delete confirm so
  // the operator sees the blast radius before removing a connection.
  const referencingByProvider = useMemo(() => {
    const out: Record<string, string[]> = {}
    for (const [pname, prof] of Object.entries(profilesResp?.profiles ?? {})) {
      if (prof.provider_ref) (out[prof.provider_ref] ??= []).push(pname)
    }
    return out
  }, [profilesResp])

  const dirtyNames = useMemo(() => {
    const names = new Set<string>()
    for (const name of Object.keys(draft)) {
      const next = draft[name]
      const prev = stored[name]
      if (!next) continue
      if (
        !prev ||
        next.provider !== prev.provider ||
        next.base_url !== prev.base_url ||
        next.api_key !== prev.api_key ||
        next.api_kind !== prev.api_kind ||
        next.supports_embedding !== prev.supports_embedding
      ) {
        names.add(name)
      }
    }
    return names
  }, [draft, stored])
  const dirty = dirtyNames.size > 0

  // Mirror dirty state into a ref so the stored-sync effect can read it without
  // depending on draft (which would re-run and wipe the edit it just captured).
  const dirtyRef = useRef(dirty)
  dirtyRef.current = dirty
  useEffect(() => {
    // Don't stomp in-progress edits when the query refetches (e.g. after
    // window-focus invalidation). Reset only when there are no unsaved rows.
    if (dirtyRef.current) return
    setDraft({})
  }, [stored])

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="bg-foreground/5 border-border rounded-t-[calc(var(--radius)-1px)] border-b pb-4">
          <CardTitle className="text-lg tracking-wide uppercase">
            LLM Providers
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="bg-muted h-32 animate-pulse rounded" />
        </CardContent>
      </Card>
    )
  }

  const patch = (name: string, patch: Partial<LlmProviderProfile>) => {
    setDraft((prev) => ({
      ...prev,
      [name]: { ...(prev[name] ?? merged[name]), ...patch } as DraftProfile,
    }))
  }

  const addProvider = (name: string) => {
    const trimmed = name.trim()
    if (!trimmed) return
    if (trimmed.includes("/") || trimmed.length > 64) {
      toast.error("Provider name must omit '/' and stay under 64 chars")
      return
    }
    if (merged[trimmed]) {
      toast.error(`Provider '${trimmed}' already exists`)
      return
    }
    setDraft((prev) => ({
      ...prev,
      [trimmed]: {
        provider: "openai",
        base_url: "",
        api_key: "",
        api_kind: "openai",
        supports_embedding: true,
        _isNew: true,
      },
    }))
    setAddOpen(false)
  }

  const drop = (name: string) => {
    if (stored[name]) {
      remove.mutate(
        { name },
        {
          onSuccess: () => toast.success(`Profile '${name}' deleted`),
          onError: (err) => toast.error(`Delete failed: ${err.message}`),
        },
      )
    } else {
      // Just clear from draft if it was never saved.
      setDraft((prev) => {
        const next = { ...prev }
        delete next[name]
        return next
      })
    }
  }

  const reset = () => {
    if (
      dirty &&
      !window.confirm("Discard all unsaved Provider changes?")
    ) {
      return
    }
    setDraft({})
  }

  const save = () => {
    if (!dirty) return
    // Validate only edited rows, so a pre-existing invalid row the user never
    // touched can't block saving an unrelated edit.
    const invalid = firstInvalidDirty(
      merged,
      dirtyNames,
      (p) => !p.base_url.trim(),
    )
    if (invalid) {
      toast.error(`Profile '${invalid}' needs a base URL`)
      return
    }
    const profiles: Record<string, LlmProviderProfile> = {}
    for (const name of Object.keys(merged)) {
      const p = merged[name]
      if (!p) continue
      profiles[name] = {
        provider: p.provider.trim() || "openai",
        base_url: p.base_url.trim(),
        api_key: p.api_key ?? "",
        api_kind: p.api_kind || "openai",
        supports_embedding: p.supports_embedding ?? true,
      }
    }
    update.mutate(
      { profiles },
      {
        onSuccess: () => toast.success("Provider profiles saved"),
        onError: (err) => toast.error(`Save failed: ${err.message}`),
      },
    )
  }

  return (
    <Card>
      <CardHeader className="bg-foreground/5 border-border rounded-t-[calc(var(--radius)-1px)] border-b pb-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <CardTitle className="flex items-center gap-2 text-lg tracking-wide uppercase">
              LLM Providers
              <TooltipProvider delayDuration={150}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      type="button"
                      aria-label="What are LLM Providers?"
                      className="text-muted-foreground hover:text-foreground focus-visible:ring-ring inline-flex items-center justify-center rounded-sm focus-visible:ring-2 focus-visible:outline-none"
                    >
                      <CircleHelp className="h-3.5 w-3.5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent
                    side="top"
                    className="max-w-md leading-relaxed normal-case"
                  >
                    A Provider is a connection (base URL, API key, API kind).
                    Profiles bundle a Provider with a default model and params —
                    those are managed in the LLM Profiles panel. Rotating an API
                    key here updates every Profile (and every linked purpose) at
                    once.
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </CardTitle>
            <CardDescription>
              Connection settings only. A Profile picks one Provider plus a
              model and default parameters; a purpose picks a Profile.
            </CardDescription>
          </div>
          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="mr-1 h-3.5 w-3.5" />
                Add Provider
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add LLM Provider</DialogTitle>
              </DialogHeader>
              <AddProviderForm
                existingNames={profileNames}
                onClose={() => setAddOpen(false)}
                onCreate={addProvider}
              />
            </DialogContent>
          </Dialog>
        </div>
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        {profileNames.length === 0 && (
          <p className="text-muted-foreground text-sm">
            No Providers yet. Use “Add Provider” above to start sharing
            connection settings across Profiles and purposes.
          </p>
        )}

        <div className="space-y-2">
          {profileNames.map((name) => {
            const profile = merged[name]
            if (!profile) return null
            return (
              <ProviderRow
                key={name}
                name={name}
                profile={profile}
                isNew={!!draft[name]?._isNew}
                dirty={!!draft[name] && !profile._isNew}
                referencingProfiles={referencingByProvider[name] ?? []}
                onPatch={(patchObj) => patch(name, patchObj)}
                onDelete={() => drop(name)}
                disabled={update.isPending || remove.isPending}
              />
            )
          })}
        </div>

        <div className="border-border flex items-center justify-end gap-2 border-t pt-3">
          {dirty && (
            <span className="text-muted-foreground mr-auto text-sm">
              {Object.keys(draft).length} unsaved change
              {Object.keys(draft).length === 1 ? "" : "s"}
            </span>
          )}
          <Button
            variant="ghost"
            onClick={reset}
            disabled={!dirty || update.isPending}
          >
            Reset
          </Button>
          <Button
            onClick={save}
            disabled={!dirty || update.isPending}
          >
            {update.isPending ? "Saving…" : "Save"}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

interface RowProps {
  name: string
  profile: DraftProfile
  isNew: boolean
  dirty: boolean
  referencingProfiles: string[]
  onPatch: (patch: Partial<LlmProviderProfile>) => void
  onDelete: () => void
  disabled: boolean
}

function ProviderRow({
  name,
  profile,
  isNew,
  dirty,
  referencingProfiles,
  onPatch,
  onDelete,
  disabled,
}: RowProps) {
  const tokenIsMasked = profile.api_key === TOKEN_SENTINEL
  const supportsEmbedding = profile.supports_embedding ?? true
  const [open, setOpen] = useState(isNew)
  const [testDialog, setTestDialog] = useState<"chat" | "embedding" | null>(
    null,
  )
  const [confirmDelete, setConfirmDelete] = useState(false)
  const panelId = `llm-provider-${name}-panel`
  const note = findApiKind(profile.api_kind)?.note

  const openTest = (mode: "chat" | "embedding") => {
    if (isNew) {
      toast.error("Save the Provider before testing it")
      return
    }
    setTestDialog(mode)
  }

  const handleDeleteClick = () => {
    // Unsaved rows have nothing on the server — clear locally with no confirm.
    if (isNew) {
      onDelete()
      return
    }
    setConfirmDelete(true)
  }

  return (
    <Card className={open ? "border-primary" : ""}>
      <LLMProviderTestDialog
        providerName={isNew ? null : name}
        mode={testDialog ?? "chat"}
        open={testDialog !== null}
        onOpenChange={(o) => {
          if (!o) setTestDialog(null)
        }}
      />
      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete provider “{name}”?</AlertDialogTitle>
            <AlertDialogDescription>
              Profiles that reference it will fail validation until repointed.
              {referencingProfiles.length > 0 &&
                ` ${referencingProfiles.length} Profile${
                  referencingProfiles.length === 1 ? "" : "s"
                } reference this provider.`}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                setConfirmDelete(false)
                onDelete()
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <div className="flex items-start justify-between gap-2 p-2">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-controls={panelId}
          className="hover:bg-muted/40 flex min-w-0 flex-1 flex-col items-start gap-0.5 rounded-md p-1 text-left"
        >
          <span className="flex flex-wrap items-center gap-2">
            <span className="flex items-center gap-1 font-mono text-sm font-semibold">
              {open ? (
                <ChevronDown className="h-4 w-4 shrink-0" aria-hidden />
              ) : (
                <ChevronRight className="h-4 w-4 shrink-0" aria-hidden />
              )}
              {name}
            </span>
            {isNew && (
              <Badge variant="default" className="text-sm">
                new
              </Badge>
            )}
            {!isNew && dirty && (
              <Badge variant="secondary" className="text-sm">
                edited
              </Badge>
            )}
            {tokenIsMasked && (
              <Badge variant="outline" className="text-sm">
                key configured
              </Badge>
            )}
            {!supportsEmbedding && (
              <Badge variant="outline" className="text-sm">
                no embedding
              </Badge>
            )}
          </span>
          <span className="text-muted-foreground truncate font-mono text-sm">
            {apiKindLabel(profile.api_kind)}
            {profile.base_url ? ` · ${profile.base_url}` : ""}
          </span>
        </button>
        <div className="flex shrink-0 items-center gap-1">
          <Button
            variant="outline"
            onClick={(e) => {
              e.stopPropagation()
              openTest("chat")
            }}
            disabled={disabled || isNew}
            aria-label={`Test chat probe for ${name}`}
          >
            Test chat
          </Button>
          <Button
            variant="outline"
            onClick={(e) => {
              e.stopPropagation()
              openTest("embedding")
            }}
            disabled={disabled || isNew || !supportsEmbedding}
            aria-label={`Test embedding probe for ${name}`}
            title={
              !supportsEmbedding
                ? "Vendor doesn't expose an embeddings endpoint"
                : `Test embedding probe for ${name}`
            }
          >
            Test embed
          </Button>
          <Button
            variant="ghost"
            className="text-destructive hover:text-destructive"
            onClick={(e) => {
              e.stopPropagation()
              handleDeleteClick()
            }}
            disabled={disabled}
            aria-label={`Delete Provider ${name}`}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>

      {open && (
        <CardContent className="p-0">
          <div
            id={panelId}
            className="grid grid-cols-1 gap-2 p-4 pt-0 sm:grid-cols-2"
            aria-label={`${name} connection settings`}
          >
            <div className="sm:col-span-2">
              <Label className="text-muted-foreground text-sm">API kind</Label>
              <Select
                value={profile.api_kind || "openai"}
                onValueChange={(value) => onPatch({ api_kind: value })}
              >
                <SelectTrigger
                  className="border-border bg-background h-9 w-full rounded border px-2"
                  title="Wire protocol used to talk to the configured base URL. Ollama native exposes think:false to disable qwen3-style reasoning. Vendor-specific kinds currently route through the OpenAI-compatible path."
                >
                  <SelectValue placeholder="Select API kind…" />
                </SelectTrigger>
                <SelectContent>
                  {API_KIND_OPTIONS.map((opt) => (
                    <SelectItem key={opt.value} value={opt.value}>
                      {opt.label}
                      {opt.note ? ` — ${opt.note}` : ""}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {note && (
                <p className="text-muted-foreground mt-1 text-sm">
                  Routes through the OpenAI-compatible path.
                </p>
              )}
            </div>
            <div className="sm:col-span-2">
              <Label className="text-muted-foreground text-sm">
                Display label (cosmetic)
              </Label>
              <Input
                type="text"
                value={profile.provider}
                onChange={(e) => onPatch({ provider: e.target.value })}
                className="h-9"
                placeholder="e.g. OpenAI prod"
              />
              <p className="text-muted-foreground mt-1 text-sm">
                Display-only: shown in the Pipeline resolved summary. Changing it
                has no effect on connectivity and does not detach linked
                Profiles or purposes.
              </p>
            </div>
            <div className="sm:col-span-2">
              <Label className="text-muted-foreground text-sm">Base URL</Label>
              <Input
                type="text"
                value={profile.base_url}
                onChange={(e) => onPatch({ base_url: e.target.value })}
                className="h-9 font-mono"
                placeholder="https://api.openai.com/v1"
              />
            </div>
            <div className="sm:col-span-2">
              <Label className="text-muted-foreground text-sm">
                API key {tokenIsMasked && "(leave *** to keep stored)"}
              </Label>
              <Input
                type="password"
                value={profile.api_key ?? ""}
                onChange={(e) => onPatch({ api_key: e.target.value })}
                className="h-9 font-mono"
                placeholder="(none — local provider)"
                autoComplete="off"
              />
            </div>
            <div className="border-border flex items-center justify-between border-t pt-2 sm:col-span-2">
              <div>
                <Label>Supports embedding</Label>
                <p className="text-muted-foreground text-sm">
                  Off when the vendor exposes only chat completions (Anthropic,
                  DeepSeek today). Linking an off profile to the embedding
                  purpose is blocked in the purpose card.
                </p>
              </div>
              <Switch
                checked={supportsEmbedding}
                onCheckedChange={(v) => onPatch({ supports_embedding: v })}
              />
            </div>
          </div>
        </CardContent>
      )}
    </Card>
  )
}

function AddProviderForm({
  existingNames,
  onClose,
  onCreate,
}: {
  existingNames: string[]
  onClose: () => void
  onCreate: (name: string) => void
}) {
  const [name, setName] = useState("")

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    const trimmed = name.trim()
    if (!trimmed) return
    if (existingNames.includes(trimmed)) {
      toast.error(`Provider "${trimmed}" already exists`)
      return
    }
    onCreate(trimmed)
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div>
        <Label className="text-muted-foreground">Provider name</Label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. openai-prod"
          autoComplete="off"
          spellCheck={false}
          required
        />
        <p className="text-muted-foreground mt-1 text-sm">
          A short identifier. Set the base URL, API key, and API kind after it’s
          created.
        </p>
      </div>
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={!name.trim()}>
          Add
        </Button>
      </div>
    </form>
  )
}
