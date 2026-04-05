import { useState, useMemo, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { CodeGraphRenderer } from "@/components/graph/CodeGraphRenderer";
import {
  useRepos,
  useCodeGraph,
  useCodeSearch,
  useCodeSymbolDetail,
  useBlastRadius,
  type CodeSearchResult,
} from "@/hooks/api";
import { ZoomIn, ZoomOut } from "lucide-react";

const EDGE_COLORS_FOR_UI: Record<string, string> = {
  calls: "#7c3aed",
  imports: "#1d4ed8",
  contains: "#2d5a3d",
  defines: "#0e7490",
};

export default function CodeGraph() {
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);
  const [viewMode, setViewMode] = useState<"files" | "symbols">("symbols");
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [selectedNode, setSelectedNode] = useState<{
    id: string;
    label: string;
    kind?: string;
    file_path?: string;
  } | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [blastRadiusIds, setBlastRadiusIds] = useState<Set<string> | undefined>(
    undefined,
  );
  const [searchResults, setSearchResults] = useState<CodeSearchResult[]>([]);
  const [showSearchResults, setShowSearchResults] = useState(false);
  const [visibleEdgeTypes, setVisibleEdgeTypes] = useState<Set<string>>(
    new Set(["calls", "contains", "defines", "imports"]),
  );

  const toggleEdgeType = useCallback((type: string) => {
    setVisibleEdgeTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }, []);

  const { data: repos } = useRepos();
  const { data: graphData, isLoading } = useCodeGraph(selectedRepoId, viewMode);
  const codeSearch = useCodeSearch();
  const blastRadius = useBlastRadius();
  const { data: symbolDetail } = useCodeSymbolDetail(
    viewMode === "symbols" && selectedNode ? selectedNode.id : null,
  );

  const nodes = useMemo(() => graphData?.nodes ?? [], [graphData]);
  const edges = useMemo(() => graphData?.edges ?? [], [graphData]);

  const handleSelect = useCallback(
    (
      node: {
        id: string;
        label: string;
        kind?: string;
        file_path?: string;
      } | null,
    ) => {
      setSelectedNode(node);
      setSelectedNodeId(node?.id ?? null);
    },
    [],
  );

  const handleSearch = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key !== "Enter" || !searchQuery.trim()) return;
      codeSearch.mutate(
        { query: searchQuery, repo_id: selectedRepoId ?? undefined },
        {
          onSuccess: (data) => {
            setSearchResults(data);
            setShowSearchResults(true);
          },
        },
      );
    },
    [searchQuery, selectedRepoId, codeSearch],
  );

  const handleSearchResultClick = useCallback(
    (result: CodeSearchResult) => {
      const matchNode = nodes.find(
        (n) =>
          n.label === result.symbol_name || n.label === result.file_path,
      );
      if (matchNode) {
        setSelectedNodeId(matchNode.id);
        handleSelect(matchNode);
      }
      setShowSearchResults(false);
    },
    [nodes, handleSelect],
  );

  const handleBlastRadius = useCallback(() => {
    if (!selectedNode) return;
    blastRadius.mutate(
      { symbol_id: selectedNode.id },
      {
        onSuccess: (data) => {
          const ids = new Set(data.affected.map((a) => a.name));
          setBlastRadiusIds(ids);
        },
      },
    );
  }, [selectedNode, blastRadius]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 p-4 border-b border-border flex-wrap">
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={selectedRepoId ?? ""}
          onChange={(e) =>
            setSelectedRepoId(e.target.value || null)
          }
        >
          <option value="">Select a repo</option>
          {repos?.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>

        <div className="flex gap-1">
          <Button
            size="sm"
            variant={viewMode === "files" ? "secondary" : "ghost"}
            onClick={() => setViewMode("files")}
          >
            Files
          </Button>
          <Button
            size="sm"
            variant={viewMode === "symbols" ? "secondary" : "ghost"}
            onClick={() => setViewMode("symbols")}
          >
            Symbols
          </Button>
        </div>

        {viewMode === "symbols" && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-muted-foreground">Edges:</span>
            {["calls", "contains", "defines", "imports"].map((type) => (
              <label key={type} className="flex items-center gap-1 cursor-pointer">
                <input
                  type="checkbox"
                  checked={visibleEdgeTypes.has(type)}
                  onChange={() => toggleEdgeType(type)}
                  className="accent-primary w-3 h-3"
                />
                <span style={{ color: EDGE_COLORS_FOR_UI[type] }}>{type}</span>
              </label>
            ))}
          </div>
        )}

        <div className="relative">
          <Input
            placeholder="Search code..."
            className="w-64 h-9"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyDown={handleSearch}
            onBlur={() => setTimeout(() => setShowSearchResults(false), 200)}
          />
          {showSearchResults && searchResults.length > 0 && (
            <div className="absolute top-full left-0 z-50 mt-1 w-96 max-h-80 overflow-y-auto rounded-md border border-border bg-popover shadow-lg">
              {searchResults.map((r, i) => (
                <button
                  key={i}
                  className="w-full text-left px-3 py-2 text-sm hover:bg-accent border-b border-border last:border-0"
                  onMouseDown={() => handleSearchResultClick(r)}
                >
                  <div className="font-medium truncate">
                    {r.file_path}
                  </div>
                  {r.symbol_name && (
                    <div className="text-xs text-muted-foreground">
                      {r.symbol_name}
                    </div>
                  )}
                  <div className="text-xs text-muted-foreground truncate mt-0.5">
                    {r.chunk_content.slice(0, 120)}
                  </div>
                  <div className="text-xs text-muted-foreground mt-0.5">
                    score: {r.score.toFixed(3)}
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>

        {blastRadiusIds && (
          <Button
            size="sm"
            variant="ghost"
            onClick={() => setBlastRadiusIds(undefined)}
          >
            Clear Blast Radius
          </Button>
        )}

        <div className="ml-auto flex items-center gap-2 text-sm text-muted-foreground">
          {nodes.length > 0 && (
            <span>
              {nodes.length} nodes, {edges.length} edges
            </span>
          )}
          <ZoomIn className="w-4 h-4" />
          <ZoomOut className="w-4 h-4" />
        </div>
      </div>

      <div className="relative flex-1">
        {!selectedRepoId && (
          <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
            Select a repository to visualize its code graph.
          </div>
        )}
        {selectedRepoId && isLoading && (
          <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
            Loading graph...
          </div>
        )}
        {selectedRepoId && !isLoading && nodes.length === 0 && (
          <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
            No graph data for this repository. Index it first from the
            Repositories page.
          </div>
        )}
        {nodes.length > 0 && (
          <CodeGraphRenderer
            nodes={nodes}
            edges={edges}
            selectedId={selectedNodeId}
            onSelect={handleSelect}
            highlightedIds={blastRadiusIds}
            visibleEdgeTypes={visibleEdgeTypes}
          />
        )}
      </div>

      <Sheet
        open={!!selectedNode}
        onOpenChange={(open) => {
          if (!open) handleSelect(null);
        }}
      >
        <SheetContent side="right" showOverlay={false}>
          <SheetHeader>
            <SheetTitle>{selectedNode?.label}</SheetTitle>
            <SheetDescription>
              {viewMode === "symbols"
                ? selectedNode?.kind ?? "symbol"
                : "file"}
            </SheetDescription>
          </SheetHeader>

          <div className="px-4 pb-4 overflow-y-auto flex-1 space-y-4">
            {viewMode === "symbols" && symbolDetail && (
              <>
                <div className="space-y-2">
                  <div className="flex gap-2 flex-wrap">
                    <Badge variant="secondary">{symbolDetail.kind}</Badge>
                    {symbolDetail.visibility && (
                      <Badge variant="outline">
                        {symbolDetail.visibility}
                      </Badge>
                    )}
                    <Badge variant="outline">
                      {symbolDetail.enrichment_status}
                    </Badge>
                  </div>

                  {symbolDetail.file_path && (
                    <p className="text-sm text-muted-foreground">
                      {symbolDetail.file_path}
                      {symbolDetail.line_start > 0 && (
                        <span>
                          :{symbolDetail.line_start}-{symbolDetail.line_end}
                        </span>
                      )}
                    </p>
                  )}

                  {symbolDetail.signature && (
                    <pre className="text-xs bg-muted p-3 rounded overflow-x-auto">
                      {symbolDetail.signature}
                    </pre>
                  )}

                  {symbolDetail.summary && (
                    <p className="text-sm">{symbolDetail.summary}</p>
                  )}

                  {symbolDetail.source_code && (
                    <div>
                      <p className="text-xs font-medium mb-1 text-muted-foreground">
                        Source
                      </p>
                      <pre className="text-xs bg-muted p-3 rounded overflow-x-auto max-h-80 overflow-y-auto">
                        {symbolDetail.source_code}
                      </pre>
                    </div>
                  )}
                </div>

                <Button
                  size="sm"
                  variant="secondary"
                  onClick={handleBlastRadius}
                  disabled={blastRadius.isPending}
                >
                  {blastRadius.isPending
                    ? "Analyzing..."
                    : "Blast Radius"}
                </Button>

                {blastRadiusIds && blastRadiusIds.size > 0 && (
                  <p className="text-sm text-muted-foreground">
                    {blastRadiusIds.size} affected symbol
                    {blastRadiusIds.size !== 1 ? "s" : ""} highlighted
                  </p>
                )}
              </>
            )}

            {viewMode === "symbols" && !symbolDetail && selectedNode && (
              <p className="text-sm text-muted-foreground">
                Loading symbol details...
              </p>
            )}

            {viewMode === "files" && selectedNode && (
              <div className="space-y-2">
                <p className="text-sm">
                  <span className="text-muted-foreground">Path: </span>
                  {selectedNode.file_path ?? selectedNode.label}
                </p>
              </div>
            )}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
