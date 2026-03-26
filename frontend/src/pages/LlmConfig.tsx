import { useLlmConfig } from "@/hooks/useApi";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function PurposeCard({ title, config }: { title: string; config: any }) {
  if (!config) return null;
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="text-sm font-medium mb-3 capitalize">{title}</h3>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between"><span className="text-muted-foreground">Provider</span><span>{config.provider}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">Model</span><span className="font-mono">{config.model}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">Base URL</span><span className="font-mono text-xs">{config.base_url}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">API Key</span><span>{config.api_key ?? "none"}</span></div>
        {config.dimensions && <div className="flex justify-between"><span className="text-muted-foreground">Dimensions</span><span>{config.dimensions}</span></div>}
        {Object.keys(config.params || {}).length > 0 && (
          <div><span className="text-muted-foreground">Params</span><pre className="mt-1 text-xs bg-background p-2 rounded">{JSON.stringify(config.params, null, 2)}</pre></div>
        )}
      </div>
    </div>
  );
}

export default function LlmConfig() {
  const { data, isLoading } = useLlmConfig();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const cfg = data as any;

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">LLM Configuration</h2>
      {isLoading && <p className="text-muted-foreground">Loading...</p>}
      <div className="grid grid-cols-2 gap-4">
        <PurposeCard title="Embedding" config={cfg?.embedding} />
        <PurposeCard title="Extraction" config={cfg?.extraction} />
        <PurposeCard title="Reasoning" config={cfg?.reasoning} />
        <PurposeCard title="Summarization" config={cfg?.summarization} />
      </div>
    </div>
  );
}
