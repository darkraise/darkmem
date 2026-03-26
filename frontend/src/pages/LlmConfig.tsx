import { useState, useEffect } from "react";
import { useLlmConfig, useUpdateLlmConfig } from "@/hooks/useApi";

interface PurposeConfig {
  provider: string;
  base_url: string;
  model: string;
  api_key: string | null;
  dimensions: number | null;
  params: Record<string, unknown>;
}

function PurposeCard({
  title,
  config,
  onSave,
  saving,
}: {
  title: string;
  config: PurposeConfig | undefined;
  onSave: (purpose: string, data: Partial<PurposeConfig>) => void;
  saving: boolean;
}) {
  const [editing, setEditing] = useState(false);
  const [form, setForm] = useState({
    provider: "",
    base_url: "",
    model: "",
    api_key: "",
    dimensions: "",
    params: "",
  });

  useEffect(() => {
    if (config) {
      setForm({
        provider: config.provider || "",
        base_url: config.base_url || "",
        model: config.model || "",
        api_key: config.api_key === "***" ? "***" : config.api_key || "",
        dimensions: config.dimensions?.toString() || "",
        params: Object.keys(config.params || {}).length > 0 ? JSON.stringify(config.params, null, 2) : "",
      });
    }
  }, [config]);

  if (!config) return null;

  const handleSave = () => {
    const data: Record<string, unknown> = {
      provider: form.provider,
      base_url: form.base_url,
      model: form.model,
    };
    if (form.api_key && form.api_key !== "***") {
      data.api_key = form.api_key;
    }
    if (form.dimensions) {
      data.dimensions = parseInt(form.dimensions, 10);
    }
    if (form.params.trim()) {
      try {
        data.params = JSON.parse(form.params);
      } catch {
        alert("Invalid JSON in params");
        return;
      }
    } else {
      data.params = {};
    }
    onSave(title.toLowerCase(), data);
    setEditing(false);
  };

  if (!editing) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-medium capitalize">{title}</h3>
          <button
            onClick={() => setEditing(true)}
            className="text-xs text-primary hover:underline"
          >
            Edit
          </button>
        </div>
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
      </div>
    );
  }

  return (
    <div className="bg-card border-2 border-primary rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium capitalize">{title}</h3>
        <div className="flex gap-2">
          <button onClick={() => setEditing(false)} className="text-xs text-muted-foreground hover:underline">Cancel</button>
          <button onClick={handleSave} disabled={saving} className="text-xs text-primary hover:underline">
            {saving ? "Saving..." : "Save"}
          </button>
        </div>
      </div>
      <div className="space-y-3 text-sm">
        <div>
          <label className="text-xs text-muted-foreground">Provider</label>
          <input value={form.provider} onChange={(e) => setForm({ ...form, provider: e.target.value })}
            className="w-full bg-background border border-border rounded px-2 py-1.5 text-sm mt-1" />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">Base URL</label>
          <input value={form.base_url} onChange={(e) => setForm({ ...form, base_url: e.target.value })}
            className="w-full bg-background border border-border rounded px-2 py-1.5 text-sm font-mono mt-1" />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">Model</label>
          <input value={form.model} onChange={(e) => setForm({ ...form, model: e.target.value })}
            className="w-full bg-background border border-border rounded px-2 py-1.5 text-sm font-mono mt-1" />
        </div>
        <div>
          <label className="text-xs text-muted-foreground">API Key</label>
          <input value={form.api_key} onChange={(e) => setForm({ ...form, api_key: e.target.value })}
            type="password"
            className="w-full bg-background border border-border rounded px-2 py-1.5 text-sm font-mono mt-1"
            placeholder="Leave as *** to keep existing" />
        </div>
        {title.toLowerCase() === "embedding" && (
          <div>
            <label className="text-xs text-muted-foreground">Dimensions</label>
            <input value={form.dimensions} onChange={(e) => setForm({ ...form, dimensions: e.target.value })}
              type="number"
              className="w-full bg-background border border-border rounded px-2 py-1.5 text-sm mt-1" />
          </div>
        )}
        <div>
          <label className="text-xs text-muted-foreground">Params (JSON)</label>
          <textarea value={form.params} onChange={(e) => setForm({ ...form, params: e.target.value })}
            rows={3}
            className="w-full bg-background border border-border rounded px-2 py-1.5 text-sm font-mono mt-1 resize-none"
            placeholder='{"temperature": 0.2}' />
        </div>
      </div>
    </div>
  );
}

export default function LlmConfig() {
  const { data, isLoading, error } = useLlmConfig();
  const updateConfig = useUpdateLlmConfig();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const cfg = data as any;

  const handleSave = (purpose: string, purposeData: Partial<PurposeConfig>) => {
    updateConfig.mutate({ [purpose]: purposeData });
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">LLM Configuration</h2>
      {isLoading && <p className="text-muted-foreground">Loading...</p>}
      {error && (
        <div className="bg-destructive/10 border border-destructive/30 rounded-lg p-4 mb-4">
          <p className="text-destructive text-sm">Failed to load config. Make sure your API key has admin scope.</p>
          <p className="text-xs text-muted-foreground mt-1">{(error as Error).message}</p>
        </div>
      )}
      <p className="text-sm text-muted-foreground mb-4">
        Configure LLM providers for each purpose. Changes are saved to the database and take effect on next memory operation.
      </p>
      <div className="grid grid-cols-2 gap-4">
        <PurposeCard title="Embedding" config={cfg?.embedding} onSave={handleSave} saving={updateConfig.isPending} />
        <PurposeCard title="Extraction" config={cfg?.extraction} onSave={handleSave} saving={updateConfig.isPending} />
        <PurposeCard title="Reasoning" config={cfg?.reasoning} onSave={handleSave} saving={updateConfig.isPending} />
        <PurposeCard title="Summarization" config={cfg?.summarization} onSave={handleSave} saving={updateConfig.isPending} />
      </div>
    </div>
  );
}
