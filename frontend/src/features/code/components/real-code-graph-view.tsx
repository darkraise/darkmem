import { useEffect, useMemo, useState } from "react"
import {
  Boxes,
  Copy,
  FolderGit2,
  Search,
  Share2,
  Workflow,
  Network,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
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
import { mermaidForProcess } from "@/demo/explore"
import type { CodeNodeKind } from "@/features/code/types"
import {
  useBlastRadius,
  useCodeFiles,
  useCodeGraph,
  useRepos,
} from "@/hooks/api"
import type { BlastRadiusResult } from "@/hooks/api"
import { chartVar } from "./code-canvas"
import { CodeGlowCanvas } from "./code-glow-canvas"
import { CodeExplorer } from "./code-explorer"
import { CodeFilters } from "./code-filters"
import { CodeGraphLodBanner } from "./code-graph-lod-banner"
import { RealCodeInspector } from "./real-code-inspector"
import { deriveCodeGraph, fileOfGraphKey } from "../lib/graph-derive"

const LEGEND_LIMIT = 12

function SectionTitle({
  icon,
  children,
}: {
  icon: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <span className="text-foreground flex items-center gap-1.5 text-sm font-semibold">
      {icon}
      {children}
    </span>
  )
}

// The real-backend counterpart of the demo Code section's CodeGraphTab.
// Community colouring and the Processes panel with Mermaid export ship in
// real mode too — GET /code/graph/{repo_id} already serves the substrate
// (T1.59 plan §3); graph-derive.ts is the client-side derivation into the
// shape CodeGlowCanvas/CodeExplorer/CodeFilters already render.
export function RealCodeGraphView({
  repoId,
  onRepoChange,
  onOpenRepositories,
}: {
  repoId: string | undefined
  onRepoChange: (id: string) => void
  onOpenRepositories: () => void
}) {
  const { data: repos } = useRepos()
  const repo =
    repos?.find((r) => r.id === repoId) ??
    repos?.find((r) => r.status === "ready") ??
    repos?.find(() => true)

  // The drill-in scope belongs to the repository it was chosen on, so
  // switching repositories never asks the new one for the old one's folder.
  const [scoped, setScoped] = useState<{
    repoId: string
    scope: string | null
  } | null>(null)
  const scope = scoped && scoped.repoId === repo?.id ? scoped.scope : null

  // `auto`: the server folds the graph to files when the scope holds more
  // nodes than the canvas can lay out (CODE_GRAPH_AUTO_LIMIT); a small
  // repository still gets its whole symbol graph.
  const {
    data: raw,
    isLoading: graphLoading,
    isError: graphError,
    isPlaceholderData: graphRefreshing,
  } = useCodeGraph(repo?.id ?? null, { level: "auto", scope })
  const { data: files } = useCodeFiles(repo?.id ?? null)

  const graph = useMemo(
    () => (repo && raw ? deriveCodeGraph(repo.id, raw) : undefined),
    [repo, raw],
  )

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [colorBy, setColorBy] = useState<"community" | "kind">("community")
  const [activeCommunity, setActiveCommunity] = useState<string | null>(null)
  const [activeProcess, setActiveProcess] = useState<string | null>(null)
  const [mermaidProcess, setMermaidProcess] = useState<string | null>(null)
  const [search, setSearch] = useState("")
  const [copied, setCopied] = useState(false)
  const [leftTab, setLeftTab] = useState("explorer")
  const [hiddenKinds, setHiddenKinds] = useState<ReadonlySet<CodeNodeKind>>(
    new Set(),
  )
  const [blast, setBlast] = useState<BlastRadiusResult | null>(null)
  const blastRadius = useBlastRadius()

  useEffect(() => {
    setSelectedId(null)
    setBlast(null)
    setActiveCommunity(null)
    setActiveProcess(null)
  }, [repo?.id])

  const filePaths = useMemo(
    () => (files ?? []).map((f) => f.file_path),
    [files],
  )

  const processIds = useMemo(() => {
    const process = graph?.processes.find((p) => p.id === activeProcess)
    if (!process || !graph) return null
    // On a file-level graph a step is a symbol the canvas does not draw;
    // its file is the node that lights up.
    const drawn = new Set(graph.nodes.map((n) => n.id))
    return new Set(
      process.steps.map((step) => (drawn.has(step) ? step : fileOfGraphKey(step))),
    )
  }, [graph, activeProcess])

  // The filter box narrows the canvas and its counter as well as the
  // explorer: a node stays when its name or its file matches, the same
  // rule the explorer applies to its rows.
  const trimmedSearch = search.trim().toLowerCase()
  const shown = useMemo(() => {
    if (!graph || trimmedSearch === "") return graph
    const nodes = graph.nodes.filter(
      (n) =>
        n.name.toLowerCase().includes(trimmedSearch) ||
        n.file.toLowerCase().includes(trimmedSearch),
    )
    const ids = new Set(nodes.map((n) => n.id))
    const edges = graph.edges.filter(
      (e) => ids.has(e.source) && ids.has(e.target),
    )
    return { ...graph, nodes, edges }
  }, [graph, trimmedSearch])

  const kindCounts = useMemo(() => {
    const counts = new Map<CodeNodeKind, number>()
    for (const n of graph?.nodes ?? []) {
      counts.set(n.kind, (counts.get(n.kind) ?? 0) + 1)
    }
    return counts
  }, [graph])

  // The legend names the largest communities only; on the darkmem repo it
  // listed all 240 and pushed the canvas half off screen.
  const legendCommunities = useMemo(() => {
    const counts = new Map<string, number>()
    for (const n of graph?.nodes ?? []) {
      counts.set(n.community, (counts.get(n.community) ?? 0) + 1)
    }
    return [...(graph?.communities ?? [])]
      .sort((a, b) => (counts.get(b.id) ?? 0) - (counts.get(a.id) ?? 0))
      .slice(0, LEGEND_LIMIT)
  }, [graph])

  const communityCounts = useMemo(() => {
    const counts = new Map<string, number>()
    for (const n of graph?.nodes ?? []) {
      if (n.community === "") continue
      counts.set(n.community, (counts.get(n.community) ?? 0) + 1)
    }
    return counts
  }, [graph])

  if (!repo) {
    return (
      <EmptyState
        kind="empty"
          icon={FolderGit2}
        title="No repositories indexed yet"
        description="Add a repository from Repositories to build a code graph."
        action={
          <Button variant="outline" onClick={onOpenRepositories}>
            Open Repositories →
          </Button>
        }
      />
    )
  }

  const selectedNode = graph?.nodes.find((n) => n.id === selectedId) ?? null

  const selectNode = (id: string | null) => {
    setSelectedId(id)
    setBlast(null)
  }

  const folded = raw?.level === "file"
  const nodeNoun = (count: number) =>
    folded ? (count === 1 ? "file" : "files") : count === 1 ? "node" : "nodes"

  const changeScope = (next: string | null) => {
    setScoped({ repoId: repo.id, scope: next })
    setSelectedId(null)
    setBlast(null)
    setActiveCommunity(null)
    setActiveProcess(null)
  }

  // On the folded graph a file has no symbol rows to expand, so opening one
  // drills into it. Only a drawn file: one that defines no symbol would
  // drill into an empty graph.
  const openFile = (path: string) => {
    if (folded && graph?.nodes.some((n) => n.id === path)) changeScope(path)
  }

  const runBlastRadius = () => {
    if (!selectedId) return
    blastRadius.mutate(
      { symbol_id: selectedId },
      { onSuccess: (result) => setBlast(result) },
    )
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

  const toolbar = (
    <div className="border-border bg-card flex flex-wrap items-center gap-2.5 border-b p-2.5">
      <Select value={repo.id} onValueChange={onRepoChange}>
        <SelectTrigger className="w-56" aria-label="Repository">
          <SelectValue>
            <span className="flex items-center gap-2">
              <FolderGit2 aria-hidden className="h-3.5 w-3.5" />
              {repo.name}
            </span>
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          {repos?.map((r) => (
            <SelectItem key={r.id} value={r.id}>
              {r.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {repo.status === "stale" && (
        <span className="border-warning-edge/60 bg-warning-solid/10 text-warning-text inline-flex items-center gap-1.5 rounded-full border border-dashed px-2.5 py-0.5 text-sm">
          stale — showing last good graph (
          {repo.last_indexed_commit ?? "unknown"})
        </span>
      )}
    </div>
  )

  if (graphLoading) {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        {toolbar}
        <p className="text-muted-foreground p-8 text-sm">Loading graph…</p>
      </div>
    )
  }

  if ((!graph || graph.nodes.length === 0) && scope !== null && !graphError) {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        {toolbar}
        <EmptyState
          kind="empty"
          icon={FolderGit2}
          title={`Nothing to draw in ${scope}`}
          description="No file or symbol under this path is indexed."
          action={
            <Button variant="outline" onClick={() => changeScope(null)}>
              Back to the whole repository
            </Button>
          }
        />
      </div>
    )
  }

  if (!graph || graph.nodes.length === 0) {
    return (
      <div className="flex min-h-0 flex-1 flex-col">
        {toolbar}
        {graphError ? (
          // Not the empty state: it tells the operator this repo was never
          // indexed and sends them to reindex a graph that may well exist.
          <p className="text-destructive-text p-3 text-sm">
            The code graph could not be loaded.
          </p>
        ) : (
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
        )}
      </div>
    )
  }

  return (
    <div className="flex min-h-0 flex-1 flex-col">
      {toolbar}

      <div className="border-border bg-card flex flex-wrap items-center gap-x-4 gap-y-2 border-b p-2.5">
        <Input
          prefix={<Search aria-hidden className="h-4 w-4" />}
          placeholder="Filter files & symbols…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          groupClassName="w-56"
          aria-label="Filter the graph and explorer by file or symbol name"
        />
        <div className="flex flex-col gap-0.5">
          <span className="text-muted-foreground text-xs">Colour by</span>
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
              kind
            </ToggleGroupItem>
            <ToggleGroupItem value="community" aria-label="Colour by community">
              community
            </ToggleGroupItem>
          </ToggleGroup>
        </div>
        <span className="text-muted-foreground ml-auto shrink-0 text-sm whitespace-nowrap">
          {graphRefreshing && "loading… "}
          {shown && shown !== graph
            ? `${shown.nodes.length} of ${graph.nodes.length} ${nodeNoun(graph.nodes.length)} · ${shown.edges.length} of ${graph.edges.length} edges`
            : `${graph.nodes.length} ${nodeNoun(graph.nodes.length)} · ${graph.edges.length} ${graph.edges.length === 1 ? "edge" : "edges"}`}
        </span>
      </div>

      {raw && (
        <CodeGraphLodBanner
          raw={raw}
          selectedFile={
            folded && selectedNode?.kind === "file" ? selectedNode.id : null
          }
          onScope={changeScope}
        />
      )}

      <div className="flex min-h-0 flex-1 flex-col lg:flex-row">
        <Tabs
          variant="underline"
          value={leftTab}
          onValueChange={setLeftTab}
          className="border-border bg-card flex min-h-0 w-full min-w-0 flex-col border-b lg:w-56 lg:shrink-0 lg:border-r lg:border-b-0"
        >
          <TabsList className="border-border shrink-0 border-b px-1">
            <TabsTrigger value="explorer">Explorer</TabsTrigger>
            <TabsTrigger value="filters">Filters</TabsTrigger>
          </TabsList>
          <TabsContent
            value="explorer"
            className="flex min-h-0 flex-1 flex-col data-[state=inactive]:hidden"
          >
            <CodeExplorer
              files={filePaths}
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

        <RealCodeInspector selectedNode={selectedNode} />

        <div className="relative flex min-h-0 min-w-0 flex-1 flex-col">
          <div className="relative min-h-64 min-w-0 flex-1">
            <CodeGlowCanvas
              graph={shown ?? graph}
              colorBy={colorBy}
              selectedId={selectedId}
              onSelect={selectNode}
              visibleIds={null}
              hiddenKinds={hiddenKinds}
              blastIds={
                blast
                  ? new Set(blast.affected.map((a) => a.key ?? a.name))
                  : null
              }
              highlightCommunity={activeCommunity}
              processIds={processIds}
            />
          </div>
          {colorBy === "community" && (
            <div className="border-border bg-card text-muted-foreground flex flex-wrap gap-x-4 gap-y-1 border-t px-2.5 py-1.5 text-sm">
              {legendCommunities.map((c) => (
                <span key={c.id} className="inline-flex items-center gap-1.5">
                  <span
                    className="h-2 w-2 rounded-[2px]"
                    style={{ background: chartVar(c.chart) }}
                  />
                  community: {c.label}
                </span>
              ))}
              {graph.communities.length > legendCommunities.length && (
                <span>
                  +{graph.communities.length - legendCommunities.length} more
                  in the Community navigator
                </span>
              )}
            </div>
          )}
        </div>

        <div className="border-border bg-card flex min-h-0 w-full min-w-0 flex-col overflow-y-auto border-t lg:w-60 lg:shrink-0 lg:border-t-0 lg:border-l">
          <div className="border-border space-y-1.5 border-b p-2.5">
            <SectionTitle icon={<Search aria-hidden className="h-3 w-3" />}>
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
                disabled={!selectedId || blastRadius.isPending}
                onClick={runBlastRadius}
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
            {graph.processes.length === 0 && (
              <EmptyState
                kind="empty"
                icon={Workflow}
                title="No traced processes"
              />
            )}
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
                  <span className="min-w-0 flex-1 truncate">
                    {process.label}
                  </span>
                  <span className="text-muted-foreground shrink-0 font-mono text-xs">
                    {process.steps.length} steps
                  </span>
                </button>
                <button
                  type="button"
                  className="text-muted-foreground hover:text-foreground shrink-0 font-mono text-xs"
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
            {graph.communities.length === 0 && (
              <EmptyState
                kind="empty"
                icon={Network}
                title="No communities detected"
              />
            )}
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

      <Dialog
        open={mermaidProcess !== null}
        onOpenChange={(open) => {
          if (!open) setMermaidProcess(null)
        }}
      >
        <DialogContent className="max-w-md">
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
                <Button
                  variant="outline"
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
