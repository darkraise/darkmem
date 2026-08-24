import { useCallback, useRef, useState, type ReactNode } from "react"
import {
  ResizableHandle,
  ResizablePanel,
  ResizablePanelGroup,
} from "darkraise-ui/components/resizable"
import { useMediaQuery } from "@/hooks/use-media-query"

/** The three-pane chat shell, shared by the real and demo pages so both keep
 *  the "one route, one layout" promise their own comments already make.
 *
 *  Above `lg` the panes are a resizable group: the reader drags the two
 *  handles to trade width between the thread list, the conversation and the
 *  retrieval context. Below `lg` they stack and the page scrolls normally —
 *  three resizable columns sharing a phone's width leaves each too narrow to
 *  read, and the group would need a horizontal scrollbar to avoid it.
 *
 *  The branch is a JS media query rather than a `lg:` class because it swaps
 *  the container element itself, which a Tailwind prefix cannot do. Crossing
 *  the breakpoint therefore remounts the panes; the conversation and stream
 *  state live in the page above this component, so nothing in flight is lost.
 */

const STORAGE_KEY = "darkmem.chat.panel-sizes"
const DEFAULT_SIZES = [16, 60, 24]

function readStoredSizes(): number[] {
  if (typeof window === "undefined") return DEFAULT_SIZES
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return DEFAULT_SIZES
    const parsed: unknown = JSON.parse(raw)
    if (
      Array.isArray(parsed) &&
      parsed.length === DEFAULT_SIZES.length &&
      parsed.every((n) => typeof n === "number" && Number.isFinite(n) && n > 0)
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
}: {
  threads: ReactNode
  conversation: ReactNode
  context: ReactNode
}) {
  const wide = useMediaQuery("(min-width: 1024px)")
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
    return (
      <div className="flex flex-col gap-4">
        {threads}
        {conversation}
        {context}
      </div>
    )
  }

  return (
    // `overflow-hidden`: the panels total 100% and the two handles add their
    // own pixels on top, which would otherwise show as a stray horizontal
    // scrollbar.
    <ResizablePanelGroup
      className="min-h-0 flex-1 overflow-hidden"
      onLayoutChange={persist}
    >
      <ResizablePanel
        id="chat-threads"
        defaultSize={initial[0]}
        minSize={10}
        maxSize={32}
        className="grid min-h-0 pr-3"
      >
        {threads}
      </ResizablePanel>
      <ResizableHandle withHandle aria-label="Resize the thread list" />
      <ResizablePanel
        id="chat-conversation"
        defaultSize={initial[1]}
        minSize={28}
        className="grid min-h-0 px-3"
      >
        {conversation}
      </ResizablePanel>
      <ResizableHandle withHandle aria-label="Resize the context panel" />
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
