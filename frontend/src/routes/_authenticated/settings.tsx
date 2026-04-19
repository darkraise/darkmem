import { useState, useEffect } from "react"
import { createFileRoute } from "@tanstack/react-router"
import {
  useEnrichmentConfig,
  useUpdateEnrichmentConfig,
  useTriggerEnrichment,
  useFeatureFlags,
  useUpdateFeatureFlags,
  useClassificationAreas,
  useMLDevices,
  useApplyMLDevice,
  useMLModelsHealth,
  useSystemPrompts,
  useUpdateSystemPrompts,
  type ClassificationAreaInfo,
} from "@/hooks/api"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Switch } from "darkraise-ui/components/switch"
import { Label } from "darkraise-ui/components/label"
import { Textarea } from "darkraise-ui/components/textarea"
import { ToggleGroup, ToggleGroupItem } from "darkraise-ui/components/toggle-group"
import { Badge } from "darkraise-ui/components/badge"
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "darkraise-ui/components/tabs"
import { toast } from "sonner"
import { PageHeader } from "darkraise-ui/layout"

export const Route = createFileRoute("/_authenticated/settings")({
  component: SettingsPage,
})

function EnrichmentCard() {
  const { data: config } = useEnrichmentConfig()
  const updateConfig = useUpdateEnrichmentConfig()
  const trigger = useTriggerEnrichment()

  const [enabled, setEnabled] = useState(false)
  const [batchSize, setBatchSize] = useState(5)
  const [interval, setInterval] = useState(10)

  useEffect(() => {
    if (config) {
      setEnabled(config.enabled)
      setBatchSize(config.batch_size)
      setInterval(config.interval_seconds)
    }
  }, [config])

  const handleSave = () => {
    updateConfig.mutate(
      { enabled, batch_size: batchSize, interval_seconds: interval },
      {
        onSuccess: () => toast.success("Enrichment config saved"),
        onError: (err) =>
          toast.error(`Failed to save: ${(err as Error).message}`),
      },
    )
  }

  const handleTrigger = () => {
    trigger.mutate(undefined, {
      onSuccess: (data) => {
        if (data.processed > 0) {
          toast.success(`Enriched ${data.processed} symbols`)
        } else {
          toast.info("No pending symbols")
        }
      },
      onError: () => toast.error("Enrichment failed"),
    })
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Enrichment Worker</CardTitle>
        <p className="text-muted-foreground text-xs">
          LLM-powered code symbol summarization
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <Label className="text-sm">Enabled</Label>
          <Switch checked={enabled} onCheckedChange={setEnabled} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <Label className="text-muted-foreground text-xs">Batch Size</Label>
            <Input
              type="number"
              min={1}
              value={batchSize}
              onChange={(e) => setBatchSize(Number(e.target.value))}
            />
          </div>
          <div>
            <Label className="text-muted-foreground text-xs">
              Interval (seconds)
            </Label>
            <Input
              type="number"
              min={1}
              value={interval}
              onChange={(e) => setInterval(Number(e.target.value))}
            />
          </div>
        </div>
        <div className="flex gap-2">
          <Button
            size="sm"
            onClick={handleSave}
            disabled={updateConfig.isPending}
          >
            {updateConfig.isPending ? "Saving..." : "Save"}
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleTrigger}
            disabled={trigger.isPending}
          >
            {trigger.isPending ? "Running..." : "Run Now"}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

function ClassificationAreasCard() {
  const { data: flags } = useFeatureFlags()
  const updateFlags = useUpdateFeatureFlags()
  const { data: allAreas } = useClassificationAreas()

  if (!flags || !allAreas) return null

  const mode = flags.classification_mode || "simple"
  const enabled = new Set(flags.classification_areas || [])

  const handleModeChange = (newMode: "simple" | "expanded") => {
    updateFlags.mutate(
      { classification_mode: newMode },
      {
        onSuccess: () => toast.success(`Classification mode: ${newMode}`),
        onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
      },
    )
  }

  const toggleArea = (key: string) => {
    const next = enabled.has(key)
      ? flags.classification_areas.filter((a) => a !== key)
      : [...flags.classification_areas, key]
    updateFlags.mutate(
      { classification_areas: next },
      {
        onSuccess: () => toast.success("Classification areas updated"),
        onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
      },
    )
  }

  const simpleTypes = [
    { key: "fact", description: "Neutral factual information, how things work, definitions" },
    { key: "decision", description: "Explicit choices made, trade-offs with reasoning" },
    { key: "preference", description: "Habits, rules, style preferences" },
    { key: "problem", description: "Bugs, errors, root causes, workarounds, gotchas" },
    { key: "reference", description: "Documentation pointers, specs, standards" },
    { key: "architecture", description: "System design, component responsibilities, patterns" },
    { key: "milestone", description: "Breakthroughs, achievements, releases" },
  ]

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Classification</CardTitle>
        <p className="text-muted-foreground text-xs">
          Control how memories are typed during pipeline processing.
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex gap-1 rounded-md border border-border p-0.5 w-fit">
          {(["simple", "expanded"] as const).map((m) => (
            <button
              key={m}
              onClick={() => handleModeChange(m)}
              disabled={updateFlags.isPending}
              className={`px-3 py-1 rounded text-xs font-medium transition-colors ${
                mode === m
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
            >
              {m.charAt(0).toUpperCase() + m.slice(1)}
            </button>
          ))}
        </div>

        {mode === "simple" ? (
          <div className="space-y-2">
            <p className="text-muted-foreground text-xs">
              7 universal types optimized for small models. Invalid LLM outputs are
              automatically remapped.
            </p>
            <div className="divide-y divide-border rounded-md border border-border">
              {simpleTypes.map((t) => (
                <div key={t.key} className="flex items-baseline gap-3 px-3 py-2">
                  <code className="text-xs font-semibold shrink-0 w-24">{t.key}</code>
                  <span className="text-muted-foreground text-xs">{t.description}</span>
                </div>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-1">
            <p className="text-muted-foreground text-xs">
              Fine-grained types from enabled domain areas. Best with larger models.
            </p>
            <div className="divide-y divide-border rounded-md border border-border">
              {allAreas.map((area: ClassificationAreaInfo) => (
                <div key={area.key} className="flex items-center justify-between px-3 py-2.5">
                  <div className="min-w-0">
                    <span className="text-sm font-medium">{area.display_name}</span>
                    <p className="text-muted-foreground text-xs truncate">
                      {area.types.join(", ")}
                    </p>
                  </div>
                  <Switch
                    checked={enabled.has(area.key)}
                    onCheckedChange={() => toggleArea(area.key)}
                    disabled={area.key === "general" || updateFlags.isPending}
                  />
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

function FeatureFlagsCard() {
  const { data: flags, isLoading } = useFeatureFlags()
  const updateFlags = useUpdateFeatureFlags()

  if (isLoading || !flags) return null

  const items = [
    { label: "Hybrid Search (BM25 + RRF)", key: "hybrid_search_enabled" as const, description: "Combines vector similarity with full-text search via Reciprocal Rank Fusion" },
    { label: "LLM Enrichment", key: "llm_enrichment_enabled" as const, description: "Run LLM classification alongside regex for A/B comparison" },
    { label: "Reranker", key: "reranker_enabled" as const, description: "Re-score search results using LLM relevance scoring" },
    { label: "ML Extraction", key: "ml_extraction" as const, description: "Use fine-tuned GLiNER + ModernBERT + REBEL heads for entity + relation extraction. LLM path is the fallback." },
    { label: "ML Classification", key: "ml_classification" as const, description: "Use the fine-tuned memory-type classifier instead of the LLM." },
    { label: "ML Retrieval", key: "ml_retrieval" as const, description: "Use the fine-tuned bge retriever for query embeddings. Falls back to the embedding LLM if the head is unavailable." },
    { label: "ML Shadow Mode", key: "ml_shadow_mode" as const, description: "Run ML heads in shadow mode alongside LLM for logging/comparison without affecting user-facing output." },
  ]

  const handleToggle = (key: keyof typeof flags, value: boolean) => {
    updateFlags.mutate(
      { [key]: value },
      {
        onSuccess: () => toast.success(`${key.replace(/_/g, " ")} ${value ? "enabled" : "disabled"}`),
        onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
      },
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Feature Flags</CardTitle>
        <p className="text-muted-foreground text-xs">
          Toggle pipeline features. Changes take effect on the next operation.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {items.map((item) => (
          <div key={item.key} className="flex items-center justify-between">
            <div>
              <Label className="text-sm">{item.label}</Label>
              <p className="text-muted-foreground text-xs">{item.description}</p>
            </div>
            <Switch
              checked={flags[item.key]}
              onCheckedChange={(v) => handleToggle(item.key, v)}
              disabled={updateFlags.isPending}
            />
          </div>
        ))}
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <div>
            <Label className="text-sm">Pipeline Concurrency</Label>
            <p className="text-muted-foreground text-xs">Max parallel LLM calls during batch processing</p>
          </div>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min={1}
              max={20}
              value={flags.pipeline_concurrency}
              onChange={(e) => {
                const v = Math.max(1, Math.min(20, Number(e.target.value) || 5))
                updateFlags.mutate(
                  { pipeline_concurrency: v },
                  {
                    onSuccess: () => toast.success(`Pipeline concurrency set to ${v}`),
                    onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
                  },
                )
              }}
              className="w-16 h-8 text-sm text-center"
              disabled={updateFlags.isPending}
            />
          </div>
        </div>
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <div>
            <Label className="text-sm">Embedding Batch Size</Label>
            <p className="text-muted-foreground text-xs">Texts per embed call to the embedding model</p>
          </div>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min={1}
              max={200}
              value={flags.embedding_batch_size ?? 20}
              onChange={(e) => {
                const v = Math.max(1, Math.min(200, Number(e.target.value) || 20))
                updateFlags.mutate(
                  { embedding_batch_size: v },
                  {
                    onSuccess: () => toast.success(`Embedding batch size set to ${v}`),
                    onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
                  },
                )
              }}
              className="w-16 h-8 text-sm text-center"
              disabled={updateFlags.isPending}
            />
          </div>
        </div>
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <div>
            <Label className="text-sm">Embedding Concurrency</Label>
            <p className="text-muted-foreground text-xs">Parallel embed calls when chunked batching</p>
          </div>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min={1}
              max={10}
              value={flags.embedding_concurrency ?? 1}
              onChange={(e) => {
                const v = Math.max(1, Math.min(10, Number(e.target.value) || 1))
                updateFlags.mutate(
                  { embedding_concurrency: v },
                  {
                    onSuccess: () => toast.success(`Embedding concurrency set to ${v}`),
                    onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
                  },
                )
              }}
              className="w-16 h-8 text-sm text-center"
              disabled={updateFlags.isPending}
            />
          </div>
        </div>
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <div>
            <Label className="text-sm">Entity Cache TTL (minutes)</Label>
            <p className="text-muted-foreground text-xs">How long entity lookups are cached during extraction</p>
          </div>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min={1}
              max={1440}
              value={flags.entity_cache_ttl_minutes ?? 60}
              onChange={(e) => {
                const v = Math.max(1, Math.min(1440, Number(e.target.value) || 60))
                updateFlags.mutate(
                  { entity_cache_ttl_minutes: v },
                  {
                    onSuccess: () => toast.success(`Entity cache TTL set to ${v} minutes`),
                    onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
                  },
                )
              }}
              className="w-16 h-8 text-sm text-center"
              disabled={updateFlags.isPending}
            />
          </div>
        </div>
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <div>
            <Label className="text-sm">Confidence Rank γ</Label>
            <p className="text-muted-foreground text-xs">Multiplicative weight of memory confidence in retrieval rank fusion. 0 disables. Try 0.2–0.5.</p>
          </div>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min={0}
              max={5}
              step={0.1}
              value={flags.confidence_rank_gamma ?? 0}
              onChange={(e) => {
                const v = Math.max(0, Math.min(5, Number(e.target.value) || 0))
                updateFlags.mutate(
                  { confidence_rank_gamma: v },
                  {
                    onSuccess: () => toast.success(`Confidence γ set to ${v}`),
                    onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
                  },
                )
              }}
              className="w-20 h-8 text-sm text-center"
              disabled={updateFlags.isPending}
            />
          </div>
        </div>
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <div>
            <Label className="text-sm">ML Idle TTL (minutes)</Label>
            <p className="text-muted-foreground text-xs">How long a loaded ML group stays resident after idle. 0 = never evict.</p>
          </div>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min={0}
              max={1440}
              value={flags.ml_idle_ttl_minutes ?? 30}
              onChange={(e) => {
                const v = Math.max(0, Math.min(1440, Number(e.target.value) || 0))
                updateFlags.mutate(
                  { ml_idle_ttl_minutes: v },
                  {
                    onSuccess: () => toast.success(`ML idle TTL set to ${v} min`),
                    onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
                  },
                )
              }}
              className="w-16 h-8 text-sm text-center"
              disabled={updateFlags.isPending}
            />
          </div>
        </div>
        <div className="flex items-center justify-between pt-2 border-t border-border">
          <div>
            <Label className="text-sm">Eviction Check Interval (seconds)</Label>
            <p className="text-muted-foreground text-xs">How often the background loop polls for idle ML groups.</p>
          </div>
          <div className="flex items-center gap-2">
            <Input
              type="number"
              min={10}
              max={3600}
              value={flags.ml_eviction_check_interval_seconds ?? 60}
              onChange={(e) => {
                const v = Math.max(10, Math.min(3600, Number(e.target.value) || 60))
                updateFlags.mutate(
                  { ml_eviction_check_interval_seconds: v },
                  {
                    onSuccess: () => toast.success(`Eviction check set to ${v}s`),
                    onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
                  },
                )
              }}
              className="w-16 h-8 text-sm text-center"
              disabled={updateFlags.isPending}
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function MLDeviceCard() {
  const { data: devices, isLoading } = useMLDevices()
  const { data: health } = useMLModelsHealth()
  const applyDevice = useApplyMLDevice()

  if (isLoading || !devices) return null

  const currentId =
    devices.current.ml_device === "cpu"
      ? "cpu"
      : `cuda:${devices.current.ml_cuda_index}`

  const handlePick = (id: string) => {
    if (id === currentId) return
    if (id === "cpu") {
      applyDevice.mutate(
        { ml_device: "cpu", ml_cuda_index: 0 },
        {
          onSuccess: (r) =>
            toast.success(
              `Loaded on ${r.effective_device}${r.reloaded ? "" : " (reload deferred)"}`,
            ),
          onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
        },
      )
      return
    }
    const idx = Number(id.replace(/^cuda:/, "")) || 0
    applyDevice.mutate(
      { ml_device: "cuda", ml_cuda_index: idx },
      {
        onSuccess: (r) =>
          toast.success(
            `Loaded on ${r.effective_device}${r.reloaded ? "" : " (reload deferred)"}`,
          ),
        onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
      },
    )
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">ML Pipeline Device</CardTitle>
        <p className="text-muted-foreground text-xs">
          Pick the device the fine-tuned ML heads run on. Changes take effect immediately and reload every loaded group.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="space-y-1">
          <Label className="text-sm">Device</Label>
          <ToggleGroup
            type="single"
            variant="outline"
            value={currentId}
            onValueChange={(id) => {
              if (!id) return
              handlePick(id)
            }}
            disabled={applyDevice.isPending}
            className="flex-wrap justify-start"
          >
            {devices.available.map((d) => (
              <ToggleGroupItem key={d.id} value={d.id} className="text-xs">
                {d.label}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>

        <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border text-xs">
          <div>
            <Label className="text-xs text-muted-foreground">Persisted Setting</Label>
            <p className="mt-1 font-mono">
              {devices.current.ml_device}
              {devices.current.ml_device === "cuda" ? `:${devices.current.ml_cuda_index}` : ""}
            </p>
          </div>
          <div>
            <Label className="text-xs text-muted-foreground">Effective</Label>
            <p className="mt-1 font-mono">
              {devices.current.effective_device ?? "(not loaded)"}
            </p>
          </div>
        </div>

        {health?.groups && (
          <div className="space-y-1 pt-2 border-t border-border">
            <Label className="text-xs text-muted-foreground">Group State</Label>
            <div className="grid grid-cols-3 gap-2 text-xs">
              {(["extraction", "classification", "retriever"] as const).map((g) => {
                const row = health.groups?.[g]
                const loaded = row?.loaded ?? false
                const idle = row?.idle_seconds
                return (
                  <div
                    key={g}
                    className="rounded-md border border-border p-2 space-y-0.5"
                  >
                    <div className="flex items-center justify-between">
                      <Label className="font-medium capitalize text-xs">{g}</Label>
                      <Badge variant={loaded ? "default" : "outline"} className="text-[10px] py-0 px-1.5">
                        {loaded ? "loaded" : "idle"}
                      </Badge>
                    </div>
                    <p className="text-muted-foreground">
                      {loaded ? `idle ${idle ?? 0}s` : "not loaded"}
                    </p>
                  </div>
                )
              })}
            </div>
            {typeof health.vram_allocated_mb === "number" && (
              <p className="text-muted-foreground text-xs pt-1">
                VRAM allocated: {health.vram_allocated_mb.toFixed(0)} MB
              </p>
            )}
          </div>
        )}

        <p className="text-muted-foreground text-xs pt-1">
          CPU fallback: {devices.current.cpu_fallback ? "on" : "off"}. If a CUDA load fails the heads reload on CPU.
        </p>
      </CardContent>
    </Card>
  )
}

const PROMPT_LABELS: Record<string, string> = {
  extraction: "Extraction (JSON entities + relations)",
  extraction_entities: "Extraction — entities tool-call",
  extraction_relationships: "Extraction — relationships tool-call",
  classification: "Memory-type classification",
  reasoning: "Reasoning / Q&A over memories",
  summarization: "Code summarization",
  chat: "Chat assistant",
  cluster_naming: "Cluster naming",
  agent_instructions: "Agent tool instructions",
}

function SystemPromptsCard() {
  const { data, isLoading } = useSystemPrompts()
  const update = useUpdateSystemPrompts()
  const [selected, setSelected] = useState<string>("extraction")
  const [draft, setDraft] = useState<string>("")
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (!data) return
    const override = data.overrides[selected] ?? ""
    const fallback = data.defaults[selected] ?? ""
    setDraft(override || fallback)
    setDirty(false)
  }, [data, selected])

  if (isLoading || !data) return null

  const purposes = Object.keys(data.defaults).sort()
  const isOverridden = Boolean(data.overrides[selected])
  const isDefault = (data.defaults[selected] ?? "") === draft

  const handleSave = () => {
    const body = isDefault
      ? { overrides: { [selected]: "" } } // empty = clear override
      : { overrides: { [selected]: draft } }
    update.mutate(body, {
      onSuccess: () =>
        toast.success(
          isDefault
            ? `Reverted ${selected} to the default prompt`
            : `Saved override for ${selected}`,
        ),
      onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
    })
    setDirty(false)
  }

  const handleRevert = () => {
    const fallback = data.defaults[selected] ?? ""
    setDraft(fallback)
    setDirty(true)
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">System Prompts</CardTitle>
        <p className="text-muted-foreground text-xs">
          Override the built-in system prompts used for LLM extraction, classification, reasoning, and more. Leave empty to fall back to the default.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        <ToggleGroup
          type="single"
          variant="outline"
          value={selected}
          onValueChange={(p) => {
            if (p) setSelected(p)
          }}
          className="flex-wrap justify-start"
        >
          {purposes.map((p) => {
            const overridden = Boolean(data.overrides[p])
            return (
              <ToggleGroupItem key={p} value={p} className="text-xs gap-1.5">
                <span>{PROMPT_LABELS[p] ?? p}</span>
                {overridden && (
                  <Badge variant="secondary" className="text-[10px] py-0 px-1.5">
                    custom
                  </Badge>
                )}
              </ToggleGroupItem>
            )
          })}
        </ToggleGroup>

        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <Label className="text-xs text-muted-foreground">
              {isOverridden ? "Overridden" : "Using built-in default"}
            </Label>
            <div className="flex gap-2">
              <Button
                type="button"
                variant="ghost"
                size="sm"
                onClick={handleRevert}
                disabled={update.isPending}
              >
                Load default
              </Button>
              <Button
                type="button"
                size="sm"
                onClick={handleSave}
                disabled={update.isPending || !dirty}
              >
                {isDefault ? "Clear override" : "Save override"}
              </Button>
            </div>
          </div>
          <Textarea
            className="min-h-[220px] font-mono text-xs"
            value={draft}
            onChange={(e) => {
              setDraft(e.target.value)
              setDirty(true)
            }}
          />
          <p className="text-muted-foreground text-xs">
            {draft.length.toLocaleString()} / 20,000 characters
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

const SETTINGS_TABS = [
  { value: "flags", label: "Feature Flags" },
  { value: "ml", label: "ML Pipeline" },
  { value: "prompts", label: "System Prompts" },
  { value: "classification", label: "Classification" },
  { value: "workers", label: "Workers" },
] as const

type SettingsTabValue = (typeof SETTINGS_TABS)[number]["value"]

function SettingsPage() {
  // Persist the active tab across reloads so deep-links from error toasts and
  // admin workflows stay on the relevant pane.
  const [tab, setTab] = useState<SettingsTabValue>(() => {
    if (typeof window === "undefined") return "flags"
    const stored = window.localStorage.getItem("darkmem.settings.tab")
    if (stored && SETTINGS_TABS.some((t) => t.value === stored)) {
      return stored as SettingsTabValue
    }
    return "flags"
  })

  const handleTabChange = (next: string) => {
    const match = SETTINGS_TABS.find((t) => t.value === next)
    if (!match) return
    setTab(match.value)
    if (typeof window !== "undefined") {
      window.localStorage.setItem("darkmem.settings.tab", match.value)
    }
  }

  return (
    <div className="p-6">
      <PageHeader
        title="Settings"
        description="Configure workers, feature flags, ML pipeline, prompts, and classification."
      />

      <Tabs value={tab} onValueChange={handleTabChange} className="mt-4">
        <TabsList className="flex-wrap">
          {SETTINGS_TABS.map((t) => (
            <TabsTrigger key={t.value} value={t.value}>
              {t.label}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="flags" className="mt-4">
          <FeatureFlagsCard />
        </TabsContent>

        <TabsContent value="ml" className="mt-4">
          <MLDeviceCard />
        </TabsContent>

        <TabsContent value="prompts" className="mt-4">
          <SystemPromptsCard />
        </TabsContent>

        <TabsContent value="classification" className="mt-4">
          <ClassificationAreasCard />
        </TabsContent>

        <TabsContent value="workers" className="mt-4">
          <EnrichmentCard />
        </TabsContent>
      </Tabs>
    </div>
  )
}
