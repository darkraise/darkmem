import { useState } from "react"
import { createFileRoute, useNavigate, useSearch } from "@tanstack/react-router"
import { MessageSquare } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import { DEMO } from "@/lib/demo-flag"
import { useDemoChatThreads } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import { DemoThreadList } from "@/features/chat/components/demo-thread-list"
import { DemoMessagePane } from "@/features/chat/components/demo-message-pane"
import { DemoContextPanel } from "@/features/chat/components/demo-context-panel"
import { ChatPanels } from "@/features/chat/components/chat-panels"
import { RealChatPage } from "@/features/chat/components/real-chat-page"

/** A conversation id as either branch mints one: a UUID on the real backend,
 *  a short slug in the demo store. Anything else is no selection. */
const CONVERSATION_ID = /^[A-Za-z0-9_-]{1,64}$/

export const Route = createFileRoute("/_authenticated/chat")({
  // The open conversation lives in ?id=, so a reload or Back/Forward keeps
  // it. It must work identically in both branches, matching ChatOverlay's
  // "Open in dedicated page" navigation.
  validateSearch: (search: Record<string, unknown>) => ({
    id:
      typeof search.id === "string" && CONVERSATION_ID.test(search.id)
        ? search.id
        : undefined,
  }),
  component: ChatRoute,
})

function ChatRoute() {
  // The standalone hooks rather than `Route.useSearch()`: the route test
  // replaces `createFileRoute` with a passthrough, so the route object it gets
  // back carries no methods.
  const { id } = useSearch({ from: "/_authenticated/chat" })
  const navigate = useNavigate()
  const select = (next: string | null, options?: { replace?: boolean }) =>
    void navigate({
      to: "/chat",
      search: { id: next ?? undefined },
      replace: options?.replace,
    })
  return DEMO ? (
    <DemoChatPage activeId={id ?? null} onSelect={select} />
  ) : (
    <RealChatPage conversationId={id ?? null} onSelect={select} />
  )
}

function DemoChatPage({
  activeId,
  onSelect,
}: {
  activeId: string | null
  onSelect: (id: string | null, options?: { replace?: boolean }) => void
}) {
  const threads = useDemoChatThreads()
  const sendChatMessage = useDemoStore((s) => s.sendChatMessage)
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
    if (threadId !== activeId) onSelect(threadId, { replace: true })
    setSelectedTurnId(null)
  }

  return (
    // Same full-height shape as RealChatPage — one route, one layout.
    <div className="flex flex-col gap-4 lg:h-full lg:min-h-0">
      <PageChrome icon={MessageSquare} title="Chat" />
      <ChatPanels
        activeKey={activeId}
        threads={
          <DemoThreadList
            threads={threads}
            activeId={activeId}
            onSelect={(id) => {
              if (id !== activeId) onSelect(id)
              setSelectedTurnId(null)
            }}
            onNew={() => {
              if (activeId) onSelect(null)
              setSelectedTurnId(null)
            }}
          />
        }
        conversation={
          <DemoMessagePane
            thread={activeThread}
            selectedTurnId={contextTurn?.id ?? null}
            onSelectTurn={setSelectedTurnId}
            onSend={handleSend}
          />
        }
        context={<DemoContextPanel context={contextTurn?.context} />}
      />
    </div>
  )
}
