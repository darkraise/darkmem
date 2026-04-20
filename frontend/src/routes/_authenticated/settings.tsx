import { useState, useEffect } from "react"
import { createFileRoute } from "@tanstack/react-router"
import {
  useEnrichmentConfig,
  useUpdateEnrichmentConfig,
  useTriggerEnrichment,
  useFeatureFlags,
  useUpdateFeatureFlags,
  useClassificationAreas,
  useSystemPrompts,
  useUpdateSystemPrompts,
  type ClassificationAreaInfo,
} from "@/hooks/api"
import { ORPHAN_PROMPTS } from "@/components/pipeline/prompt-map"
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
import { resolveStoredTab, type SettingsTabValue } from "@/lib/settings-tab"

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

  const toggles = [
    { label: "Hybrid Search (BM25 + RRF)", key: "hybrid_search_enabled" as const, description: "Combines vector similarity with full-text search via Reciprocal Rank Fusion" },
    { label: "LLM Enrichment", key: "llm_enrichment_enabled" as const, description: "Run LLM classification alongside regex for A/B comparison" },
    { label: "Reranker", key: "reranker_enabled" as const, description: "Re-score search results using LLM relevance scoring" },
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

  const NumericRow = ({
    label, description, flagKey, min, max, step, defaultValue, width = "w-16",
  }: {
    label: string; description: string; flagKey: keyof typeof flags;
    min: number; max: number; step?: number; defaultValue: number; width?: string
  }) => (
    <div className="flex items-center justify-between pt-2 border-t border-border">
      <div>
        <Label className="text-sm">{label}</Label>
        <p className="text-muted-foreground text-xs">{description}</p>
      </div>
      <Input
        type="number"
        min={min}
        max={max}
        step={step}
        value={(flags[flagKey] as number) ?? defaultValue}
        onChange={(e) => {
          const v = Math.max(min, Math.min(max, Number(e.target.value) || defaultValue))
          updateFlags.mutate(
            { [flagKey]: v },
            {
              onSuccess: () => toast.success(`${label} set to ${v}`),
              onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
            },
          )
        }}
        className={`${width} h-8 text-sm text-center`}
        disabled={updateFlags.isPending}
      />
    </div>
  )

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Feature Flags</CardTitle>
        <p className="text-muted-foreground text-xs">
          Toggle pipeline features. Changes take effect on the next operation.
        </p>
      </CardHeader>
      <CardContent className="space-y-3">
        {toggles.map((item) => (
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
        <NumericRow label="Pipeline Concurrency" description="Max parallel LLM calls during batch processing" flagKey="pipeline_concurrency" min={1} max={20} defaultValue={5} />
        <NumericRow label="Embedding Batch Size" description="Texts per embed call" flagKey="embedding_batch_size" min={1} max={200} defaultValue={20} />
        <NumericRow label="Embedding Concurrency" description="Parallel embed calls" flagKey="embedding_concurrency" min={1} max={10} defaultValue={1} />
        <NumericRow label="Entity Cache TTL (minutes)" description="How long entity lookups are cached during extraction" flagKey="entity_cache_ttl_minutes" min={1} max={1440} defaultValue={60} />
        <NumericRow label="Confidence Rank γ" description="Multiplicative weight of memory confidence in retrieval rank fusion. 0 disables. Try 0.2–0.5." flagKey="confidence_rank_gamma" min={0} max={5} step={0.1} defaultValue={0} width="w-20" />
      </CardContent>
    </Card>
  )
}

function AssistantPromptsCard() {
  const { data, isLoading } = useSystemPrompts()
  const update = useUpdateSystemPrompts()
  const [selected, setSelected] = useState<string>(ORPHAN_PROMPTS[0])
  const [draft, setDraft] = useState("")
  const [dirty, setDirty] = useState(false)

  useEffect(() => {
    if (!data) return
    setDraft(data.overrides[selected] ?? data.defaults[selected] ?? "")
    setDirty(false)
  }, [data, selected])

  if (isLoading || !data) return null
  const isOverridden = Boolean(data.overrides[selected])
  const isDefault = (data.defaults[selected] ?? "") === draft

  const save = () => {
    const body = isDefault
      ? { overrides: { [selected]: "" } }
      : { overrides: { [selected]: draft } }
    update.mutate(body, {
      onSuccess: () =>
        toast.success(isDefault ? `Reverted ${selected}` : `Saved override for ${selected}`),
      onError: (err) => toast.error(`Failed: ${(err as Error).message}`),
    })
    setDirty(false)
  }

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Assistant Prompts</CardTitle>
        <p className="text-muted-foreground text-xs">
          Override the system prompts used by chat, cluster naming, and agent instructions.
          Leave empty to fall back to the default.
        </p>
      </CardHeader>
      <CardContent className="space-y-2">
        <ToggleGroup
          type="single"
          variant="outline"
          value={selected}
          onValueChange={(p) => {
            if (p) setSelected(p)
          }}
          className="flex-wrap justify-start"
        >
          {ORPHAN_PROMPTS.map((p) => (
            <ToggleGroupItem key={p} value={p} className="text-xs">
              {p}
              {data.overrides[p] && (
                <Badge variant="secondary" className="ml-1 text-[10px]">custom</Badge>
              )}
            </ToggleGroupItem>
          ))}
        </ToggleGroup>
        <Textarea
          className="min-h-[200px] font-mono text-xs"
          value={draft}
          onChange={(e) => {
            setDraft(e.target.value)
            setDirty(true)
          }}
        />
        <div className="flex items-center justify-between">
          <span className="text-[10px] text-muted-foreground">
            {draft.length.toLocaleString()} / 20,000 · {isOverridden ? "overridden" : "using default"}
          </span>
          <Button size="sm" onClick={save} disabled={update.isPending || !dirty}>
            {isDefault ? "Clear override" : "Save override"}
          </Button>
        </div>
      </CardContent>
    </Card>
  )
}

const SETTINGS_TABS = [
  { value: "flags", label: "Feature Flags" },
  { value: "classification", label: "Classification" },
  { value: "workers", label: "Workers" },
  { value: "assistant", label: "Assistant Prompts" },
] as const satisfies readonly { value: SettingsTabValue; label: string }[]

function SettingsPage() {
  const [tab, setTab] = useState<SettingsTabValue>(() => {
    if (typeof window === "undefined") return "flags"
    return resolveStoredTab(window.localStorage.getItem("darkmem.settings.tab"))
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
        description="Configure workers, feature flags, prompts, and classification."
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

        <TabsContent value="classification" className="mt-4">
          <ClassificationAreasCard />
        </TabsContent>

        <TabsContent value="workers" className="mt-4">
          <EnrichmentCard />
        </TabsContent>

        <TabsContent value="assistant" className="mt-4">
          <AssistantPromptsCard />
        </TabsContent>
      </Tabs>
    </div>
  )
}
