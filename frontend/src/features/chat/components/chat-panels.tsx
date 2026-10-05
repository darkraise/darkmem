import { useCallback, useRef, useState, type ReactNode } from "react"
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "darkraise-ui/components/resizable"
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "darkraise-ui/components/tabs"
import { useMediaQuery } from "@/hooks/use-media-query"

/** The three-pane chat shell, shared by the real and demo pages so both keep
 *  the "one route, one layout" promise their own comments already make.
 *
 *  Above `lg` the panes are a resizable group: the reader drags the two
 *  handles to trade width between the thread list, the conversation and the
 *  retrieval context. Below `lg` the three panes become tabs — three
 *  resizable columns sharing a phone's width leaves each too narrow to read,
 *  and stacking them put the composer mid-page above the context panel.
 *
 *  The branch is a JS media query rather than a `lg:` class because it swaps
 *  the container element itself, which a Tailwind prefix cannot do. Crossing
 *  the breakpoint therefore remounts the panes; the conversation and stream
 *  state live in the page above this component, so nothing in flight is lost.
 */

const STORAGE_KEY = "darkmem.chat.panel-sizes"
/** The thread pane's floor, in percent (the group takes no pixel sizes). At
 *  the narrowest wide layout it still fits the pane's header and search box. */
export const THREADS_MIN_SIZE = 18
const DEFAULT_SIZES = [20, 56, 24]

function readStoredSizes(): number[] {
  if (typeof window === "undefined") return DEFAULT_SIZES
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_SIZES
    const parsed: unknown = JSON.parse(raw)
    if (
      Array.isArray(parsed) &&
      parsed.length === DEFAULT_SIZES.length &&
      parsed.every(
        (n) => typeof n === "number" && Number.isFinite(n) && n > 0,
      ) &&
      (parsed[0] as number) >= THREADS_MIN_SIZE
    ) {
      return parsed as number[]
    }
  } catch {
    // A cleared, quota-blocked or hand-edited store is not an error worth
    // showing anyone — the layout simply opens at its default.
  }
  return DEFAULT_SIZES
}

export function ChatPanels({
  threads,
  conversation,
  context,
  activeKey,
}: {
  threads: ReactNode
  conversation: ReactNode
  context: ReactNode
  /** The open conversation's id. Below lg, picking a thread (or starting a
   *  new one) changes it, which brings the Conversation tab forward. */
  activeKey?: string | null
}) {
  const wide = useMediaQuery("(min-width: 1024px)")
  const [narrowTab, setNarrowTab] = useState("conversation")
  const [seenKey, setSeenKey] = useState(activeKey)
  if (seenKey !== activeKey) {
    setSeenKey(activeKey)
    setNarrowTab("conversation")
  }
  // Read once. Re-reading on every render would fight the group, which owns
  // the live sizes after mount and only reports them back through
  // `onLayoutChange`.
  const [initial] = useState(readStoredSizes)
  const lastWritten = useRef<string>("")

  const persist = useCallback((sizes: number[]) => {
    if (sizes.length !== DEFAULT_SIZES.length) return
    const serialized = JSON.stringify(sizes.map((n) => Number(n.toFixed(2))))
    if (serialized === lastWritten.current) return
    lastWritten.current = serialized
    try {
      window.localStorage.setItem(STORAGE_KEY, serialized)
    } catch {
      // Private-mode or quota-blocked storage: the drag still works for this
      // visit, it just does not survive a reload.
    }
  }, [])

  if (!wide) {
    // Stacked, the composer sat mid-page with the whole context panel under
    // it. Below lg each pane is a tab instead, so the conversation owns the
    // screen and its composer sits at the bottom of the viewport. Panes stay
    // mounted (`forceMount`) so a half-typed draft survives a tab switch.
    return (
      <Tabs
        variant="underline"
        value={narrowTab}
        onValueChange={setNarrowTab}
        className="flex flex-col gap-3"
      >
        <TabsList className="border-border border-b">
          <TabsTrigger value="threads">Threads</TabsTrigger>
          <TabsTrigger value="conversation">Conversation</TabsTrigger>
          <TabsTrigger value="context">Context</TabsTrigger>
        </TabsList>
        <TabsContent
          value="threads"
          forceMount
          className="grid data-[state=inactive]:hidden"
        >
          {threads}
        </TabsContent>
        <TabsContent
          value="conversation"
          forceMount
          // The viewport minus the app header, page title and tab strip.
          className="grid h-[calc(100dvh-11rem)] min-h-[22rem] grid-rows-[minmax(0,1fr)] data-[state=inactive]:hidden"
        >
          {conversation}
        </TabsContent>
        <TabsContent
          value="context"
          forceMount
          className="grid data-[state=inactive]:hidden"
        >
          {context}
        </TabsContent>
      </Tabs>
    )
  }

  return (
    // `overflow-hidden`: the panels total 100% and the two handles add their
    // own pixels on top, which would otherwise show as a stray horizontal
    // scrollbar.
    //
    // The border lives HERE, on the group, not on the three panes. Each pane
    // used to carry its own card edge, so every seam rendered three lines —
    // the left pane's edge, the handle, the right pane's edge — with the drag
    // target floating between two borders that were not it. One outer border
    // plus the handle means the seam is a single line and that line is the
    // thing you grab. The panes keep their own edges below `lg`, where they
    // stack as separate cards and each one does need bounding.
    <ResizablePanelGroup
      className="border-border bg-card min-h-0 flex-1 overflow-hidden rounded-md border"
      onLayoutChange={persist}
    >
      <ResizablePanel
        id="chat-threads"
        defaultSize={initial[0]}
        minSize={THREADS_MIN_SIZE}
        maxSize={32}
        className="grid min-h-0 pr-3"
      >
        {threads}
      </ResizablePanel>
      <ResizableHandle
        withHandle
        aria-label="Resize the thread list"
        // The line stays 1px; only the pointer target grows. The
        // library's own `after:w-1` is a 4px grab zone, which is a
        // hard aim for a full-height divider.
        className="after:w-3"
      />
      <ResizablePanel
        id="chat-conversation"
        defaultSize={initial[1]}
        minSize={28}
        className="grid min-h-0 px-3"
      >
        {conversation}
      </ResizablePanel>
      <ResizableHandle
        withHandle
        aria-label="Resize the context panel"
        // The line stays 1px; only the pointer target grows. The
        // library's own `after:w-1` is a 4px grab zone, which is a
        // hard aim for a full-height divider.
        className="after:w-3"
      />
      <ResizablePanel
        id="chat-context"
        defaultSize={initial[2]}
        minSize={12}
        maxSize={45}
        className="grid min-h-0 pl-3"
      >
        {context}
      </ResizablePanel>
    </ResizablePanelGroup>
  )
}
