import { useEffect, useMemo, useState } from "react"
import {
  Card,
  CardContent,
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
import { CircleHelp, Trash2 } from "lucide-react"
import { toast } from "darkraise-ui/components/sonner"
import { Switch } from "darkraise-ui/components/switch"
import {
  useLlmProviders,
  useUpdateLlmProviders,
  useDeleteLlmProvider,
  type LlmProviderProfile,
} from "@/hooks/api"
import { API_KIND_OPTIONS } from "./api-kinds"
import { LLMProviderTestDialog } from "./LLMProviderTestDialog"
import { firstInvalidDirty } from "./dirty-save"

const TOKEN_SENTINEL = "***"

type DraftProfile = LlmProviderProfile & { _isNew?: boolean }
type DraftMap = Record<string, DraftProfile>

export function LLMProvidersPanel() {
  const { data, isLoading } = useLlmProviders()
  const update = useUpdateLlmProviders()
  const remove = useDeleteLlmProvider()

  const [draft, setDraft] = useState<DraftMap>({})
  const [newName, setNewName] = useState("")

  const stored: DraftMap = useMemo(() => {
    const out: DraftMap = {}
    for (const [name, profile] of Object.entries(data?.profiles ?? {})) {
      out[name] = { ...profile }
    }
    return out
  }, [data])

  useEffect(() => {
    setDraft({})
  }, [stored])

  const merged: DraftMap = useMemo(
    () => ({ ...stored, ...draft }),
    [stored, draft],
  )
  const profileNames = Object.keys(merged).sort()

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

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">LLM provider profiles</CardTitle>
        </CardHeader>
        <CardContent>
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

  const addProfile = () => {
    const trimmed = newName.trim()
    if (!trimmed) return
    if (trimmed.includes("/") || trimmed.length > 64) {
      toast.error("Profile name must omit '/' and stay under 64 chars")
      return
    }
    if (merged[trimmed]) {
      toast.error(`Profile '${trimmed}' already exists`)
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
    setNewName("")
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

  const reset = () => setDraft({})

  const save = () => {
    if (!dirty) return
    // Validate only edited rows, so a pre-existing invalid row the user never
    // touched can't block saving an unrelated edit.
    const invalid = firstInvalidDirty(merged, dirtyNames, (p) => !p.base_url.trim())
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
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base">
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
                className="max-w-md text-base leading-relaxed"
              >
                A Provider is a connection (base URL, API key, API kind).
                Profiles bundle a Provider with a default model and params —
                those are managed in the LLM Profiles panel. Rotating an API key
                here updates every Profile (and every linked purpose) at once.
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </CardTitle>
        <p className="text-muted-foreground text-base">
          Connection settings only. A Profile picks one Provider plus a model
          and default parameters; a purpose picks a Profile.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {profileNames.length === 0 && (
          <p className="text-muted-foreground text-base">
            No Providers yet. Add one below to start sharing connection settings
            across Profiles and purposes.
          </p>
        )}

        <div className="space-y-3">
          {profileNames.map((name) => {
            const profile = merged[name]
            if (!profile) return null
            return (
              <ProfileRow
                key={name}
                name={name}
                profile={profile}
                isNew={!!draft[name]?._isNew}
                dirty={!!draft[name] && !profile._isNew}
                onPatch={(patchObj) => patch(name, patchObj)}
                onDelete={() => drop(name)}
                disabled={update.isPending || remove.isPending}
              />
            )
          })}
        </div>

        <div className="border-border flex items-center gap-2 border-t pt-3">
          <div className="flex flex-1 items-center gap-2">
            <Label htmlFor="new_provider_name" className="text-base">
              New Provider
            </Label>
            <Input
              id="new_provider_name"
              type="text"
              autoComplete="off"
              spellCheck={false}
              placeholder="e.g. openai-prod"
              value={newName}
              onChange={(e) => setNewName(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter") {
                  e.preventDefault()
                  addProfile()
                }
              }}
              className="h-8 max-w-xs text-base"
            />
          </div>
          <Button
            variant="outline"
            className="text-base"
            onClick={addProfile}
            disabled={!newName.trim()}
          >
            Add
          </Button>
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
            className="text-base"
            onClick={reset}
            disabled={!dirty || update.isPending}
          >
            Reset
          </Button>
          <Button
            className="text-base"
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
  onPatch: (patch: Partial<LlmProviderProfile>) => void
  onDelete: () => void
  disabled: boolean
}

function ProfileRow({
  name,
  profile,
  isNew,
  dirty,
  onPatch,
  onDelete,
  disabled,
}: RowProps) {
  const tokenIsMasked = profile.api_key === TOKEN_SENTINEL
  const supportsEmbedding = profile.supports_embedding ?? true
  const [testDialog, setTestDialog] = useState<"chat" | "embedding" | null>(
    null,
  )

  const openTest = (mode: "chat" | "embedding") => {
    if (isNew) {
      toast.error("Save the Provider before testing it")
      return
    }
    setTestDialog(mode)
  }

  return (
    <div className="border-border space-y-2 rounded-md border p-3">
      <LLMProviderTestDialog
        providerName={isNew ? null : name}
        mode={testDialog ?? "chat"}
        open={testDialog !== null}
        onOpenChange={(o) => {
          if (!o) setTestDialog(null)
        }}
      />
      <div className="flex items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <span className="font-mono text-base">{name}</span>
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
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            onClick={() => openTest("chat")}
            disabled={disabled || isNew}
            aria-label={`Test chat probe for ${name}`}
          >
            Test chat
          </Button>
          <Button
            variant="outline"
            onClick={() => openTest("embedding")}
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
            onClick={onDelete}
            disabled={disabled}
            aria-label={`Delete Provider ${name}`}
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div>
          <Label className="text-muted-foreground text-sm">Provider</Label>
          <Input
            type="text"
            value={profile.provider}
            onChange={(e) => onPatch({ provider: e.target.value })}
            className="h-8 text-base"
            placeholder="openai | ollama | anthropic"
          />
        </div>
        <div>
          <Label className="text-muted-foreground text-sm">API kind</Label>
          <Select
            value={profile.api_kind || "openai"}
            onValueChange={(value) => onPatch({ api_kind: value })}
          >
            <SelectTrigger className="border-border bg-background h-8 w-full rounded border px-2 text-base">
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
        </div>
        <div className="sm:col-span-2">
          <Label className="text-muted-foreground text-sm">Base URL</Label>
          <Input
            type="text"
            value={profile.base_url}
            onChange={(e) => onPatch({ base_url: e.target.value })}
            className="h-8 font-mono text-base"
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
            className="h-8 font-mono text-base"
            placeholder="(none — local provider)"
            autoComplete="off"
          />
        </div>
        <div className="border-border flex items-center justify-between border-t pt-2 sm:col-span-2">
          <div>
            <Label className="text-base">Supports embedding</Label>
            <p className="text-muted-foreground text-sm">
              Off when the vendor exposes only chat completions (Anthropic,
              DeepSeek today). Linking an off profile to the embedding purpose
              is blocked in the purpose card.
            </p>
          </div>
          <Switch
            checked={supportsEmbedding}
            onCheckedChange={(v) => onPatch({ supports_embedding: v })}
          />
        </div>
      </div>
    </div>
  )
}
