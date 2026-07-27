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
import {
  ChevronDown,
  ChevronRight,
  CircleHelp,
  Plus,
  Search,
  Trash2,
} from "lucide-react"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
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
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "darkraise-ui/components/select"
import {
  Combobox,
  ComboboxControl,
  ComboboxInput,
  ComboboxTrigger,
  ComboboxContent,
  ComboboxList,
  ComboboxItem,
  ComboboxItemText,
  ComboboxEmpty,
} from "darkraise-ui/components/combobox"
import {
  useLlmProfiles,
  useUpdateLlmProfiles,
  useDeleteLlmProfile,
  useLlmProviders,
  useProviderModels,
  type LlmProfile,
} from "@/hooks/api"
import { navigateToSettingsTab } from "@/lib/settings-tab"
import { ignorePortaledOverlayPointerDown } from "@/lib/portal-overlays"
import { KNOWN_PURPOSES, purposeOf, type KnownPurpose } from "./purpose-of"
import { apiKindSupportsEmbedding } from "./api-kinds"

type DraftProfile = LlmProfile & { _isNew?: boolean; _paramsText?: string }
type DraftMap = Record<string, DraftProfile>

type GroupBy = "provider" | "purpose"
const GROUP_BY_STORAGE_KEY = "darkmem.llm-profiles.group-by"

