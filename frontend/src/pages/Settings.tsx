import { useState } from "react";
import {
  useSystemPrompts,
  useUpdateSystemPrompt,
  useResetSystemPrompt,
  type SystemPromptProfile,
} from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
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
    </div>
  );
}
