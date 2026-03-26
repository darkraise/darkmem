import { useState } from "react";
import { useSystemPrompts } from "@/hooks/useApi";
import { getApiKey, setApiKey } from "@/lib/api";

export default function Settings() {
  const { data: prompts } = useSystemPrompts();
  const [key, setKey] = useState(getApiKey() ?? "");
  const [saved, setSaved] = useState(false);

  const handleSaveKey = () => {
    setApiKey(key);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Settings</h2>
      <div className="bg-card border border-border rounded-lg p-4 mb-6">
        <h3 className="text-sm font-medium mb-3">API Key</h3>
        <div className="flex gap-2">
          <input value={key} onChange={(e) => setKey(e.target.value)} placeholder="dm_..."
            className="flex-1 bg-background border border-border rounded px-3 py-2 text-sm font-mono" type="password" />
          <button onClick={handleSaveKey} className="px-4 py-2 bg-primary text-primary-foreground rounded text-sm">
            {saved ? "Saved!" : "Save"}
          </button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">Set the API key used for dashboard requests.</p>
      </div>
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-sm font-medium mb-3">System Prompt Profiles</h3>
        <div className="space-y-3">
          {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
          {prompts?.map((p: any) => (
            <div key={p.name} className="border border-border rounded p-3">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{p.display_name}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-accent text-muted-foreground">{p.name}</span>
                {p.is_default && <span className="text-xs text-primary">default</span>}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Extraction: {p.extraction_depth}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
