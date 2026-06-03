import { createFileRoute } from "@tanstack/react-router"
import { useState, useMemo, useCallback, useRef, useEffect } from "react"
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
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import {
  CodeGraphRenderer,
  type CodeGraphHandle,
  type CodeGraphLayout,
  type CodeGraphColorMode,
} from "@/features/graph/components/code-graph-renderer"
import { CodeInspectorPanel } from "@/features/graph/components/code-inspector-panel"
import { CodeAnalysisPanel } from "@/features/graph/components/code-analysis-panel"
import { CodeGraphSearch } from "@/features/graph/components/code-graph-search"
import { ProcessFlowModal } from "@/features/graph/components/process-flow-modal"
import {
  deriveProcesses,
  type CodeProcess,
} from "@/features/graph/lib/code-processes"
import {
  useRepos,
  useCodeGraph,
  useCodeSearch,
  useCodeSymbolDetail,
  useBlastRadius,
  type CodeSearchResult,
  type BlastRadiusResult,
} from "@/hooks/api"
import {
  PanelLeft,
  PanelRight,
  Search,
  Loader2,
  ZoomIn,
  ZoomOut,
  Maximize,
  Crosshair,
  Eraser,
  Play,
  Pause,
  Network,
  GitBranch,
  CircleDot,
  Tag,
  Boxes,
} from "lucide-react"
import {
  useCodeGraphTheme,
  communityColor,
} from "@/features/graph/lib/code-graph-theme"

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
  const [layout, setLayout] = useState<CodeGraphLayout>("force")
  const [colorMode, setColorMode] = useState<CodeGraphColorMode>("type")
  const [selectedCommunityId, setSelectedCommunityId] = useState<string | null>(
    null,
  )
  const [isPlaying, setIsPlaying] = useState(true)
  const [searchPaletteOpen, setSearchPaletteOpen] = useState(false)
  const [selectedProcess, setSelectedProcess] = useState<CodeProcess | null>(
    null,
  )
  const [processModalOpen, setProcessModalOpen] = useState(false)

  const rendererRef = useRef<CodeGraphHandle>(null)
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
  // buildGraph auto-starts the FA2 worker whenever it (re)builds in force mode
  // (e.g. on a repo switch), so keep the play/pause toggle in sync with it.
  useEffect(() => {
    if (layout === "force") setIsPlaying(true)
  }, [graphData, layout])
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
        // Deselecting the stage also clears any process/community emphasis;
        // without this the emphasis (gated on !sel) would re-reveal once the
        // selection drops.
        setSelectedProcess(null)
        setSelectedCommunityId(null)
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

  const handleSymbolSelect = useCallback(
    (name: string, filePath: string) => {
      const all = graphData?.nodes ?? []
      // Symbol browser rows carry the canonical name + file_path; resolve the
      // node the same way handleSearchResultClick does, preferring an exact
      // name::file_path match before a looser label fallback.
      const matchNode =
        all.find((n) => n.label === name && n.file_path === filePath) ??
        all.find((n) => n.label === name)
      if (!matchNode) {
        toast.error(`"${name}" isn't in the current graph`)
        return
      }
      if (!filteredNodes.some((n) => n.id === matchNode.id)) {
        setFocusDepth(null)
        setVisibleNodeTypes((prev) =>
          new Set(prev).add(matchNode.kind || "function"),
        )
      }
      setSelectedNodeId(matchNode.id)
      handleSelect(matchNode)
      rendererRef.current?.focusNode(matchNode.id)
    },
    [graphData, filteredNodes, handleSelect],
  )

  const symbolKinds = useMemo(() => {
    const kinds = new Set<string>()
    for (const n of graphData?.nodes ?? []) {
      if (n.kind && n.kind !== "community" && n.kind !== "process") {
        kinds.add(n.kind)
      }
    }
    return Array.from(kinds).sort()
  }, [graphData])

  const searchNodes = useMemo(
    () =>
      (graphData?.nodes ?? []).map((n) => ({
        id: n.id,
        label: n.label,
        kind: n.kind || "function",
      })),
    [graphData],
  )

  const processes = useMemo(
    () =>
      graphData
        ? deriveProcesses(graphData.nodes, graphData.edges)
        : [],
    [graphData],
  )

  // Communities derive from `member_of` edges (member symbol -> community node)
  // plus the community nodes themselves. Size prefers the backend's
  // properties.size when present, else falls back to the counted membership.
  const communities = useMemo(() => {
    const nodes = graphData?.nodes ?? []
    const edges = graphData?.edges ?? []
    const communityNodes = nodes.filter((n) => n.kind === "community")
    if (communityNodes.length === 0) return []

    const ids = new Set(communityNodes.map((n) => n.id))
    const members = new Map<string, string[]>()
    for (const e of edges) {
      if (e.type !== "member_of" || !ids.has(e.target)) continue
      if (!members.has(e.target)) members.set(e.target, [])
      members.get(e.target)!.push(e.source)
    }

    return communityNodes
      .map((n) => {
        const memberIds = members.get(n.id) ?? []
        const props = (n as { properties?: Record<string, unknown> | null })
          .properties
        const declaredSize = props ? Number(props.size) : NaN
        const size = Number.isFinite(declaredSize)
          ? declaredSize
          : memberIds.length
        // The renderer anchors a community's hue on the community node id, so
        // the navigator does too — keeping the swatch and the node color in
        // sync. The community node is highlighted alongside its members so the
        // navigator selection and the renderer's emphasis ring agree.
        return {
          id: n.id,
          label: n.label,
          size,
          nodeIds: [n.id, ...memberIds],
        }
      })
      .sort((a, b) => b.size - a.size)
  }, [graphData])

  // Pre-resolve each community's swatch so the navigator and the renderer's
  // community-mode node colors share one accent-derived source.
  const communityList = useMemo(
    () =>
      communities.map((c) => ({
        id: c.id,
        label: c.label,
        size: c.size,
        nodeIds: c.nodeIds,
        color: communityColor(c.id, tokens),
      })),
    [communities, tokens],
  )

  // Emphasis set drives the renderer's primary-ring highlight; it carries the
  // selected process's nodes or the selected community's members, kept
  // independent of blast-radius (destructive). The two selections are mutually
  // exclusive — picking one clears the other.
  const emphasisNodeIds = useMemo(() => {
    if (selectedProcess) return new Set(selectedProcess.nodeIds)
    if (selectedCommunityId) {
      const community = communities.find((c) => c.id === selectedCommunityId)
      if (community) return new Set(community.nodeIds)
    }
    return undefined
  }, [selectedProcess, selectedCommunityId, communities])

  const handleProcessSelect = useCallback(
    (process: CodeProcess) => {
      // Re-clicking the active row turns the emphasis off rather than reopening
      // the modal with no way back to a clear stage.
      if (selectedProcess?.id === process.id) {
        setSelectedProcess(null)
        return
      }
      // Process and community emphasis are mutually exclusive.
      setSelectedCommunityId(null)
      setSelectedProcess(process)
      setProcessModalOpen(true)
    },
    [selectedProcess],
  )

  const handleCommunitySelect = useCallback(
    (community: { id: string; nodeIds: string[] }) => {
      // Re-clicking the active community clears its emphasis.
      if (selectedCommunityId === community.id) {
        setSelectedCommunityId(null)
        return
      }
      // The renderer gates emphasis on `!sel`, so clear any node selection and
      // the (mutually exclusive) process emphasis first, then reveal members
      // hidden by the active type/focus filters so the highlight is visible.
      handleSelect(null)
      setSelectedProcess(null)
      const memberNodes = (graphData?.nodes ?? []).filter((n) =>
        community.nodeIds.includes(n.id),
      )
      const hiddenKinds = memberNodes
        .filter((n) => !filteredNodes.some((f) => f.id === n.id))
        .map((n) => n.kind || "function")
      if (hiddenKinds.length > 0) {
        setFocusDepth(null)
        setVisibleNodeTypes((prev) => {
          const next = new Set(prev)
          for (const kind of hiddenKinds) next.add(kind)
          return next
        })
      }
      setSelectedCommunityId(community.id)
      rendererRef.current?.fitView()
    },
    [selectedCommunityId, graphData, filteredNodes, handleSelect],
  )

  const handleColorModeChange = useCallback((value: string) => {
    if (!value) return
    setColorMode(value as CodeGraphColorMode)
  }, [])

  const handleProcessFocus = useCallback(
    (process: CodeProcess) => {
      // Clear the node selection first: the renderer gates process emphasis on
      // `!sel`, so an active selection would mask the highlight entirely.
      handleSelect(null)
      // Reveal flow nodes hidden by the active type/focus filters, mirroring
      // handleSearchResultClick/handlePalettePick, so the focus is never a no-op.
      const flowNodes = (graphData?.nodes ?? []).filter((n) =>
        process.nodeIds.includes(n.id),
      )
      const hiddenKinds = flowNodes
        .filter((n) => !filteredNodes.some((f) => f.id === n.id))
        .map((n) => n.kind || "function")
      if (hiddenKinds.length > 0) {
        setFocusDepth(null)
        setVisibleNodeTypes((prev) => {
          const next = new Set(prev)
          for (const kind of hiddenKinds) next.add(kind)
          return next
        })
      }
      setSelectedProcess(process)
      rendererRef.current?.fitView()
    },
    [graphData, filteredNodes, handleSelect],
  )

  const handlePalettePick = useCallback(
    (id: string) => {
      const matchNode = (graphData?.nodes ?? []).find((n) => n.id === id)
      if (!matchNode) return
      // Reveal a node hidden by the active type/focus filters before selecting,
      // mirroring handleSearchResultClick so the quick-jump is never a no-op.
      if (!filteredNodes.some((n) => n.id === matchNode.id)) {
        setFocusDepth(null)
        setVisibleNodeTypes((prev) =>
          new Set(prev).add(matchNode.kind || "function"),
        )
      }
      setSelectedNodeId(matchNode.id)
      handleSelect(matchNode)
      rendererRef.current?.focusNode(matchNode.id)
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
            data.affected.map((a) => a.key ?? `${a.name}::${a.file_path}`),
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

  const handleLayoutChange = useCallback((value: string) => {
    if (!value) return
    const next = value as CodeGraphLayout
    setLayout(next)
    // Manual layouts hold the FA2 worker stopped; reflect that in the toggle so
    // play/pause and the running state stay in sync after a layout switch.
    setIsPlaying(next === "force")
  }, [])

  const handleTogglePlay = useCallback(() => {
    const next = !isPlaying
    rendererRef.current?.setLayoutRunning(next)
    setIsPlaying(next)
  }, [isPlaying])

  const handleFocusSelected = useCallback(() => {
    if (selectedNodeId) rendererRef.current?.focusNode(selectedNodeId)
  }, [selectedNodeId])

  const handleClearSelection = useCallback(() => {
    rendererRef.current?.clearSelection()
  }, [])

  // ⌘K / Ctrl+K toggles the graph-node quick-jump palette.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        setSearchPaletteOpen((prev) => !prev)
      }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
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
          <Button
            variant="ghost"
            size="icon"
            className="ml-1 h-7 w-7 text-muted-foreground hover:text-foreground"
            onClick={() => setSearchPaletteOpen(true)}
            title="Jump to node (⌘K)"
            aria-label="Jump to node"
          >
            <Search className="h-3.5 w-3.5" />
          </Button>
        </div>

        {/* Layout switcher */}
        <ToggleGroup
          type="single"
          value={layout}
          onValueChange={handleLayoutChange}
          className="shrink-0 gap-0"
        >
          <ToggleGroupItem
            value="force"
            variant="outline"
            className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2"
            title="Force layout"
            aria-label="Force layout"
          >
            <Network className="h-3.5 w-3.5" />
          </ToggleGroupItem>
          <ToggleGroupItem
            value="tree"
            variant="outline"
            className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2"
            title="Tree layout"
            aria-label="Tree layout"
          >
            <GitBranch className="h-3.5 w-3.5" />
          </ToggleGroupItem>
          <ToggleGroupItem
            value="circles"
            variant="outline"
            className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2"
            title="Concentric layout"
            aria-label="Concentric layout"
          >
            <CircleDot className="h-3.5 w-3.5" />
          </ToggleGroupItem>
        </ToggleGroup>

        {/* Color-by switcher */}
        <ToggleGroup
          type="single"
          value={colorMode}
          onValueChange={handleColorModeChange}
          className="shrink-0 gap-0"
        >
          <ToggleGroupItem
            value="type"
            variant="outline"
            className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2"
            title="Color by type"
            aria-label="Color by type"
          >
            <Tag className="h-3.5 w-3.5" />
          </ToggleGroupItem>
          <ToggleGroupItem
            value="community"
            variant="outline"
            className="data-[pressed]:bg-primary/20 data-[pressed]:text-primary h-7 px-2"
            title="Color by community"
            aria-label="Color by community"
          >
            <Boxes className="h-3.5 w-3.5" />
          </ToggleGroupItem>
        </ToggleGroup>

        {/* Camera controls + play/pause */}
        <div className="flex shrink-0 items-center gap-0.5">
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-foreground"
            onClick={() => rendererRef.current?.zoomIn()}
            title="Zoom in"
            aria-label="Zoom in"
          >
            <ZoomIn className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-foreground"
            onClick={() => rendererRef.current?.zoomOut()}
            title="Zoom out"
            aria-label="Zoom out"
          >
            <ZoomOut className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7 text-muted-foreground hover:text-foreground"
            onClick={() => rendererRef.current?.fitView()}
            title="Fit to view"
            aria-label="Fit to view"
          >
            <Maximize className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            disabled={!selectedNodeId}
            className="h-7 w-7 text-muted-foreground hover:text-foreground disabled:opacity-40"
            onClick={handleFocusSelected}
            title="Focus selected node"
            aria-label="Focus selected node"
          >
            <Crosshair className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            disabled={!selectedNodeId}
            className="h-7 w-7 text-muted-foreground hover:text-foreground disabled:opacity-40"
            onClick={handleClearSelection}
            title="Clear selection"
            aria-label="Clear selection"
          >
            <Eraser className="h-3.5 w-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon"
            disabled={layout !== "force"}
            className={`h-7 w-7 disabled:opacity-40 ${isPlaying ? "bg-primary/15 text-primary" : "text-muted-foreground hover:text-foreground"}`}
            onClick={handleTogglePlay}
            title={isPlaying ? "Pause layout" : "Play layout"}
            aria-label={isPlaying ? "Pause layout" : "Play layout"}
          >
            {isPlaying ? (
              <Pause className="h-3.5 w-3.5" />
            ) : (
              <Play className="h-3.5 w-3.5" />
            )}
          </Button>
        </div>

        <div className="h-4 w-px bg-border" />

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
              repoId={selectedRepoId}
              nodeColors={nodeColors}
              symbolKinds={symbolKinds}
              onSymbolSelect={handleSymbolSelect}
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
              ref={rendererRef}
              nodes={filteredNodes}
              edges={filteredEdges}
              selectedId={selectedNodeId}
              onSelect={handleSelect}
              highlightedIds={blastRadiusIds}
              emphasisNodeIds={emphasisNodeIds}
              visibleEdgeTypes={visibleEdgeTypes}
              nodeColors={nodeColors}
              edgeColors={edgeColors}
              tokens={tokens}
              layout={layout}
              colorMode={colorMode}
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
              processes={processes}
              selectedProcessId={selectedProcess?.id ?? null}
              onProcessSelect={handleProcessSelect}
              communities={communityList}
              selectedCommunityId={selectedCommunityId}
              onCommunitySelect={handleCommunitySelect}
            />
          </div>
        )}
      </div>

      <CodeGraphSearch
        open={searchPaletteOpen}
        onOpenChange={setSearchPaletteOpen}
        nodes={searchNodes}
        nodeColors={nodeColors}
        onPick={handlePalettePick}
      />

      <ProcessFlowModal
        process={selectedProcess}
        open={processModalOpen}
        onOpenChange={setProcessModalOpen}
        nodeColors={nodeColors}
        onFocus={handleProcessFocus}
      />
    </div>
  )
}
