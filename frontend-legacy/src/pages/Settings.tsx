import { useState, useEffect } from "react";
import {
  useSystemPrompts,
  useUpdateSystemPrompt,
  useResetSystemPrompt,
  useEnrichmentConfig,
  useUpdateEnrichmentConfig,
  useTriggerEnrichment,
  type SystemPromptProfile,
} from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { toast } from "sonner";

function PromptCard({
  profile,
  isEditing,
  onEdit,
  onCancel,
}: {
  profile: SystemPromptProfile;
  isEditing: boolean;
  onEdit: () => void;
  onCancel: () => void;
}) {
  const [draft, setDraft] = useState(profile.content);
  const updatePrompt = useUpdateSystemPrompt();
  const resetPrompt = useResetSystemPrompt();

  const handleSave = () => {
    updatePrompt.mutate(
      { purpose: profile.purpose, content: draft },
      {
        onSuccess: () => {
          toast.success(`Saved ${profile.display_name}`);
          onCancel();
        },
        onError: (err) =>
          toast.error(`Failed to save: ${(err as Error).message}`),
      },
    );
  };

  const handleReset = () => {
    resetPrompt.mutate(profile.purpose, {
      onSuccess: () => {
        toast.success(`Reset ${profile.display_name} to default`);
        onCancel();
      },
      onError: (err) =>
        toast.error(`Failed to reset: ${(err as Error).message}`),
    });
  };

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
              className="text-xs h-6 px-2"
              onClick={onEdit}
            >
              Edit
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <pre className="text-xs text-muted-foreground whitespace-pre-wrap font-mono bg-muted/50 rounded p-3 max-h-40 overflow-y-auto">
            {profile.content}
          </pre>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="border-2 border-primary">
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
              className="text-xs h-6 px-2 text-destructive"
              onClick={handleReset}
              disabled={resetPrompt.isPending}
            >
              {resetPrompt.isPending ? "Resetting..." : "Reset to Default"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs h-6 px-2"
              onClick={onCancel}
            >
              Cancel
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-xs h-6 px-2 text-primary"
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
          className="text-sm font-mono resize-none"
        />
      </CardContent>
    </Card>
  );
}

function EnrichmentCard() {
  const { data: config } = useEnrichmentConfig();
  const updateConfig = useUpdateEnrichmentConfig();
  const trigger = useTriggerEnrichment();

  const [enabled, setEnabled] = useState(false);
  const [batchSize, setBatchSize] = useState(5);
  const [interval, setInterval] = useState(10);

  useEffect(() => {
    if (config) {
      setEnabled(config.enabled);
      setBatchSize(config.batch_size);
      setInterval(config.interval_seconds);
    }
  }, [config]);

  const handleSave = () => {
    updateConfig.mutate(
      { enabled, batch_size: batchSize, interval_seconds: interval },
      {
        onSuccess: () => toast.success("Enrichment config saved"),
        onError: (err) =>
          toast.error(`Failed to save: ${(err as Error).message}`),
      },
    );
  };

  const handleTrigger = () => {
    trigger.mutate(undefined, {
      onSuccess: (data) => {
        if (data.processed > 0) {
          toast.success(`Enriched ${data.processed} symbols`);
        } else {
          toast.info("No pending symbols");
        }
      },
      onError: () => toast.error("Enrichment failed"),
    });
  };

  return (
    <Card>
      <CardHeader className="pb-2">
        <CardTitle className="text-sm">Enrichment Worker</CardTitle>
        <p className="text-xs text-muted-foreground">
          LLM-powered code symbol summarization
        </p>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex items-center justify-between">
          <label className="text-sm">Enabled</label>
          <Switch checked={enabled} onCheckedChange={setEnabled} />
        </div>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs text-muted-foreground">Batch Size</label>
            <Input
              type="number"
              min={1}
              value={batchSize}
              onChange={(e) => setBatchSize(Number(e.target.value))}
            />
          </div>
          <div>
            <label className="text-xs text-muted-foreground">
              Interval (seconds)
            </label>
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
  );
}

export default function Settings() {
  const { data: prompts, isLoading, error } = useSystemPrompts();
  const [editingPurpose, setEditingPurpose] = useState<string | null>(null);

  const editable = prompts?.filter((p) => p.is_editable);

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-4">Settings</h2>
      {isLoading && <p className="text-muted-foreground">Loading...</p>}
      {error && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 mb-4">
          <p className="text-destructive text-sm">Failed to load prompts.</p>
          <p className="text-xs text-muted-foreground mt-1">
            {(error as Error).message}
          </p>
        </div>
      )}
      <p className="text-sm text-muted-foreground mb-4">
        Edit system prompts used by the pipeline. Changes take effect on the
        next memory operation.
      </p>
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

      <h3 className="text-lg font-semibold mt-8 mb-4">Workers</h3>
      <div className="grid grid-cols-1 gap-4">
        <EnrichmentCard />
      </div>
    </div>
  );
}
