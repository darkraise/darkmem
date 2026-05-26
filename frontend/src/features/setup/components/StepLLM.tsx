import { useState } from "react"
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
  API_KIND_OPTIONS,
  type LlmApiKind,
} from "@/features/pipeline/api-kinds"
import {
  PURPOSES,
  REQUIRED_PURPOSES_NON_EMBEDDING,
  type Purpose,
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

// Which api_kinds expose an embeddings endpoint at all. Anthropic and
// DeepSeek do not — picking those should auto-clear the supports_embedding
// toggle so step 2 doesn't sit there demanding an embedding model that the
// vendor cannot serve. The user can still flip it back on for custom
// proxies that route embeddings through an OpenAI-compat endpoint.
const KIND_SUPPORTS_EMBEDDING: Record<LlmApiKind, boolean> = {
  openai: true,
  ollama: true,
  google: true,
  zai: true,
  anthropic: false,
  deepseek: false,
}

const PURPOSE_HINT: Record<Purpose, string> = {
  embedding: "Vector model used for memory and code search",
  extraction: "Structured-data extraction from memories",
  classification: "Memory classification and tagging",
  reasoning: "Chat answers, summaries, plan reasoning",
  summarization: "Optional — long-form summarisation calls",
  reranker: "Optional — reorders search hits",
}

export function StepLLM() {
  const llm = useSetupWizardStore((s) => s.llm)
  const setLlmField = useSetupWizardStore((s) => s.setLlmField)
  const setLlmPurpose = useSetupWizardStore((s) => s.setLlmPurpose)
  const probe = useProbeModels()
  const [probeError, setProbeError] = useState<string | null>(null)

  const handleApiKindChange = (api_kind: LlmApiKind) => {
    setLlmField("api_kind", api_kind)
    if (
      !llm.base_url ||
      Object.values(BASE_URL_DEFAULTS).includes(llm.base_url)
    ) {
      setLlmField("base_url", BASE_URL_DEFAULTS[api_kind])
    }
    setLlmField("supports_embedding", KIND_SUPPORTS_EMBEDDING[api_kind])
  }

  const handleFetchModels = async () => {
    setProbeError(null)
    try {
      const result = await probe.mutateAsync({
        api_kind: llm.api_kind as LlmApiKind,
        base_url: llm.base_url,
        api_key: llm.api_key || null,
      })
      if (result.error) {
        setProbeError(result.error)
        setLlmField("models", [])
      } else {
        setLlmField("models", result.models)
      }
    } catch (e) {
      setProbeError((e as Error).message)
    }
  }

  const visiblePurposes = PURPOSES.filter(
    (p) => p !== "embedding" || llm.supports_embedding,
  )

  return (
    <div className="space-y-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Provider</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="space-y-1">
            <Label>API kind</Label>
            <Select
              value={llm.api_kind}
              onValueChange={(v) => handleApiKindChange(v as LlmApiKind)}
            >
              <SelectTrigger>
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
              value={llm.base_url}
              onChange={(e) => setLlmField("base_url", e.target.value)}
            />
          </div>
          <div className="space-y-1">
            <Label>API key</Label>
            <Input
              type="password"
              value={llm.api_key}
              onChange={(e) => setLlmField("api_key", e.target.value)}
              placeholder={
                llm.api_kind === "ollama"
                  ? "(not required for Ollama)"
                  : "sk-..."
              }
            />
          </div>
          <div className="flex items-start gap-2">
            <Switch
              className="mt-0.5"
              checked={llm.supports_embedding}
              onCheckedChange={(v) => setLlmField("supports_embedding", v)}
            />
            <div className="text-sm">
              <div>Provider supports embeddings</div>
              <div className="text-muted-foreground text-xs">
                Auto-set from API kind (off for Anthropic and DeepSeek).
                Override only for custom proxies that route embeddings through
                this base URL.
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={handleFetchModels} disabled={probe.isPending}>
              {probe.isPending ? "Fetching..." : "Fetch available models"}
            </Button>
            {llm.models.length > 0 && (
              <span className="text-muted-foreground text-sm">
                {llm.models.length} model{llm.models.length === 1 ? "" : "s"}{" "}
                loaded
              </span>
            )}
          </div>
          {probeError && (
            <p role="alert" className="text-destructive text-sm">
              {probeError}
            </p>
          )}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Per-purpose models</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {visiblePurposes.map((purpose) => {
            const draft = llm.perPurpose[purpose]
            const required =
              purpose === "embedding"
                ? llm.supports_embedding
                : REQUIRED_PURPOSES_NON_EMBEDDING.includes(purpose)
            return (
              <div
                key={purpose}
                className="grid grid-cols-[140px,1fr,auto] items-center gap-3"
              >
                <div>
                  <div className="text-sm font-medium capitalize">
                    {purpose}
                    {required && (
                      <span className="text-destructive ml-1">*</span>
                    )}
                  </div>
                  <div className="text-muted-foreground text-xs">
                    {PURPOSE_HINT[purpose]}
                  </div>
                </div>
                <div className="flex flex-col gap-1">
                  <Input
                    list={`models-${purpose}`}
                    value={draft.model}
                    onChange={(e) =>
                      setLlmPurpose(purpose, { model: e.target.value })
                    }
                    placeholder="model id"
                  />
                  <datalist id={`models-${purpose}`}>
                    {llm.models.map((m) => (
                      <option key={m} value={m} />
                    ))}
                  </datalist>
                </div>
                {purpose !== "embedding" && purpose !== "reranker" ? (
                  <label className="flex items-center gap-2 text-xs">
                    <Switch
                      checked={draft.reasoning}
                      onCheckedChange={(v) =>
                        setLlmPurpose(purpose, { reasoning: v })
                      }
                    />
                    reasoning
                  </label>
                ) : (
                  <span />
                )}
              </div>
            )
          })}
        </CardContent>
      </Card>
    </div>
  )
}

export function isStepLLMValid(
  llm: ReturnType<typeof useSetupWizardStore.getState>["llm"],
): boolean {
  if (llm.skipped) return true
  if (!llm.api_kind.trim()) return false
  if (!llm.base_url.trim()) return false
  if (llm.supports_embedding && !llm.perPurpose.embedding.model.trim())
    return false
  for (const p of REQUIRED_PURPOSES_NON_EMBEDDING) {
    if (!llm.perPurpose[p].model.trim()) return false
  }
  return true
}
