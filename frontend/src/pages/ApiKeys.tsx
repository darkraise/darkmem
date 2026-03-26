import { useState } from "react";
import { useApiKeys, useCreateApiKey, useDeleteApiKey } from "@/hooks/useApi";
import { setApiKey } from "@/lib/api";

export default function ApiKeys() {
  const { data: keys, isLoading } = useApiKeys();
  const createKey = useCreateApiKey();
  const deleteKey = useDeleteApiKey();
  const [name, setName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);

  const handleCreate = () => {
    if (!name.trim()) return;
    createKey.mutate({ name, scopes: ["read", "write", "admin"] }, {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      onSuccess: (data: any) => {
        setNewKey(data.raw_key);
        setName("");
      },
    });
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">API Keys</h2>
      <div className="bg-card border border-border rounded-lg p-4 mb-4">
        <h3 className="text-sm font-medium mb-3">Create New Key</h3>
        <div className="flex gap-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Key name"
            className="flex-1 bg-background border border-border rounded px-3 py-2 text-sm" />
          <button onClick={handleCreate} className="px-4 py-2 bg-primary text-primary-foreground rounded text-sm">Create</button>
        </div>
        {newKey && (
          <div className="mt-3 p-3 bg-accent rounded border border-border">
            <p className="text-xs text-muted-foreground mb-1">Copy this key — it won't be shown again:</p>
            <code className="text-sm text-primary font-mono break-all">{newKey}</code>
            <button onClick={() => { setApiKey(newKey); setNewKey(null); }}
              className="block mt-2 text-xs text-primary hover:underline">Use as current key</button>
          </div>
        )}
      </div>
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-border text-muted-foreground">
            <th className="text-left p-3">Name</th><th className="text-left p-3">Scopes</th>
            <th className="text-left p-3">Created</th><th className="text-left p-3">Last Used</th><th className="p-3" />
          </tr></thead>
          <tbody>
            {/* eslint-disable-next-line @typescript-eslint/no-explicit-any */}
            {keys?.map((k: any) => (
              <tr key={k.id} className="border-b border-border">
                <td className="p-3">{k.name}</td>
                <td className="p-3">{k.scopes?.join(", ")}</td>
                <td className="p-3 text-muted-foreground">{new Date(k.created_at).toLocaleDateString()}</td>
                <td className="p-3 text-muted-foreground">{k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "—"}</td>
                <td className="p-3"><button onClick={() => deleteKey.mutate(k.id)} className="text-destructive text-xs hover:underline">Delete</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        {isLoading && <p className="p-3 text-muted-foreground">Loading...</p>}
        {!isLoading && !keys?.length && <p className="p-3 text-muted-foreground">No API keys.</p>}
      </div>
    </div>
  );
}
