import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { MessageSquare } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { DEMO } from "@/lib/demo-flag"
import { useDemoChatThreads } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import { DemoThreadList } from "@/features/chat/components/demo-thread-list"
import { DemoMessagePane } from "@/features/chat/components/demo-message-pane"
import { DemoContextPanel } from "@/features/chat/components/demo-context-panel"
import { RealChatPage } from "@/features/chat/components/real-chat-page"

export const Route = createFileRoute("/_authenticated/chat")({
  // The ?id= search param must keep working identically in both branches,
  // matching ChatOverlay's "Open in dedicated page" navigation.
  validateSearch: (search: Record<string, unknown>) => ({
    id: typeof search.id === "string" ? search.id : undefined,
  }),
  component: () => {
    const { id } = Route.useSearch()
    return DEMO ? <DemoChatPage initialId={id} /> : <RealChatPage initialId={id} />
  },
})

function DemoChatPage({ initialId }: { initialId?: string }) {
  const threads = useDemoChatThreads()
  const sendChatMessage = useDemoStore((s) => s.sendChatMessage)
  const [activeId, setActiveId] = useState<string | null>(initialId ?? null)
  const [selectedTurnId, setSelectedTurnId] = useState<string | null>(null)

  const activeThread = threads.find((t) => t.id === activeId)

  // The panel shows the selected assistant turn, defaulting to the latest
  // one that carries a context.
  const contextTurn =
    activeThread?.messages.find(
      (m) => m.id === selectedTurnId && m.context !== undefined,
    ) ??
    [...(activeThread?.messages ?? [])]
      .reverse()
      .find((m) => m.role === "assistant" && m.context !== undefined)

  const handleSend = (content: string) => {
    const threadId = sendChatMessage(activeId, content)
    setActiveId(threadId)
    setSelectedTurnId(null)
  }

  return (
    // Same full-height shape as RealChatPage — one route, one layout.
    <div className="flex flex-col gap-4 lg:h-full lg:min-h-0">
      <PageChrome
        icon={MessageSquare}
        title="Chat"
        description="Conversation over memory — every turn's retrieval context stays visible, labelled with the same vocabulary Memories uses."
      />
      <div className="grid grid-cols-1 gap-4 lg:min-h-0 lg:flex-1 lg:grid-cols-[14rem_minmax(0,1fr)_18rem]">
        <DemoThreadList
          threads={threads}
          activeId={activeId}
          onSelect={(id) => {
            setActiveId(id)
            setSelectedTurnId(null)
          }}
          onNew={() => {
            setActiveId(null)
            setSelectedTurnId(null)
          }}
        />
        <DemoMessagePane
          thread={activeThread}
          selectedTurnId={contextTurn?.id ?? null}
          onSelectTurn={setSelectedTurnId}
          onSend={handleSend}
        />
        <DemoContextPanel context={contextTurn?.context} />
      </div>
    </div>
  )
}
