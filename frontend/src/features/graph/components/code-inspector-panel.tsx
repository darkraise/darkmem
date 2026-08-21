import {
  memo,
  useState,
  useMemo,
  useEffect,
  useRef,
  type ReactNode,
} from "react"
import { ChevronRight,
  Diamond,
  FileCode,
} from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Card, CardContent, CardHeader } from "darkraise-ui/components/card"
import { EmptyState } from "@/components/darkmem"
import { Input } from "darkraise-ui/components/input"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "darkraise-ui/components/select"
import { Spinner } from "darkraise-ui/components/spinner"
import {
  Tabs,
  TabsList,
  TabsTrigger,
  TabsContent,
} from "darkraise-ui/components/tabs"
import {
  TreeView,
  TreeViewTree,
  TreeViewBranch,
  TreeViewBranchControl,
  TreeViewBranchIndicator,
  TreeViewBranchText,
  TreeViewBranchContent,
  TreeViewItem,
  type TreeNode,
} from "darkraise-ui/components/tree-view"
import { useCodeSymbols } from "@/hooks/api"
import type { CodeSymbolDetail, CodeSearchResult } from "@/hooks/api"

interface CodeInspectorPanelProps {
  symbolDetail: CodeSymbolDetail | null | undefined
  searchResults: CodeSearchResult[]
  fileList: string[]
  onFileSelect: (id: string) => void
  onSearchResultClick: (result: CodeSearchResult) => void
  repoId: string | null
  nodeColors: Record<string, string>
  symbolKinds: string[]
  onSymbolSelect: (name: string, filePath: string) => void
}

type InspectorTab = "source" | "files" | "results" | "symbols"

const SYMBOLS_PAGE_SIZE = 25
const ALL_KINDS = "__all__"

// Memoized: the tree is the most expensive subtree in the panel, and its
// props are referentially stable across selection/filter changes upstream.
const FileTree = memo(function FileTree({
  files,
  onSelect,
}: {
  files: string[]
  onSelect: (id: string) => void
}) {
  const { nodes, leafIds, branchIds } = useMemo(() => {
    const root: Record<string, Record<string, unknown>> = {}
    for (const fp of files) {
      const parts = fp.replace(/\\/g, "/").split("/")
      let current: Record<string, unknown> = root
      for (const part of parts) {
        if (!current[part]) current[part] = {}
        current = current[part] as Record<string, unknown>
      }
    }
    const leaves = new Set<string>()
    const branches: string[] = []
    const toNodes = (node: Record<string, unknown>, path = ""): TreeNode[] =>
      Object.keys(node)
        .sort()
        .map((key) => {
          const fullPath = path ? `${path}/${key}` : key
          const children = node[key] as Record<string, unknown>
          if (Object.keys(children).length === 0) {
            leaves.add(fullPath)
            return { id: fullPath, name: key }
          }
          branches.push(fullPath)
          return {
            id: fullPath,
            name: key,
            children: toNodes(children, fullPath),
          }
        })
    return { nodes: toNodes(root), leafIds: leaves, branchIds: branches }
  }, [files])

  const [selected, setSelected] = useState<string[]>([])

  const renderNode = (node: TreeNode): ReactNode =>
    node.children && node.children.length > 0 ? (
      <TreeViewBranch key={node.id} value={node.id}>
        <TreeViewBranchControl className="font-mono">
          <TreeViewBranchIndicator>
            <ChevronRight className="h-3.5 w-3.5" />
          </TreeViewBranchIndicator>
          <TreeViewBranchText>{node.name}</TreeViewBranchText>
        </TreeViewBranchControl>
        <TreeViewBranchContent>
          {node.children.map(renderNode)}
        </TreeViewBranchContent>
      </TreeViewBranch>
    ) : (
      <TreeViewItem
        key={node.id}
        value={node.id}
        aria-label={node.id}
        className="font-mono"
        // Re-selecting the current file must still notify the graph —
        // single-select toggleSelected short-circuits on the same id, so
        // onSelectedChange alone would drop the event. Keyboard activation
        // bypasses click entirely, hence the parallel keydown guard.
        onClick={() => {
          if (selected[0] === node.id) onSelect(node.id)
        }}
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && selected[0] === node.id) {
            onSelect(node.id)
          }
        }}
      >
        <span className="truncate">{node.name}</span>
      </TreeViewItem>
    )

  return (
    <TreeView
      className="px-2"
      selectionMode="single"
      variant="filled"
      selected={selected}
      // Collapsed branches render no children, so starting big repos
      // collapsed keeps the tree's DOM (and first paint) small; small repos
      // keep the everything-visible behavior.
      defaultExpanded={branchIds.length <= 50 ? branchIds : []}
      onSelectedChange={({ value }) => {
        const id = value[0]
        // Branch-control clicks also toggle selection; only file leaves may select.
        if (id && leafIds.has(id)) {
          setSelected(value)
          onSelect(id)
        }
      }}
    >
      {/* tabIndex seeds the roving tabindex: every treeitem starts at -1 and
          the tree's focus initializer only runs when the ul itself receives
          focus, so without this the tree is keyboard-unreachable. */}
      <TreeViewTree tabIndex={0}>{nodes.map(renderNode)}</TreeViewTree>
    </TreeView>
  )
})

