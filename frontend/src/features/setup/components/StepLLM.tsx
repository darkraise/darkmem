import { useEffect, useState } from "react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { Switch } from "darkraise-ui/components/switch"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
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
import { Plus, Trash2, X } from "lucide-react"
import { EmptyState } from "@/components/darkmem"
import {
  API_KIND_OPTIONS,
  embeddingKindWarning,
  type LlmApiKind,
} from "@/features/setup/api-kinds"
import {
  PURPOSES,
  REQUIRED_PURPOSES_NON_EMBEDDING,
  missingRequiredModels,
  type Purpose,
  type WizardProvider,
  useSetupWizardStore,
} from "@/features/setup/setupWizardStore"
import { useProbeModels } from "@/hooks/api/use-setup-api"

const BASE_URL_DEFAULTS: Record<LlmApiKind, string> = {
  openai: "https://api.openai.com/v1",
  ollama: "http://localhost:11434/v1",
  anthropic: "https://api.anthropic.com/v1",
  google: "https://generativelanguage.googleapis.com/v1beta/openai",
  deepseek: "https://api.deepseek.com/v1",
  zai: "https://api.z.ai/api/paas/v4",
}

const PURPOSE_HINT: Record<Purpose, string> = {
  embedding: "Vector model used for memory and code search",
  extraction: "Structured-data extraction from memories",
  classification: "Memory classification and tagging",
  reasoning: "Chat answers, summaries, plan reasoning",
  summarization: "Optional — long-form summarisation calls",
  reranker: "Optional — reorders search hits",
}

