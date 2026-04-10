import { useState, useEffect } from "react"
import { createFileRoute } from "@tanstack/react-router"
import {
  useEnrichmentConfig,
  useUpdateEnrichmentConfig,
  useTriggerEnrichment,
  useFeatureFlags,
  useUpdateFeatureFlags,
  useClassificationAreas,
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
                    checked={area.key === "general" || enabled.has(area.key)}
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
      </CardContent>
    </Card>
  )
}

function SettingsPage() {
  return (
    <div className="p-6">
      <PageHeader
        title="Settings"
        description="Configure workers, feature flags, and classification areas."
      />

      <div className="mb-8">
        <h3 className="mb-4 text-base font-semibold">Workers</h3>
        <div className="grid grid-cols-1 gap-4">
          <EnrichmentCard />
        </div>
      </div>

      <div className="mb-8">
        <h3 className="mb-4 text-base font-semibold">Feature Flags</h3>
        <div className="grid grid-cols-1 gap-4">
          <FeatureFlagsCard />
        </div>
      </div>

      <div>
        <h3 className="mb-4 text-base font-semibold">Classification</h3>
        <div className="grid grid-cols-1 gap-4">
          <ClassificationAreasCard />
        </div>
      </div>
    </div>
  )
}
