import { createFileRoute } from "@tanstack/react-router";
import { useState, useMemo, useCallback, type ReactNode } from "react";
import { Button } from "darkraise-ui/components/button";
import { Input } from "darkraise-ui/components/input";
import { Badge } from "darkraise-ui/components/badge";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "darkraise-ui/components/sheet";
import { CodeGraphRenderer } from "@/features/graph/components/code-graph-renderer";
import {
  useRepos,
  useCodeGraph,
  useCodeSearch,
  useCodeSymbolDetail,
  useBlastRadius,
  type CodeSearchResult,
} from "@/hooks/api";
import { ZoomIn, ZoomOut } from "lucide-react";

export const Route = createFileRoute("/_authenticated/code-graph")({
  component: CodeGraphPage,
});

const NODE_COLORS_FOR_FILTER: Record<string, string> = {
  file: "#3b82f6", module: "#8b5cf6", class: "#f59e0b", struct: "#fb923c",
  interface: "#ec4899", trait: "#f472b6", enum: "#f97316", function: "#10b981",
  method: "#14b8a6", type: "#64748b", impl: "#7c3aed",
  property: "#64748b", route: "#f43f5e", tool: "#a855f7",
  community: "#818cf8", process: "#f43f5e",
};

const EDGE_COLORS_FOR_FILTER: Record<string, string> = {
  calls: "#7c3aed", imports: "#1d4ed8", contains: "#2d5a3d", defines: "#0e7490",
  extends: "#c2410c", implements: "#be185d", has_method: "#0e7490",
  has_property: "#64748b", handles_route: "#f43f5e", handles_tool: "#a855f7",
  method_overrides: "#c2410c", method_implements: "#be185d", accesses: "#64748b",
  member_of: "#818cf8", step_in_process: "#f43f5e", entry_point_of: "#f43f5e",
};

const ALL_NODE_TYPES = [
  "file", "module", "class", "struct", "interface", "trait",
  "enum", "function", "method", "type", "impl",
  "property", "route", "tool",
  "community", "process",
];

function FileTree({ files, onSelect }: { files: string[]; onSelect: (id: string) => void }) {
  const tree = useMemo(() => {
    const root: Record<string, any> = {};
    for (const fp of files) {
      const parts = fp.replace(/\\/g, "/").split("/");
      let current = root;
      for (const part of parts) {
        if (!current[part]) current[part] = {};
        current = current[part];
      }
    }
    return root;
  }, [files]);

  const renderTree = (node: Record<string, any>, path: string = "", depth: number = 0): ReactNode[] => {
    return Object.keys(node).sort().map((key) => {
      const fullPath = path ? `${path}/${key}` : key;
      const isLeaf = Object.keys(node[key]).length === 0;
      return (
        <div key={fullPath}>
          <div
            className={`flex items-center gap-1 py-0.5 px-1 text-xs cursor-pointer hover:bg-accent/30 rounded ${isLeaf ? "text-foreground" : "text-muted-foreground font-medium"}`}
            style={{ paddingLeft: `${depth * 12 + 4}px` }}
            onClick={() => isLeaf ? onSelect(fullPath) : undefined}
          >
            <span className="truncate">{key}</span>
          </div>
          {!isLeaf && renderTree(node[key], fullPath, depth + 1)}
        </div>
      );
    });
  };

  return <div className="text-xs max-h-48 overflow-y-auto">{renderTree(tree)}</div>;
}

