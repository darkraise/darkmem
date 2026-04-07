import { useState, useEffect } from "react"
import { createFileRoute } from "@tanstack/react-router"
import {
  useSystemPrompts,
  useUpdateSystemPrompt,
  useResetSystemPrompt,
  useEnrichmentConfig,
  useUpdateEnrichmentConfig,
  useTriggerEnrichment,
  type SystemPromptProfile,
} from "@/hooks/api"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Switch } from "darkraise-ui/components/switch"
import { Textarea } from "darkraise-ui/components/textarea"
import { Label } from "darkraise-ui/components/label"
import { toast } from "sonner"
import { PageHeader } from "darkraise-ui/layout"

export const Route = createFileRoute("/_authenticated/settings")({
  component: SettingsPage,
})

function PromptCard({
  profile,
  isEditing,
  onEdit,
  onCancel,
}: {
  profile: SystemPromptProfile
  isEditing: boolean
  onEdit: () => void
  onCancel: () => void
}) {
  const [draft, setDraft] = useState(profile.content)
  const updatePrompt = useUpdateSystemPrompt()
  const resetPrompt = useResetSystemPrompt()

  const handleSave = () => {
    updatePrompt.mutate(
      { purpose: profile.purpose, content: draft },
      {
        onSuccess: () => {
          toast.success(`Saved ${profile.display_name}`)
          onCancel()
        },
        onError: (err) =>
          toast.error(`Failed to save: ${(err as Error).message}`),
      },
    )
  }

  const handleReset = () => {
    resetPrompt.mutate(profile.purpose, {
      onSuccess: () => {
        toast.success(`Reset ${profile.display_name} to default`)
        onCancel()
      },
      onError: (err) =>
        toast.error(`Failed to reset: ${(err as Error).message}`),
    })
  }

  if (!isEditing) {
    return (
      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <CardTitle className="text-sm">{profile.display_name}</CardTitle>
              <Badge variant="secondary">{profile.purpose}</Badge>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={onEdit}
            >
              Edit
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <pre className="text-muted-foreground bg-muted/50 max-h-40 overflow-y-auto rounded p-3 font-mono text-xs whitespace-pre-wrap">
            {profile.content}
          </pre>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card className="border-primary border-2">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <CardTitle className="text-sm">{profile.display_name}</CardTitle>
            <Badge variant="secondary">{profile.purpose}</Badge>
          </div>
          <div className="flex gap-2">
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive h-6 px-2 text-xs"
              onClick={handleReset}
              disabled={resetPrompt.isPending}
            >
              {resetPrompt.isPending ? "Resetting..." : "Reset to Default"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="h-6 px-2 text-xs"
              onClick={onCancel}
            >
              Cancel
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-primary h-6 px-2 text-xs"
              onClick={handleSave}
              disabled={updatePrompt.isPending}
            >
              {updatePrompt.isPending ? "Saving..." : "Save"}
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <Textarea
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          rows={10}
          className="resize-none font-mono text-sm"
        />
      </CardContent>
    </Card>
  )
}

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

function SettingsPage() {
  const { data: prompts, isLoading, error } = useSystemPrompts()
  const [editingPurpose, setEditingPurpose] = useState<string | null>(null)

  const editable = prompts?.filter((p) => p.is_editable)

  return (
    <div className="p-6">
      <PageHeader
        title="Settings"
        description="Configure system prompts and workers."
      />

      <div className="mb-8">
        <h3 className="mb-2 text-base font-semibold">System Prompts</h3>
        <p className="text-muted-foreground mb-4 text-sm">
          Edit system prompts used by the pipeline. Changes take effect on the
          next memory operation.
        </p>
        {isLoading && <p className="text-muted-foreground">Loading...</p>}
        {error && (
          <div className="bg-destructive/10 border-destructive/30 mb-4 rounded-lg border p-4">
            <p className="text-destructive text-sm">Failed to load prompts.</p>
            <p className="text-muted-foreground mt-1 text-xs">
              {(error as Error).message}
            </p>
          </div>
        )}
        <div className="grid grid-cols-1 gap-4">
          {editable?.map((p) => (
            <PromptCard
              key={p.purpose}
              profile={p}
              isEditing={editingPurpose === p.purpose}
              onEdit={() => setEditingPurpose(p.purpose)}
              onCancel={() => setEditingPurpose(null)}
            />
          ))}
        </div>
      </div>

      <div>
        <h3 className="mb-4 text-base font-semibold">Workers</h3>
        <div className="grid grid-cols-1 gap-4">
          <EnrichmentCard />
        </div>
      </div>
    </div>
  )
}
