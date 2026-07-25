import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { MessageSquare } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { useDemoChatThreads } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import { DemoThreadList } from "@/features/chat/components/demo-thread-list"
import { DemoMessagePane } from "@/features/chat/components/demo-message-pane"
import { DemoContextPanel } from "@/features/chat/components/demo-context-panel"

export const Route = createFileRoute("/_authenticated/chat")({
  validateSearch: (search: Record<string, unknown>) => ({
    id: typeof search.id === "string" ? search.id : undefined,
  }),
  component: ChatPage,
})

function ChatPage() {
  const { id: initialId } = Route.useSearch()
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
    <div className="space-y-4">
      <PageChrome
        icon={MessageSquare}
        title="Chat"
        description="Conversation over memory — every turn's retrieval context stays visible, labelled with the same vocabulary Memories uses."
      />
      <div className="grid grid-cols-1 items-start gap-4 lg:grid-cols-[14rem_minmax(0,1fr)_18rem]">
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
