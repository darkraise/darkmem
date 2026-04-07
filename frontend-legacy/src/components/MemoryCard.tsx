import type { Memory } from "@/hooks/useApi";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

export function MemoryCard({ memory, onDelete }: { memory: Memory; onDelete?: (id: string) => void }) {
  return (
    <Card>
      <CardContent className="pt-4">
        <p className="text-sm text-foreground">{memory.content}</p>
        <div className="flex items-center gap-2 mt-3 flex-wrap">
          {memory.tags.map((tag) => (
            <Badge key={tag} variant="secondary">{tag}</Badge>
          ))}
        </div>
        <div className="flex items-center justify-between mt-3 text-xs text-muted-foreground">
          <div className="flex items-center gap-3">
            <span>{memory.source}</span>
            {memory.memory_type && <span>{memory.memory_type}</span>}
            <span>{new Date(memory.created_at).toLocaleString()}</span>
          </div>
          {onDelete && (
            <Button
              variant="ghost"
              size="sm"
              className="text-destructive hover:text-destructive h-6 px-2 text-xs"
              onClick={() => { if (window.confirm("Delete this memory?")) onDelete(memory.id); }}
            >
              delete
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
