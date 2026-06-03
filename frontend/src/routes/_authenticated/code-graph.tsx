import { createFileRoute } from "@tanstack/react-router"
import { useState, useMemo, useCallback, useRef } from "react"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "darkraise-ui/components/select"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { toast } from "darkraise-ui/components/sonner"
import { CodeGraphRenderer } from "@/features/graph/components/code-graph-renderer"
import { CodeInspectorPanel } from "@/features/graph/components/code-inspector-panel"
import { CodeAnalysisPanel } from "@/features/graph/components/code-analysis-panel"
import {
  useRepos,
  useCodeGraph,
  useCodeSearch,
  useCodeSymbolDetail,
  useBlastRadius,
  type CodeSearchResult,
  type BlastRadiusResult,
} from "@/hooks/api"
import { PanelLeft, PanelRight, Search, Loader2 } from "lucide-react"
import { useCodeGraphTheme } from "@/features/graph/lib/code-graph-theme"

export const Route = createFileRoute("/_authenticated/code-graph")({
  component: CodeGraphPage,
})

const ALL_NODE_TYPES = [
  "file",
  "module",
  "class",
  "struct",
  "interface",
  "trait",
  "enum",
  "function",
  "method",
  "type",
  "impl",
  "property",
  "route",
  "tool",
  "community",
  "process",
]

const ALL_EDGE_TYPES = [
  "calls",
  "contains",
  "defines",
  "imports",
  "extends",
  "implements",
  "has_method",
  "has_property",
  "handles_route",
  "handles_tool",
  "method_overrides",
  "method_implements",
  "accesses",
  "member_of",
  "step_in_process",
  "entry_point_of",
]

