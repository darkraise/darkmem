import { useState } from "react";
import { useSearchMemories, useReason } from "@/hooks/useApi";
import { MemoryCard } from "@/components/MemoryCard";

export default function Search() {
  const [query, setQuery] = useState("");
  const search = useSearchMemories();
  const reason = useReason();
  const [mode, setMode] = useState<"search" | "reason">("search");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    if (mode === "search") {
      search.mutate({ query, limit: 20 });
    } else {
      reason.mutate({ question: query, limit: 10 });
    }
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Search</h2>
      <form onSubmit={handleSubmit} className="flex gap-2 mb-4">
        <input
          value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder={mode === "search" ? "Search memories..." : "Ask a question..."}
          className="flex-1 bg-background border border-border rounded px-3 py-2 text-sm text-foreground"
        />
        <select value={mode} onChange={(e) => setMode(e.target.value as "search" | "reason")}
          className="bg-background border border-border rounded px-3 py-2 text-sm text-foreground">
          <option value="search">Search</option>
          <option value="reason">Reason</option>
        </select>
        <button type="submit" className="px-4 py-2 bg-primary text-primary-foreground rounded text-sm">Go</button>
      </form>
      {mode === "reason" && reason.data && (
        <div className="bg-card border border-border rounded-lg p-4 mb-4">
          <h3 className="text-sm font-medium mb-2">Answer</h3>
          <p className="text-sm text-foreground whitespace-pre-wrap">{reason.data.answer}</p>
          {reason.data.sources.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border">
              <span className="text-xs text-muted-foreground">{reason.data.sources.length} sources used</span>
            </div>
          )}
        </div>
      )}
      <div className="space-y-3">
        {search.data?.map((m) => <MemoryCard key={m.id} memory={m} />)}
      </div>
    </div>
  );
}
