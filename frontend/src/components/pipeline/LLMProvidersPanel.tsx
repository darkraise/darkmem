import { useEffect, useMemo, useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { Button } from "darkraise-ui/components/button"
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

const merged: DraftMap = useMemo(() => ({ ...stored, ...draft }), [stored, draft])
const profileNames = Object.keys(merged).sort()

const dirty = useMemo(() => {
if (Object.keys(draft).length === 0) return false
for (const name of Object.keys(draft)) {
const next = draft[name]
const prev = stored[name]
if (!prev) return true
if (
next.provider !== prev.provider ||
next.base_url !== prev.base_url ||
next.api_key !== prev.api_key ||
next.api_kind !== prev.api_kind ||
next.supports_embedding !== prev.supports_embedding
) {
return true
}
}
return false
}, [draft, stored])

if (isLoading) {
return (
<Card>
<CardHeader className="pb-2">
<CardTitle className="text-sm">LLM provider profiles</CardTitle>
</CardHeader>
<CardContent>
<div className="h-32 bg-muted rounded animate-pulse" />
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
const profiles: Record<string, LlmProviderProfile> = {}
for (const name of Object.keys(merged)) {
const p = merged[name]
// For new rows, require base_url to be set.
if (!p.base_url.trim()) {
toast.error(`Profile '${name}' needs a base URL`)
return
}
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
<CardTitle className="text-sm flex items-center gap-2">
LLM Providers
<TooltipProvider delayDuration={150}>
<Tooltip>
<TooltipTrigger asChild>
<button
type="button"
aria-label="What are LLM Providers?"
className="text-muted-foreground hover:text-foreground inline-flex items-center justify-center rounded-sm focus-visible:ring-ring focus-visible:ring-2 focus-visible:outline-none"
>
<CircleHelp className="h-3.5 w-3.5" />
</button>
</TooltipTrigger>
<TooltipContent side="top" className="max-w-md text-xs leading-relaxed">
A Provider is a connection (base URL, API key, API kind).
Profiles bundle a Provider with a default model and params
— those are managed in the LLM Profiles panel. Rotating
an API key here updates every Profile (and every linked
purpose) at once.
</TooltipContent>
</Tooltip>
</TooltipProvider>
</CardTitle>
<p className="text-muted-foreground text-xs">
Connection settings only. A Profile picks one Provider plus a
model and default parameters; a purpose picks a Profile.
</p>
</CardHeader>
<CardContent className="space-y-4">
{profileNames.length === 0 && (
<p className="text-muted-foreground text-xs">
No Providers yet. Add one below to start sharing connection
settings across Profiles and purposes.
</p>
)}

<div className="space-y-3">
{profileNames.map((name) => (
<ProfileRow
key={name}
name={name}
profile={merged[name]}
isNew={!!draft[name]?._isNew}
dirty={!!draft[name] && !merged[name]._isNew}
onPatch={(patchObj) => patch(name, patchObj)}
onDelete={() => drop(name)}
disabled={update.isPending || remove.isPending}
/>
))}
</div>

<div className="border-t border-border pt-3 flex items-center gap-2">
<div className="flex-1 flex items-center gap-2">
<Label htmlFor="new_provider_name" className="text-xs">New Provider</Label>
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
className="h-8 text-xs max-w-xs"
/>
</div>
<Button
variant="outline"
className="text-xs"
onClick={addProfile}
disabled={!newName.trim()}
>
Add
</Button>
</div>

<div className="flex items-center justify-end gap-2 border-t border-border pt-3">
{dirty && (
<span className="text-[10px] text-muted-foreground mr-auto">
{Object.keys(draft).length} unsaved change
{Object.keys(draft).length === 1 ? "" : "s"}
</span>
)}
<Button
variant="ghost"
className="text-xs"
onClick={reset}
disabled={!dirty || update.isPending}
>
Reset
</Button>
<Button className="text-xs" onClick={save} disabled={!dirty || update.isPending}>
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

function ProfileRow({ name, profile, isNew, dirty, onPatch, onDelete, disabled }: RowProps) {
const tokenIsMasked = profile.api_key === TOKEN_SENTINEL
const supportsEmbedding = profile.supports_embedding ?? true
const [testDialog, setTestDialog] = useState<"chat" | "embedding" | null>(null)

const openTest = (mode: "chat" | "embedding") => {
if (isNew) {
toast.error("Save the Provider before testing it")
return
}
setTestDialog(mode)
}

return (
<div className="rounded-md border border-border p-3 space-y-2">
<LLMProviderTestDialog
providerName={isNew ? null : name}
mode={testDialog ?? "chat"}
open={testDialog !== null}
onOpenChange={(o) => { if (!o) setTestDialog(null) }}
/>
<div className="flex items-center justify-between gap-2">
<div className="flex items-center gap-2 flex-wrap">
<span className="text-xs font-mono">{name}</span>
{isNew && (
<Badge variant="default" className="text-[9px]">new</Badge>
)}
{!isNew && dirty && (
<Badge variant="secondary" className="text-[9px]">edited</Badge>
)}
{tokenIsMasked && (
<Badge variant="outline" className="text-[9px]">key configured</Badge>
)}
{!supportsEmbedding && (
<Badge variant="outline" className="text-[9px]">no embedding</Badge>
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
<div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
<div>
<Label className="text-[10px] text-muted-foreground">Provider</Label>
<Input
type="text"
value={profile.provider}
onChange={(e) => onPatch({ provider: e.target.value })}
className="h-8 text-xs"
placeholder="openai | ollama | anthropic"
/>
</div>
<div>
<Label className="text-[10px] text-muted-foreground">API kind</Label>
<select
value={profile.api_kind || "openai"}
onChange={(e) => onPatch({ api_kind: e.target.value })}
className="h-8 w-full text-xs rounded border border-border bg-background px-2"
>
{API_KIND_OPTIONS.map((opt) => (
<option key={opt.value} value={opt.value}>
{opt.label}
{opt.note ? ` — ${opt.note}` : ""}
</option>
))}
</select>
</div>
<div className="sm:col-span-2">
<Label className="text-[10px] text-muted-foreground">Base URL</Label>
<Input
type="text"
value={profile.base_url}
onChange={(e) => onPatch({ base_url: e.target.value })}
className="h-8 text-xs font-mono"
placeholder="https://api.openai.com/v1"
/>
</div>
<div className="sm:col-span-2">
<Label className="text-[10px] text-muted-foreground">
API key {tokenIsMasked && "(leave *** to keep stored)"}
</Label>
<Input
type="password"
value={profile.api_key ?? ""}
onChange={(e) => onPatch({ api_key: e.target.value })}
className="h-8 text-xs font-mono"
placeholder="(none — local provider)"
autoComplete="off"
/>
</div>
<div className="sm:col-span-2 flex items-center justify-between border-t border-border pt-2">
<div>
<Label className="text-xs">Supports embedding</Label>
<p className="text-[10px] text-muted-foreground">
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
</div>
)
}