function CodeGraphPage() {
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null);
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
    new Set(["calls", "contains", "defines", "imports", "extends", "implements", "has_method", "has_property", "handles_route", "handles_tool", "method_overrides", "method_implements", "accesses", "member_of", "step_in_process", "entry_point_of"]),
  );
  const [visibleNodeTypes, setVisibleNodeTypes] = useState<Set<string>>(
    new Set(ALL_NODE_TYPES),
  );
  const [focusDepth, setFocusDepth] = useState<number | null>(null);

  const toggleEdgeType = useCallback((type: string) => {
    setVisibleEdgeTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }, []);

  const toggleNodeType = useCallback((type: string) => {
    setVisibleNodeTypes((prev) => {
      const next = new Set(prev);
      if (next.has(type)) next.delete(type);
      else next.add(type);
      return next;
    });
  }, []);

  const { data: repos } = useRepos();
  const { data: graphData, isLoading } = useCodeGraph(selectedRepoId);
  const codeSearch = useCodeSearch();
  const blastRadius = useBlastRadius();
  const { data: symbolDetail } = useCodeSymbolDetail(
    selectedNode && selectedNode.kind !== "file" && selectedNode.kind !== "module"
      ? selectedNode.id
      : null,
  );

  const filteredNodes = useMemo(() => {
    if (!graphData?.nodes) return [];
    let nodes = graphData.nodes.filter((n) =>
      visibleNodeTypes.has(n.kind || "function"),
    );

    if (focusDepth !== null && selectedNodeId) {
      const edgeMap = new Map<string, Set<string>>();
      for (const e of graphData.edges) {
        if (!edgeMap.has(e.source)) edgeMap.set(e.source, new Set());
        if (!edgeMap.has(e.target)) edgeMap.set(e.target, new Set());
        edgeMap.get(e.source)!.add(e.target);
        edgeMap.get(e.target)!.add(e.source);
      }

      const visited = new Set<string>();
      const queue: [string, number][] = [[selectedNodeId, 0]];
      visited.add(selectedNodeId);

      while (queue.length > 0) {
        const [current, depth] = queue.shift()!;
        if (depth >= focusDepth) continue;
        for (const neighbor of edgeMap.get(current) || []) {
          if (!visited.has(neighbor)) {
            visited.add(neighbor);
            queue.push([neighbor, depth + 1]);
          }
        }
      }

      nodes = nodes.filter((n) => visited.has(n.id));
    }

    return nodes;
  }, [graphData, visibleNodeTypes, focusDepth, selectedNodeId]);

  const filteredEdges = useMemo(() => {
    if (!graphData?.edges) return [];
    const nodeIds = new Set(filteredNodes.map((n) => n.id));
    return graphData.edges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target),
    );
  }, [graphData, filteredNodes]);

  const fileList = useMemo(() =>
    filteredNodes.filter(n => n.kind === "file").map(n => n.id).sort(),
    [filteredNodes]
  );

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
      if (!node) setBlastRadiusIds(undefined);
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
      const matchNode = filteredNodes.find(
        (n) =>
          n.label === result.symbol_name || n.label === result.file_path,
      );
      if (matchNode) {
        setSelectedNodeId(matchNode.id);
        handleSelect(matchNode);
      }
      setShowSearchResults(false);
    },
    [filteredNodes, handleSelect],
  );

  const handleBlastRadius = useCallback(() => {
    if (!selectedNode) return;
    blastRadius.mutate(
      { symbol_id: selectedNode.id },
      {
        onSuccess: (data) => {
          const ids = new Set(
            data.affected.map((a) => `${a.name}::${a.file_path}`)
          );
          if (selectedNode) ids.add(selectedNode.id);
          setBlastRadiusIds(ids);
        },
      },
    );
  }, [selectedNode, blastRadius]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-3 p-3 border-b border-border bg-card">
        <select
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
          value={selectedRepoId ?? ""}
          onChange={(e) => setSelectedRepoId(e.target.value || null)}
        >
          <option value="">Select a repo</option>
          {repos?.map((r) => (
            <option key={r.id} value={r.id}>
              {r.name}
            </option>
          ))}
        </select>

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
                  <div className="font-medium truncate">{r.file_path}</div>
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

        <div className="flex-1" />

        <div className="flex items-center gap-1.5 text-xs">
          <span className="text-muted-foreground">Depth:</span>
          {([null, 1, 2, 3, 5] as const).map((d) => (
            <button
              key={d ?? "all"}
              className={`px-1.5 py-0.5 rounded text-xs ${
                focusDepth === d
                  ? "bg-primary text-primary-foreground"
                  : "text-muted-foreground hover:text-foreground"
              }`}
              onClick={() => setFocusDepth(d)}
            >
              {d === null ? "All" : `${d}`}
            </button>
          ))}
        </div>

        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          {filteredNodes.length > 0 && (
            <span>
              {filteredNodes.length} nodes, {filteredEdges.length} edges
            </span>
          )}
          <ZoomIn className="w-4 h-4" />
          <ZoomOut className="w-4 h-4" />
        </div>
      </div>

      <div className="flex flex-1 overflow-hidden">
        <div className="w-44 border-r border-border bg-card p-3 space-y-4 overflow-y-auto shrink-0">
          {fileList.length > 0 && (
            <div>
              <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-2">Files</div>
              <FileTree
                files={fileList}
                onSelect={(id) => {
                  setSelectedNodeId(id);
                  handleSelect({ id, label: id.split("/").pop() || id, kind: "file" });
                }}
              />
            </div>
          )}

          <div>
            <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-2">
              Node Types
            </div>
            <div className="space-y-1">
              {ALL_NODE_TYPES.map((type) => (
                <label
                  key={type}
                  className="flex items-center gap-2 text-xs cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={visibleNodeTypes.has(type)}
                    onChange={() => toggleNodeType(type)}
                    className="accent-primary w-3 h-3"
                  />
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: NODE_COLORS_FOR_FILTER[type] }}
                  />
                  <span className="capitalize">{type}</span>
                </label>
              ))}
            </div>
          </div>

          <div>
            <div className="text-xs uppercase tracking-wider text-muted-foreground font-medium mb-2">
              Edge Types
            </div>
            <div className="space-y-1">
              {["calls", "contains", "defines", "imports", "extends", "implements", "has_method", "has_property", "handles_route", "handles_tool", "method_overrides", "method_implements", "accesses", "member_of", "step_in_process", "entry_point_of"].map((type) => (
                <label
                  key={type}
                  className="flex items-center gap-2 text-xs cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={visibleEdgeTypes.has(type)}
                    onChange={() => toggleEdgeType(type)}
                    className="accent-primary w-3 h-3"
                  />
                  <span
                    className="w-2 h-2 rounded-full shrink-0"
                    style={{ backgroundColor: EDGE_COLORS_FOR_FILTER[type] }}
                  />
                  <span className="capitalize">{type}</span>
                </label>
              ))}
            </div>
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
          {selectedRepoId && !isLoading && filteredNodes.length === 0 && (
            <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
              No graph data for this repository. Index it first from the
              Repositories page.
            </div>
          )}
          {filteredNodes.length > 0 && (
            <CodeGraphRenderer
              nodes={filteredNodes}
              edges={filteredEdges}
              selectedId={selectedNodeId}
              onSelect={handleSelect}
              highlightedIds={blastRadiusIds}
              visibleEdgeTypes={visibleEdgeTypes}
            />
          )}
        </div>
      </div>

      <Sheet
        open={!!selectedNode}
        onOpenChange={(open) => {
          if (!open) handleSelect(null);
        }}
      >
        <SheetContent side="right">
          <SheetHeader>
            <SheetTitle>{selectedNode?.label}</SheetTitle>
            <SheetDescription>
              {selectedNode?.kind ?? "symbol"}
            </SheetDescription>
          </SheetHeader>

          <div className="px-4 pb-4 overflow-y-auto flex-1 space-y-4">
            {symbolDetail && (
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
                  {blastRadius.isPending ? "Analyzing..." : "Blast Radius"}
                </Button>

                {blastRadiusIds && blastRadiusIds.size > 0 && (
                  <p className="text-sm text-muted-foreground">
                    {blastRadiusIds.size} affected symbol
                    {blastRadiusIds.size !== 1 ? "s" : ""} highlighted
                  </p>
                )}
              </>
            )}

            {!symbolDetail && selectedNode && selectedNode.kind !== "file" && selectedNode.kind !== "module" && (
              <p className="text-sm text-muted-foreground">
                Loading symbol details...
              </p>
            )}

            {selectedNode && (selectedNode.kind === "file" || selectedNode.kind === "module") && (
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
