import { useState } from "react";
import { useSearchMemories, useReason } from "@/hooks/useApi";
import { MemoryCard } from "@/components/MemoryCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";

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
    <div className="p-6">
      <h2 className="text-xl font-semibold mb-4">Search</h2>
      <form onSubmit={handleSubmit} className="flex gap-2 mb-4">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={mode === "search" ? "Search memories..." : "Ask a question..."}
          className="flex-1"
        />
        <Select value={mode} onValueChange={(v) => setMode(v as "search" | "reason")}>
          <SelectTrigger className="w-32">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="search">Search</SelectItem>
            <SelectItem value="reason">Reason</SelectItem>
          </SelectContent>
        </Select>
        <Button type="submit" disabled={search.isPending || reason.isPending}>
          {search.isPending || reason.isPending ? "Searching..." : "Go"}
        </Button>
      </form>
      {mode === "reason" && reason.data && (
        <Card className="mb-4">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">Answer</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-foreground whitespace-pre-wrap">{reason.data.answer}</p>
            {reason.data.sources.length > 0 && (
              <div className="mt-3 pt-3 border-t border-border">
                <span className="text-xs text-muted-foreground">{reason.data.sources.length} sources used</span>
              </div>
            )}
          </CardContent>
        </Card>
      )}
      <div className="space-y-3">
        {search.data?.map((m) => <MemoryCard key={m.id} memory={m} />)}
      </div>
    </div>
  );
}
