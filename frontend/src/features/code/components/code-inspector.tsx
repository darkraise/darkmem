import { useEffect, useMemo, useRef } from "react"
import {
  ChevronDown,
  ChevronRight,
  Code2,
  Pin,
  PinOff,
  PanelLeftClose,
  PanelLeftOpen,
  X,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  FloatingPanel,
  FloatingPanelContent,
  FloatingPanelDragHandle,
  FloatingPanelHeader,
} from "darkraise-ui/components/floating-panel"
import { cn } from "darkraise-ui/lib"
import { buildFileSource, type FileSource } from "@/demo/code-source"
import type { DemoCodeGraph } from "@/features/code/types"

export interface OpenCodeFile {
  path: string
  /** Pinned files dock into the column's flow; unpinned ones float free. */
  pinned: boolean
  collapsed: boolean
}

const MIN_FLOAT_WIDTH = 260

const KEYWORDS =
  /\b(from|import|class|def|return|self|export|function|const|await|async|None|True|False)\b/g

/** Comment/keyword/string tinting — enough structure to read, no tokenizer. */
function highlight(line: string, language: FileSource["language"]) {
  const commentAt = line.indexOf(language === "python" ? "#" : "//")
  if (commentAt === 0 || line.trimStart().startsWith('"""')) {
    return <span className="text-muted-foreground/70">{line}</span>
  }
  const parts: React.ReactNode[] = []
  let last = 0
  for (const match of line.matchAll(KEYWORDS)) {
    const start = match.index ?? 0
    if (start > last) parts.push(line.slice(last, start))
    parts.push(
      <span key={`${start}-${match[0]}`} className="text-primary-text">
        {match[0]}
      </span>,
    )
    last = start + match[0].length
  }
  parts.push(line.slice(last))
  return <>{parts}</>
}

function FileBody({
  source,
  activeSymbolId,
  onSelectSymbol,
}: {
  source: FileSource
  activeSymbolId: string | null
  onSelectSymbol: (nodeId: string) => void
}) {
  const anchorByLine = useMemo(() => {
    const map = new Map<number, string>()
    for (const anchor of source.anchors) map.set(anchor.line, anchor.id)
    return map
  }, [source])

  return (
    <div className="bg-background/60 overflow-x-auto font-mono text-[12px] leading-[1.55]">
      {source.lines.map((line, i) => {
        const nodeId = anchorByLine.get(i + 1)
        const active = nodeId != null && nodeId === activeSymbolId
        return (
          <div
            key={i}
            id={nodeId ? `inspector-anchor-${nodeId}` : undefined}
            className={cn(
              "flex gap-2.5 px-2",
              active && "bg-primary/12",
              nodeId && !active && "hover:bg-muted/40",
            )}
          >
            <span className="text-muted-foreground/50 w-7 shrink-0 text-right select-none">
              {i + 1}
            </span>
            {nodeId ? (
              <button
                type="button"
                className="min-w-0 flex-1 text-left whitespace-pre"
                onClick={() => onSelectSymbol(nodeId)}
              >
                {highlight(line, source.language)}
              </button>
            ) : (
              <span className="min-w-0 flex-1 whitespace-pre">
                {highlight(line, source.language)}
              </span>
            )}
          </div>
        )
      })}
    </div>
  )
}

function PanelChrome({
  source,
  file,
  onTogglePinned,
  onToggleCollapsed,
  onClose,
}: {
  source: FileSource
  file: OpenCodeFile
  onTogglePinned: () => void
  onToggleCollapsed: () => void
  onClose: () => void
}) {
  const dir = source.path.includes("/")
    ? source.path.slice(0, source.path.lastIndexOf("/"))
    : ""
  const name = source.path.slice(source.path.lastIndexOf("/") + 1)
  return (
    <>
      <button
        type="button"
        aria-expanded={!file.collapsed}
        onClick={onToggleCollapsed}
        className="flex min-w-0 flex-1 items-center gap-1.5 text-left"
      >
        {file.collapsed ? (
          <ChevronRight aria-hidden className="h-3.5 w-3.5 shrink-0" />
        ) : (
          <ChevronDown aria-hidden className="h-3.5 w-3.5 shrink-0" />
        )}
        <Code2 aria-hidden className="text-primary-text h-3.5 w-3.5 shrink-0" />
        <span className="min-w-0 flex-1 truncate font-mono text-sm">
          {name}
          {dir && (
            <span className="text-muted-foreground ml-1.5 text-xs">{dir}</span>
          )}
        </span>
      </button>
      <span className="text-muted-foreground shrink-0 font-mono text-xs">
        {source.symbols.length} sym
      </span>
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6 shrink-0"
        aria-label={
          file.pinned ? "Unpin — float this file" : "Pin — dock this file"
        }
        aria-pressed={file.pinned}
        onClick={onTogglePinned}
      >
        {file.pinned ? (
          <Pin aria-hidden className="text-primary-text h-3 w-3" />
        ) : (
          <PinOff aria-hidden className="h-3 w-3" />
        )}
      </Button>
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6 shrink-0"
        aria-label={`Close ${name}`}
        onClick={onClose}
      >
        <X aria-hidden className="h-3 w-3" />
      </Button>
    </>
  )
}

