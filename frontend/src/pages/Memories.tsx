import { useState, useMemo } from "react";
import { usePaginatedSearch, useDeleteMemory, useTags } from "@/hooks/useApi";
import type { Memory } from "@/hooks/useApi";
import { apiFetch } from "@/lib/api";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet";
import { X } from "lucide-react";
import { useQueryClient } from "@tanstack/react-query";

const PAGE_SIZE = 50;

const SOURCE_COLORS: Record<string, string> = {
  "claude-code": "#58a6ff",
  "mcp-test": "#3fb950",
  api: "#d2a8ff",
  "rest-test": "#ffa657",
  dashboard: "#f778ba",
};

function relativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function Memories() {
  const [searchInput, setSearchInput] = useState("");
  const [query, setQuery] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [tagFilter, setTagFilter] = useState("");
  const [typeFilter, setTypeFilter] = useState("");
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [detailMemory, setDetailMemory] = useState<Memory | null>(null);

  const { data, isLoading } = usePaginatedSearch({
    query: query || undefined,
    tags_any: tagFilter ? [tagFilter] : undefined,
    source: sourceFilter || undefined,
    memory_type: typeFilter || undefined,
    limit: PAGE_SIZE,
    offset,
  });
  const { data: tagsData } = useTags();
  const deleteMemory = useDeleteMemory();
  const qc = useQueryClient();

  const memories = data?.items ?? [];
  const total = data?.total ?? 0;
  const pageStart = offset + 1;
  const pageEnd = Math.min(offset + PAGE_SIZE, total);

  const distinctSources = useMemo(() => {
    const set = new Set(memories.map((m) => m.source));
    return Array.from(set).sort();
  }, [memories]);

  const distinctTypes = useMemo(() => {
    const set = new Set(memories.map((m) => m.memory_type).filter(Boolean) as string[]);
    return Array.from(set).sort();
  }, [memories]);

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setQuery(searchInput);
    setOffset(0);
    setSelected(new Set());
  };

  const handleFilterChange = (setter: (v: string) => void) => (e: React.ChangeEvent<HTMLSelectElement>) => {
    setter(e.target.value);
    setOffset(0);
    setSelected(new Set());
  };

  const toggleSelect = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleSelectAll = () => {
    if (selected.size === memories.length) {
      setSelected(new Set());
    } else {
      setSelected(new Set(memories.map((m) => m.id)));
    }
  };

  const handleDelete = (id: string) => {
    if (!window.confirm("Delete this memory?")) return;
    deleteMemory.mutate(id, {
      onSuccess: () => {
        setSelected((prev) => { const next = new Set(prev); next.delete(id); return next; });
        if (detailMemory?.id === id) setDetailMemory(null);
        qc.invalidateQueries({ queryKey: ["memoriesPaginated"] });
      },
    });
  };

  const handleBulkDelete = () => {
    if (!window.confirm(`Delete ${selected.size} memories?`)) return;
    const ids = Array.from(selected);
    Promise.all(ids.map((id) => deleteMemory.mutateAsync(id))).then(() => {
      setSelected(new Set());
      setDetailMemory(null);
      qc.invalidateQueries({ queryKey: ["memoriesPaginated"] });
    });
  };

  const handleBulkArchive = () => {
    if (!window.confirm(`Archive ${selected.size} memories?`)) return;
    const ids = Array.from(selected);
    Promise.all(ids.map((id) => apiFetch(`/memories/${id}`, { method: "PUT", body: JSON.stringify({ is_archived: true }) }))).then(() => {
      setSelected(new Set());
      setDetailMemory(null);
      qc.invalidateQueries({ queryKey: ["memoriesPaginated"] });
    });
  };

  return (
    <div className="p-6 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Memories</h2>
        {total > 0 && (
          <span className="text-sm text-muted-foreground">{total} memories</span>
        )}
      </div>

      {/* Search + filters */}
      <form onSubmit={handleSearch} className="flex flex-col lg:flex-row gap-2 mb-4">
        <Input
          value={searchInput}
          onChange={(e) => setSearchInput(e.target.value)}
          placeholder="Search memories..."
          className="flex-1"
        />
        <div className="flex gap-2 flex-wrap">
          <select
            value={sourceFilter}
            onChange={handleFilterChange(setSourceFilter)}
            className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm text-foreground outline-none dark:bg-input/30"
          >
            <option value="">All sources</option>
            {distinctSources.map((s) => <option key={s} value={s}>{s}</option>)}
          </select>
          <select
            value={tagFilter}
            onChange={handleFilterChange(setTagFilter)}
            className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm text-foreground outline-none dark:bg-input/30"
          >
            <option value="">All tags</option>
            {tagsData?.map((t) => <option key={t.name} value={t.name}>{t.name}</option>)}
          </select>
          <select
            value={typeFilter}
            onChange={handleFilterChange(setTypeFilter)}
            className="h-8 rounded-lg border border-input bg-transparent px-2 text-sm text-foreground outline-none dark:bg-input/30"
          >
            <option value="">All types</option>
            {distinctTypes.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <Button type="submit" size="sm">Search</Button>
        </div>
      </form>

      {/* Loading */}
      {isLoading && <p className="text-muted-foreground">Loading...</p>}

      {/* Empty state */}
      {!isLoading && memories.length === 0 && (
        <p className="text-muted-foreground">
          {query || sourceFilter || tagFilter || typeFilter
            ? "No memories match your filters."
            : "No memories yet. Create one via the API or Claude Code to get started."}
        </p>
      )}

      {/* Memory list */}
      {memories.length > 0 && (
        <Card className="flex-1 overflow-hidden">
          <CardContent className="p-0">
            {/* Select all header */}
            <div className="flex items-center gap-3 px-4 py-2 border-b border-border text-xs text-muted-foreground">
              <input
                type="checkbox"
                checked={selected.size === memories.length && memories.length > 0}
                onChange={toggleSelectAll}
                className="accent-primary"
              />
              <span>Select all</span>
            </div>

            {/* Rows */}
            <div className="divide-y divide-border">
              {memories.map((m) => (
                <div
                  key={m.id}
                  className={`flex items-start gap-3 px-4 py-3 cursor-pointer transition-colors hover:bg-accent/30 ${selected.has(m.id) ? "bg-accent/20" : ""}`}
                  onClick={() => setDetailMemory(m)}
                >
                  <input
                    type="checkbox"
                    checked={selected.has(m.id)}
                    onChange={(e) => { e.stopPropagation(); toggleSelect(m.id); }}
                    onClick={(e) => e.stopPropagation()}
                    className="accent-primary mt-1"
                  />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm truncate flex-1">{m.content}</span>
                      <button
                        className="text-muted-foreground hover:text-destructive shrink-0"
                        onClick={(e) => { e.stopPropagation(); handleDelete(m.id); }}
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    </div>
                    <div className="flex items-center gap-1.5 mt-1 text-xs text-muted-foreground flex-wrap">
                      {m.tags.map((tag) => (
                        <Badge key={tag} variant="secondary" className="text-[10px] px-1.5 py-0">{tag}</Badge>
                      ))}
                      <span className="ml-auto flex items-center gap-1.5 shrink-0">
                        <span style={{ color: SOURCE_COLORS[m.source] ?? "#8b949e" }}>{m.source}</span>
                        {m.memory_type && <><span>·</span><span>{m.memory_type}</span></>}
                        <span>·</span>
                        <span>{relativeTime(m.created_at)}</span>
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Pagination */}
      {total > PAGE_SIZE && (
        <div className="flex items-center justify-between mt-3 text-sm text-muted-foreground">
          <span>Showing {pageStart}–{pageEnd} of {total}</span>
          <div className="flex gap-2">
            <Button variant="outline" size="sm" disabled={offset === 0} onClick={() => { setOffset(Math.max(0, offset - PAGE_SIZE)); setSelected(new Set()); }}>
              Previous
            </Button>
            <Button variant="outline" size="sm" disabled={offset + PAGE_SIZE >= total} onClick={() => { setOffset(offset + PAGE_SIZE); setSelected(new Set()); }}>
              Next
            </Button>
          </div>
        </div>
      )}

      {/* Bulk action bar */}
      {selected.size > 0 && (
        <div className="flex items-center gap-4 mt-3 p-3 bg-card border border-border rounded-lg text-sm">
          <span className="text-primary font-medium">{selected.size} selected</span>
          <Button variant="destructive" size="sm" onClick={handleBulkDelete}>Delete</Button>
          <Button variant="outline" size="sm" onClick={handleBulkArchive}>Archive</Button>
        </div>
      )}

      {/* Detail side panel */}
      <Sheet open={!!detailMemory} onOpenChange={(open) => { if (!open) setDetailMemory(null); }}>
        <SheetContent side="right" className="w-full sm:max-w-md overflow-y-auto">
          <SheetHeader>
            <SheetTitle className="text-base">Memory Details</SheetTitle>
          </SheetHeader>
          {detailMemory && (
            <div className="space-y-4 mt-4">
              <div>
                <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-1">Content</div>
                <p className="text-sm whitespace-pre-wrap">{detailMemory.content}</p>
              </div>
              {detailMemory.tags.length > 0 && (
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-1">Tags</div>
                  <div className="flex gap-1.5 flex-wrap">
                    {detailMemory.tags.map((tag) => <Badge key={tag} variant="secondary">{tag}</Badge>)}
                  </div>
                </div>
              )}
              <div className="grid grid-cols-2 gap-3 text-sm">
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">Source</div>
                  <span style={{ color: SOURCE_COLORS[detailMemory.source] ?? "#c9d1d9" }}>{detailMemory.source}</span>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">Type</div>
                  <span>{detailMemory.memory_type ?? "—"}</span>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">Importance</div>
                  <span>{detailMemory.importance}</span>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">Created</div>
                  <span>{new Date(detailMemory.created_at).toLocaleString()}</span>
                </div>
                <div>
                  <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-0.5">Updated</div>
                  <span>{new Date(detailMemory.updated_at).toLocaleString()}</span>
                </div>
              </div>
              <div className="pt-3 border-t border-border">
                <Button variant="destructive" size="sm" onClick={() => handleDelete(detailMemory.id)}>
                  Delete Memory
                </Button>
              </div>
            </div>
          )}
        </SheetContent>
      </Sheet>
    </div>
  );
}
