import { useState } from "react";
import { useMemories, useDeleteMemory, useCreateMemory } from "@/hooks/useApi";
import { MemoryCard } from "@/components/MemoryCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent } from "@/components/ui/card";

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
    <div className="p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Memories</h2>
        <Button
          variant={showCreate ? "outline" : "default"}
          size="sm"
          onClick={() => setShowCreate(!showCreate)}
        >
          {showCreate ? "Cancel" : "New Memory"}
        </Button>
      </div>
      {showCreate && (
        <Card className="mb-4">
          <CardContent className="pt-4 space-y-3">
            <Textarea
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="Memory content..."
              rows={3}
              className="resize-none"
            />
            <Input
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="Tags (comma-separated)"
            />
            <Button size="sm" onClick={handleCreate}>Save</Button>
          </CardContent>
        </Card>
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
