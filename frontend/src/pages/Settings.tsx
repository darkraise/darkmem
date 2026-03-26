import { useSystemPrompts } from "@/hooks/useApi";

export default function Settings() {
  const { data: prompts } = useSystemPrompts();

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Settings</h2>
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
