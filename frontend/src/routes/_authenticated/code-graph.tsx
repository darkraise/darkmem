import { createFileRoute } from "@tanstack/react-router"
import { useState, useMemo, useCallback, useRef, useEffect } from "react"
import { useFullBleedContent } from "@/hooks/use-full-bleed-content"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "darkraise-ui/components/select"
import { Button } from "darkraise-ui/components/button"
import { ButtonGroup } from "darkraise-ui/components/button-group"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { Input } from "darkraise-ui/components/input"
import { Kbd } from "darkraise-ui/components/kbd"
import {
  SegmentGroup,
  SegmentGroupIndicator,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import { toast } from "darkraise-ui/components/sonner"
import { Spinner } from "darkraise-ui/components/spinner"
import { Toggle } from "darkraise-ui/components/toggle"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import { Toolbar, ToolbarSeparator } from "darkraise-ui/components/toolbar"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
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
  CircleAlert,
  Tag,
  Boxes,
  FolderGit2,
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
  "namespace",
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
  "unknown",
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
  useFullBleedContent()

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
  // Mirror refs for in-flight callbacks (blast-radius/search responses must
  // not commit under a selection or repo they weren't run for).
  const selectedNodeIdRef = useRef<string | null>(null)
  const selectedRepoIdRef = useRef<string | null>(selectedRepoId)
  selectedRepoIdRef.current = selectedRepoId
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
  const {
    data: graphData,
    isLoading,
    isError: isGraphError,
    refetch: refetchGraph,
  } = useCodeGraph(selectedRepoId)
  const codeSearch = useCodeSearch()
  const codeSearchRef = useRef(codeSearch)
  codeSearchRef.current = codeSearch
  const blastRadius = useBlastRadius()

  // Only ids carrying a name::file_path key resolve as symbols; plain-name
  // kinds (process, community, route, tool, property) would 404/422 on the
  // symbol endpoints, so they never qualify for detail or blast radius.
  const analyzableNodeId =
    selectedNode &&
    selectedNode.kind !== "file" &&
    selectedNode.kind !== "module" &&
    selectedNode.id.includes("::")
      ? selectedNode.id
      : null
  const { data: symbolDetail } = useCodeSymbolDetail(analyzableNodeId)
  const gatedSymbolDetail = analyzableNodeId ? (symbolDetail ?? null) : null

  // Changing repos invalidates every per-repo selection. Without this reset a
  // stale selectedNodeId seeds the focus BFS against the new repo's edges and
  // filters out everything ("No graph data" on an indexed repo), and the
  // panels keep rendering the previous repo's detail/blast/search state.
  useEffect(() => {
    setSelectedNode(null)
    setSelectedNodeId(null)
    selectedNodeIdRef.current = null
    setBlastRadiusIds(undefined)
    setBlastRadiusData(null)
    setSearchResults([])
    setSearchQuery("")
    setSelectedProcess(null)
    setProcessModalOpen(false)
    setSelectedCommunityId(null)
    setFocusDepth(null)
  }, [selectedRepoId])

  const typeFilteredNodes = useMemo(() => {
    if (!graphData?.nodes) return []
    return graphData.nodes.filter((n) =>
      visibleNodeTypes.has(n.kind || "unknown"),
    )
  }, [graphData, visibleNodeTypes])

  // Two-stage memo on purpose: without a depth filter the array identity must
  // not change on selection clicks, or every click rebuilds the renderer
  // scene and the file tree.
  const filteredNodes = useMemo(() => {
    if (focusDepth === null || !selectedNodeId || !graphData?.edges) {
      return typeFilteredNodes
    }
    const edgeMap = new Map<string, Set<string>>()
    for (const e of graphData.edges) {
      if (!edgeMap.has(e.source)) edgeMap.set(e.source, new Set())
      if (!edgeMap.has(e.target)) edgeMap.set(e.target, new Set())
      edgeMap.get(e.source)!.add(e.target)
      edgeMap.get(e.target)!.add(e.source)
    }

    const visited = new Set<string>([selectedNodeId])
    const queue: [string, number][] = [[selectedNodeId, 0]]
    let head = 0
    while (head < queue.length) {
      const [current, depth] = queue[head++]!
      if (depth >= focusDepth) continue
      for (const neighbor of edgeMap.get(current) || []) {
        if (!visited.has(neighbor)) {
          visited.add(neighbor)
          queue.push([neighbor, depth + 1])
        }
      }
    }

    return typeFilteredNodes.filter((n) => visited.has(n.id))
  }, [typeFilteredNodes, graphData, focusDepth, selectedNodeId])

  const filteredEdges = useMemo(() => {
    if (!graphData?.edges) return []
    const nodeIds = new Set(filteredNodes.map((n) => n.id))
    return graphData.edges.filter(
      (e) => nodeIds.has(e.source) && nodeIds.has(e.target),
    )
  }, [graphData, filteredNodes])

  // Derived from the unfiltered graph: the file browser should list the whole
  // repo regardless of canvas filters, and the stable identity keeps the
  // (expensive) tree from rebuilding on every filter or selection change.
  const fileList = useMemo(
    () =>
      (graphData?.nodes ?? [])
        .filter((n) => n.kind === "file")
        .map((n) => n.id)
        .sort(),
    [graphData],
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
      // Blast-radius results are scoped to the symbol they were run for;
      // moving the selection must not present them under another node.
      if (node?.id !== selectedNodeIdRef.current) {
        setBlastRadiusIds(undefined)
        setBlastRadiusData(null)
      }
      selectedNodeIdRef.current = node?.id ?? null
      setSelectedNode(node)
      setSelectedNodeId(node?.id ?? null)
      if (!node) {
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
      const forRepo = selectedRepoId
      codeSearchRef.current.mutate(
        { query: searchQuery, repo_id: forRepo ?? undefined },
        {
          onSuccess: (data) => {
            // Semantic search takes seconds; a response that lands after a
            // repo switch must not repopulate the new repo's results.
            if (selectedRepoIdRef.current !== forRepo) return
            setSearchResults(data)
            if (data.length === 0) {
              toast.info(`No matches for "${searchQuery.trim()}"`)
            } else {
              // Results render in the inspector's Results tab; surface the
              // panel so Enter never appears to do nothing.
              setShowInspector(true)
            }
          },
          onError: (err) => {
            toast.error(`Search failed: ${err.message}`)
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
      // The renderer gates emphasis on `!sel` (like handleCommunitySelect), so
      // a lingering node selection would mask the highlight entirely.
      handleSelect(null)
      setSelectedProcess(process)
      setProcessModalOpen(true)
    },
    [selectedProcess, handleSelect],
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
      // The file browser lists the unfiltered repo, so the clicked file may be
      // hidden by the canvas filters — reveal it like the other entry points.
      if (!filteredNodes.some((n) => n.id === id)) {
        setFocusDepth(null)
        setVisibleNodeTypes((prev) => new Set(prev).add("file"))
      }
      setSelectedNodeId(id)
      handleSelect({
        id,
        label: id.split("/").pop() || id,
        kind: "file",
      })
    },
    [filteredNodes, handleSelect],
  )

  const handleBlastRadius = useCallback(() => {
    if (!selectedNode) return
    const forId = selectedNode.id
    blastRadius.mutate(
      { symbol_id: forId },
      {
        onSuccess: (data) => {
          // The selection may have moved while the request was in flight;
          // committing then would show this symbol's impact under another.
          if (selectedNodeIdRef.current !== forId) return
          const ids = new Set(
            data.affected.map((a) => a.key ?? `${a.name}::${a.file_path}`),
          )
          ids.add(forId)
          setBlastRadiusIds(ids)
          setBlastRadiusData(data)
        },
        onError: (err) => {
          toast.error(`Blast radius failed: ${err.message}`)
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

  const handleTogglePlay = useCallback((pressed: boolean) => {
    rendererRef.current?.setLayoutRunning(pressed)
    setIsPlaying(pressed)
  }, [])

  const handleFocusSelected = useCallback(() => {
    if (selectedNodeId) rendererRef.current?.focusNode(selectedNodeId)
  }, [selectedNodeId])

  const handleClearSelection = useCallback(() => {
    rendererRef.current?.clearSelection()
  }, [])

  // ⌘K / Ctrl+K toggles the graph-node quick-jump palette. Suppressed while
  // the process modal is open — stacking the palette over the modal leaves
  // Escape closing both layers at once.
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault()
        if (processModalOpen) return
        setSearchPaletteOpen((prev) => !prev)
      }
    }
    window.addEventListener("keydown", handler)
    return () => window.removeEventListener("keydown", handler)
  }, [processModalOpen])

  return (
    <div ref={rootRef} className="code-graph-root flex h-full flex-col">
      <h1 className="sr-only">Code Graph</h1>
      {/* ── Toolbar ─────────────────────────────────────────────── */}
      <Toolbar className="code-graph-toolbar flex shrink-0 items-center gap-3 border-b border-border px-4 py-2">
        <TooltipProvider>
        {/* Left: panel toggle + repo */}
        <Tooltip>
          <TooltipTrigger asChild>
            <Toggle
              size="sm"
              pressed={showInspector}
              onPressedChange={setShowInspector}
              aria-label="Toggle code inspector"
            >
              <PanelLeft className="h-3.5 w-3.5" />
            </Toggle>
          </TooltipTrigger>
          <TooltipContent>Toggle code inspector</TooltipContent>
        </Tooltip>

        <Select
          value={selectedRepoId ?? "__none__"}
          onValueChange={(v) => setSelectedRepoId(v === "__none__" ? null : v)}
        >
          <SelectTrigger className="h-7 w-44 font-mono text-sm">
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
              className="h-7 pl-8 font-mono text-sm"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyDown={handleSearch}
            />
            {codeSearch.isPending && (
              <span className="absolute top-1/2 right-2.5 -translate-y-1/2">
                <Spinner size="sm" />
              </span>
            )}
          </div>
          <Tooltip>
            <TooltipTrigger asChild>
              <Button
                variant="ghost"
                size="icon"
                className="ml-1"
                onClick={() => setSearchPaletteOpen(true)}
                aria-label="Jump to node"
              >
                <Search className="h-3.5 w-3.5" />
              </Button>
            </TooltipTrigger>
            <TooltipContent>
              Jump to node <Kbd size="sm">⌘K</Kbd>
            </TooltipContent>
          </Tooltip>
        </div>

        {/* Layout switcher */}
        <ToggleGroup
          type="single"
          value={layout}
          onValueChange={handleLayoutChange}
          className="shrink-0 gap-0"
          aria-label="Graph layout"
        >
          <Tooltip>
            <TooltipTrigger asChild>
              {/* Explicit data-state: TooltipTrigger asChild injects its own
                  open/closed data-state which otherwise overwrites the
                  item's on/off and kills the pressed styling. */}
              <ToggleGroupItem
                value="force"
                variant="outline"
                aria-label="Force layout"
                data-state={layout === "force" ? "on" : "off"}
              >
                <Network className="h-3.5 w-3.5" />
              </ToggleGroupItem>
            </TooltipTrigger>
            <TooltipContent>Force layout</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <ToggleGroupItem
                value="tree"
                variant="outline"
                aria-label="Tree layout"
                data-state={layout === "tree" ? "on" : "off"}
              >
                <GitBranch className="h-3.5 w-3.5" />
              </ToggleGroupItem>
            </TooltipTrigger>
            <TooltipContent>Tree layout</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <ToggleGroupItem
                value="circles"
                variant="outline"
                aria-label="Concentric layout"
                data-state={layout === "circles" ? "on" : "off"}
              >
                <CircleDot className="h-3.5 w-3.5" />
              </ToggleGroupItem>
            </TooltipTrigger>
            <TooltipContent>Concentric layout</TooltipContent>
          </Tooltip>
        </ToggleGroup>

        {/* Color-by switcher */}
        <ToggleGroup
          type="single"
          value={colorMode}
          onValueChange={handleColorModeChange}
          className="shrink-0 gap-0"
          aria-label="Color nodes by"
        >
          <Tooltip>
            <TooltipTrigger asChild>
              <ToggleGroupItem
                value="type"
                variant="outline"
                aria-label="Color by type"
                data-state={colorMode === "type" ? "on" : "off"}
              >
                <Tag className="h-3.5 w-3.5" />
              </ToggleGroupItem>
            </TooltipTrigger>
            <TooltipContent>Color by type</TooltipContent>
          </Tooltip>
          <Tooltip>
            <TooltipTrigger asChild>
              <ToggleGroupItem
                value="community"
                variant="outline"
                aria-label="Color by community"
                data-state={colorMode === "community" ? "on" : "off"}
              >
                <Boxes className="h-3.5 w-3.5" />
              </ToggleGroupItem>
            </TooltipTrigger>
            <TooltipContent>Color by community</TooltipContent>
          </Tooltip>
        </ToggleGroup>

        {/* Camera controls + play/pause */}
        <div className="flex shrink-0 items-center gap-0.5">
          <ButtonGroup>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => rendererRef.current?.zoomIn()}
                  aria-label="Zoom in"
                >
                  <ZoomIn className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Zoom in</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => rendererRef.current?.zoomOut()}
                  aria-label="Zoom out"
                >
                  <ZoomOut className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Zoom out</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => rendererRef.current?.fitView()}
                  aria-label="Fit to view"
                >
                  <Maximize className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Fit to view</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={!selectedNodeId}
                  onClick={handleFocusSelected}
                  aria-label="Focus selected node"
                >
                  <Crosshair className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Focus selected node</TooltipContent>
            </Tooltip>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button
                  variant="ghost"
                  size="icon"
                  disabled={!selectedNodeId}
                  onClick={handleClearSelection}
                  aria-label="Clear selection"
                >
                  <Eraser className="h-3.5 w-3.5" />
                </Button>
              </TooltipTrigger>
              <TooltipContent>Clear selection</TooltipContent>
            </Tooltip>
          </ButtonGroup>
          <Tooltip>
            <TooltipTrigger asChild>
              <Toggle
                size="sm"
                pressed={isPlaying}
                onPressedChange={handleTogglePlay}
                disabled={layout !== "force"}
                aria-label={isPlaying ? "Pause layout" : "Play layout"}
              >
                {isPlaying ? (
                  <Pause className="h-3.5 w-3.5" />
                ) : (
                  <Play className="h-3.5 w-3.5" />
                )}
              </Toggle>
            </TooltipTrigger>
            <TooltipContent>
              {isPlaying ? "Pause layout" : "Play layout"}
            </TooltipContent>
          </Tooltip>
        </div>

        <ToolbarSeparator orientation="vertical" className="h-4" />

        {/* Right: depth + stats + panel toggle */}
        <div className="flex shrink-0 items-center gap-1 font-mono text-sm">
          <span className="mr-1 text-muted-foreground">Depth</span>
          <SegmentGroup
            value={focusDepth === null ? "all" : String(focusDepth)}
            onValueChange={(v) => setFocusDepth(v === "all" ? null : Number(v))}
            orientation="horizontal"
            aria-label="Focus depth"
          >
            <SegmentGroupIndicator />
            {([null, 1, 2, 3, 5] as const).map((d) => (
              <SegmentGroupItem
                key={d ?? "all"}
                value={d === null ? "all" : String(d)}
              >
                {d === null ? "All" : d}
              </SegmentGroupItem>
            ))}
          </SegmentGroup>
        </div>

        <ToolbarSeparator orientation="vertical" className="h-4" />

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

        <Tooltip>
          <TooltipTrigger asChild>
            <Toggle
              size="sm"
              pressed={showAnalysis}
              onPressedChange={setShowAnalysis}
              aria-label="Toggle analysis panel"
            >
              <PanelRight className="h-3.5 w-3.5" />
            </Toggle>
          </TooltipTrigger>
          <TooltipContent>Toggle analysis panel</TooltipContent>
        </Tooltip>
        </TooltipProvider>
      </Toolbar>

      {/* ── Three-panel content ────────────────────────────────── */}
      <div className="flex min-h-0 flex-1 overflow-hidden">
        {/* Left: Code Inspector */}
        {showInspector && (
          <div className="w-[280px] shrink-0 overflow-hidden">
            <CodeInspectorPanel
              symbolDetail={gatedSymbolDetail}
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
              <EmptyState
                icon={<FolderGit2 className="h-8 w-8" />}
                title="Select a repository"
                description="to visualize its code graph"
              />
            </div>
          )}
          {selectedRepoId && isLoading && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center">
              <Spinner size="lg" label="Loading graph…" />
            </div>
          )}
          {selectedRepoId && !isLoading && isGraphError && !graphData && (
            <div className="absolute inset-0 z-10 flex flex-col items-center justify-center">
              <EmptyState
                icon={<CircleAlert className="h-8 w-8" />}
                title="Failed to load graph"
                description="The request failed — this is not an indexing problem"
                action={
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => refetchGraph()}
                  >
                    Retry
                  </Button>
                }
              />
            </div>
          )}
          {selectedRepoId &&
            !isLoading &&
            !isGraphError &&
            filteredNodes.length === 0 && (
              <div className="absolute inset-0 z-10 flex flex-col items-center justify-center">
                <EmptyState
                  icon={<CircleAlert className="h-8 w-8" />}
                  title="No graph data"
                  description="Index this repo from the Repositories page"
                />
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
              onLayoutRunningChange={setIsPlaying}
              viewportKey={selectedRepoId}
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
              symbolDetail={gatedSymbolDetail}
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