function SymbolsTab({
  repoId,
  nodeColors,
  symbolKinds,
  onSymbolSelect,
}: {
  repoId: string | null
  nodeColors: Record<string, string>
  symbolKinds: string[]
  onSymbolSelect: (name: string, filePath: string) => void
}) {
  const [rawQuery, setRawQuery] = useState("")
  const [debouncedQuery, setDebouncedQuery] = useState("")
  const [kind, setKind] = useState(ALL_KINDS)
  const [offset, setOffset] = useState(0)

  useEffect(() => {
    const t = setTimeout(() => setDebouncedQuery(rawQuery.trim()), 300)
    return () => clearTimeout(t)
  }, [rawQuery])

  // A new query, kind filter, or repo resets to the first page so the offset
  // window never points past a shrunken result set.
  useEffect(() => {
    setOffset(0)
  }, [debouncedQuery, kind, repoId])

  const { data, isFetching } = useCodeSymbols({
    repoId,
    q: debouncedQuery || undefined,
    kind: kind === ALL_KINDS ? undefined : kind,
    offset,
    limit: SYMBOLS_PAGE_SIZE,
  })

  const items = data?.items ?? []
  const total = data?.total ?? 0
  const rangeStart = total === 0 ? 0 : offset + 1
  const rangeEnd = Math.min(offset + items.length, total)
  const hasPrev = offset > 0
  const hasNext = offset + SYMBOLS_PAGE_SIZE < total

  if (!repoId) {
    return (
      <EmptyState
        kind="filtered"
        className="font-mono"
        title="No repository selected"
        description="Select a repository to browse symbols"
      />
    )
  }

  return (
    <div className="flex h-full flex-col">
      <div className="border-border flex shrink-0 flex-col gap-2 border-b p-3">
        <Input
          placeholder="Filter symbols…"
          className="h-8 font-mono text-sm"
          value={rawQuery}
          onChange={(e) => setRawQuery(e.target.value)}
        />
        <Select value={kind} onValueChange={setKind}>
          <SelectTrigger className="h-8 font-mono text-sm">
            <SelectValue placeholder="All kinds" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ALL_KINDS}>All</SelectItem>
            {symbolKinds.map((k) => (
              <SelectItem key={k} value={k}>
                {k}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <ScrollArea className="min-h-0 flex-1">
        <div className="space-y-0.5 p-2">
          {items.length > 0 ? (
            items.map((sym) => (
              <Button
                variant="ghost"
                key={sym.id}
                className="group w-full rounded-md px-3 py-2 text-left"
                onClick={() => onSymbolSelect(sym.name, sym.file_path)}
              >
                <div className="flex items-center gap-2">
                  <span
                    aria-hidden="true"
                    className="size-2 shrink-0 rounded-full"
                    style={{
                      backgroundColor:
                        nodeColors[sym.kind] ?? "hsl(var(--muted-foreground))",
                    }}
                  />
                  <span className="text-foreground min-w-0 flex-1 truncate font-mono text-sm">
                    {sym.name}
                  </span>
                  <span className="text-muted-foreground shrink-0 font-mono text-sm">
                    {sym.kind}
                  </span>
                </div>
                <div className="text-muted-foreground mt-1 truncate font-mono text-sm">
                  {sym.file_path}
                  {sym.line_start > 0 && (
                    <span>
                      {" "}
                      · L{sym.line_start}–{sym.line_end}
                    </span>
                  )}
                </div>
              </Button>
            ))
          ) : isFetching ? (
            <div className="flex h-32 items-center justify-center">
              <Spinner size="sm" label="Loading symbols…" />
            </div>
          ) : (
            <EmptyState
              kind="filtered"
              className="font-mono"
              title="No symbols found"
            />
          )}
        </div>
      </ScrollArea>

      <div className="border-border flex shrink-0 items-center justify-between gap-2 border-t px-3 py-2">
        <span className="text-muted-foreground font-mono text-sm tabular-nums">
          {rangeStart}-{rangeEnd} of {total}
        </span>
        <div className="flex items-center gap-1">
          <Button
            variant="outline"
            className="font-mono"
            disabled={!hasPrev}
            onClick={() => setOffset((o) => Math.max(0, o - SYMBOLS_PAGE_SIZE))}
          >
            Prev
          </Button>
          <Button
            variant="outline"
            className="font-mono"
            disabled={!hasNext}
            onClick={() => setOffset((o) => o + SYMBOLS_PAGE_SIZE)}
          >
            Next
          </Button>
        </div>
      </div>
    </div>
  )
}

export function CodeInspectorPanel({
  symbolDetail,
  searchResults,
  fileList,
  onFileSelect,
  onSearchResultClick,
  repoId,
  nodeColors,
  symbolKinds,
  onSymbolSelect,
}: CodeInspectorPanelProps) {
  const [activeTab, setActiveTab] = useState<InspectorTab>("source")

  // Fresh search results surface their own tab — they land here from the
  // toolbar search, which otherwise gives no visible response when another
  // tab is active. Identity-guarded so a panel remount with old results
  // (inspector toggled closed and back open) doesn't yank the tab again.
  const seenResultsRef = useRef(searchResults)
  useEffect(() => {
    if (searchResults === seenResultsRef.current) return
    seenResultsRef.current = searchResults
    if (searchResults.length > 0) setActiveTab("results")
  }, [searchResults])

  const tabs: { id: InspectorTab; label: string; count?: number }[] = [
    { id: "source", label: "Source" },
    { id: "symbols", label: "Symbols" },
    { id: "files", label: "Files", count: fileList.length || undefined },
    {
      id: "results",
      label: "Results",
      count: searchResults.length || undefined,
    },
  ]

  return (
    <div className="code-inspector-panel border-border flex h-full flex-col border-r">
      <div className="border-border flex shrink-0 items-center gap-2 border-b px-4 py-2.5">
        <div className="bg-primary h-1.5 w-1.5 rounded-full" />
        <span className="text-foreground font-mono text-sm font-semibold tracking-[0.2em] uppercase">
          Code Inspector
        </span>
      </div>

      <Tabs
        variant="underline"
        value={activeTab}
        onValueChange={(v) => setActiveTab(v as InspectorTab)}
        className="flex min-h-0 flex-1 flex-col"
      >
        <TabsList className="w-full shrink-0 gap-0">
          {tabs.map((tab) => (
            <TabsTrigger
              key={tab.id}
              value={tab.id}
              className="flex-1 gap-1.5 font-mono text-sm tracking-widest uppercase"
            >
              {tab.label}
              {tab.count !== undefined && (
                <Badge variant="secondary" size="sm">
                  {tab.count}
                </Badge>
              )}
            </TabsTrigger>
          ))}
        </TabsList>

        <TabsContent value="symbols" className="mt-0 min-h-0 flex-1">
          <SymbolsTab
            repoId={repoId}
            nodeColors={nodeColors}
            symbolKinds={symbolKinds}
            onSymbolSelect={onSymbolSelect}
          />
        </TabsContent>

        <TabsContent value="source" className="mt-0 min-h-0 flex-1">
          <ScrollArea className="h-full">
            <div className="p-3">
              {symbolDetail ? (
                <div className="space-y-3">
                  <div className="border-border bg-card flex items-center gap-2 rounded-md border px-3 py-1.5">
                    <span className="text-primary font-mono text-sm">◈</span>
                    <span className="text-foreground flex-1 truncate font-mono text-sm">
                      {symbolDetail.file_path ?? symbolDetail.name}
                    </span>
                    {symbolDetail.line_start > 0 && (
                      <span className="text-muted-foreground shrink-0 font-mono text-sm">
                        L{symbolDetail.line_start}–{symbolDetail.line_end}
                      </span>
                    )}
                  </div>

                  {symbolDetail.signature && (
                    <Card className="overflow-hidden">
                      <CardHeader className="border-border border-b px-3 py-1">
                        <span className="text-muted-foreground font-mono text-sm tracking-[0.2em] uppercase">
                          Signature
                        </span>
                      </CardHeader>
                      <CardContent className="p-0">
                        <pre className="text-foreground overflow-x-auto px-3 py-2 font-mono text-sm leading-relaxed whitespace-pre-wrap">
                          {symbolDetail.signature}
                        </pre>
                      </CardContent>
                    </Card>
                  )}

                  {symbolDetail.source_code && (
                    <Card className="overflow-hidden">
                      <CardHeader className="border-border flex-row items-center justify-between space-y-0 border-b px-3 py-1">
                        <span className="text-muted-foreground font-mono text-sm tracking-[0.2em] uppercase">
                          Source
                        </span>
                        <span className="text-muted-foreground font-mono text-sm">
                          {symbolDetail.source_code.split("\n").length} lines
                        </span>
                      </CardHeader>
                      <CardContent className="p-0">
                        {/* ScrollArea's viewport is h-full, which cannot resolve
                            against an auto-height root; the flex column lets
                            max-h clamp the viewport so long sources scroll. */}
                        <ScrollArea className="flex max-h-[65vh] flex-col">
                          <pre className="text-foreground overflow-x-auto px-3 py-2 font-mono text-sm leading-[1.6]">
                            {symbolDetail.source_code}
                          </pre>
                        </ScrollArea>
                      </CardContent>
                    </Card>
                  )}

                  {symbolDetail.docstring && (
                    <Card className="overflow-hidden">
                      <CardHeader className="border-border border-b px-3 py-1">
                        <span className="text-muted-foreground font-mono text-sm tracking-[0.2em] uppercase">
                          Docstring
                        </span>
                      </CardHeader>
                      <CardContent className="p-0">
                        <p className="text-muted-foreground px-3 py-2 font-mono text-sm leading-relaxed whitespace-pre-wrap">
                          {symbolDetail.docstring}
                        </p>
                      </CardContent>
                    </Card>
                  )}
                </div>
              ) : (
                <EmptyState
                  kind="empty"
          icon={Diamond}
                  className="font-mono"
                  title="Select a symbol to inspect"
                  description="Click a node in the graph"
                />
              )}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="files" className="mt-0 min-h-0 flex-1">
          <ScrollArea className="h-full">
            <div className="py-2">
              {/* Keyed per repo: expansion/selection are uncontrolled, and a
                  cached repo switch would otherwise keep the old tree state */}
              {fileList.length > 0 ? (
                <FileTree
                  key={repoId ?? "none"}
                  files={fileList}
                  onSelect={onFileSelect}
                />
              ) : (
                <EmptyState
                  kind="empty"
          icon={FileCode}
                  className="font-mono"
                  title="No files loaded"
                />
              )}
            </div>
          </ScrollArea>
        </TabsContent>

        <TabsContent value="results" className="mt-0 min-h-0 flex-1">
          <ScrollArea className="h-full">
            <div className="space-y-0.5 p-2">
              {searchResults.length > 0 ? (
                searchResults.map((r, i) => (
                  <Button
                    variant="ghost"
                    key={`${r.file_path}:${r.symbol_name ?? ""}:${i}`}
                    className="group w-full rounded-md px-3 py-2.5 text-left"
                    onClick={() => onSearchResultClick(r)}
                  >
                    <div className="text-foreground truncate font-mono text-sm">
                      {r.file_path}
                    </div>
                    {r.symbol_name && (
                      <div className="text-primary mt-0.5 font-mono text-sm">
                        {r.symbol_name}
                      </div>
                    )}
                    <div className="text-muted-foreground mt-1 line-clamp-2 font-mono text-sm leading-relaxed">
                      {r.chunk_content.slice(0, 140)}
                    </div>
                    <div className="text-muted-foreground mt-1 font-mono text-sm">
                      score {r.score.toFixed(3)}
                    </div>
                  </Button>
                ))
              ) : (
                <EmptyState
                  kind="filtered"
                  className="font-mono"
                  title="No search results"
                  description="Press Enter in the search bar"
                />
              )}
            </div>
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  )
}
