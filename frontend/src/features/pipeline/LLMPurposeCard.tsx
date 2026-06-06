import { useState, useEffect } from "react"
import { Card, CardContent } from "darkraise-ui/components/card"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import {
  NumberInput,
  NumberInputControl,
  NumberInputField,
  NumberInputTriggerGroup,
  NumberInputIncrementTrigger,
  NumberInputDecrementTrigger,
} from "darkraise-ui/components/number-input"
import { Switch } from "darkraise-ui/components/switch"
import { Textarea } from "darkraise-ui/components/textarea"
import { Badge } from "darkraise-ui/components/badge"
import { toast } from "darkraise-ui/components/sonner"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import {
  Collapsible,
  CollapsibleTrigger,
  CollapsibleContent,
} from "darkraise-ui/components/collapsible"
import {
  useUpdateLlmConfig,
  useLlmProviders,
  useLlmProfiles,
  useMlProfiles,
  type LlmPurposeConfig,
  type PipelineState,
} from "@/hooks/api"
import { navigateToSettingsTab } from "@/lib/settings-tab"
import { PROMPT_PURPOSE_MAP, type LLMPurpose } from "./prompt-map"
import { LLMPurposePromptEditor } from "./LLMPurposePromptEditor"
import { API_KIND_OPTIONS } from "./api-kinds"

// The dropdown reflects the explicit ``profile_ref`` link the server stores
// on the purpose row. Returns that name when it still exists in the current
// (purpose-filtered) profile set, else "" so the placeholder shows again —
// e.g. when the linked profile was renamed or deleted.
export function resolveActiveProfileName(
  profileRef: string | null | undefined,
  profileNames: readonly string[],
): string {
  return profileNames.includes(profileRef ?? "") ? (profileRef ?? "") : ""
}

