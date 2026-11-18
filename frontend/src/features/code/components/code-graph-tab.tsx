import { useEffect, useMemo, useRef, useState } from "react"
import {
  Boxes,
  Copy,
  Crosshair,
  FileCode2,
  FolderGit2,
  Maximize,
  PanelLeftClose,
  PanelLeftOpen,
  Play,
  Search,
  Share2,
  Tag,
  TriangleAlert,
  Workflow,
  X,
  ZoomIn,
  ZoomOut,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "darkraise-ui/components/tooltip"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "darkraise-ui/components/tabs"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import {
  ToggleGroup,
  ToggleGroupItem,
} from "darkraise-ui/components/toggle-group"
import { EmptyState } from "@/components/darkmem"
import { cn } from "darkraise-ui/lib"
import { useMediaQuery } from "@/hooks/use-media-query"
import { phaseProgressLabel, phaseProgressPercent } from "../lib/phase-progress"
import { useDemoCodeRepos, useDemoCodeGraph } from "@/demo/hooks"
import {
  computeBlastRadius,
  mermaidForProcess,
  neighborhoodWithin,
  type BlastRadius,
} from "@/demo/explore"
import type { CodeNodeKind } from "@/features/code/types"
import type { DemoRepo } from "@/demo/types"
import { chartVar } from "./code-canvas"
import { CodeGlowCanvas } from "./code-glow-canvas"
import { CodeExplorer } from "./code-explorer"
import { CodeFilters } from "./code-filters"
import {
  CodeInspector,
  FloatingFilePanel,
  type OpenCodeFile,
} from "./code-inspector"
import { RepoStatusChip } from "./repo-status-chip"

const DEPTHS = ["all", "1", "2", "3"] as const
type DepthValue = (typeof DEPTHS)[number]

const STATUS_DOT: Record<DemoRepo["status"], string> = {
  ready: "bg-success-solid",
  indexing: "bg-info-solid",
  stale: "bg-warning-solid",
  error: "bg-destructive-solid",
  registered: "bg-muted-foreground",
}

function SectionTitle({
  icon,
  children,
}: {
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <span className="text-muted-foreground flex items-center gap-1.5 font-mono text-sm tracking-wide uppercase">
      {icon}
      {children}
    </span>
  )
}

export function CodeGraphTab({
  repoId,
  focusSymbolId,
  focusFile,
  onRepoChange,
  onOpenRepositories,
}: {
  repoId: string | undefined
  /** Graph node to select on arrival — a Code Wiki deep link. */
  focusSymbolId?: string
  /** File to open in the inspector on arrival — a Code Wiki deep link. */
  focusFile?: string
  onRepoChange: (id: string) => void
  onOpenRepositories: () => void
}) {
  const repos = useDemoCodeRepos()
  const repo =
    repos.find((r) => r.id === repoId) ??
    repos.find((r) => r.status === "ready") ??
    repos.find(() => true)
  const graph = useDemoCodeGraph(repo?.id)

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [colorBy, setColorBy] = useState<"community" | "kind">("community")
  const [depth, setDepth] = useState<DepthValue>("all")
  const [zoom, setZoom] = useState(1)
  const [blast, setBlast] = useState<BlastRadius | null>(null)
  const [activeCommunity, setActiveCommunity] = useState<string | null>(null)
  const [activeProcess, setActiveProcess] = useState<string | null>(null)
  const [mermaidProcess, setMermaidProcess] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [copied, setCopied] = useState(false)
  const [leftTab, setLeftTab] = useState("explorer")
  const [hiddenKinds, setHiddenKinds] = useState<ReadonlySet<CodeNodeKind>>(
    new Set(),
  )
  const [openFiles, setOpenFiles] = useState<OpenCodeFile[]>([])
  const [inspectorCollapsed, setInspectorCollapsed] = useState(false)
  const [explorerCollapsed, setExplorerCollapsed] = useState(false)
  const wide = useMediaQuery("(min-width: 1024px)")

  // Explorer (224px), a docked inspector and the analysis rail are all
  // fixed-width columns, so with all three open the canvas shrinks to about a
  // quarter of the row. When the inspector opens, the Explorer folds to a
  // strip; when it closes (or every file floats), the Explorer comes back.
  // The reader can still expand the Explorer by hand at any time.
  const inspectorShowing =
    openFiles.some((f) => f.pinned) && !inspectorCollapsed
  const prevInspectorShowing = useRef(inspectorShowing)
  useEffect(() => {
    if (prevInspectorShowing.current === inspectorShowing) return
    prevInspectorShowing.current = inspectorShowing
    setExplorerCollapsed(inspectorShowing)
  }, [inspectorShowing])
  const explorerStrip = wide && explorerCollapsed

  // The canvas column's width bounds a floating file panel: it is scoped to
  // that column, and a 420px panel in a narrower column would spill over the
  // analysis rail and cover its controls.
  const [canvasEl, setCanvasEl] = useState<HTMLDivElement | null>(null)
  const [canvasWidth, setCanvasWidth] = useState<number | null>(null)
  useEffect(() => {
    if (!canvasEl) return
    const measure = () => setCanvasWidth(canvasEl.clientWidth)
    measure()
    if (typeof ResizeObserver === "undefined") return
    const observer = new ResizeObserver(measure)
    observer.observe(canvasEl)
    return () => observer.disconnect()
  }, [canvasEl])

  // Selection, analysis, camera, and open source files are per-repo state.
  useEffect(() => {
    setSelectedId(null)
    setBlast(null)
    setActiveCommunity(null)
    setActiveProcess(null)
    setZoom(1)
    setDepth("all")
    setOpenFiles([])
    setHiddenKinds(new Set())
  }, [repo?.id])

  // Arriving from a Code Wiki reference: select the named symbol (or open
  // the named file) so the link lands on the thing the prose was about.
  useEffect(() => {
    if (!graph) return
    const node = focusSymbolId
      ? graph.nodes.find((n) => n.id === focusSymbolId)
      : focusFile
        ? graph.nodes.find((n) => n.kind === "file" && n.file === focusFile)
        : undefined
    const path = node?.file ?? focusFile
    if (!path) return
    setSelectedId(node?.id ?? null)
    setInspectorCollapsed(false)
    setOpenFiles((prev) =>
      prev.some((f) => f.path === path)
        ? prev
        : [...prev, { path, pinned: true, collapsed: false }],
    )
  }, [graph, focusSymbolId, focusFile])

  const visibleIds = useMemo(() => {
    if (!graph || !selectedId || depth === "all") return null
    return neighborhoodWithin(graph.edges, selectedId, Number(depth))
  }, [graph, selectedId, depth])

  const processIds = useMemo(() => {
    const process = graph?.processes.find((p) => p.id === activeProcess)
    return process ? new Set(process.steps) : null
  }, [graph, activeProcess])

  const kindCounts = useMemo(() => {
    const counts = new Map<CodeNodeKind, number>()
    for (const n of graph?.nodes ?? []) {
      counts.set(n.kind, (counts.get(n.kind) ?? 0) + 1)
    }
    return counts
  }, [graph])

  const communityCounts = useMemo(() => {
    const counts = new Map<string, number>()
    for (const n of graph?.nodes ?? []) {
      counts.set(n.community, (counts.get(n.community) ?? 0) + 1)
    }
    return counts
  }, [graph])

  if (!repo) return null
  const selectedNode = graph?.nodes.find((n) => n.id === selectedId)

  const openFile = (path: string) => {
    setOpenFiles((prev) =>
      prev.some((f) => f.path === path)
        ? prev.map((f) => (f.path === path ? { ...f, collapsed: false } : f))
        : [...prev, { path, pinned: true, collapsed: false }],
    )
    setInspectorCollapsed(false)
  }

  // Selecting a symbol — from the graph, the explorer, or the source itself
  // — is also what opens its file in the inspector.
  const selectNode = (id: string | null) => {
    setSelectedId(id)
    setBlast(null)
    if (!id) return
    const node = graph?.nodes.find((n) => n.id === id)
    if (node) openFile(node.file)
  }

  const patchFile = (path: string, patch: Partial<OpenCodeFile>) =>
    setOpenFiles((prev) =>
      prev.map((f) => (f.path === path ? { ...f, ...patch } : f)),
    )

  // The canvas centres on the selected node itself; focusing only zooms in.
  const focusSelected = () => {
    if (selectedId) setZoom(1.6)
  }

  const copyMermaid = (text: string) => {
    void navigator.clipboard
      ?.writeText(text)
      .catch(() => undefined)
      .finally(() => {
        setCopied(true)
        window.setTimeout(() => setCopied(false), 1500)
      })
  }

  const currentPhase = repo.phases?.find((p) => p.state === "current")
  const progressLabel = phaseProgressLabel(repo.phases)

  const toolbar = (
    <div className="border-border bg-card flex flex-wrap items-center gap-2.5 border-b p-2.5">
      <Select value={repo.id} onValueChange={onRepoChange}>
        <SelectTrigger
          className="w-auto max-w-[20rem] min-w-56"
          aria-label="Repository"
          title={repo.name}
        >
          <SelectValue>
            <span className="flex min-w-0 items-center gap-2">
              <FolderGit2 aria-hidden className="h-3.5 w-3.5 shrink-0" />
              <span
                className={cn(
                  "h-2 w-2 shrink-0 rounded-full",
                  STATUS_DOT[repo.status],
                )}
              />
              <span className="min-w-0 truncate">{repo.name}</span>
            </span>
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {repos.map((r) => (
            <SelectItem key={r.id} value={r.id}>
              {r.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {repo.status === "stale" && repo.stale && (
        <span className="border-warning-edge/60 bg-warning-solid/10 text-warning-text inline-flex items-center gap-1.5 rounded-full border border-dashed px-2.5 py-0.5 text-sm">
          stale — showing last good graph ({repo.stale.last_good_head})
        </span>
      )}
      <span className="flex-1" />
      <RepoStatusChip status={repo.status} />
    </div>
  )

  // Non-populated repo states — each failure cause looks different (honesty).
  if (repo.status === "indexing") {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        {toolbar}
        <div className="flex-1 space-y-3 p-8">
          <p className="text-sm font-semibold">
            Building the code graph for {repo.name}
          </p>
          <div className="text-info-text flex flex-wrap items-center gap-2.5 font-mono text-sm">
            {progressLabel
              ? `${progressLabel} · ${currentPhase?.label ?? ""}`
              : "starting…"}
            <span className="bg-muted h-1.5 w-56 overflow-hidden rounded-full">
              <span
                className="bg-info-solid block h-full rounded-full"
                style={{ width: `${phaseProgressPercent(repo.phases)}%` }}
              />
            </span>
          </div>
        </div>
      </div>
    )
  }

  if (repo.status === "error") {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        {toolbar}
        <div className="flex-1 p-8">
          <div className="border-destructive-edge/50 bg-destructive-solid/8 flex max-w-xl gap-2.5 rounded-md border p-3.5">
            <TriangleAlert
              aria-hidden
              className="text-destructive-text h-4.5 w-4.5 shrink-0"
            />
            <div className="space-y-1.5 text-sm">
              <p className="font-semibold">Failed to index {repo.name}</p>
              <p className="text-muted-foreground font-mono">
                {repo.error?.message}
              </p>
              <Button
                variant="outline"
                className="rounded-full"
                onClick={onOpenRepositories}
              >
                Fix on Repositories →
              </Button>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!graph) {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        {toolbar}
        <EmptyState
          kind="empty"
          icon={FolderGit2}
          title="No graph yet"
          description={`${repo.name} has not been indexed yet.`}
          action={
            <Button variant="outline" onClick={onOpenRepositories}>
              Open reindex dialog on Repositories →
            </Button>
          }
        />
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {toolbar}

      {/* controls row */}
      <div className="border-border bg-card flex flex-wrap items-center gap-x-4 gap-y-2 border-b p-2.5">
        <Input
          prefix={<Search aria-hidden className="h-4 w-4" />}
          placeholder="Filter files & symbols…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          groupClassName="w-56"
          aria-label="Filter the explorer by file or symbol name"
        />
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground font-mono text-xs uppercase">
            colour by
          </span>
          <ToggleGroup
            type="single"
            size="sm"
            value={colorBy}
            onValueChange={(value) => {
              if (value === "community" || value === "kind") setColorBy(value)
            }}
            aria-label="Colour nodes by"
          >
            <ToggleGroupItem value="kind" aria-label="Colour by type">
              <Tag aria-hidden className="h-3.5 w-3.5" />
            </ToggleGroupItem>
            <ToggleGroupItem value="community" aria-label="Colour by community">
              <Boxes aria-hidden className="h-3.5 w-3.5" />
            </ToggleGroupItem>
          </ToggleGroup>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground font-mono text-xs uppercase">
            camera
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              aria-label="Zoom in"
              onClick={() => setZoom((z) => Math.min(z * 1.25, 3))}
            >
              <ZoomIn aria-hidden className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              aria-label="Zoom out"
              onClick={() => setZoom((z) => Math.max(z / 1.25, 0.6))}
            >
              <ZoomOut aria-hidden className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              aria-label="Fit to view"
              onClick={() => setZoom(1)}
            >
              <Maximize aria-hidden className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              aria-label="Focus selected node"
              disabled={!selectedId}
              onClick={focusSelected}
            >
              <Crosshair aria-hidden className="h-3.5 w-3.5" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              aria-label="Clear selection"
              disabled={!selectedId}
              onClick={() => selectNode(null)}
            >
              <X aria-hidden className="h-3.5 w-3.5" />
            </Button>
          </div>
        </div>
        <div className="flex flex-col gap-0.5">
          {/* Depth is measured from the selected node, so without one it
              would be a pressed control with no effect: disabled until a
              node is selected, like Focus and Clear beside it. */}
          <span
            className="text-muted-foreground font-mono text-xs uppercase"
            title={selectedId ? undefined : "Select a node to filter by depth"}
          >
            depth from selected
          </span>
          <ToggleGroup
            type="single"
            size="sm"
            value={depth}
            disabled={!selectedId}
            onValueChange={(value) => {
              if (DEPTHS.includes(value as DepthValue))
                setDepth(value as DepthValue)
            }}
            aria-label="Neighbourhood depth (from the selected node)"
          >
            {DEPTHS.map((d) => (
              <ToggleGroupItem key={d} value={d} className="font-mono">
                {d === "all" ? "All" : d}
              </ToggleGroupItem>
            ))}
          </ToggleGroup>
        </div>
        <span className="text-muted-foreground ml-auto font-mono text-sm whitespace-nowrap">
          <b className="text-primary-text font-semibold">
            {graph.nodes.length}
          </b>{" "}
          nodes ·{" "}
          <b className="text-primary-text font-semibold">
            {graph.edges.length}
          </b>{" "}
          edges
        </span>
      </div>

      {/* body — explorer/filters rail, code inspector, canvas, analysis.
          From lg up the row fills the full-bleed page and each column
          scrolls on its own. Below lg the sections stack at their natural
          (or a fixed) height and the page scrolls: squeezing four stacked
          sections into one viewport left the canvas 0px tall, painting over
          the analysis rail. */}
      <div className="flex flex-col lg:min-h-0 lg:flex-1 lg:flex-row">
        {/* explorer / filters */}
        {explorerStrip ? (
          <div className="border-border bg-card flex w-9 shrink-0 flex-col items-center gap-2 border-r py-2">
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              aria-label="Expand explorer"
              onClick={() => setExplorerCollapsed(false)}
            >
              <PanelLeftOpen aria-hidden className="h-3.5 w-3.5" />
            </Button>
            <span
              className="text-muted-foreground font-mono text-xs tracking-widest uppercase"
              style={{ writingMode: "vertical-rl" }}
            >
              {leftTab === "filters" ? "filters" : "explorer"}
            </span>
          </div>
        ) : (
          <Tabs
            variant="underline"
            value={leftTab}
            onValueChange={setLeftTab}
            className="border-border bg-card flex h-72 w-full min-w-0 shrink-0 flex-col border-b lg:h-auto lg:min-h-0 lg:w-56 lg:border-r lg:border-b-0"
          >
            <div className="border-border flex shrink-0 items-center border-b px-1">
              <TabsList className="min-w-0 flex-1">
                <TabsTrigger value="explorer">Explorer</TabsTrigger>
                <TabsTrigger value="filters">Filters</TabsTrigger>
              </TabsList>
              <Button
                variant="ghost"
                size="icon"
                className="hidden h-6 w-6 shrink-0 lg:inline-flex"
                aria-label="Collapse explorer"
                onClick={() => setExplorerCollapsed(true)}
              >
                <PanelLeftClose aria-hidden className="h-3.5 w-3.5" />
              </Button>
            </div>
            <TabsContent
              value="explorer"
              className="flex min-h-0 flex-1 flex-col data-[state=inactive]:hidden"
            >
              <CodeExplorer
                files={repo.files}
                graph={graph}
                query={search}
                activePath={selectedNode?.file ?? null}
                selectedNodeId={selectedId}
                onOpenFile={openFile}
                onSelectSymbol={selectNode}
              />
            </TabsContent>
            <TabsContent
              value="filters"
              className="flex min-h-0 flex-1 flex-col data-[state=inactive]:hidden"
            >
              <CodeFilters
                counts={kindCounts}
                hidden={hiddenKinds}
                onToggle={(kind) =>
                  setHiddenKinds((prev) => {
                    const next = new Set(prev)
                    if (next.has(kind)) next.delete(kind)
                    else next.add(kind)
                    return next
                  })
                }
                onReset={() => setHiddenKinds(new Set())}
              />
            </TabsContent>
          </Tabs>
        )}

        {/* code inspector — opened files stack top-to-bottom */}
        {openFiles.length > 0 && (
          <CodeInspector
            files={openFiles}
            graph={graph}
            activeSymbolId={selectedId}
            collapsed={inspectorCollapsed}
            onToggleCollapsedPanel={() => setInspectorCollapsed((v) => !v)}
            onTogglePinned={(path) =>
              patchFile(path, {
                pinned: !openFiles.find((f) => f.path === path)?.pinned,
              })
            }
            onToggleCollapsed={(path) =>
              patchFile(path, {
                collapsed: !openFiles.find((f) => f.path === path)?.collapsed,
              })
            }
            onClose={(path) =>
              setOpenFiles((prev) => prev.filter((f) => f.path !== path))
            }
            onCloseAll={() => setOpenFiles([])}
            onSelectSymbol={selectNode}
          />
        )}

        {/* canvas */}
        {/* `overflow-hidden`: floating file panels are scoped to this column
            and must never paint over the analysis rail beside it. */}
        <div
          ref={setCanvasEl}
          className="relative flex h-[min(70vh,30rem)] min-w-0 shrink-0 flex-col overflow-hidden lg:h-auto lg:min-h-0 lg:flex-1 lg:shrink"
        >
          <div className="relative min-h-0 min-w-0 flex-1 lg:min-h-64">
            <CodeGlowCanvas
              graph={graph}
              colorBy={colorBy}
              selectedId={selectedId}
              onSelect={selectNode}
              visibleIds={visibleIds}
              hiddenKinds={hiddenKinds}
              blastIds={blast ? new Set(blast.affected.map((a) => a.id)) : null}
              highlightCommunity={activeCommunity}
              processIds={processIds}
              zoom={zoom}
            />
          </div>
          {openFiles
            .filter((f) => !f.pinned)
            .map((file, index) => (
              <FloatingFilePanel
                key={file.path}
                file={file}
                index={index}
                boundsWidth={canvasWidth}
                graph={graph}
                activeSymbolId={selectedId}
                onTogglePinned={(path) => patchFile(path, { pinned: true })}
                onToggleCollapsed={(path) =>
                  patchFile(path, { collapsed: !file.collapsed })
                }
                onClose={(path) =>
                  setOpenFiles((prev) => prev.filter((f) => f.path !== path))
                }
                onSelectSymbol={selectNode}
              />
            ))}
          <div className="border-border bg-card text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 border-t px-2.5 py-1.5 text-sm">
            {colorBy === "community" ? (
              graph.communities.map((c) => (
                <span key={c.id} className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2 w-2 rounded-[2px]"
                    style={{ background: chartVar(c.chart) }}
                  />
                  community: {c.label}
                </span>
              ))
            ) : (
              <>
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2 w-2 rounded-[2px]"
                    style={{ background: chartVar(1) }}
                  />
                  structural
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2 w-2 rounded-[2px]"
                    style={{ background: chartVar(2) }}
                  />
                  types
                </span>
                <span className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2 w-2 rounded-[2px]"
                    style={{ background: chartVar(3) }}
                  />
                  callables
                </span>
              </>
            )}
            <span className="inline-flex items-center gap-1.5">
              <span className="border-primary h-2.5 w-2.5 rounded-full border-[1.6px]" />
              selected
            </span>
            <span className="inline-flex items-center gap-1.5">
              <span className="border-destructive-edge h-2.5 w-2.5 rounded-full border-[1.6px] border-dashed" />
              blast-radius affected
            </span>
          </div>
        </div>

        {/* analysis panel */}
        <div className="border-border bg-card flex w-full min-w-0 shrink-0 flex-col border-t lg:min-h-0 lg:w-60 lg:overflow-y-auto lg:border-t-0 lg:border-l">
          <div className="border-border space-y-1.5 border-b p-2.5">
            <SectionTitle icon={<Crosshair aria-hidden className="h-3 w-3" />}>
              Selected symbol
            </SectionTitle>
            {selectedNode ? (
              <p className="font-mono text-sm font-semibold">
                {selectedNode.name}
                <span className="text-muted-foreground block text-sm font-normal">
                  {selectedNode.kind} · {selectedNode.file}
                </span>
              </p>
            ) : (
              <p className="text-muted-foreground text-sm">
                Click a node or a symbol row to inspect it.
              </p>
            )}
          </div>

          <div className="border-border space-y-2 border-b p-2.5">
            <SectionTitle icon={<Share2 aria-hidden className="h-3 w-3" />}>
              Blast radius
            </SectionTitle>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                className="border-primary/50 text-primary-text bg-primary/8 rounded-full"
                disabled={!selectedId}
                onClick={() => {
                  if (selectedId)
                    setBlast(computeBlastRadius(graph, selectedId))
                }}
              >
                Run Blast Radius
              </Button>
              {blast && (
                <button
                  type="button"
                  className="text-muted-foreground font-mono text-sm"
                  onClick={() => setBlast(null)}
                >
                  Clear
                </button>
              )}
            </div>
            {blast ? (
              <>
                <div className="flex gap-1">
                  {(["low", "medium", "high", "critical"] as const).map(
                    (bucket) => (
                      <span
                        key={bucket}
                        className={cn(
                          "border-border bg-muted text-muted-foreground flex-1 rounded-sm border px-0.5 py-0.5 text-center font-mono text-xs uppercase",
                          blast.risk === bucket &&
                            "border-destructive-edge/55 bg-destructive-solid/12 text-destructive-text font-semibold",
                        )}
                      >
                        {bucket}
                      </span>
                    ),
                  )}
                </div>
                <p className="text-sm">
                  <b className="text-destructive-text font-mono">{blast.total}</b>{" "}
                  affected transitively
                </p>
                {blast.depths.map((d) => {
                  const max = Math.max(1, ...blast.depths.map((x) => x.count))
                  return (
                    <div
                      key={d.label}
                      className="text-muted-foreground flex items-center gap-1.5 font-mono text-sm"
                    >
                      <span className="w-7 shrink-0">{d.label}</span>
                      <span className="bg-muted h-1.5 flex-1 overflow-hidden rounded-full">
                        <span
                          className="bg-destructive-solid/65 block h-full"
                          style={{ width: `${(d.count / max) * 100}%` }}
                        />
                      </span>
                      <span className="w-4 shrink-0 text-right">{d.count}</span>
                    </div>
                  )
                })}
                {blast.affected.slice(0, 3).map((a) => (
                  // Name over file: side by side, a 240px rail cut both.
                  <p
                    key={a.id}
                    className="min-w-0 text-sm"
                    title={`${a.name} · ${a.file} · depth ${a.depth}`}
                  >
                    <span className="block truncate">{a.name}</span>
                    <span className="text-muted-foreground flex min-w-0 font-mono text-xs">
                      <span className="min-w-0 truncate">
                        {a.file.split("/").pop()}
                      </span>
                      <span className="shrink-0">&nbsp;· d{a.depth}</span>
                    </span>
                  </p>
                ))}
                {blast.affected.length > 3 && (
                  <p className="text-muted-foreground font-mono text-sm">
                    +{blast.affected.length - 3} more
                  </p>
                )}
              </>
            ) : (
              <p className="text-muted-foreground text-sm">
                {selectedId
                  ? "Run to see what transitively depends on the selected symbol."
                  : "Select a symbol first."}
              </p>
            )}
          </div>

          <div className="border-border space-y-1 border-b p-2.5">
            <SectionTitle icon={<Workflow aria-hidden className="h-3 w-3" />}>
              Processes
            </SectionTitle>
            {/* The label owns line one and the step count sits under it, so
                three processes never truncate to the same "memor…" stub; the
                Mermaid export is an icon button with a tooltip. */}
            <TooltipProvider delayDuration={150}>
              {graph.processes.map((process) => (
                <div
                  key={process.id}
                  className={cn(
                    "flex items-start gap-1.5 rounded-sm px-1 py-0.5",
                    activeProcess === process.id && "bg-primary/10",
                  )}
                >
                  <button
                    type="button"
                    aria-pressed={activeProcess === process.id}
                    className="flex min-w-0 flex-1 items-start gap-1.5 text-left text-sm"
                    onClick={() =>
                      setActiveProcess((cur) =>
                        cur === process.id ? null : process.id,
                      )
                    }
                  >
                    <Play
                      aria-hidden
                      className="text-muted-foreground mt-1 h-3 w-3 shrink-0"
                    />
                    <span className="min-w-0 flex-1">
                      <span className="block break-words">{process.label}</span>
                      <span className="text-muted-foreground block font-mono text-xs">
                        {process.steps.length} steps
                      </span>
                    </span>
                  </button>
                  <Tooltip>
                    <TooltipTrigger
                      aria-label={`Mermaid export for ${process.label}`}
                      className="text-muted-foreground hover:text-foreground focus-visible:ring-ring mt-0.5 inline-flex h-6 w-6 shrink-0 items-center justify-center rounded-sm focus-visible:ring-2 focus-visible:outline-none"
                      onClick={() => setMermaidProcess(process.id)}
                    >
                      <FileCode2 aria-hidden className="h-3.5 w-3.5" />
                    </TooltipTrigger>
                    <TooltipContent side="left">Mermaid export</TooltipContent>
                  </Tooltip>
                </div>
              ))}
            </TooltipProvider>
          </div>

          <div className="space-y-1 p-2.5">
            <SectionTitle icon={<Boxes aria-hidden className="h-3 w-3" />}>
              Community navigator
            </SectionTitle>
            {graph.communities.map((community) => (
              <button
                key={community.id}
                type="button"
                className={cn(
                  "flex w-full items-center gap-1.5 rounded-sm px-1 py-0.5 text-left text-sm",
                  activeCommunity === community.id && "bg-primary/10",
                )}
                onClick={() =>
                  setActiveCommunity((cur) =>
                    cur === community.id ? null : community.id,
                  )
                }
              >
                <span
                  className="h-2 w-2 shrink-0 rounded-full"
                  style={{ background: chartVar(community.chart) }}
                />
                <span className="min-w-0 flex-1 truncate">
                  {community.label}
                </span>
                <span className="text-muted-foreground shrink-0 font-mono text-xs">
                  {communityCounts.get(community.id) ?? 0}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* process detail + Mermaid export */}
      <Dialog
        open={mermaidProcess !== null}
        onOpenChange={(open) => {
          if (!open) setMermaidProcess(null)
        }}
      >
        <DialogContent className="max-w-lg">
          {(() => {
            const process = graph.processes.find((p) => p.id === mermaidProcess)
            if (!process) return null
            const mermaid = mermaidForProcess(process, graph)
            return (
              <>
                <DialogHeader>
                  <DialogTitle>
                    {process.label} · {process.steps.length} steps
                  </DialogTitle>
                </DialogHeader>
                <pre className="bg-background border-border text-muted-foreground overflow-x-auto rounded-md border p-3 font-mono text-sm leading-relaxed whitespace-pre">
                  {mermaid}
                </pre>
                <DialogFooter>
                  <Button
                    variant="outline"
                    onClick={() => copyMermaid(mermaid)}
                  >
                    <Copy aria-hidden className="mr-1 h-3.5 w-3.5" />
                    {copied ? "Copied" : "Copy Mermaid"}
                  </Button>
                </DialogFooter>
              </>
            )
          })()}
        </DialogContent>
      </Dialog>
    </div>
  )
}