function ProviderRow({ provider }: { provider: WizardProvider }) {
  const update = useSetupWizardStore((s) => s.updateLlmProvider)
  const remove = useSetupWizardStore((s) => s.removeLlmProvider)
  const probe = useProbeModels()
  const [probeError, setProbeError] = useState<string | null>(null)

  const handleTest = async () => {
    setProbeError(null)
    try {
      const result = await probe.mutateAsync({
        api_kind: provider.api_kind,
        base_url: provider.base_url,
        api_key: provider.api_key || null,
      })
      if (result.error) setProbeError(result.error)
    } catch (e) {
      setProbeError((e as Error).message)
    }
  }

  return (
    <div className="border-border bg-card flex flex-col gap-2.5 rounded-lg border p-3">
      <div className="flex items-center gap-2">
        <span className="font-mono text-sm font-semibold">{provider.name}</span>
        <Button
          size="icon"
          variant="ghost"
          className="text-destructive ml-auto"
          aria-label={`Remove ${provider.name}`}
          onClick={() => remove(provider.name)}
        >
          <Trash2 aria-hidden className="h-4 w-4" />
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-3">
        <Select
          value={provider.api_kind}
          onValueChange={(v) => update(provider.name, { api_kind: v as LlmApiKind })}
        >
          <SelectTrigger aria-label={`${provider.name} api_kind`}>
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {API_KIND_OPTIONS.map((k) => (
              <SelectItem key={k.value} value={k.value}>
                {k.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Input
          value={provider.base_url}
          aria-label={`${provider.name} base_url`}
          onChange={(e) => update(provider.name, { base_url: e.target.value })}
        />
        <Input
          type="password"
          value={provider.api_key}
          aria-label={`${provider.name} api_key`}
          onChange={(e) => update(provider.name, { api_key: e.target.value })}
          placeholder={provider.api_kind === "ollama" ? "(not required)" : "sk-..."}
        />
      </div>
      <div className="flex items-center gap-2">
        <Button
          size="sm"
          variant="outline"
          disabled={probe.isPending}
          onClick={handleTest}
        >
          {probe.isPending ? "Testing…" : "Test"}
        </Button>
        {probe.data && !probe.data.error && (
          <span className="text-muted-foreground text-sm">
            {probe.data.models.length} model{probe.data.models.length === 1 ? "" : "s"}
          </span>
        )}
        {probeError && (
          <span role="alert" className="text-destructive text-sm">
            {probeError}
          </span>
        )}
      </div>
    </div>
  )
}

function NewProviderRow() {
  const providers = useSetupWizardStore((s) => s.llm.providers)
  const addProvider = useSetupWizardStore((s) => s.addLlmProvider)
  const [open, setOpen] = useState(false)
  const [name, setName] = useState("")
  const [apiKind, setApiKind] = useState<LlmApiKind>("openai")
  const [baseUrl, setBaseUrl] = useState(BASE_URL_DEFAULTS.openai)
  const [apiKey, setApiKey] = useState("")

  if (!open) {
    return (
      <button
        type="button"
        onClick={() => setOpen(true)}
        className="border-border text-muted-foreground hover:text-foreground hover:border-primary/50 flex min-h-[3rem] items-center justify-center gap-2 rounded-lg border border-dashed p-3 text-sm transition-colors"
      >
        <Plus aria-hidden className="h-4 w-4" />
        Add provider
      </button>
    )
  }

  const nameTaken = providers.some((p) => p.name === name.trim())
  const canCreate = name.trim().length > 0 && baseUrl.trim().length > 0 && !nameTaken

  const handleApiKindChange = (kind: LlmApiKind) => {
    setApiKind(kind)
    if (!baseUrl || Object.values(BASE_URL_DEFAULTS).includes(baseUrl)) {
      setBaseUrl(BASE_URL_DEFAULTS[kind])
    }
  }

  const submit = () => {
    if (!canCreate) return
    addProvider({ name: name.trim(), api_kind: apiKind, base_url: baseUrl.trim(), api_key: apiKey })
    setOpen(false)
    setName("")
    setApiKind("openai")
    setBaseUrl(BASE_URL_DEFAULTS.openai)
    setApiKey("")
  }

  return (
    <div className="border-border bg-card flex flex-col gap-2.5 rounded-lg border border-dashed p-3">
      <div className="flex items-center gap-2">
        <span className="text-sm font-semibold">New provider</span>
        <Button
          size="icon"
          variant="ghost"
          className="ml-auto"
          aria-label="Cancel new provider"
          onClick={() => setOpen(false)}
        >
          <X aria-hidden className="h-4 w-4" />
        </Button>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        <div className="space-y-1">
          <Label>Name</Label>
          <Input
            value={name}
            aria-label="new provider name"
            onChange={(e) => setName(e.target.value)}
            placeholder="e.g. my-openai"
          />
          {nameTaken && (
            <p className="text-destructive text-sm">Name already in use</p>
          )}
        </div>
        <div className="space-y-1">
          <Label>API kind</Label>
          <Select value={apiKind} onValueChange={(v) => handleApiKindChange(v as LlmApiKind)}>
            <SelectTrigger aria-label="new provider api_kind">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {API_KIND_OPTIONS.map((k) => (
                <SelectItem key={k.value} value={k.value}>
                  {k.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1">
          <Label>Base URL</Label>
          <Input
            value={baseUrl}
            aria-label="new provider base_url"
            onChange={(e) => setBaseUrl(e.target.value)}
          />
        </div>
        <div className="space-y-1">
          <Label>API key</Label>
          <Input
            type="password"
            value={apiKey}
            aria-label="new provider api_key"
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={apiKind === "ollama" ? "(not required)" : "sk-..."}
          />
        </div>
      </div>
      <Button size="sm" disabled={!canCreate} onClick={submit} className="self-end">
        Create
      </Button>
    </div>
  )
}

function PurposeRow({ purpose }: { purpose: Purpose }) {
  const providers = useSetupWizardStore((s) => s.llm.providers)
  const draft = useSetupWizardStore((s) => s.llm.perPurpose[purpose])
  const setLlmPurpose = useSetupWizardStore((s) => s.setLlmPurpose)
  const probe = useProbeModels()

  const provider = providers.find((p) => p.name === draft.provider_name)
  const isEmbedding = purpose === "embedding"
  const required = REQUIRED_PURPOSES_NON_EMBEDDING.includes(purpose)
  const warning = isEmbedding ? embeddingKindWarning(provider?.api_kind) : null

  const providerName = draft.provider_name
  useEffect(() => {
    if (!provider) return
    probe.mutate({
      api_kind: provider.api_kind,
      base_url: provider.base_url,
      api_key: provider.api_key || null,
    })
    // Re-probe only when the *selected* provider's identity or connection
    // details change — `probe.mutate`'s identity is not stable across
    // renders, so depending on it here would re-probe every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [providerName, provider?.api_kind, provider?.base_url, provider?.api_key])

  const modelItems = (probe.data?.models ?? []).map((m) => ({ value: m, label: m }))

  return (
    <div className="grid grid-cols-1 gap-3 sm:grid-cols-[140px_1fr_1fr_auto] sm:items-start">
      <div>
        <div className="text-sm font-medium capitalize">
          {purpose}
          {required && <span className="text-destructive ml-1">*</span>}
        </div>
        <div className="text-muted-foreground text-sm">{PURPOSE_HINT[purpose]}</div>
      </div>
      <Select
        value={draft.provider_name}
        onValueChange={(v) => setLlmPurpose(purpose, { provider_name: v })}
      >
        <SelectTrigger aria-label={`${purpose} provider_name`}>
          <SelectValue placeholder="no provider selected" />
        </SelectTrigger>
        <SelectContent>
          {providers.map((p) => (
            <SelectItem key={p.name} value={p.name} className="font-mono">
              {p.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      <div className="flex flex-col gap-1">
        <Combobox
          items={modelItems}
          inputValue={draft.model}
          onInputValueChange={(d) => setLlmPurpose(purpose, { model: d.value })}
          openOnClick
          openOnFocus
        >
          <ComboboxControl>
            <ComboboxInput aria-label={`${purpose} model`} placeholder="model id" />
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
        {probe.data?.error && (
          <span className="text-destructive text-sm">{probe.data.error}</span>
        )}
        {warning && <span className="text-warning text-sm">{warning}</span>}
      </div>
      {!isEmbedding && purpose !== "reranker" ? (
        <Label className="flex items-center gap-2">
          <Switch
            checked={draft.reasoning}
            onCheckedChange={(v) => setLlmPurpose(purpose, { reasoning: v })}
            aria-label={`${purpose} reasoning`}
          />
          reasoning
        </Label>
      ) : (
        <span />
      )}
    </div>
  )
}

export function StepLLM() {
  const providers = useSetupWizardStore((s) => s.llm.providers)

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Providers</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2.5">
          {providers.length === 0 && (
            <EmptyState
              kind="empty"
              title="No providers defined"
              description="A provider is one vendor connection every purpose below can be pointed at — define at least one to fill in the required purposes."
            />
          )}
          {providers.map((p) => (
            <ProviderRow key={p.name} provider={p} />
          ))}
          <NewProviderRow />
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-base">Assign purposes</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {PURPOSES.map((purpose) => (
            <PurposeRow key={purpose} purpose={purpose} />
          ))}
        </CardContent>
      </Card>
    </div>
  )
}

export function isStepLLMValid(
  llm: ReturnType<typeof useSetupWizardStore.getState>["llm"],
): boolean {
  if (llm.skipped) return true
  if (llm.providers.length === 0) return false
  return missingRequiredModels(llm).length === 0
}
