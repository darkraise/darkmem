import { useState } from "react";
import { useMemories, useDeleteMemory, useCreateMemory } from "@/hooks/useApi";
import { MemoryCard } from "@/components/MemoryCard";

export default function Memories() {
  const { data: memories, isLoading } = useMemories();
  const deleteMemory = useDeleteMemory();
  const createMemory = useCreateMemory();
  const [showCreate, setShowCreate] = useState(false);
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");

  const handleCreate = () => {
    if (!content.trim()) return;
    createMemory.mutate(
      { content, tags: tags.split(",").map((t) => t.trim()).filter(Boolean), source: "dashboard" },
      { onSuccess: () => { setContent(""); setTags(""); setShowCreate(false); } }
    );
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Memories</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm hover:opacity-90"
        >
          {showCreate ? "Cancel" : "New Memory"}
        </button>
      </div>
      {showCreate && (
        <div className="bg-card border border-border rounded-lg p-4 mb-4 space-y-3">
          <textarea
            value={content} onChange={(e) => setContent(e.target.value)}
            placeholder="Memory content..." rows={3}
            className="w-full bg-background border border-border rounded p-2 text-sm text-foreground resize-none"
          />
          <input
            value={tags} onChange={(e) => setTags(e.target.value)}
            placeholder="Tags (comma-separated)"
            className="w-full bg-background border border-border rounded p-2 text-sm text-foreground"
          />
          <button onClick={handleCreate} className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm">Save</button>
        </div>
      )}
      {isLoading && <p className="text-muted-foreground">Loading...</p>}
      <div className="space-y-3">
        {memories?.map((m) => (
          <MemoryCard key={m.id} memory={m} onDelete={(id) => deleteMemory.mutate(id)} />
        ))}
      </div>
    </div>
  );
}