export interface CodeFilePanelProps {
  file: OpenCodeFile
  graph: DemoCodeGraph | undefined
  activeSymbolId: string | null
  onTogglePinned: (path: string) => void
  onToggleCollapsed: (path: string) => void
  onClose: (path: string) => void
  onSelectSymbol: (nodeId: string) => void
}

/** A docked file card — one entry in the inspector column's top-down flow. */
function DockedFilePanel({
  file,
  graph,
  activeSymbolId,
  onTogglePinned,
  onToggleCollapsed,
  onClose,
  onSelectSymbol,
}: CodeFilePanelProps) {
  const source = useMemo(
    () => buildFileSource(graph, file.path),
    [graph, file.path],
  )
  return (
    <div className="border-border bg-card overflow-hidden rounded-md border shadow-sm">
      <div className="border-border bg-muted/40 flex items-center gap-1 border-b px-1.5 py-1">
        <PanelChrome
          source={source}
          file={file}
          onTogglePinned={() => onTogglePinned(file.path)}
          onToggleCollapsed={() => onToggleCollapsed(file.path)}
          onClose={() => onClose(file.path)}
        />
      </div>
      {!file.collapsed && (
        <FileBody
          source={source}
          activeSymbolId={activeSymbolId}
          onSelectSymbol={onSelectSymbol}
        />
      )}
    </div>
  )
}

/**
 * An undocked file — the same card lifted out of the column into a
 * draggable panel over the canvas. Re-pinning drops it back into the flow.
 */
export function FloatingFilePanel({
  file,
  graph,
  index,
  boundsWidth,
  activeSymbolId,
  onTogglePinned,
  onToggleCollapsed,
  onClose,
  onSelectSymbol,
}: CodeFilePanelProps & {
  index: number
  /** Width of the column the panel floats in; the panel is sized to fit it
   *  so it never spills over the neighbouring analysis rail. */
  boundsWidth?: number | null
}) {
  const source = useMemo(
    () => buildFileSource(graph, file.path),
    [graph, file.path],
  )
  const offset = 24 + index * 28
  const fitWidth =
    boundsWidth != null
      ? Math.max(MIN_FLOAT_WIDTH, Math.min(420, boundsWidth - offset - 24))
      : 420
  return (
    <FloatingPanel
      scope="local"
      defaultPosition={{ x: offset, y: offset }}
      defaultSize={{ width: fitWidth, height: 320 }}
      maxWidth={
        boundsWidth != null
          ? Math.max(MIN_FLOAT_WIDTH, boundsWidth - 16)
          : undefined
      }
      minWidth={MIN_FLOAT_WIDTH}
      minHeight={120}
      className="border-border bg-card z-20 flex flex-col overflow-hidden rounded-md border shadow-lg"
    >
      {/* The chrome sits directly in the header row, not inside
          FloatingPanelTitle — that slot is a single inline label and would
          wrap the pin/close controls onto a second line. */}
      <FloatingPanelHeader className="border-border bg-muted/40 flex items-center gap-1 border-b px-1.5 py-1">
        <FloatingPanelDragHandle className="text-muted-foreground shrink-0 cursor-grab" />
        <PanelChrome
          source={source}
          file={file}
          onTogglePinned={() => onTogglePinned(file.path)}
          onToggleCollapsed={() => onToggleCollapsed(file.path)}
          onClose={() => onClose(file.path)}
        />
      </FloatingPanelHeader>
      {!file.collapsed && (
        <FloatingPanelContent className="min-h-0 flex-1 overflow-auto">
          <FileBody
            source={source}
            activeSymbolId={activeSymbolId}
            onSelectSymbol={onSelectSymbol}
          />
        </FloatingPanelContent>
      )}
    </FloatingPanel>
  )
}

