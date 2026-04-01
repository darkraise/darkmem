import { useSystemPrompts } from "@/hooks/useApi";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";

export default function Settings() {
  const { data: prompts } = useSystemPrompts();

  return (
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-4">Settings</h2>
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">System Prompt Profiles</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {prompts?.map((p) => (
              <div key={p.name} className="border border-border rounded p-3">
                <div className="flex items-center gap-2">
                  <span className="font-medium text-sm">{p.display_name}</span>
                  <Badge variant="secondary">{p.name}</Badge>
                  {p.is_default && <Badge variant="outline" className="text-primary border-primary">default</Badge>}
                </div>
                <p className="text-xs text-muted-foreground mt-1">Extraction: {p.extraction_depth}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