function apiKindLabel(kind: string | undefined): string {
  return API_KIND_OPTIONS.find((o) => o.value === kind)?.label ?? kind ?? ""
}

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
      if (!p) return false
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
  // ``provider_ref`` is the connection-inheritance link; when set, the purpose
  // resolves its endpoint from a Provider, so the raw connection fields are not
  // the source of truth. Default the override drawer open only for purposes
  // that are already inline-managed (no provider to inherit from).
  const [overrideOpen, setOverrideOpen] = useState(!config.provider_ref)
  const linkedToProfile = !!draft.provider_ref
  const isMl = !!draft.ml_profile_ref
  const canResetToProfile = !!(config.profile_ref || config.ml_profile_ref)

  const activeProfileName = resolveActiveProfileName(
    draft.profile_ref,
    profileNames,
  )

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

  const applyLlmProfile = (profileName: string) => {
    const prof = allLlmProfiles[profileName]
    if (!prof) return
    const linkedProvider = allProviders[prof.provider_ref]
    if (!linkedProvider) {
      // A dangling provider_ref must not leave the previous connection fields in
      // place under a "Resolved from Profile X" caption — that misrepresents what
      // the purpose will actually use.
      toast.error(
        `Profile "${profileName}" points at a missing provider; set the connection manually.`,
      )
    }
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
            api_kind: linkedProvider.api_kind as LlmPurposeConfig["api_kind"],
            api_key: linkedProvider.api_key ?? "",
          }
        : { provider: "", base_url: "", api_key: "" }),
    })
    setParamsText(
      Object.keys(prof.params || {}).length
        ? JSON.stringify(prof.params, null, 2)
        : "",
    )
    setDirty(true)
  }

  const applyMlProfile = (mlName: string) => {
    const mlProf = allMlProfiles[mlName]
    if (!mlProf) return
    // ML profile selected — clear the LLM-side draft state and route the
    // classifier to the in-process ML runtime. The resolver's ml_profile_ref
    // column is what the pipeline reads to decide which classifier service
    // to construct.
    patch({
      ml_profile_ref: mlName,
      profile_ref: null,
      provider_ref: null,
      model: mlProf.model_repo,
      api_key: "",
    })
    setParamsText("")
    setDirty(true)
  }

  // Drop both inheritance links so the inline connection fields become the
  // source of truth (and get sent on save). Current resolved values stay as
  // the starting point for manual editing.
  const detach = () => {
    patch({ provider_ref: null, profile_ref: null, ml_profile_ref: null })
    setOverrideOpen(true)
  }

  const resetToProfile = () => {
    if (config.ml_profile_ref) applyMlProfile(config.ml_profile_ref)
    else if (config.profile_ref) applyLlmProfile(config.profile_ref)
  }

  const panelId = `llm-purpose-${purpose}-panel`
  const noProfiles = profileNames.length === 0 && mlProfileNames.length === 0
  const linkLabel = draft.profile_ref
    ? `Profile “${draft.profile_ref}”`
    : `Provider “${draft.provider_ref}”`

  return (
    <Card className={open ? "border-primary" : ""}>
      <Button
        variant="ghost"
        type="button"
        className="flex w-full items-center justify-between gap-2 p-2 text-left"
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-controls={panelId}
      >
        <span className="flex items-center gap-2 text-base font-semibold capitalize">
          {open ? "▾" : "▸"} {purpose}
        </span>
        <span className="text-muted-foreground truncate font-mono text-sm">
          {config.model}
          {config.dimensions ? ` · ${config.dimensions}d` : ""} ·{" "}
          {config.provider}
        </span>
      </Button>
      {open && (
        <CardContent className="p-0">
          <div
            id={panelId}
            className="space-y-4 p-4 pt-0"
            aria-label={`${purpose} LLM configuration`}
          >
            {/* Profile picker — the primary decision for this purpose. */}
            <div className="space-y-1.5">
              <div className="flex items-center gap-2">
                <Label className="text-base">Profile</Label>
                {linkedToProfile && !isMl && (
                  <Badge
                    variant="secondary"
                    className="text-sm"
                    title={`Linked Provider: ${draft.provider_ref}`}
                  >
                    via {draft.provider_ref}
                  </Badge>
                )}
                {isMl && (
                  <Badge
                    variant="secondary"
                    className="text-sm"
                    title="In-process ML classifier"
                  >
                    ml: {draft.ml_profile_ref}
                  </Badge>
                )}
              </div>
              <Select
                value={
                  draft.ml_profile_ref &&
                  mlProfileNames.includes(draft.ml_profile_ref)
                    ? `ml:${draft.ml_profile_ref}`
                    : activeProfileName
                      ? `llm:${activeProfileName}`
                      : ""
                }
                onValueChange={(value) => {
                  if (!value) return
                  if (value.startsWith("ml:")) {
                    applyMlProfile(value.slice(3))
                    return
                  }
                  applyLlmProfile(value.slice(4))
                }}
                disabled={noProfiles}
              >
                <SelectTrigger
                  className="h-9 w-full text-base"
                  title="Apply a saved Profile to this purpose."
                >
                  <SelectValue
                    placeholder={
                      noProfiles
                        ? "(no Profiles available — create one in Settings)"
                        : "Apply a Profile…"
                    }
                  />
                </SelectTrigger>
                <SelectContent>
                  {profileNames.map((name) => {
                    const p = allLlmProfiles[name]
                    if (!p) return null
                    return (
                      <SelectItem key={`llm-${name}`} value={`llm:${name}`}>
                        {name} — {p.provider_ref}/{p.model}
                      </SelectItem>
                    )
                  })}
                  {mlProfileNames.map((name) => {
                    const m = allMlProfiles[name]
                    if (!m) return null
                    return (
                      <SelectItem key={`ml-${name}`} value={`ml:${name}`}>
                        [ml] {name} — {m.model_repo}
                      </SelectItem>
                    )
                  })}
                </SelectContent>
              </Select>
              <div className="flex items-center justify-between gap-2">
                <p className="text-muted-foreground text-sm">
                  Pick a saved preset, or override below.
                </p>
                <Button
                  variant="link"
                  type="button"
                  className="h-auto p-0 text-sm"
                  onClick={() => navigateToSettingsTab("llm-profiles")}
                >
                  Manage Profiles →
                </Button>
              </div>
            </div>

            {/* Resolved values — read-only echo of what the link resolves to,
                replacing the old wall of dimmed inputs. For a custom purpose
                the editable fields live in the (open) override below, so we
                show only a state caption here to avoid duplicating them. */}
            {isMl ? (
              <div className="bg-muted/40 border-border rounded-md border p-3 text-sm">
                In-process ML classifier —{" "}
                <span className="font-mono">{draft.model}</span>. No connection
                settings apply.
              </div>
            ) : linkedToProfile ? (
              <div className="bg-muted/40 border-border space-y-1 rounded-md border p-3 text-sm">
                <SummaryRow label="Provider" value={draft.provider} />
                <SummaryRow label="Model" value={draft.model} mono />
                <SummaryRow label="API kind" value={apiKindLabel(draft.api_kind)} />
                <SummaryRow label="Base URL" value={draft.base_url} mono truncate />
                <p className="text-muted-foreground pt-1">
                  Resolved from {linkLabel}
                </p>
              </div>
            ) : (
              <p className="text-muted-foreground text-sm">
                Custom — not linked to a Profile. Connection is set in the
                override below.
              </p>
            )}

            {purpose === "embedding" && (
              <div className="flex items-center justify-between">
                <Label className="text-base">Dimensions</Label>
                <NumberInput
                  min={1}
                  value={draft.dimensions ?? undefined}
                  onValueChange={(d) =>
                    patch({ dimensions: d.valueAsNumber || null })
                  }
                  className="w-28"
                >
                  <NumberInputControl>
                    <NumberInputField className="h-9 text-center text-base" />
                    <NumberInputTriggerGroup>
                      <NumberInputIncrementTrigger />
                      <NumberInputDecrementTrigger />
                    </NumberInputTriggerGroup>
                  </NumberInputControl>
                </NumberInput>
              </div>
            )}

            {purpose !== "embedding" && !isMl && (
              <div className="flex items-center justify-between gap-2">
                <div>
                  <Label className="text-base">Reasoning mode</Label>
                  {linkedToProfile && (
                    <p className="text-muted-foreground text-sm">
                      Overrides the linked Profile.
                    </p>
                  )}
                </div>
                <Switch
                  checked={draft.reasoning}
                  onCheckedChange={(v) => patch({ reasoning: v })}
                />
              </div>
            )}

            {/* Connection override — every field that duplicates the Providers
                and Profiles tabs lives here, collapsed by default. */}
            {!isMl && (
              <Collapsible
                open={overrideOpen}
                onOpenChange={setOverrideOpen}
                className="border-border border-t pt-3"
              >
                <CollapsibleTrigger className="text-muted-foreground hover:text-foreground flex w-full cursor-pointer items-center justify-between gap-2 text-base font-medium">
                  <span>
                    {overrideOpen ? "▾" : "▸"} Override connection for this
                    purpose
                  </span>
                  <span
                    className={
                      linkedToProfile
                        ? "text-muted-foreground text-sm"
                        : "text-destructive text-sm"
                    }
                  >
                    {linkedToProfile ? "linked" : "detached"}
                  </span>
                </CollapsibleTrigger>
                <CollapsibleContent className="space-y-3 pt-3">
                  {linkedToProfile ? (
                    <div className="border-warning/40 bg-warning/10 space-y-2 rounded-md border p-2 text-sm">
                      <p>
                        This purpose inherits its connection from {linkLabel}.
                        Detach to edit the endpoint for this purpose only.
                      </p>
                      <div className="flex flex-wrap gap-2">
                        <Button
                          variant="secondary"
                          type="button"
                          onClick={detach}
                        >
                          Detach & edit manually
                        </Button>
                        {canResetToProfile && (
                          <Button
                            variant="ghost"
                            type="button"
                            onClick={resetToProfile}
                          >
                            Reset to Profile
                          </Button>
                        )}
                      </div>
                    </div>
                  ) : (
                    <>
                      {canResetToProfile && (
                        <div className="flex justify-end">
                          <Button
                            variant="ghost"
                            type="button"
                            onClick={resetToProfile}
                          >
                            Reset to Profile
                          </Button>
                        </div>
                      )}
                      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                        <Field
                          label="Provider"
                          value={draft.provider}
                          onChange={(v) => patch({ provider: v })}
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
                        />
                        <Field
                          label="API key"
                          mono
                          type="password"
                          value={draft.api_key ?? ""}
                          onChange={(v) => patch({ api_key: v })}
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <Label className="text-base">API</Label>
                        <Select
                          value={draft.api_kind ?? "openai"}
                          onValueChange={(v) => patch({ api_kind: v })}
                        >
                          <SelectTrigger
                            className="h-9 text-base"
                            title="Wire protocol used to talk to the configured base URL. Ollama native exposes think:false to disable qwen3-style reasoning. Vendor-specific kinds reserve a slot for future native adapters and currently route through OpenAI compat."
                          >
                            <SelectValue />
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
                    </>
                  )}

                  {/* Model override stays reachable even while linked; editing
                      it detaches the Profile link (but keeps inheriting the
                      connection from the Provider). */}
                  {linkedToProfile && (
                    <Field
                      label="Model (override)"
                      mono
                      value={draft.model}
                      onChange={(v) => patch({ model: v })}
                    />
                  )}

                  <div>
                    <Label className="text-muted-foreground text-sm">
                      Parameters (JSON)
                    </Label>
                    <Textarea
                      value={paramsText}
                      onChange={(e) => {
                        setParamsText(e.target.value)
                        // Editing params manually breaks the profile link, same
                        // as the field-level patches. The save still sends
                        // profile_ref:"" so the server clears the FK.
                        setDraft((d) => ({ ...d, profile_ref: null }))
                        setDirty(true)
                      }}
                      rows={3}
                      className="mt-1 font-mono text-base"
                      placeholder='{"temperature": 0.2}'
                    />
                  </div>
                </CollapsibleContent>
              </Collapsible>
            )}

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

            {promptKeys.length > 0 && (
              <div className="border-border rounded-md border p-3">
                <LLMPurposePromptEditor keys={promptKeys} prompts={prompts} />
              </div>
            )}
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

function SummaryRow({
  label,
  value,
  mono,
  truncate,
}: {
  label: string
  value: string
  mono?: boolean
  truncate?: boolean
}) {
  return (
    <div className="flex items-baseline gap-3">
      <span className="text-muted-foreground w-20 shrink-0">{label}</span>
      <span
        className={`min-w-0 ${mono ? "font-mono" : ""} ${
          truncate ? "truncate" : ""
        }`}
      >
        {value || "—"}
      </span>
    </div>
  )
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
      <Label className="text-muted-foreground text-sm">{label}</Label>
      <Input
        type={type ?? "text"}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        disabled={disabled}
        className={`h-9 text-base ${mono ? "font-mono" : ""} disabled:opacity-50`}
      />
    </div>
  )
}