export function CodeInspector({
  files,
  graph,
  activeSymbolId,
  collapsed,
  onToggleCollapsedPanel,
  onTogglePinned,
  onToggleCollapsed,
  onClose,
  onCloseAll,
  onSelectSymbol,
}: {
  files: OpenCodeFile[]
  graph: DemoCodeGraph | undefined
  activeSymbolId: string | null
  collapsed: boolean
  onToggleCollapsedPanel: () => void
  onTogglePinned: (path: string) => void
  onToggleCollapsed: (path: string) => void
  onClose: (path: string) => void
  onCloseAll: () => void
  onSelectSymbol: (nodeId: string) => void
}) {
  const scrollRef = useRef<HTMLDivElement | null>(null)
  const docked = files.filter((f) => f.pinned)

  // Selecting a symbol anywhere scrolls its declaration into view.
  useEffect(() => {
    if (!activeSymbolId || collapsed) return
    const el = document.getElementById(`inspector-anchor-${activeSymbolId}`)
    const box = scrollRef.current
    if (!el || !box || !box.contains(el)) return
    // Scroll only the inspector's own column. `scrollIntoView` would also
    // scroll every scrollable ancestor, shifting the whole page (and its
    // toolbar under the app header) when a node is clicked.
    const offset =
      el.getBoundingClientRect().top - box.getBoundingClientRect().top
    box.scrollTop += offset - box.clientHeight / 2 + el.clientHeight / 2
  }, [activeSymbolId, collapsed, files])

  // With every open file floating there is nothing to dock, so the column
  // folds to its strip instead of holding 24rem open for a placeholder.
  const allFloating = files.length > 0 && docked.length === 0

  if (collapsed || allFloating) {
    return (
      <div className="border-border bg-card flex w-full shrink-0 items-center gap-2 border-b px-2 py-1 lg:w-9 lg:flex-col lg:border-r lg:border-b-0 lg:px-0 lg:py-2">
        {!allFloating && (
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            aria-label="Expand code inspector"
            onClick={onToggleCollapsedPanel}
          >
            <PanelLeftOpen aria-hidden className="h-3.5 w-3.5" />
          </Button>
        )}
        <span className="text-muted-foreground font-mono text-xs tracking-widest uppercase lg:[writing-mode:vertical-rl]">
          inspector · {allFloating ? `${files.length} floating` : files.length}
        </span>
      </div>
    )
  }

  return (
    // Below lg the column stacks above the canvas with a capped height, so a
    // long file scrolls inside it rather than pushing the graph off-screen.
    <div className="border-border bg-muted/20 flex max-h-[60vh] w-full min-w-0 shrink-0 flex-col border-b lg:max-h-none lg:w-80 lg:border-r lg:border-b-0 2xl:w-[24rem]">
      <div className="border-border bg-card flex items-center gap-1 border-b px-2 py-1.5">
        <span className="text-muted-foreground flex min-w-0 flex-1 items-center gap-1.5 font-mono text-sm tracking-wide uppercase">
          <Code2 aria-hidden className="h-3 w-3" />
          Code inspector
        </span>
        <Button
          variant="ghost"
          className="text-muted-foreground shrink-0 text-xs"
          onClick={onCloseAll}
        >
          close all
        </Button>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 shrink-0"
          aria-label="Collapse code inspector"
          onClick={onToggleCollapsedPanel}
        >
          <PanelLeftClose aria-hidden className="h-3.5 w-3.5" />
        </Button>
      </div>
      <div
        ref={scrollRef}
        className="min-h-0 flex-1 space-y-2 overflow-auto p-2"
      >
        {docked.length === 0 ? (
          <p className="text-muted-foreground p-2 text-sm">
            {files.length === 0
              ? "Open a file from the Explorer, or select a node in the graph, to read its source here."
              : "Every open file is floating over the canvas — re-pin one to dock it back into this column."}
          </p>
        ) : (
          docked.map((file) => (
            <DockedFilePanel
              key={file.path}
              file={file}
              graph={graph}
              activeSymbolId={activeSymbolId}
              onTogglePinned={onTogglePinned}
              onToggleCollapsed={onToggleCollapsed}
              onClose={onClose}
              onSelectSymbol={onSelectSymbol}
            />
          ))
        )}
      </div>
    </div>
  )
}
