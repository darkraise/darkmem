import { useEffect, useMemo, useState } from "react"
import {
  Boxes,
  ChevronsLeftRight,
  Copy,
  Crosshair,
  FolderGit2,
  ListTree,
  Maximize,
  Orbit,
  Pause,
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
import { Kbd } from "darkraise-ui/components/kbd"
import {
  CommandDialog,
  Command,
  CommandInput,
  CommandList,
  CommandEmpty,
  CommandItem,
} from "darkraise-ui/components/command"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
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
import { EmptyState } from "darkraise-ui/components/empty-state"
import { cn } from "darkraise-ui/lib"
import { useDemoCodeRepos, useDemoCodeGraph } from "@/demo/hooks"
import {
  computeBlastRadius,
  layoutGraph,
  mermaidForProcess,
  neighborhoodWithin,
  type BlastRadius,
  type GraphLayoutMode,
  type Point,
} from "@/demo/explore"
import type { CodeNodeKind, DemoRepo } from "@/demo/types"
import { CANVAS_H, CANVAS_W, chartVar, CodeCanvas } from "./code-canvas"
import { RepoStatusChip } from "./repo-status-chip"

const LAYOUTS: GraphLayoutMode[] = ["force", "tree", "circles"]
const DEPTHS = ["all", "1", "2", "3"] as const
type DepthValue = (typeof DEPTHS)[number]

const KIND_CHART: Record<CodeNodeKind, number> = {
  file: 1,
  module: 1,
  class: 2,
  method: 3,
  function: 3,
}

const STATUS_DOT: Record<DemoRepo["status"], string> = {
  ready: "bg-success",
  indexing: "bg-info",
  stale: "bg-warning",
  error: "bg-destructive",
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
  onRepoChange,
  onOpenRepositories,
}: {
  repoId: string | undefined
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
  const [layout, setLayout] = useState<GraphLayoutMode>("force")
  const [colorBy, setColorBy] = useState<"community" | "kind">("community")
  const [depth, setDepth] = useState<DepthValue>("all")
  const [playing, setPlaying] = useState(true)
  const [zoom, setZoom] = useState(1)
  const [center, setCenter] = useState<Point | null>(null)
  const [blast, setBlast] = useState<BlastRadius | null>(null)
  const [activeCommunity, setActiveCommunity] = useState<string | null>(null)
  const [activeProcess, setActiveProcess] = useState<string | null>(null)
  const [mermaidProcess, setMermaidProcess] = useState<string | null>(null)
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [search, setSearch] = useState("")
  const [copied, setCopied] = useState(false)

  // Selection, analysis, and camera are per-repo state.
  useEffect(() => {
    setSelectedId(null)
    setBlast(null)
    setActiveCommunity(null)
    setActiveProcess(null)
    setZoom(1)
    setCenter(null)
    setDepth("all")
  }, [repo?.id])

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") {
        e.preventDefault()
        setPaletteOpen((v) => !v)
      }
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [])

  const positions = useMemo(
    () =>
      graph
        ? layoutGraph(
            graph.nodes.map((n) => ({ id: n.id, group: n.community })),
            graph.edges,
            layout,
            CANVAS_W,
            CANVAS_H,
          )
        : {},
    [graph, layout],
  )

  const visibleIds = useMemo(() => {
    if (!graph || !selectedId || depth === "all") return null
    return neighborhoodWithin(graph.edges, selectedId, Number(depth))
  }, [graph, selectedId, depth])

  const processIds = useMemo(() => {
    const process = graph?.processes.find((p) => p.id === activeProcess)
    return process ? new Set(process.steps) : null
  }, [graph, activeProcess])

  const filteredNodes = useMemo(() => {
    if (!graph) return []
    const q = search.trim().toLowerCase()
    if (q === "") return graph.nodes
    return graph.nodes.filter((n) => n.name.toLowerCase().includes(q))
  }, [graph, search])

  const communityCounts = useMemo(() => {
    const counts = new Map<string, number>()
    for (const n of graph?.nodes ?? []) {
      counts.set(n.community, (counts.get(n.community) ?? 0) + 1)
    }
    return counts
  }, [graph])

  if (!repo) return null
  const selectedNode = graph?.nodes.find((n) => n.id === selectedId)

  const selectNode = (id: string | null) => {
    setSelectedId(id)
    setBlast(null)
  }

  const focusSelected = () => {
    if (!selectedId) return
    const pos = positions[selectedId]
    if (pos) {
      setCenter(pos)
      setZoom(1.6)
    }
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

  const donePhases =
    repo.phases?.filter((p) => p.state === "done").length ?? 0
  const activePhases =
    repo.phases?.filter((p) => p.state !== "skipped").length ?? 0
  const currentPhase = repo.phases?.find((p) => p.state === "current")

  const toolbar = (
    <div className="border-border bg-card flex flex-wrap items-center gap-2.5 border-b p-2.5">
      <Select value={repo.id} onValueChange={onRepoChange}>
        <SelectTrigger className="w-56" aria-label="Repository">
          <SelectValue>
            <span className="flex items-center gap-2">
              <FolderGit2 aria-hidden className="h-3.5 w-3.5" />
              <span
                className={cn(
                  "h-2 w-2 shrink-0 rounded-full",
                  STATUS_DOT[repo.status],
                )}
              />
              {repo.name}
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
      <span className="border-border text-muted-foreground inline-flex items-center gap-1.5 rounded-full border border-dashed px-2.5 py-0.5 font-mono text-sm uppercase">
        <ChevronsLeftRight aria-hidden className="h-3 w-3" />
        scope: repository, not project
      </span>
      {repo.status === "stale" && repo.stale && (
        <span className="border-warning/60 bg-warning/10 text-warning inline-flex items-center gap-1.5 rounded-full border border-dashed px-2.5 py-0.5 text-sm">
          serving last-good graph ({repo.stale.last_good_head}) — stale
        </span>
      )}
      <span className="flex-1" />
      <RepoStatusChip status={repo.status} />
    </div>
  )

  // Non-populated repo states — each failure cause looks different (honesty).
  if (repo.status === "indexing") {
    return (
      <div className="border-border overflow-hidden rounded-lg border">
        {toolbar}
        <div className="space-y-3 p-8">
          <p className="text-sm font-semibold">
            Building the code graph for {repo.name}
          </p>
          <div className="text-info flex items-center gap-2.5 font-mono text-sm">
            {currentPhase
              ? `phase ${String(currentPhase.n).padStart(2, "0")} — ${donePhases + 1} of ${activePhases} phases`
              : "starting…"}
            <span className="bg-muted h-1.5 w-56 overflow-hidden rounded-full">
              <span
                className="bg-info block h-full rounded-full"
                style={{
                  width: `${Math.round((donePhases / Math.max(activePhases, 1)) * 100)}%`,
                }}
              />
            </span>
          </div>
          <p className="text-muted-foreground max-w-xl text-sm">
            The layout switcher, canvas, and analysis panel have nothing to
            render until this run completes — the graph is not empty, it is{" "}
            <b className="text-foreground">not built yet</b>. Community and
            process detection run after structure and cross-file binding, so
            the community navigator and Processes panel populate last.
          </p>
        </div>
      </div>
    )
  }

  if (repo.status === "error") {
    return (
      <div className="border-border overflow-hidden rounded-lg border">
        {toolbar}
        <div className="p-8">
          <div className="border-destructive/50 bg-destructive/8 flex max-w-xl gap-2.5 rounded-md border p-3.5">
            <TriangleAlert
              aria-hidden
              className="text-destructive h-4.5 w-4.5 shrink-0"
            />
            <div className="space-y-1.5 text-sm">
              <p className="font-semibold">Failed to index {repo.name}</p>
              <p className="text-muted-foreground font-mono">
                {repo.error?.message}
              </p>
              <Button
                variant="outline"
                size="sm"
                className="rounded-full"
                onClick={onOpenRepositories}
              >
                Fix on Repositories →
              </Button>
            </div>
          </div>
          <p className="text-muted-foreground mt-3 max-w-xl text-sm">
            With no successful index ever committed for this repo, there is
            nothing to fall back to — the failure is the whole story. A
            fail-stale banner over a last-good graph is the Repositories
            surface's concern.
          </p>
        </div>
      </div>
    )
  }

  if (!graph) {
    return (
      <div className="border-border overflow-hidden rounded-lg border">
        {toolbar}
        <EmptyState
          className="py-12"
          icon={<FolderGit2 aria-hidden className="h-6 w-6" />}
          title="No graph yet"
          description={`${repo.name} is registered but has never been indexed — no symbols, no edges, no communities or processes to browse. Index it from Repositories to build the graph.`}
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
    <div className="border-border overflow-hidden rounded-lg border">
      {toolbar}

      {/* controls row */}
      <div className="border-border bg-card flex flex-wrap items-center gap-x-4 gap-y-2 border-b p-2.5">
        <Input
          prefix={<Search aria-hidden className="h-4 w-4" />}
          placeholder="Search symbols…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          groupClassName="w-52"
          aria-label="Search symbols"
        />
        <Button
          variant="outline"
          size="sm"
          onClick={() => setPaletteOpen(true)}
        >
          Jump to node <Kbd size="sm">⌘K</Kbd>
        </Button>
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground font-mono text-[10px] uppercase">
            layout
          </span>
          <ToggleGroup
            type="single"
            size="sm"
            value={layout}
            onValueChange={(value) => {
              if (LAYOUTS.includes(value as GraphLayoutMode))
                setLayout(value as GraphLayoutMode)
            }}
            aria-label="Graph layout"
          >
            <ToggleGroupItem value="force" aria-label="Force layout">
              <Share2 aria-hidden className="h-3.5 w-3.5" />
            </ToggleGroupItem>
            <ToggleGroupItem value="tree" aria-label="Tree layout">
              <ListTree aria-hidden className="h-3.5 w-3.5" />
            </ToggleGroupItem>
            <ToggleGroupItem value="circles" aria-label="Circles layout">
              <Orbit aria-hidden className="h-3.5 w-3.5" />
            </ToggleGroupItem>
          </ToggleGroup>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground font-mono text-[10px] uppercase">
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
          <span className="text-muted-foreground font-mono text-[10px] uppercase">
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
              onClick={() => {
                setZoom(1)
                setCenter(null)
              }}
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
            <Button
              variant="outline"
              size="icon"
              className={cn(
                "h-7 w-7",
                playing && "border-primary/50 text-primary bg-primary/10",
              )}
              aria-label={playing ? "Pause layout" : "Play layout"}
              aria-pressed={playing}
              onClick={() => setPlaying((v) => !v)}
            >
              {playing ? (
                <Pause aria-hidden className="h-3.5 w-3.5" />
              ) : (
                <Play aria-hidden className="h-3.5 w-3.5" />
              )}
            </Button>
          </div>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground font-mono text-[10px] uppercase">
            depth
          </span>
          <ToggleGroup
            type="single"
            size="sm"
            value={depth}
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
          <b className="text-primary font-semibold">{graph.nodes.length}</b> n{" "}
          <b className="text-primary font-semibold">{graph.edges.length}</b> e
        </span>
      </div>

      {/* three-panel body */}
      <div className="grid min-h-[300px] grid-cols-1 md:grid-cols-[11rem_minmax(0,1fr)_15rem]">
        {/* symbol browser */}
        <div className="border-border bg-card flex min-w-0 flex-col border-b md:border-r md:border-b-0">
          <span className="border-border text-muted-foreground border-b px-2.5 py-1.5 font-mono text-sm tracking-wide uppercase">
            Symbols
          </span>
          <div className="flex flex-col gap-px overflow-y-auto p-1.5">
            {filteredNodes.length === 0 ? (
              <p className="text-muted-foreground p-2 text-sm">
                No symbol matches "{search}" — the graph itself is unchanged.
              </p>
            ) : (
              filteredNodes.map((node) => (
                <button
                  key={node.id}
                  type="button"
                  onClick={() => selectNode(node.id)}
                  className={cn(
                    "flex items-center gap-1.5 rounded-sm px-1.5 py-1 text-left text-sm",
                    node.id === selectedId
                      ? "bg-primary/12"
                      : "hover:bg-muted/50",
                  )}
                >
                  <span
                    className="h-2 w-2 shrink-0 rounded-[2px]"
                    style={{ background: chartVar(KIND_CHART[node.kind]) }}
                  />
                  <span className="min-w-0 flex-1 truncate font-mono">
                    {node.name}
                  </span>
                  <span className="text-muted-foreground shrink-0 font-mono text-[10px] uppercase">
                    {node.kind}
                  </span>
                </button>
              ))
            )}
          </div>
        </div>

        {/* canvas */}
        <div className="flex min-w-0 flex-col">
          <CodeCanvas
            graph={graph}
            layout={layout}
            colorBy={colorBy}
            selectedId={selectedId}
            onSelect={selectNode}
            visibleIds={visibleIds}
            blastIds={blast ? new Set(blast.affected.map((a) => a.id)) : null}
            highlightCommunity={activeCommunity}
            processIds={processIds}
            playing={playing}
            zoom={zoom}
            center={center}
          />
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
              <span className="border-destructive h-2.5 w-2.5 rounded-full border-[1.6px] border-dashed" />
              blast-radius affected
            </span>
          </div>
        </div>

        {/* analysis panel */}
        <div className="border-border bg-card flex min-w-0 flex-col border-t md:border-t-0 md:border-l">
          <div className="border-border space-y-1.5 border-b p-2.5">
            <SectionTitle
              icon={<Crosshair aria-hidden className="h-3 w-3" />}
            >
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
              Blast radius risk buckets
            </SectionTitle>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                className="border-primary/50 text-primary bg-primary/8 rounded-full"
                disabled={!selectedId}
                onClick={() => {
                  if (selectedId) setBlast(computeBlastRadius(graph, selectedId))
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
                          "border-border bg-muted text-muted-foreground flex-1 rounded-sm border px-0.5 py-0.5 text-center font-mono text-[10px] uppercase",
                          blast.risk === bucket &&
                            "border-destructive/55 bg-destructive/12 text-destructive font-semibold",
                        )}
                      >
                        {bucket}
                      </span>
                    ),
                  )}
                </div>
                <p className="text-sm">
                  <b className="text-destructive font-mono">{blast.total}</b>{" "}
                  affected transitively
                </p>
                {blast.depths.map((d) => {
                  const max = Math.max(
                    1,
                    ...blast.depths.map((x) => x.count),
                  )
                  return (
                    <div
                      key={d.label}
                      className="text-muted-foreground flex items-center gap-1.5 font-mono text-sm"
                    >
                      <span className="w-7 shrink-0">{d.label}</span>
                      <span className="bg-muted h-1.5 flex-1 overflow-hidden rounded-full">
                        <span
                          className="bg-destructive/65 block h-full"
                          style={{ width: `${(d.count / max) * 100}%` }}
                        />
                      </span>
                      <span className="w-4 shrink-0 text-right">
                        {d.count}
                      </span>
                    </div>
                  )
                })}
                {blast.affected.slice(0, 3).map((a) => (
                  <p key={a.id} className="flex items-center gap-1.5 text-sm">
                    {a.name}
                    <span className="text-muted-foreground ml-auto font-mono text-[10px]">
                      {a.file.split("/").pop()} · d{a.depth}
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
            {graph.processes.map((process) => (
              <div
                key={process.id}
                className={cn(
                  "flex items-center gap-1.5 rounded-sm px-1 py-0.5",
                  activeProcess === process.id && "bg-primary/10",
                )}
              >
                <button
                  type="button"
                  className="flex min-w-0 flex-1 items-center gap-1.5 text-left text-sm"
                  onClick={() =>
                    setActiveProcess((cur) =>
                      cur === process.id ? null : process.id,
                    )
                  }
                >
                  <Play
                    aria-hidden
                    className="text-muted-foreground h-3 w-3 shrink-0"
                  />
                  <span className="min-w-0 flex-1 truncate">
                    {process.label}
                  </span>
                  <span className="text-muted-foreground shrink-0 font-mono text-[10px]">
                    {process.steps.length} steps
                  </span>
                </button>
                <button
                  type="button"
                  className="text-muted-foreground hover:text-foreground shrink-0 font-mono text-[10px]"
                  onClick={() => setMermaidProcess(process.id)}
                >
                  mermaid
                </button>
              </div>
            ))}
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
                <span className="text-muted-foreground shrink-0 font-mono text-[10px]">
                  {communityCounts.get(community.id) ?? 0}
                </span>
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* ⌘K node quick-jump */}
      <CommandDialog
        open={paletteOpen}
        onOpenChange={setPaletteOpen}
        title="Jump to node"
      >
        <Command>
          <CommandInput placeholder="Type a symbol name…" />
          <CommandList>
            <CommandEmpty>No matching node.</CommandEmpty>
            {graph.nodes.map((node) => (
              <CommandItem
                key={node.id}
                value={node.name}
                onSelect={() => {
                  selectNode(node.id)
                  setPaletteOpen(false)
                  const pos = positions[node.id]
                  if (pos) {
                    setCenter(pos)
                    setZoom(1.6)
                  }
                }}
              >
                <span
                  className="mr-1.5 h-2 w-2 shrink-0 rounded-[2px]"
                  style={{ background: chartVar(KIND_CHART[node.kind]) }}
                />
                {node.name}
                <span className="text-muted-foreground ml-auto font-mono text-[10px] uppercase">
                  {node.kind}
                </span>
              </CommandItem>
            ))}
          </CommandList>
        </Command>
      </CommandDialog>

      {/* process detail + Mermaid export */}
      <Dialog
        open={mermaidProcess !== null}
        onOpenChange={(open) => {
          if (!open) setMermaidProcess(null)
        }}
      >
        <DialogContent className="max-w-md">
          {(() => {
            const process = graph.processes.find(
              (p) => p.id === mermaidProcess,
            )
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
                <Button
                  variant="outline"
                  size="sm"
                  className="self-end"
                  onClick={() => copyMermaid(mermaid)}
                >
                  <Copy aria-hidden className="mr-1 h-3.5 w-3.5" />
                  {copied ? "Copied" : "Copy Mermaid"}
                </Button>
              </>
            )
          })()}
        </DialogContent>
      </Dialog>
    </div>
  )
}
