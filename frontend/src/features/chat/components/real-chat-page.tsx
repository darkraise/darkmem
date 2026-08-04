import { useEffect, useState } from "react"
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
  const [selectedTurnId, setSelectedTurnId] = useState<string | null>(null)

  const {
    data: convData,
    isLoading: conversationsLoading,
    isError: conversationsError,
    refetch: refetchConversations,
  } = useConversations()
  const conversations = convData?.conversations ?? []

  const { data: convDetail } = useConversation(activeId)
  const messages = convDetail?.messages ?? []

  const stream = useChatStream()
  const createConversation = useCreateConversation()
  const deleteConversation = useDeleteConversation()

  // Mirrors DemoChatPage's own mechanism: defaults to the latest assistant
  // turn that carries a context, or the explicitly selected one.
  const contextTurn =
    messages.find((m) => m.id === selectedTurnId && m.context !== undefined) ??
    [...messages].reverse().find((m) => m.role === "assistant" && m.context !== undefined)

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
  const contextFacts = live
    ? live.facts
    : (contextTurn?.context?.facts ?? [])
  const contextEnvelope = live
    ? live.envelope
    : (contextTurn?.context?.envelope ?? null)

  const handleSend = async (content: string) => {
    const resultId = await stream.sendMessage(activeId, content)
    if (!activeId && resultId) setActiveId(resultId)
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
        <ChatSidebar
          conversations={conversations}
          activeId={activeId}
          onSelect={(id) => setActiveId(id)}
          onCreate={async () => {
            const conv = await createConversation.mutateAsync({})
            setActiveId(conv.id)
          }}
          onDelete={(id) => {
            deleteConversation.mutate(id)
            if (id === activeId) setActiveId(null)
          }}
          isLoading={conversationsLoading}
          isError={conversationsError}
          onRetry={() => refetchConversations()}
        />

        <div className="border-border bg-card flex min-h-[24rem] flex-col overflow-hidden rounded-md border">
          <ChatMessages
            messages={messages}
            streamingContent={stream.streamingContent}
            streamingSources={stream.sources}
            isStreaming={stream.isStreaming}
            pendingUserMessage={stream.pendingUserMessage}
          />
          <ChatInput
            onSend={handleSend}
            onStop={stream.abort}
            isStreaming={stream.isStreaming}
          />
        </div>

        <ChatContextPanel
          rows={contextRows}
          facts={contextFacts}
          envelope={contextEnvelope}
        />
      </div>
    </div>
  )
}
