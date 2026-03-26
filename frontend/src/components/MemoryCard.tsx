import type { Memory } from "@/hooks/useApi";

export function MemoryCard({ memory, onDelete }: { memory: Memory; onDelete?: (id: string) => void }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <p className="text-sm text-foreground">{memory.content}</p>
      <div className="flex items-center gap-2 mt-3 flex-wrap">
        {memory.tags.map((tag) => (
          <span key={tag} className="text-xs px-2 py-0.5 rounded bg-accent text-primary">{tag}</span>
        ))}
      </div>
      <div className="flex items-center justify-between mt-3 text-xs text-muted-foreground">
        <div className="flex items-center gap-3">
          <span>{memory.source}</span>
          {memory.memory_type && <span>{memory.memory_type}</span>}
          <span>{new Date(memory.created_at).toLocaleString()}</span>
        </div>
        {onDelete && (
          <button onClick={() => onDelete(memory.id)} className="text-destructive hover:underline">delete</button>
        )}
      </div>
    </div>
  );
}
