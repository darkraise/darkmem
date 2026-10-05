import { useEffect, useState, useRef } from "react"
import { MessageSquare } from "lucide-react"
import { PageChrome } from "@/components/app-chrome"
import {
  useConversations,
  useConversation,
  useCreateConversation,
  useDeleteConversation,
} from "@/hooks/api"
import { useChatStream } from "../hooks/use-chat-stream"
import { ChatSidebar } from "./chat-sidebar"
import { ChatMessages } from "./chat-messages"
import { ChatInput } from "./chat-input"
import { ChatContextPanel, type ChatContextRow } from "./chat-context-panel"
import { ChatPanels } from "./chat-panels"

/**
 * The real-backend counterpart of the demo Chat page (Ruling 5's DEMO ?
 * demo : real split). Assembles the already-real ChatSidebar, ChatMessages
 * + ChatInput, and useChatStream + useConversation — the same hooks
 * ChatOverlay already uses, just laid out as the three-column
 * thread-list | message-pane | context-panel shape DemoChatPage has,
 * instead of ChatOverlay's floating panel (T1.60, Step 7).
 */
export function RealChatPage({ initialId }: { initialId?: string }) {
  const [activeId, setActiveId] = useState<string | null>(initialId ?? null)
  const [routeId, setRouteId] = useState(initialId)
  const [selectedTurnId, setSelectedTurnId] = useState<string | null>(null)
  const selectionVersion = useRef(0)
  const selectConversation = (id: string | null) => {
    selectionVersion.current += 1
    setActiveId(id)
  }

  if (routeId !== initialId) {
    setRouteId(initialId)
    setActiveId(initialId ?? null)
  }

  useEffect(() => {
    selectionVersion.current += 1
  }, [initialId])

  const {
    data: convData,
    isLoading: conversationsLoading,
    isError: conversationsError,
    refetch: refetchConversations,
  } = useConversations()
  const conversations = convData?.conversations ?? []

  const { data: convDetail } = useConversation(activeId)
  const messages = convDetail?.messages ?? []

  const stream = useChatStream(activeId)
  const createConversation = useCreateConversation()
  const deleteConversation = useDeleteConversation()

  // Mirrors DemoChatPage's own mechanism: defaults to the latest assistant
  // turn that carries a context, or the explicitly selected one.
  const contextTurn =
    messages.find((m) => m.id === selectedTurnId && m.context !== undefined) ??
    [...messages]
      .reverse()
      .find((m) => m.role === "assistant" && m.context !== undefined)

  useEffect(() => {
    setSelectedTurnId(null)
  }, [activeId])

  // The live-streaming turn while one is in flight, else the selected
  // historical turn's persisted snapshot, else no context yet (§6.4). The
  // envelope travels with the rows it qualifies: reading one turn's rows
  // beside another turn's channel states would describe a retrieval that
  // never happened.
  const live = stream.isStreaming && stream.sources ? stream.sources : null
  const contextRows: ChatContextRow[] | null = live
    ? live.memories
    : contextTurn
      ? (contextTurn.context?.memories ?? [])
      : null
  const contextFacts = live ? live.facts : (contextTurn?.context?.facts ?? [])
  const contextEnvelope = live
    ? live.envelope
    : (contextTurn?.context?.envelope ?? null)

  const handleSend = async (content: string) => {
    const originVersion = selectionVersion.current
    const resultId = await stream.sendMessage(activeId, content)
    if (selectionVersion.current === originVersion) {
      if (!activeId && resultId) setActiveId(resultId)
      setSelectedTurnId(null)
    }
  }

  return (
    // Fills the scrollport at `lg` (see FULL_HEIGHT_ROUTES in
    // routes/_authenticated.tsx) so the three panes scroll inside themselves
    // and the input stays put. Below `lg` the columns stack and the page
    // scrolls normally — three panes sharing one viewport height would leave
    // each of them too short to read.
    <div className="flex flex-col gap-4 lg:h-full lg:min-h-0">
      <PageChrome icon={MessageSquare} title="Chat" />
      {/* The three panes are one surface, so they share a height rather than
          each ending where its own content does — and above `lg` the reader
          sets how that width is split. */}
      <ChatPanels
        activeKey={activeId}
        threads={
          <ChatSidebar
            conversations={conversations}
            activeId={activeId}
            onSelect={selectConversation}
            onCreate={async () => {
              const conv = await createConversation.mutateAsync({})
              selectConversation(conv.id)
            }}
            onDelete={(id) => {
              deleteConversation.mutate(id)
              if (id === activeId) selectConversation(null)
            }}
            isLoading={conversationsLoading}
            isError={conversationsError}
            onRetry={() => refetchConversations()}
          />
        }
        conversation={
          /* `min-h-0` is what lets ChatMessages' own `overflow-auto` engage: a
             flex child defaults to `min-height: auto`, which would grow this
             card to its content and push the input off the bottom. */
          <div className="border-border bg-card flex min-h-[24rem] flex-col overflow-hidden rounded-md border lg:min-h-0 lg:rounded-none lg:border-0 lg:bg-transparent">
            <ChatMessages
              messages={messages}
              streamingContent={stream.streamingContent}
              streamingSources={stream.sources}
              isStreaming={stream.isStreaming}
              pendingUserMessage={stream.pendingUserMessage}
            />
            <ChatInput
              key={activeId ?? "new"}
              error={stream.error}
              retryDraft={stream.retryDraft}
              uncertainDraft={stream.uncertainDraft}
              onSend={handleSend}
              onStop={stream.abort}
              isStreaming={stream.isStreaming}
            />
          </div>
        }
        context={
          <ChatContextPanel
            rows={contextRows}
            facts={contextFacts}
            envelope={contextEnvelope}
          />
        }
      />
    </div>
  )
}
