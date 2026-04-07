import { useState, useEffect } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { useLlmConfig, useUpdateLlmConfig, type LlmPurposeConfig } from "@/hooks/api"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Textarea } from "darkraise-ui/components/textarea"
import { Label } from "darkraise-ui/components/label"
import { Card, CardContent, CardHeader, CardTitle } from "darkraise-ui/components/card"
import { PageHeader } from "darkraise-ui/layout"

export const Route = createFileRoute("/_authenticated/llm")({
  component: LlmConfigPage,
})

function PurposeCard({
  title,
  config,
  onSave,
  saving,
}: {
  title: string
  config: LlmPurposeConfig | undefined
  onSave: (purpose: string, data: Partial<LlmPurposeConfig>) => void
  saving: boolean
}) {
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState({
    provider: "",
    base_url: "",
    model: "",
    api_key: "",
    dimensions: "",
    params: "",
  })

  useEffect(() => {
    if (config) {
      setForm({
        provider: config.provider || "",
        base_url: config.base_url || "",
        model: config.model || "",
        api_key: config.api_key === "***" ? "***" : config.api_key || "",
        dimensions: config.dimensions?.toString() || "",
        params: Object.keys(config.params || {}).length > 0 ? JSON.stringify(config.params, null, 2) : "",
      })
    }
  }, [config])

  if (!config) return null

  const handleSave = () => {
    const data: Record<string, unknown> = {
      provider: form.provider,
      base_url: form.base_url,
      model: form.model,
    }
    if (form.api_key && form.api_key !== "***") {
      data.api_key = form.api_key
    }
    if (form.dimensions) {
      data.dimensions = parseInt(form.dimensions, 10)
    }
    if (form.params.trim()) {
      try {
        data.params = JSON.parse(form.params)
      } catch {
        alert("Invalid JSON in params")
        return
      }
    } else {
      data.params = {}
    }
    onSave(title.toLowerCase(), data)
    setEditing(false)
  }

  if (!editing) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm capitalize">{title}</CardTitle>
            <Button variant="ghost" size="sm" className="text-xs h-6 px-2" onClick={() => setEditing(true)}>
              Edit
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Provider</span>
              <span>{config.provider}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Model</span>
              <span className="font-mono">{config.model}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Base URL</span>
              <span className="font-mono text-xs">{config.base_url}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">API Key</span>
              <span>{config.api_key ?? "none"}</span>
            </div>
            {config.dimensions && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">Dimensions</span>
                <span>{config.dimensions}</span>
              </div>
            )}
            {Object.keys(config.params || {}).length > 0 && (
              <div>
                <span className="text-muted-foreground">Params</span>
                <pre className="mt-1 text-xs bg-background p-2 rounded">
                  {JSON.stringify(config.params, null, 2)}
                </pre>
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-2 border-primary">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm capitalize">{title}</CardTitle>
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" className="text-xs h-6 px-2" onClick={() => setEditing(false)}>
              Cancel
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs h-6 px-2 text-primary"
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-3 text-sm">
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Provider</Label>
            <Input value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })} className="h-8 text-sm" />
          </div>
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Base URL</Label>
            <Input value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })} className="h-8 text-sm font-mono" />
          </div>
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Model</Label>
            <Input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })} className="h-8 text-sm font-mono" />
          </div>
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">API Key</Label>
            <Input
              value={form.api_key}
              onChange={(e) => setForm({ ...form, api_key: e.target.value })}
              type="password"
              className="h-8 text-sm font-mono"
              placeholder="Leave as *** to keep existing"
            />
          </div>
          {title.toLowerCase() === "embedding" && (
            <div className="space-y-1">
              <Label className="text-xs text-muted-foreground">Dimensions</Label>
              <Input
                value={form.dimensions}
                onChange={(e) => setForm({ ...form, dimensions: e.target.value })}
                type="number"
                className="h-8 text-sm"
              />
            </div>
          )}
          <div className="space-y-1">
            <Label className="text-xs text-muted-foreground">Params (JSON)</Label>
            <Textarea
              value={form.params}
              onChange={(e) => setForm({ ...form, params: e.target.value })}
              rows={3}
              className="text-sm font-mono resize-none"
              placeholder='{"temperature": 0.2}'
            />
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

function LlmConfigPage() {
  const { data, isLoading, error } = useLlmConfig()
  const updateConfig = useUpdateLlmConfig()

  const handleSave = (purpose: string, purposeData: Partial<LlmPurposeConfig>) => {
    updateConfig.mutate({ [purpose]: purposeData })
  }

  return (
    <div className="p-6">
      <PageHeader
        title="LLM Configuration"
        description="Configure LLM providers for each purpose. Changes take effect on the next memory operation."
      />
      {isLoading && <p className="text-muted-foreground">Loading...</p>}
      {error && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 mb-4">
          <p className="text-destructive text-sm">Failed to load config. Make sure your API key has admin scope.</p>
          <p className="text-xs text-muted-foreground mt-1">{(error as Error).message}</p>
        </div>
      )}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <PurposeCard title="Embedding" config={data?.embedding} onSave={handleSave} saving={updateConfig.isPending} />
        <PurposeCard title="Extraction" config={data?.extraction} onSave={handleSave} saving={updateConfig.isPending} />
        <PurposeCard title="Reasoning" config={data?.reasoning} onSave={handleSave} saving={updateConfig.isPending} />
        <PurposeCard title="Summarization" config={data?.summarization} onSave={handleSave} saving={updateConfig.isPending} />
      </div>
    </div>
  )
}
