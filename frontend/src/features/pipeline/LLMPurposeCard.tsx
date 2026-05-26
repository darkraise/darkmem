import { useState, useEffect } from "react"
import { Card, CardContent } from "darkraise-ui/components/card"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { Switch } from "darkraise-ui/components/switch"
import { Textarea } from "darkraise-ui/components/textarea"
import { Badge } from "darkraise-ui/components/badge"
import { toast } from "darkraise-ui/components/sonner"
import {
  useUpdateLlmConfig,
  useLlmProviders,
  useLlmProfiles,
  useMlProfiles,
  type LlmPurposeConfig,
  type PipelineState,
} from "@/hooks/api"
import { PROMPT_PURPOSE_MAP, type LLMPurpose } from "./prompt-map"
import { LLMPurposePromptEditor } from "./LLMPurposePromptEditor"
import { API_KIND_OPTIONS } from "./api-kinds"

interface Props {
  purpose: LLMPurpose
  config: LlmPurposeConfig
  prompts: PipelineState["prompts"]
  onObsoleteDetected?: (counts: {
    memories: number
    code_chunks: number
    entities: number
  }) => void
}

export function LLMPurposeCard({
  purpose,
  config,
  prompts,
  onObsoleteDetected,
}: Props) {
  const update = useUpdateLlmConfig()
  const { data: providersResp } = useLlmProviders()
  const { data: llmProfilesResp } = useLlmProfiles()
  const { data: mlProfilesResp } = useMlProfiles()
  const allProviders = providersResp?.profiles ?? {}
  const allLlmProfiles = llmProfilesResp?.profiles ?? {}
  const allMlProfiles = mlProfilesResp?.profiles ?? {}
  // Strict per-purpose filter: only show Profiles whose ``purpose`` column
  // matches the card. Profiles created before the purpose column existed
  // (purpose=NULL) fall back to the legacy embedding/reasoning heuristic
  // so they don't disappear from the menu after the migration backfill.
  const profileNames = Object.keys(allLlmProfiles)
    .filter((name) => {
      const p = allLlmProfiles[name]
      const provider = allProviders[p.provider_ref]
      if (p.purpose) {
        if (p.purpose !== purpose) return false
        if (purpose === "embedding") return provider?.supports_embedding ?? true
        return true
      }
      // Legacy fallback when purpose isn't set on the profile row.
      if (purpose === "embedding") {
        return p.is_embedding && (provider?.supports_embedding ?? true)
      }
      return !p.is_embedding
    })
    .sort()
  // ML profiles only surface for the classifier card. Names are kept in
  // a separate list so the option label can flag them as ``[ml]`` and
  // the apply-handler can dispatch to ml_profile_ref instead of
  // profile_ref.
  const mlProfileNames =
    purpose === "classification" ? Object.keys(allMlProfiles).sort() : []
  const [open, setOpen] = useState(purpose === "extraction")
  const [draft, setDraft] = useState<LlmPurposeConfig>(config)
  const [paramsText, setParamsText] = useState(
    Object.keys(config.params || {}).length
      ? JSON.stringify(config.params, null, 2)
      : "",
  )
  const [dirty, setDirty] = useState(false)
  const linkedToProfile = !!draft.provider_ref

  // The dropdown reads ``draft.profile_ref`` directly — the explicit
  // link the server stores on the purpose row. Manual edits to any
  // profile-derived field clear the link so the placeholder shows again.
  // Falls back to "" when the linked name is unknown to the current
  // profile set (e.g., the profile was renamed or deleted).
  const activeProfileName = profileNames.includes(draft.profile_ref ?? "")
    ? (draft.profile_ref as string)
    : ""

  useEffect(() => {
    // Don't stomp in-progress edits when the aggregator refetches (e.g. after
    // window-focus invalidation). Sync only when the card is clean.
    if (dirty) return
    setDraft(config)
    setParamsText(
      Object.keys(config.params || {}).length
        ? JSON.stringify(config.params, null, 2)
        : "",
    )
  }, [config, dirty])

  const promptKeys = PROMPT_PURPOSE_MAP[purpose]

  const save = () => {
    const payload: Record<string, unknown> = {
      model: draft.model,
      reasoning: draft.reasoning,
      provider_ref: draft.provider_ref ?? "",
      // Empty string clears the profile link on the server (matches the
      // provider_ref convention). null on draft means user manually
      // edited a field and broke the link.
      profile_ref: draft.profile_ref ?? "",
      ml_profile_ref: draft.ml_profile_ref ?? "",
    }
    // Connection fields are only sent when the user manages them on the
    // purpose itself. With a profile linked, we leave the stored values
    // alone so a later unlink falls back to whatever was there last.
    if (!linkedToProfile) {
      payload.provider = draft.provider
      payload.base_url = draft.base_url
      payload.api_kind = draft.api_kind ?? "openai"
      if (draft.api_key && draft.api_key !== "***")
        payload.api_key = draft.api_key
    }
    if (purpose === "embedding" && draft.dimensions)
      payload.dimensions = draft.dimensions
    if (paramsText.trim()) {
      try {
        payload.params = JSON.parse(paramsText)
      } catch {
        toast.error("Invalid JSON in params")
        return
      }
    }
    update.mutate(
      { [purpose]: payload },
      {
        onSuccess: (data) => {
          setDirty(false)
          const obs = data.obsolete_after_change
          if (
            obs &&
            (obs.memories > 0 || obs.code_chunks > 0 || obs.entities > 0)
          ) {
            onObsoleteDetected?.(obs)
          } else {
            toast.success(`${purpose} updated`)
          }
        },
        onError: (err) => toast.error(`Save failed: ${err.message}`),
      },
    )
  }

  const cancel = () => {
    setDraft(config)
    setParamsText(
      Object.keys(config.params || {}).length
        ? JSON.stringify(config.params, null, 2)
        : "",
    )
    setDirty(false)
  }

  const panelId = `llm-purpose-${purpose}-panel`

  return (
    <Card className={open ? "border-primary" : ""}>
      <button
        type="button"
        className="flex w-full items-center justify-between gap-2 p-2 text-left"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={panelId}
      >
        <span className="flex items-center gap-2 text-xs font-semibold capitalize">
          {open ? "▾" : "▸"} {purpose}
        </span>
        <span className="text-muted-foreground truncate font-mono text-[10px]">
          {config.model}
          {config.dimensions ? ` · ${config.dimensions}d` : ""} ·{" "}
          {config.provider}
        </span>
      </button>
      {open && (
        <CardContent className="p-0">
          <div
            id={panelId}
            className="space-y-3 p-4 pt-0"
            aria-label={`${purpose} LLM configuration`}
          >
            <div className="flex items-center gap-2">
              <Label className="text-xs">Profile</Label>
              <select
                value={
                  draft.ml_profile_ref &&
                  mlProfileNames.includes(draft.ml_profile_ref)
                    ? `ml:${draft.ml_profile_ref}`
                    : activeProfileName
                      ? `llm:${activeProfileName}`
                      : ""
                }
                onChange={(e) => {
                  const value = e.target.value
                  if (!value) return
                  if (value.startsWith("ml:")) {
                    const mlName = value.slice(3)
                    const mlProf = allMlProfiles[mlName]
                    if (!mlProf) return
                    // ML profile selected — clear the LLM-side draft state and
                    // route the classifier to the in-process ML runtime. The
                    // resolver's ml_profile_ref column is what the pipeline
                    // reads to decide which classifier service to construct.
                    patch({
                      ml_profile_ref: mlName,
                      profile_ref: null,
                      provider_ref: null,
                      model: mlProf.model_repo,
                      api_key: "",
                    })
                    setParamsText("")
                    setDirty(true)
                    return
                  }
                  const profileName = value.slice(4)
                  const prof = allLlmProfiles[profileName]
                  if (!prof) return
                  const linkedProvider = allProviders[prof.provider_ref]
                  patch({
                    profile_ref: profileName,
                    ml_profile_ref: null,
                    provider_ref: prof.provider_ref,
                    model: prof.model,
                    reasoning: prof.is_embedding ? false : prof.reasoning,
                    params: prof.params || {},
                    ...(linkedProvider
                      ? {
                          provider: linkedProvider.provider,
                          base_url: linkedProvider.base_url,
                          api_kind:
                            linkedProvider.api_kind as LlmPurposeConfig["api_kind"],
                          api_key: linkedProvider.api_key ?? "",
                        }
                      : {}),
                  })
                  setParamsText(
                    Object.keys(prof.params || {}).length
                      ? JSON.stringify(prof.params, null, 2)
                      : "",
                  )
                  setDirty(true)
                }}
                className="border-border bg-background h-9 flex-1 rounded border px-2 text-sm"
                title="Apply a saved Profile to this purpose."
                disabled={
                  profileNames.length === 0 && mlProfileNames.length === 0
                }
              >
                <option value="">
                  {profileNames.length === 0 && mlProfileNames.length === 0
                    ? "(no Profiles available — create one in Settings)"
                    : "Apply a Profile…"}
                </option>
                {profileNames.map((name) => {
                  const p = allLlmProfiles[name]
                  return (
                    <option key={`llm-${name}`} value={`llm:${name}`}>
                      {name} — {p.provider_ref}/{p.model}
                    </option>
                  )
                })}
                {mlProfileNames.map((name) => {
                  const m = allMlProfiles[name]
                  return (
                    <option key={`ml-${name}`} value={`ml:${name}`}>
                      [ml] {name} — {m.model_repo}
                    </option>
                  )
                })}
              </select>
              {linkedToProfile && !draft.ml_profile_ref && (
                <Badge
                  variant="secondary"
                  className="text-[9px]"
                  title={`Linked Provider: ${draft.provider_ref}`}
                >
                  via {draft.provider_ref}
                </Badge>
              )}
              {draft.ml_profile_ref && (
                <Badge
                  variant="secondary"
                  className="text-[9px]"
                  title="In-process ML classifier"
                >
                  ml: {draft.ml_profile_ref}
                </Badge>
              )}
            </div>

            <div className="grid grid-cols-2 gap-2">
              <Field
                label="Provider"
                value={draft.provider}
                onChange={(v) => patch({ provider: v })}
                disabled={linkedToProfile}
              />
              <Field
                label="Model"
                mono
                value={draft.model}
                onChange={(v) => patch({ model: v })}
              />
              <Field
                label="Base URL"
                mono
                value={draft.base_url}
                onChange={(v) => patch({ base_url: v })}
                disabled={linkedToProfile}
              />
              <Field
                label="API key"
                mono
                type="password"
                value={draft.api_key ?? ""}
                onChange={(v) => patch({ api_key: v })}
                disabled={linkedToProfile}
              />
              {purpose === "embedding" && (
                <Field
                  label="Dimensions"
                  value={String(draft.dimensions ?? "")}
                  onChange={(v) => patch({ dimensions: Number(v) || null })}
                />
              )}
            </div>

            <div className="flex items-center gap-2">
              <Label className="text-xs">API</Label>
              <select
                value={draft.api_kind ?? "openai"}
                onChange={(e) => patch({ api_kind: e.target.value })}
                disabled={linkedToProfile}
                className="border-border bg-background h-7 rounded border px-2 text-xs disabled:opacity-50"
                title="Wire protocol used to talk to the configured base URL. Ollama native exposes think:false to disable qwen3-style reasoning. Vendor-specific kinds reserve a slot for future native adapters and currently route through OpenAI compat."
              >
                {API_KIND_OPTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                    {opt.note ? ` — ${opt.note}` : ""}
                  </option>
                ))}
              </select>
              {linkedToProfile && (
                <span className="text-muted-foreground text-[10px]">
                  managed by profile <code>{draft.provider_ref}</code>
                </span>
              )}
            </div>

            {purpose !== "embedding" && (
              <div className="flex items-center gap-2">
                <Label className="text-xs">Reasoning mode</Label>
                <Switch
                  checked={draft.reasoning}
                  onCheckedChange={(v) => patch({ reasoning: v })}
                />
              </div>
            )}

            <details>
              <summary className="text-muted-foreground cursor-pointer text-[10px]">
                More… (JSON params)
              </summary>
              <Textarea
                value={paramsText}
                onChange={(e) => {
                  setParamsText(e.target.value)
                  // Editing params manually breaks the profile link, same as
                  // the field-level patches. The save still sends profile_ref:""
                  // so the server clears the FK.
                  setDraft((d) => ({ ...d, profile_ref: null }))
                  setDirty(true)
                }}
                rows={3}
                className="mt-1 font-mono text-xs"
                placeholder='{"temperature": 0.2}'
              />
            </details>

            {dirty && (
              <div className="flex justify-end gap-2">
                <Button
                  variant="ghost"
                  onClick={cancel}
                  disabled={update.isPending}
                >
                  Cancel
                </Button>
                <Button onClick={save} disabled={update.isPending}>
                  {update.isPending ? "Saving…" : "Save"}
                </Button>
              </div>
            )}

            <LLMPurposePromptEditor keys={promptKeys} prompts={prompts} />
          </div>
        </CardContent>
      )}
    </Card>
  )

  function patch(p: Partial<LlmPurposeConfig>) {
    // Manual edits to any profile-derived field break the link to the
    // applied Profile. The apply onChange handler explicitly re-sets
    // profile_ref on its own patch payload, so it overrides the clear.
    const next: Partial<LlmPurposeConfig> =
      "profile_ref" in p ? p : { ...p, profile_ref: null }
    setDraft((d) => ({ ...d, ...next }))
    setDirty(true)
  }
}

function Field({
  label,
  value,
  onChange,
  mono,
  type,
  disabled,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  mono?: boolean
  type?: string
  disabled?: boolean
}) {
  return (
    <div>
      <Label className="text-muted-foreground text-[10px]">{label}</Label>
      <Input
        type={type ?? "text"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={`h-7 text-xs ${mono ? "font-mono" : ""} disabled:opacity-50`}
      />
    </div>
  )
}