function CodeGraphPage() {
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null)
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null)
  const [selectedNode, setSelectedNode] = useState<{
    id: string
    label: string
    kind?: string
    file_path?: string
  } | null>(null)
  const [searchQuery, setSearchQuery] = useState("")
  const [blastRadiusIds, setBlastRadiusIds] = useState<Set<string> | undefined>(
    undefined,
  )
  const [blastRadiusData, setBlastRadiusData] =
    useState<BlastRadiusResult | null>(null)
  const [searchResults, setSearchResults] = useState<CodeSearchResult[]>([])
  const [visibleEdgeTypes, setVisibleEdgeTypes] = useState<Set<string>>(
    new Set(ALL_EDGE_TYPES),
  )
  const [visibleNodeTypes, setVisibleNodeTypes] = useState<Set<string>>(
    new Set(ALL_NODE_TYPES),
  )
  const [focusDepth, setFocusDepth] = useState<number | null>(null)
  const [showInspector, setShowInspector] = useState(true)
  const [showAnalysis, setShowAnalysis] = useState(true)

  const rootRef = useRef<HTMLDivElement>(null)
  const { tokens, nodeColors, edgeColors } = useCodeGraphTheme(
    rootRef,
    ALL_NODE_TYPES,
    ALL_EDGE_TYPES,
  )

  const toggleEdgeType = useCallback((type: string) => {
    setVisibleEdgeTypes((prev) => {
      const next = new Set(prev)
      if (next.has(type)) next.delete(type)
      else next.add(type)
      return next
    })
  }, [])

  const toggleNodeType = useCallback((type: string) => {
    setVisibleNodeTypes((prev) => {
      const next = new Set(prev)
      if (next.has(type)) next.delete(type)
      else next.add(type)
      return next
    })
  }, [])

  const { data: repos } = useRepos()
  const { data: graphData, isLoading } = useCodeGraph(selectedRepoId)
  const codeSearch = useCodeSearch()
  const codeSearchRef = useRef(codeSearch)
  codeSearchRef.current = codeSearch
  const blastRadius = useBlastRadius()
  const { data: symbolDetail } = useCodeSymbolDetail(
    selectedNode &&
      selectedNode.kind !== "file" &&
      selectedNode.kind !== "module"
      ? selectedNode.id
      : null,
  )

  const filteredNodes = useMemo(() => {
    if (!graphData?.nodes) return []
    let nodes = graphData.nodes.filter((n) =>
      visibleNodeTypes.has(n.kind || "function"),
    )

    if (focusDepth !== null && selectedNodeId) {
      const edgeMap = new Map<string, Set<string>>()
      for (const e of graphData.edges) {
        if (!edgeMap.has(e.source)) edgeMap.set(e.source, new Set())
        if (!edgeMap.has(e.target)) edgeMap.set(e.target, new Set())
        edgeMap.get(e.source)!.add(e.target)
        edgeMap.get(e.target)!.add(e.source)
      }

      const visited = new Set<string>()
      const queue: [string, number][] = [[selectedNodeId, 0]]
      visited.add(selectedNodeId)

      while (queue.length > 0) {
        const [current, depth] = queue.shift()!
        if (depth >= focusDepth) continue
        for (const neighbor of edgeMap.get(current) || []) {
          if (!visited.has(neighbor)) {
            visited.add(neighbor)
            queue.push([neighbor, depth + 1])
          }
        }
      }

      nodes = nodes.filter((n) => visited.has(n.id))
    }

    return nodes
  }, [graphData, visibleNodeTypes, focusDepth, selectedNodeId])

  const filteredEdges = useMemo(() => {
    if (!graphData?.edges) return []
    const nodeIds = new Set(filteredNodes.map((n) => n.id))
    return graphData.edges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target),
    )
  }, [graphData, filteredNodes])

  const fileList = useMemo(
    () =>
      filteredNodes
        .filter((n) => n.kind === "file")
        .map((n) => n.id)
        .sort(),
    [filteredNodes],
  )

  const handleSelect = useCallback(
    (
      node: {
        id: string
        label: string
        kind?: string
        file_path?: string
      } | null,
    ) => {
      setSelectedNode(node)
      setSelectedNodeId(node?.id ?? null)
      if (!node) {
        setBlastRadiusIds(undefined)
        setBlastRadiusData(null)
      }
    },
    [],
  )

  const handleSearch = useCallback(
    (e: React.KeyboardEvent<HTMLInputElement>) => {
      if (e.key !== "Enter" || !searchQuery.trim()) return
      codeSearchRef.current.mutate(
        { query: searchQuery, repo_id: selectedRepoId ?? undefined },
        {
          onSuccess: (data) => {
            setSearchResults(data)
          },
        },
      )
    },
    [searchQuery, selectedRepoId],
  )

  const handleSearchResultClick = useCallback(
    (result: CodeSearchResult) => {
      const all = graphData?.nodes ?? []
      // Resolve against the FULL node set (not the filtered subset) so an
      // off-screen match is still actionable, and disambiguate same-named
      // symbols by file_path before falling back to a name/path label match.
      const matchNode =
        all.find(
          (n) => n.label === result.symbol_name && n.file_path === result.file_path,
        ) ??
        all.find(
          (n) => n.label === result.symbol_name || n.label === result.file_path,
        )
      if (!matchNode) {
        toast.error(`"${result.symbol_name}" isn't in the current graph`)
        return
      }
      // If the match is hidden by the active type/focus filters, reveal it so
      // the selection is actually shown rather than a silent no-op.
      if (!filteredNodes.some((n) => n.id === matchNode.id)) {
        setFocusDepth(null)
        setVisibleNodeTypes((prev) => new Set(prev).add(matchNode.kind || "function"))
      }
      setSelectedNodeId(matchNode.id)
      handleSelect(matchNode)
    },
    [graphData, filteredNodes, handleSelect],
  )

  const handleFileSelect = useCallback(
    (id: string) => {
      setSelectedNodeId(id)
      handleSelect({
        id,
        label: id.split("/").pop() || id,
        kind: "file",
      })
    },
    [handleSelect],
  )

  const handleBlastRadius = useCallback(() => {
    if (!selectedNode) return
    blastRadius.mutate(
      { symbol_id: selectedNode.id },
      {
        onSuccess: (data) => {
          const ids = new Set(
            data.affected.map((a) => `${a.name}::${a.file_path}`),
          )
          if (selectedNode) ids.add(selectedNode.id)
          setBlastRadiusIds(ids)
          setBlastRadiusData(data)
        },
      },
    )
  }, [selectedNode, blastRadius])

  const handleClearBlastRadius = useCallback(() => {
    setBlastRadiusIds(undefined)
    setBlastRadiusData(null)
  }, [])

  return (
    <div ref={rootRef} className="code-graph-root flex h-full flex-col">
      <h1 className="sr-only">Code Graph</h1>
      {/* ── Toolbar ─────────────────────────────────────────────── */}
      <div className="code-graph-toolbar flex shrink-0 items-center gap-3 border-b border-border px-4 py-2">
        {/* Left: panel toggle + repo */}
        <Button
          variant="ghost"
          size="icon"
          className={`rounded p-1.5 transition-colors ${showInspector ? "bg-primary/15 text-primary" : "text-muted-foreground hover:text-foreground"}`}
          onClick={() => setShowInspector(!showInspector)}
          title="Toggle code inspector"
          aria-label="Toggle code inspector"
        >
          <PanelLeft className="h-3.5 w-3.5" />
        </Button>

        <Select
          value={selectedRepoId ?? "__none__"}
          onValueChange={(v) => setSelectedRepoId(v === "__none__" ? null : v)}
        >
          <SelectTrigger className="h-7 w-44 border-border bg-transparent font-mono text-sm text-foreground hover:border-primary/40 focus:border-primary/50">
            <SelectValue placeholder="Select repo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__none__">Select repo</SelectItem>
            {repos?.map((r) => (
              <SelectItem key={r.id} value={r.id}>
                {r.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Center: search */}
        <div className="flex flex-1 justify-center">
          <div className="relative w-full max-w-md">
            <Search className="absolute top-1/2 left-2.5 h-3 w-3 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search symbols…"
              className="h-7 border-border bg-transparent pl-8 font-mono text-sm text-foreground placeholder:text-muted-foreground hover:border-primary/40 focus-visible:border-primary/50 focus-visible:ring-2 focus-visible:ring-ring"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleSearch}
            />
            {codeSearch.isPending && (
              <Loader2 className="absolute top-1/2 right-2.5 h-3 w-3 -translate-y-1/2 animate-spin text-primary" />
            )}
          </div>
        </div>

        {/* Right: depth + stats + panel toggle */}
        <div className="flex shrink-0 items-center gap-1 font-mono text-sm">
          <span className="mr-1 text-muted-foreground">Depth</span>
          {([null, 1, 2, 3, 5] as const).map((d) => (
            <Button
              variant="ghost"
              key={d ?? "all"}
              className={`rounded-sm px-1.5 py-0.5 transition-colors ${
                focusDepth === d
                  ? "bg-primary/15 text-primary"
                  : "text-muted-foreground hover:bg-accent hover:text-foreground"
              }`}
              onClick={() => setFocusDepth(d)}
            >
              {d === null ? "All" : d}
            </Button>
          ))}
        </div>

        <div className="h-4 w-px bg-border" />

        {filteredNodes.length > 0 && (
          <div className="shrink-0 font-mono text-sm text-muted-foreground tabular-nums">
            <span className="text-primary">{filteredNodes.length}</span>
            <span className="mx-0.5 text-muted-foreground">n</span>
            <span className="ml-1 text-primary">
              {filteredEdges.length}
            </span>
            <span className="mx-0.5 text-muted-foreground">e</span>
          </div>
        )}

        <Button
          variant="ghost"
          size="icon"
          className={`rounded p-1.5 transition-colors ${showAnalysis ? "bg-primary/15 text-primary" : "text-muted-foreground hover:text-foreground"}`}
          onClick={() => setShowAnalysis(!showAnalysis)}
          title="Toggle analysis panel"
          aria-label="Toggle analysis panel"
        >
          <PanelRight className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* ── Three-panel content ────────────────────────────────── */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        {/* Left: Code Inspector */}
        {showInspector && (
          <div className="w-[280px] shrink-0 overflow-hidden">
            <CodeInspectorPanel
              symbolDetail={
                selectedNode &&
                selectedNode.kind !== "file" &&
                selectedNode.kind !== "module"
                  ? (symbolDetail ?? null)
                  : null
              }
              searchResults={searchResults}
              fileList={fileList}
              onFileSelect={handleFileSelect}
              onSearchResultClick={handleSearchResultClick}
            />
          </div>
        )}

        {/* Center: Graph Canvas */}
        <div className="relative min-w-0 flex-1">
          {!selectedRepoId && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-xl border border-border bg-card">
                <span className="font-mono text-2xl text-muted-foreground">◇</span>
              </div>
              <p className="font-mono text-base text-foreground">
                Select a repository
              </p>
              <p className="mt-1 font-mono text-sm text-muted-foreground">
                to visualize its code graph
              </p>
            </div>
          )}
          {selectedRepoId && isLoading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center">
              <Loader2 className="mb-3 h-6 w-6 animate-spin text-primary" />
              <p className="font-mono text-base text-foreground">
                Loading graph…
              </p>
            </div>
          )}
          {selectedRepoId && !isLoading && filteredNodes.length === 0 && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-xl border border-border bg-card">
                <span className="font-mono text-2xl text-muted-foreground">!</span>
              </div>
              <p className="font-mono text-base text-foreground">No graph data</p>
              <p className="mt-1 font-mono text-sm text-muted-foreground">
                Index this repo from the Repositories page
              </p>
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
              nodeColors={nodeColors}
              edgeColors={edgeColors}
              tokens={tokens}
            />
          )}

          {/* Floating graph background (behind renderer) */}
          <div className="absolute inset-0 -z-10 bg-background" />
        </div>

        {/* Right: Analysis */}
        {showAnalysis && (
          <div className="w-[300px] shrink-0 overflow-hidden">
            <CodeAnalysisPanel
              selectedNode={selectedNode}
              symbolDetail={
                selectedNode &&
                selectedNode.kind !== "file" &&
                selectedNode.kind !== "module"
                  ? (symbolDetail ?? null)
                  : null
              }
              blastRadiusIds={blastRadiusIds}
              blastRadiusData={blastRadiusData}
              onBlastRadius={handleBlastRadius}
              onClearBlastRadius={handleClearBlastRadius}
              isBlastRadiusLoading={blastRadius.isPending}
              nodeCount={filteredNodes.length}
              edgeCount={filteredEdges.length}
              visibleNodeTypes={visibleNodeTypes}
              visibleEdgeTypes={visibleEdgeTypes}
              onToggleNodeType={toggleNodeType}
              onToggleEdgeType={toggleEdgeType}
              nodeColors={nodeColors}
              edgeColors={edgeColors}
              allNodeTypes={ALL_NODE_TYPES}
              allEdgeTypes={ALL_EDGE_TYPES}
            />
          </div>
        )}
      </div>
    </div>
  )
}