// Select value standing in for purpose === null (Radix forbids empty values).
const LEGACY_PURPOSE = "__legacy__"

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
    for (const [name, profile] of Object.entries(
      profilesResp?.profiles ?? {},
    )) {
      out[name] = {
        ...profile,
        _paramsText: Object.keys(profile.params || {}).length
          ? JSON.stringify(profile.params, null, 2)
          : "",
      }
    }
    return out
  }, [profilesResp])

  // Mirror the draft into a ref so the stored-sync effect can read the current
  // dirty state without listing draft as a dependency (which would re-run on
  // every keystroke and wipe the edit it just captured).
  const draftRef = useRef(draft)
  draftRef.current = draft
  useEffect(() => {
    // Don't stomp in-progress edits when the query refetches (e.g. after
    // window-focus invalidation). Reset only when there are no unsaved rows.
    if (Object.keys(draftRef.current).length > 0) return
    setDraft({})
  }, [stored])

  const merged: DraftMap = useMemo(
    () => ({ ...stored, ...draft }),
    [stored, draft],
  )
  const profileNames = Object.keys(merged).sort()
  const providerNames = Object.keys(providersResp?.profiles ?? {}).sort()

  const [groupBy, setGroupBy] = useState<GroupBy>(readStoredGroupBy)
  useEffect(() => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(GROUP_BY_STORAGE_KEY, groupBy)
    }
  }, [groupBy])

  // Bucket profile names by the chosen grouping. Keys are the tab labels;
  // values are the profile names that belong in each tab. Grouping by purpose
  // uses the stored ``purpose`` column (via purposeOf) so these tabs agree with
  // the Pipeline dropdown filter, not a name heuristic.
  const groups: Record<string, string[]> = useMemo(() => {
    const out: Record<string, string[]> = {}
    if (groupBy === "provider") {
      for (const name of profileNames) {
        const key = merged[name]?.provider_ref || "(unset)"
        ;(out[key] ??= []).push(name)
      }
    } else {
      for (const name of profileNames) {
        const profile = merged[name]
        if (!profile) continue
        const key = purposeOf(profile, name)
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
        (a, b) =>
          order.indexOf(a as KnownPurpose) - order.indexOf(b as KnownPurpose),
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
    setActiveGroup((prev) =>
      prev && groupKeys.includes(prev) ? prev : (groupKeys[0] ?? ""),
    )
  }, [groupKeys])

  // Rows the user actually touched (a draft entry). Validation gates on these
  // only, so a pre-existing invalid row never blocks saving an unrelated edit.
  const dirtyNames = useMemo(() => new Set(Object.keys(draft)), [draft])
  const dirty = dirtyNames.size > 0

  const [search, setSearch] = useState("")
  const matchesSearch = (name: string): boolean => {
    const q = search.trim().toLowerCase()
    if (!q) return true
    const p = merged[name]
    return (
      name.toLowerCase().includes(q) ||
      (p?.provider_ref ?? "").toLowerCase().includes(q) ||
      (p?.model ?? "").toLowerCase().includes(q)
    )
  }
  const visibleCount = profileNames.filter(matchesSearch).length

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

  const reset = () => {
    if (
      dirty &&
      !window.confirm("Discard all unsaved Profile changes?")
    ) {
      return
    }
    setDraft({})
  }

  const save = () => {
    if (!dirty) return
    const profiles: Record<string, LlmProfile> = {}
    for (const name of Object.keys(merged)) {
      const p = merged[name]
      if (!p) continue
      const edited = dirtyNames.has(name)
      if (edited && (!p.provider_ref || !providerNames.includes(p.provider_ref))) {
        toast.error(`Profile '${name}' references an unknown Provider`)
        return
      }
      if (edited && !p.model.trim()) {
        toast.error(`Profile '${name}' needs a model`)
        return
      }
      const providerSupportsEmbedding = apiKindSupportsEmbedding(
        providersResp?.profiles[p.provider_ref]?.api_kind,
      )
      if (
        edited &&
        (p.purpose === "embedding" || p.is_embedding) &&
        !providerSupportsEmbedding
      ) {
        toast.error(
          `Profile '${name}' is an embedding profile but Provider '${
            p.provider_ref || "(none)"
          }' has no embeddings endpoint`,
        )
        return
      }
      let params: Record<string, unknown> = p.params ?? {}
      const text = p._paramsText?.trim() ?? ""
      if (text) {
        try {
          params = JSON.parse(text)
          if (typeof params !== "object" || Array.isArray(params)) {
            throw new Error("must be a JSON object")
          }
        } catch (err) {
          if (edited) {
            toast.error(
              `Profile '${name}' has invalid params JSON: ${(err as Error).message}`,
            )
            return
          }
          params = p.params ?? {}
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
        <CardHeader className="bg-foreground/5 rounded-t-[calc(var(--radius)-1px)] border-border border-b pb-4">
          <CardTitle className="text-lg uppercase tracking-wide">
            LLM Profiles
          </CardTitle>
        </CardHeader>
        <CardContent className="pt-4">
          <div className="bg-muted h-32 animate-pulse rounded" />
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardHeader className="bg-foreground/5 rounded-t-[calc(var(--radius)-1px)] border-border border-b pb-4">
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="min-w-0">
            <CardTitle className="flex items-center gap-2 text-lg uppercase tracking-wide">
              LLM Profiles
              <TooltipProvider delayDuration={150}>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      variant="ghost"
                      size="icon"
                      type="button"
                      aria-label="What are LLM Profiles?"
                      className="text-muted-foreground hover:text-foreground focus-visible:ring-ring inline-flex items-center justify-center rounded-sm focus-visible:ring-2 focus-visible:outline-none"
                    >
                      <CircleHelp className="h-3.5 w-3.5" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent
                    side="top"
                    className="max-w-md leading-relaxed normal-case"
                  >
                    A Profile is a preset for one purpose: a Provider plus a
                    model, default params, and the purpose-style flags
                    (embedding-only, reasoning-enabled). Pick a Profile in the
                    LLM purpose card on the Pipeline page to populate the form
                    with these defaults.
                  </TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </CardTitle>
            <CardDescription>
              Reusable per-purpose presets. Pick a Provider, a model, and
              defaults; the purpose card uses these as starting values.
            </CardDescription>
          </div>
          <Dialog open={addOpen} onOpenChange={setAddOpen}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="mr-1 h-3.5 w-3.5" />
                Add Profile
              </Button>
            </DialogTrigger>
            <DialogContent
              onPointerDownOutside={ignorePortaledOverlayPointerDown}
            >
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
      </CardHeader>
      <CardContent className="space-y-4 pt-4">
        {profileNames.length === 0 && (
          <p className="text-muted-foreground text-sm">
            No Profiles yet. Add one below.
          </p>
        )}

        {profileNames.length > 0 && (
          <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
            <Label htmlFor="profiles_group_by">
              Group by
            </Label>
            <Select
              value={groupBy}
              onValueChange={(value) => setGroupBy(value as GroupBy)}
            >
              <SelectTrigger
                id="profiles_group_by"
                className="border-border bg-background h-9 rounded border px-2"
              >
                <SelectValue>
                  {groupBy === "provider" ? "Provider" : "Purpose"}
                </SelectValue>
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="provider">Provider</SelectItem>
                <SelectItem value="purpose">Purpose</SelectItem>
              </SelectContent>
            </Select>
            <div className="relative w-full max-w-xs">
              <Search className="text-muted-foreground pointer-events-none absolute top-1/2 left-2 h-4 w-4 -translate-y-1/2" />
              <Input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search name, provider, or model…"
                aria-label="Search profiles"
                className="h-9 pl-8"
              />
            </div>
            <span className="text-muted-foreground text-sm">
              {search.trim()
                ? `${visibleCount} of ${profileNames.length} shown`
                : `${profileNames.length} profile${
                    profileNames.length === 1 ? "" : "s"
                  } across ${groupKeys.length} ${
                    groupBy === "provider" ? "provider" : "purpose"
                  }${groupKeys.length === 1 ? "" : "s"}`}
            </span>
            <Button
              variant="link"
              type="button"
              className="ml-auto h-auto p-0 text-sm"
              onClick={() => navigateToSettingsTab("llm-providers")}
            >
              Manage Providers →
            </Button>
          </div>
        )}

        {profileNames.length > 0 && groupKeys.length > 0 && (
          <Tabs value={activeGroup} onValueChange={setActiveGroup}>
            <TabsList className="flex-wrap">
              {groupKeys.map((key) => (
                <TabsTrigger key={key} value={key}>
                  {key}
                  <Badge variant="secondary" className="ml-1.5 text-sm">
                    {(groups[key] ?? []).filter(matchesSearch).length}
                  </Badge>
                </TabsTrigger>
              ))}
            </TabsList>
            {groupKeys.map((key) => {
              const visible = (groups[key] ?? []).filter(matchesSearch)
              return (
                <TabsContent key={key} value={key} className="mt-3 space-y-2">
                  {visible.length === 0 && (
                    <p className="text-muted-foreground text-sm">
                      No profiles in this group match “{search}”.
                    </p>
                  )}
                  {visible.map((name) => {
                    const profile = merged[name]
                    if (!profile) return null
                    const providerSupportsEmbedding = apiKindSupportsEmbedding(
                      providersResp?.profiles[profile.provider_ref]?.api_kind,
                    )
                    return (
                      <ProfileRow
                        key={name}
                        name={name}
                        profile={profile}
                        isNew={!!draft[name]?._isNew}
                        dirty={!!draft[name] && !profile._isNew}
                        providerNames={providerNames}
                        providerSupportsEmbedding={providerSupportsEmbedding}
                        onPatch={(p) => patch(name, p)}
                        onDelete={() => drop(name)}
                        disabled={update.isPending || remove.isPending}
                      />
                    )
                  })}
                </TabsContent>
              )
            })}
          </Tabs>
        )}

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
  providerSupportsEmbedding: boolean
  onPatch: (p: Partial<DraftProfile>) => void
  onDelete: () => void
  disabled: boolean
}

function ProfileRow({
  name,
  profile,
  isNew,
  dirty,
  providerNames,
  providerSupportsEmbedding,
  onPatch,
  onDelete,
  disabled,
}: RowProps) {
  const { data: modelsResp, isLoading: modelsLoading } = useProviderModels(
    profile.provider_ref || null,
    !!profile.provider_ref,
  )
  const modelItems = useMemo(
    () => (modelsResp?.models ?? []).map((m) => ({ value: m, label: m })),
    [modelsResp?.models],
  )
  const [open, setOpen] = useState(isNew)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const panelId = `llm-profile-${name}-panel`
  const paramCount = Object.keys(profile.params || {}).length
  const embeddingMismatch =
    (profile.purpose === "embedding" || profile.is_embedding) &&
    !providerSupportsEmbedding

  // Selecting a purpose keeps the embedding/reasoning flags consistent with it
  // so the Pipeline filter and the switches never disagree.
  const purposePatch = (v: string): Partial<DraftProfile> => {
    if (v === LEGACY_PURPOSE) return { purpose: null }
    if (v === "embedding")
      return { purpose: v, is_embedding: true, reasoning: false }
    // Non-embedding purposes must clear is_embedding so the flag and the purpose
    // column can never disagree (only purpose==='embedding' sets is_embedding).
    if (v === "reasoning")
      return { purpose: v, is_embedding: false, reasoning: true }
    return { purpose: v, is_embedding: false }
  }

  const handleDeleteClick = () => {
    if (isNew) {
      onDelete()
      return
    }
    setConfirmDelete(true)
  }

  return (
    <Card className={open ? "border-primary" : ""}>
      <AlertDialog open={confirmDelete} onOpenChange={setConfirmDelete}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete profile “{name}”?</AlertDialogTitle>
            <AlertDialogDescription>
              Any purpose linked to it on the Pipeline page will fall back to its
              placeholder.
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
            {profile.purpose ? (
              <Badge variant="outline" className="text-sm">
                {profile.purpose}
              </Badge>
            ) : (
              <Badge variant="outline" className="text-muted-foreground text-sm">
                legacy
              </Badge>
            )}
            {profile.reasoning && !profile.is_embedding && (
              <Badge variant="outline" className="text-sm">
                reasoning
              </Badge>
            )}
          </span>
          <span className="text-muted-foreground truncate font-mono text-sm">
            {profile.provider_ref || "no provider"} /{" "}
            {profile.model || "no model"}
            {paramCount > 0
              ? ` · ${paramCount} param${paramCount === 1 ? "" : "s"}`
              : ""}
          </span>
        </button>
        <Button
          variant="ghost"
          className="text-destructive hover:text-destructive shrink-0"
          onClick={(e) => {
            e.stopPropagation()
            handleDeleteClick()
          }}
          disabled={disabled}
          aria-label={`Delete Profile ${name}`}
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      {open && (
        <CardContent className="p-0">
          <div
            id={panelId}
            className="space-y-3 p-4 pt-0"
            aria-label={`${name} profile settings`}
          >
            <div className="grid grid-cols-1 gap-3 lg:grid-cols-3">
              <div>
                <Label className="text-muted-foreground text-sm">Provider</Label>
                <Select
                  value={profile.provider_ref || "__none__"}
                  onValueChange={(value) =>
                    onPatch({
                      provider_ref: value === "__none__" ? "" : value,
                      model: "",
                    })
                  }
                >
                  <SelectTrigger className="border-border bg-background h-9 w-full rounded border px-2">
                    <SelectValue>
                      {profile.provider_ref || "Select a provider…"}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {providerNames.map((p) => (
                      <SelectItem key={p} value={p}>
                        {p}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-muted-foreground text-sm">Model</Label>
                {/* Combobox: fetched models autocomplete, but free-text
                    entry still works. Vendor /v1/models endpoints are sometimes
                    incomplete (e.g., z.ai omits glm-4.5-flash), so a hard select
                    would lock the user out of valid models. */}
                <Combobox
                  items={modelItems}
                  inputValue={profile.model}
                  onInputValueChange={(d) => onPatch({ model: d.value.trim() })}
                  openOnClick
                  openOnFocus
                >
                  <ComboboxControl>
                    <ComboboxInput
                      className="font-mono"
                      placeholder={
                        modelsLoading
                          ? "fetching models…"
                          : "model id (e.g. gpt-4o-mini)"
                      }
                    />
                    <ComboboxTrigger />
                  </ComboboxControl>
                  <ComboboxContent>
                    <ComboboxList>
                      {modelItems.map((it) => (
                        <ComboboxItem key={it.value} item={it}>
                          <ComboboxItemText>{it.label}</ComboboxItemText>
                        </ComboboxItem>
                      ))}
                      <ComboboxEmpty>No models</ComboboxEmpty>
                    </ComboboxList>
                  </ComboboxContent>
                </Combobox>
                {modelsResp?.error && (
                  <p className="text-destructive mt-1 text-sm">
                    {modelsResp.error}
                  </p>
                )}
                {modelsResp && modelsResp.models.length > 0 && (
                  <p className="text-muted-foreground mt-1 text-sm">
                    {modelsResp.models.length} models from vendor — type to
                    filter or enter a name not in the list.
                  </p>
                )}
              </div>
              <div>
                <Label
                  className="text-muted-foreground text-sm"
                  title="Which Pipeline dropdown this profile appears in. “Legacy / unset” falls back to the embedding/non-embedding heuristic."
                >
                  Purpose
                </Label>
                <Select
                  value={profile.purpose ?? LEGACY_PURPOSE}
                  onValueChange={(v) => onPatch(purposePatch(v))}
                >
                  <SelectTrigger className="border-border bg-background h-9 w-full rounded border px-2">
                    <SelectValue>
                      {profile.purpose ?? "Legacy / unset"}
                    </SelectValue>
                  </SelectTrigger>
                  <SelectContent>
                    {KNOWN_PURPOSES.map((p) => (
                      <SelectItem key={p} value={p}>
                        {p}
                      </SelectItem>
                    ))}
                    <SelectItem value={LEGACY_PURPOSE}>
                      Legacy / unset
                    </SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>

            {embeddingMismatch && (
              <p className="border-warning/40 bg-warning/10 rounded-md border p-2 text-sm">
                Provider “{profile.provider_ref || "(none)"}” has no embeddings
                endpoint, so this profile won’t appear in the Pipeline embedding
                dropdown.
              </p>
            )}

            <div>
              <Label className="text-muted-foreground text-sm">
                Default params (JSON object, optional)
              </Label>
              <Textarea
                value={profile._paramsText ?? ""}
                onChange={(e) => onPatch({ _paramsText: e.target.value })}
                rows={3}
                className="font-mono"
                placeholder='{"temperature": 0.2}'
              />
            </div>
            <div className="border-border flex flex-wrap items-center gap-x-8 gap-y-2 border-t pt-3">
              <div className="flex items-center gap-2">
                <Switch
                  checked={!!profile.is_embedding}
                  onCheckedChange={(v) =>
                    onPatch({
                      is_embedding: v,
                      reasoning: v ? false : profile.reasoning,
                    })
                  }
                  aria-label="Embedding profile"
                />
                <span className="text-sm">Embedding profile</span>
              </div>
              <div className="flex items-center gap-2">
                <Switch
                  checked={!!profile.reasoning}
                  onCheckedChange={(v) => onPatch({ reasoning: v })}
                  disabled={!!profile.is_embedding}
                  aria-label="Reasoning enabled"
                />
                <span
                  className={
                    profile.is_embedding
                      ? "text-muted-foreground text-sm"
                      : "text-sm"
                  }
                >
                  Reasoning enabled
                </span>
              </div>
            </div>
          </div>
        </CardContent>
      )}
    </Card>
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

  if (providerNames.length === 0) {
    return (
      <div className="space-y-3">
        <p className="text-muted-foreground text-sm">
          You need at least one LLM Provider before adding a Profile.
        </p>
        <div className="flex justify-end gap-2">
          <Button type="button" variant="ghost" onClick={onClose}>
            Cancel
          </Button>
          <Button
            type="button"
            onClick={() => {
              navigateToSettingsTab("llm-providers")
              onClose()
            }}
          >
            Manage Providers →
          </Button>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={submit} className="space-y-3">
      <div>
        <Label className="text-muted-foreground">Profile name</Label>
        <Input
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="e.g. openai-classification-fast"
          required
        />
      </div>
      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <div>
          <Label className="text-muted-foreground">Provider</Label>
          <Select
            value={providerRef || "__none__"}
            onValueChange={(value) =>
              setProviderRef(value === "__none__" ? "" : value)
            }
          >
            <SelectTrigger className="border-border bg-background h-9 w-full rounded border px-2">
              <SelectValue>{providerRef || "Select a provider…"}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              {providerNames.map((p) => (
                <SelectItem key={p} value={p}>
                  {p}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div>
          <Label className="text-muted-foreground">Purpose</Label>
          <Select
            value={purpose}
            onValueChange={(value) => setPurpose(value as KnownPurpose)}
          >
            <SelectTrigger className="border-border bg-background h-9 w-full rounded border px-2">
              <SelectValue>{purpose}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              {KNOWN_PURPOSES.map((p) => (
                <SelectItem key={p} value={p}>
                  {p}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>
      <p className="text-muted-foreground text-sm">
        This profile shows in the Pipeline dropdown for the selected purpose; you
        can change it later on the row. Model and params are filled in inline
        after the row appears. Embedding requires an embedding-capable Provider.
      </p>
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
