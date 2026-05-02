import { useEffect, useMemo, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { Button } from "darkraise-ui/components/button"
import { Badge } from "darkraise-ui/components/badge"
import { Switch } from "darkraise-ui/components/switch"
import { Textarea } from "darkraise-ui/components/textarea"
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "darkraise-ui/components/tabs"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import { CircleHelp, Plus, Trash2 } from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "darkraise-ui/components/dialog"
import { toast } from "sonner"
import {
  useLlmProfiles,
  useUpdateLlmProfiles,
  useDeleteLlmProfile,
  useLlmProviders,
  useProviderModels,
  type LlmProfile,
} from "@/hooks/api"

type DraftProfile = LlmProfile & { _isNew?: boolean; _paramsText?: string }
type DraftMap = Record<string, DraftProfile>

type GroupBy = "provider" | "purpose"
const GROUP_BY_STORAGE_KEY = "darkmem.llm-profiles.group-by"

// Pipeline purposes recognised by the rest of the system. Profile names
// usually contain one of these as a hyphen-separated segment (e.g.
// "openai-extraction", "zai-flash-extraction"). Anything that doesn't
// match falls into the "other" tab.
const KNOWN_PURPOSES = [
  "embedding",
  "extraction",
  "classification",
  "reasoning",
  "summarization",
  "reranker",
] as const
type KnownPurpose = (typeof KNOWN_PURPOSES)[number]
const KNOWN_PURPOSE_SET = new Set<string>(KNOWN_PURPOSES)

function inferPurpose(profileName: string, isEmbedding: boolean): KnownPurpose | "other" {
  // Walk segments right-to-left so a name like "openai-embedding-large"
  // routes to "embedding" (the keyword), not the trailing variant tag.
  const segments = profileName.toLowerCase().split("-")
  for (let i = segments.length - 1; i >= 0; i--) {
    if (KNOWN_PURPOSE_SET.has(segments[i])) {
      return segments[i] as KnownPurpose
    }
  }
  if (isEmbedding) return "embedding"
  return "other"
}

function readStoredGroupBy(): GroupBy {
  if (typeof window === "undefined") return "provider"
  const raw = window.localStorage.getItem(GROUP_BY_STORAGE_KEY)
  return raw === "purpose" ? "purpose" : "provider"
}

export function LLMProfilesPanel() {
  const { data: profilesResp, isLoading } = useLlmProfiles()
  const { data: providersResp } = useLlmProviders()
  const update = useUpdateLlmProfiles()
  const remove = useDeleteLlmProfile()
  const [draft, setDraft] = useState<DraftMap>({})

  const stored: DraftMap = useMemo(() => {
    const out: DraftMap = {}
    for (const [name, profile] of Object.entries(profilesResp?.profiles ?? {})) {
      out[name] = {
        ...profile,
        _paramsText: Object.keys(profile.params || {}).length
          ? JSON.stringify(profile.params, null, 2)
          : "",
      }
    }
    return out
  }, [profilesResp])

  useEffect(() => {
    setDraft({})
  }, [stored])

  const merged: DraftMap = useMemo(() => ({ ...stored, ...draft }), [stored, draft])
  const profileNames = Object.keys(merged).sort()
  const providerNames = Object.keys(providersResp?.profiles ?? {}).sort()

  const [groupBy, setGroupBy] = useState<GroupBy>(readStoredGroupBy)
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(GROUP_BY_STORAGE_KEY, groupBy)
    }
  }, [groupBy])

  // Bucket profile names by the chosen grouping. Keys are the tab labels;
  // values are the profile names that belong in each tab.
  const groups: Record<string, string[]> = useMemo(() => {
    const out: Record<string, string[]> = {}
    if (groupBy === "provider") {
      for (const name of profileNames) {
        const key = merged[name]?.provider_ref || "(unset)"
        ;(out[key] ??= []).push(name)
      }
    } else {
      for (const name of profileNames) {
        const key = inferPurpose(name, !!merged[name]?.is_embedding)
        ;(out[key] ??= []).push(name)
      }
    }
    return out
  }, [profileNames, merged, groupBy])

  const groupKeys = useMemo(() => {
    const keys = Object.keys(groups)
    if (groupBy === "purpose") {
      // Stable purpose order, with unknown buckets ("other") at the end.
      const order = [...KNOWN_PURPOSES, "other"]
      return keys.sort(
        (a, b) => order.indexOf(a as KnownPurpose) - order.indexOf(b as KnownPurpose),
      )
    }
    return keys.sort()
  }, [groups, groupBy])

  const [activeGroup, setActiveGroup] = useState<string>("")
  useEffect(() => {
    // Pick the first group when the available list changes; preserve the
    // current selection if it's still valid.
    if (groupKeys.length === 0) {
      setActiveGroup("")
      return
    }
    setActiveGroup((prev) => (prev && groupKeys.includes(prev) ? prev : groupKeys[0]))
  }, [groupKeys])

  const dirty = Object.keys(draft).length > 0

  const patch = (name: string, p: Partial<DraftProfile>) => {
    setDraft((prev) => ({
      ...prev,
      [name]: { ...(prev[name] ?? merged[name]), ...p } as DraftProfile,
    }))
  }

  const [addOpen, setAddOpen] = useState(false)

  const addProfile = (
    name: string,
    providerRef: string,
    purpose: KnownPurpose,
  ) => {
    const trimmed = name.trim()
    if (!trimmed) return
    if (trimmed.includes("/") || trimmed.length > 64) {
      toast.error("Profile name must omit '/' and stay under 64 chars")
      return
    }
    if (merged[trimmed]) {
      toast.error(`Profile '${trimmed}' already exists`)
      return
    }
    if (providerNames.length === 0) {
      toast.error("Add an LLM Provider first")
      return
    }
    setDraft((prev) => ({
      ...prev,
      [trimmed]: {
        provider_ref: providerRef,
        model: "",
        params: {},
        is_embedding: purpose === "embedding",
        reasoning: purpose === "reasoning",
        purpose,
        _isNew: true,
        _paramsText: "",
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
    const profiles: Record<string, LlmProfile> = {}
    for (const name of Object.keys(merged)) {
      const p = merged[name]
      if (!p.provider_ref || !providerNames.includes(p.provider_ref)) {
        toast.error(`Profile '${name}' references an unknown Provider`)
        return
      }
      if (!p.model.trim()) {
        toast.error(`Profile '${name}' needs a model`)
        return
      }
      let params: Record<string, unknown> = {}
      const text = p._paramsText?.trim() ?? ""
      if (text) {
        try {
          params = JSON.parse(text)
          if (typeof params !== "object" || Array.isArray(params)) {
            throw new Error("must be a JSON object")
          }
        } catch (err) {
          toast.error(`Profile '${name}' has invalid params JSON: ${(err as Error).message}`)
          return
        }
      }
      profiles[name] = {
        provider_ref: p.provider_ref,
        model: p.model.trim(),
        params,
        is_embedding: !!p.is_embedding,
        reasoning: p.is_embedding ? false : !!p.reasoning,
        purpose: p.purpose ?? null,
      }
    }
    update.mutate(
      { profiles },
      {
        onSuccess: () => toast.success("LLM Profiles saved"),
        onError: (err) => toast.error(`Save failed: ${err.message}`),
      },
    )
  }

  if (isLoading) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">LLM Profiles</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="h-32 bg-muted rounded animate-pulse" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          LLM Profiles
          <TooltipProvider delayDuration={150}>
            <Tooltip>
              <TooltipTrigger asChild>
                <button
                  type="button"
                  aria-label="What are LLM Profiles?"
                  className="text-muted-foreground hover:text-foreground inline-flex items-center justify-center rounded-sm focus-visible:ring-ring focus-visible:ring-2 focus-visible:outline-none"
                >
                  <CircleHelp className="h-3.5 w-3.5" />
                </button>
              </TooltipTrigger>
              <TooltipContent side="top" className="max-w-md text-xs leading-relaxed">
                A Profile is a preset for one purpose: a Provider plus a
                model, default params, and the purpose-style flags
                (embedding-only, reasoning-enabled). Pick a Profile in
                the LLM purpose card on the Pipeline page to populate
                the form with these defaults.
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
        </CardTitle>
        <p className="text-muted-foreground text-xs">
          Reusable per-purpose presets. Pick a Provider, a model, and
          defaults; the purpose card uses these as starting values.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        {profileNames.length === 0 && (
          <p className="text-muted-foreground text-xs">
            No Profiles yet. Add one below.
          </p>
        )}

        {profileNames.length > 0 && (
          <div className="flex items-center gap-2">
            <Label htmlFor="profiles_group_by" className="text-xs">Group by</Label>
            <select
              id="profiles_group_by"
              value={groupBy}
              onChange={(e) => setGroupBy(e.target.value as GroupBy)}
              className="h-8 text-xs rounded border border-border bg-background px-2"
            >
              <option value="provider">Provider</option>
              <option value="purpose">Purpose</option>
            </select>
            <span className="text-[10px] text-muted-foreground">
              {profileNames.length} profile{profileNames.length === 1 ? "" : "s"} across {groupKeys.length} {groupBy === "provider" ? "provider" : "purpose"}{groupKeys.length === 1 ? "" : "s"}
            </span>
          </div>
        )}

        {profileNames.length > 0 && groupKeys.length > 0 && (
          <Tabs value={activeGroup} onValueChange={setActiveGroup}>
            <TabsList className="flex-wrap">
              {groupKeys.map((key) => (
                <TabsTrigger key={key} value={key} className="text-xs">
                  {key}
                  <Badge variant="secondary" className="ml-1.5 text-[9px]">
                    {groups[key].length}
                  </Badge>
                </TabsTrigger>
              ))}
            </TabsList>
            {groupKeys.map((key) => (
              <TabsContent key={key} value={key} className="space-y-3 mt-3">
                {groups[key].map((name) => (
                  <ProfileRow
                    key={name}
                    name={name}
                    profile={merged[name]}
                    isNew={!!draft[name]?._isNew}
                    dirty={!!draft[name] && !merged[name]._isNew}
                    providerNames={providerNames}
                    onPatch={(p) => patch(name, p)}
                    onDelete={() => drop(name)}
                    disabled={update.isPending || remove.isPending}
                  />
                ))}
              </TabsContent>
            ))}
          </Tabs>
        )}

        <div className="border-t border-border pt-3 flex items-center justify-end">
          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger asChild>
              <Button variant="outline">
                <Plus className="h-3.5 w-3.5 mr-1" />
                Add Profile
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Add LLM Profile</DialogTitle>
              </DialogHeader>
              <AddProfileForm
                providerNames={providerNames}
                existingNames={profileNames}
                onClose={() => setAddOpen(false)}
                onCreate={addProfile}
              />
            </DialogContent>
          </Dialog>
        </div>

        <div className="flex items-center justify-end gap-2 border-t border-border pt-3">
          {dirty && (
            <span className="text-[10px] text-muted-foreground mr-auto">
              {Object.keys(draft).length} unsaved change
              {Object.keys(draft).length === 1 ? "" : "s"}
            </span>
          )}
          <Button variant="ghost" onClick={reset} disabled={!dirty || update.isPending}>
            Reset
          </Button>
          <Button onClick={save} disabled={!dirty || update.isPending}>
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
  providerNames: string[]
  onPatch: (p: Partial<DraftProfile>) => void
  onDelete: () => void
  disabled: boolean
}

function ProfileRow({ name, profile, isNew, dirty, providerNames, onPatch, onDelete, disabled }: RowProps) {
  const { data: modelsResp, isLoading: modelsLoading } = useProviderModels(
    profile.provider_ref || null,
    !!profile.provider_ref,
  )
  return (
    <div className="rounded-md border border-border p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-mono">{name}</span>
          {isNew && <Badge variant="default" className="text-[9px]">new</Badge>}
          {!isNew && dirty && <Badge variant="secondary" className="text-[9px]">edited</Badge>}
          {profile.is_embedding && (
            <Badge variant="outline" className="text-[9px]">embedding</Badge>
          )}
          {profile.reasoning && !profile.is_embedding && (
            <Badge variant="outline" className="text-[9px]">reasoning</Badge>
          )}
        </div>
        <Button
          variant="ghost"
          className="text-destructive hover:text-destructive"
          onClick={onDelete}
          disabled={disabled}
          aria-label={`Delete Profile ${name}`}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        <div>
          <Label className="text-[10px] text-muted-foreground">Provider</Label>
          <select
            value={profile.provider_ref}
            onChange={(e) => onPatch({ provider_ref: e.target.value, model: "" })}
            className="h-9 w-full text-sm rounded border border-border bg-background px-2"
          >
            {providerNames.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>
        <div>
          <Label className="text-[10px] text-muted-foreground">Model</Label>
          {/* Datalist combobox: fetched models autocomplete, but free-text
              entry still works. Vendor /v1/models endpoints are sometimes
              incomplete (e.g., z.ai omits glm-4.5-flash), so a hard select
              would lock the user out of valid models. */}
          <Input
            type="text"
            list={`models-${profile.provider_ref}`}
            value={profile.model}
            onChange={(e) => onPatch({ model: e.target.value })}
            placeholder={
              modelsLoading ? "fetching models…" : "model id (e.g. gpt-4o-mini)"
            }
            className="font-mono"
          />
          {modelsResp && modelsResp.models.length > 0 && (
            <datalist id={`models-${profile.provider_ref}`}>
              {modelsResp.models.map((m) => (
                <option key={m} value={m} />
              ))}
            </datalist>
          )}
          {modelsResp?.error && (
            <p className="text-[10px] text-destructive mt-1">{modelsResp.error}</p>
          )}
          {modelsResp && modelsResp.models.length > 0 && (
            <p className="text-[10px] text-muted-foreground mt-1">
              {modelsResp.models.length} models from vendor — type to filter
              or enter a name not in the list.
            </p>
          )}
        </div>
      </div>
      <div>
        <Label className="text-[10px] text-muted-foreground">
          Default params (JSON object, optional)
        </Label>
        <Textarea
          value={profile._paramsText ?? ""}
          onChange={(e) => onPatch({ _paramsText: e.target.value })}
          rows={3}
          className="text-xs font-mono"
          placeholder='{"temperature": 0.2}'
        />
      </div>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 border-t border-border pt-2">
        <div className="flex items-center justify-between">
          <Label className="text-xs">Embedding profile</Label>
          <Switch
            checked={!!profile.is_embedding}
            onCheckedChange={(v) => onPatch({ is_embedding: v, reasoning: v ? false : profile.reasoning })}
          />
        </div>
        <div className="flex items-center justify-between">
          <Label className="text-xs">Reasoning enabled</Label>
          <Switch
            checked={!!profile.reasoning}
            onCheckedChange={(v) => onPatch({ reasoning: v })}
            disabled={!!profile.is_embedding}
          />
        </div>
      </div>
    </div>
  )
}

function AddProfileForm({
  providerNames,
  existingNames,
  onClose,
  onCreate,
}: {
  providerNames: string[]
  existingNames: string[]
  onClose: () => void
  onCreate: (name: string, providerRef: string, purpose: KnownPurpose) => void
}) {
  const [name, setName] = useState("")
  const [providerRef, setProviderRef] = useState(providerNames[0] ?? "")
  const [purpose, setPurpose] = useState<KnownPurpose>("extraction")

  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return
    if (existingNames.includes(name.trim())) {
      toast.error(`Profile "${name.trim()}" already exists`)
      return
    }
    if (!providerRef) {
      toast.error("Pick a Provider")
      return
    }
    onCreate(name.trim(), providerRef, purpose)
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div>
        <Label className="text-xs text-muted-foreground">Profile name</Label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. openai-classification-fast"
          required
        />
      </div>
      <div className="grid grid-cols-2 gap-3">
        <div>
          <Label className="text-xs text-muted-foreground">Provider</Label>
          <select
            value={providerRef}
            onChange={(e) => setProviderRef(e.target.value)}
            className="h-9 w-full text-sm rounded border border-border bg-background px-2"
            required
          >
            {providerNames.length === 0 && <option value="">(no providers — add one first)</option>}
            {providerNames.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>
        <div>
          <Label className="text-xs text-muted-foreground">Purpose</Label>
          <select
            value={purpose}
            onChange={(e) => setPurpose(e.target.value as KnownPurpose)}
            className="h-9 w-full text-sm rounded border border-border bg-background px-2"
            required
          >
            {KNOWN_PURPOSES.map((p) => (
              <option key={p} value={p}>{p}</option>
            ))}
          </select>
        </div>
      </div>
      <p className="text-[10px] text-muted-foreground">
        Strict per-purpose: this profile will only show in the Pipeline page's
        dropdown for the selected purpose. Model and params are filled in inline
        after the row appears.
      </p>
      <div className="flex justify-end gap-2 pt-2">
        <Button type="button" variant="ghost" onClick={onClose}>
          Cancel
        </Button>
        <Button type="submit" disabled={!name.trim() || providerNames.length === 0}>
          Add
        </Button>
      </div>
    </form>
  )
}
