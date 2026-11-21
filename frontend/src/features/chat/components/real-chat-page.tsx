import { useEffect, useState, useRef } from "react"
import { MessageSquare } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { toast } from "darkraise-ui/components/sonner"
import { PageChrome } from "@/components/app-chrome"
import { EmptyState } from "@/components/darkmem"
import {
  useConversations,
  useConversation,
  useDeleteConversation,
} from "@/hooks/api"
import { ApiError } from "@/lib/api"
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
 *
 * The open conversation is the route's `?id=` (`conversationId`), so a reload
 * or Back/Forward keeps it; `onSelect` moves it. `null` is an unsaved draft:
 * "New" opens one without creating anything, and the first send creates the
 * conversation server-side (each click used to store an empty "Untitled").
 */
export function RealChatPage({
  conversationId,
  onSelect,
}: {
  conversationId: string | null
  onSelect: (id: string | null, options?: { replace?: boolean }) => void
}) {
  // Each "New" is a distinct draft, so a turn still streaming from an earlier
  // draft stays with that draft rather than appearing in the fresh one.
  const [draft, setDraft] = useState(0)
  const activeKey = conversationId ?? `draft:${draft}`
  const [selectedTurnId, setSelectedTurnId] = useState<string | null>(null)
  // Read when a send completes: completion acts only if the reader is still on
  // the conversation (or draft) that sent the turn.
  const activeKeyRef = useRef(activeKey)
  useEffect(() => {
    activeKeyRef.current = activeKey
  }, [activeKey])

  const {
    data: convData,
    isLoading: conversationsLoading,
    isError: conversationsError,
    refetch: refetchConversations,
  } = useConversations()
  const conversations = convData?.conversations ?? []

  const {
    data: convDetail,
    isLoading: conversationLoading,
    error: conversationError,
    refetch: refetchConversation,
  } = useConversation(conversationId)
  const messages = convDetail?.messages ?? []
  const conversationMissing =
    conversationError instanceof ApiError && conversationError.status === 404

  const stream = useChatStream(activeKey)
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
  }, [activeKey])

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
    const origin = activeKey
    const resultId = await stream.sendMessage(
      conversationId,
      content,
      undefined,
      origin,
    )
    if (activeKeyRef.current === origin) {
      // The draft becomes the conversation its first turn created. Replacing
      // the entry keeps Back from returning to a draft that no longer exists.
      if (!conversationId && resultId) onSelect(resultId, { replace: true })
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
        activeKey={activeKey}
        threads={
          <ChatSidebar
            conversations={conversations}
            activeId={conversationId}
            onSelect={(id) => {
              if (id !== conversationId) onSelect(id)
            }}
            onCreate={() => {
              setDraft((n) => n + 1)
              if (conversationId) onSelect(null)
            }}
            onDelete={(id) => {
              deleteConversation.mutate(id, {
                onSuccess: () => {
                  if (activeKeyRef.current === id) onSelect(null, { replace: true })
                },
                onError: (error) =>
                  toast.error(`Conversation not deleted: ${error.message}`),
              })
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
            {conversationError && !stream.isStreaming ? (
              <div className="flex flex-1 items-center justify-center p-4">
                {conversationMissing ? (
                  <EmptyState
                    kind="missing"
                    title="Conversation not found"
                    description="It may have been deleted."
                    action={
                      <Button onClick={() => onSelect(null, { replace: true })}>
                        Start a new conversation
                      </Button>
                    }
                  />
                ) : (
                  <EmptyState
                    kind="failed"
                    title="Failed to load this conversation"
                    action={
                      <Button
                        variant="outline"
                        onClick={() => refetchConversation()}
                      >
                        Retry
                      </Button>
                    }
                  />
                )}
              </div>
            ) : (
              <ChatMessages
                messages={messages}
                streamingContent={stream.streamingContent}
                streamingSources={stream.sources}
                isStreaming={stream.isStreaming}
                pendingUserMessage={stream.pendingUserMessage}
                isLoading={conversationLoading}
              />
            )}
            {/* A deleted conversation takes no turn: the send would only
                come back as "Conversation not found". */}
            {!conversationMissing && (
              <ChatInput
                key={activeKey}
                error={stream.error}
                retryDraft={stream.retryDraft}
                uncertainDraft={stream.uncertainDraft}
                onSend={handleSend}
                onStop={stream.abort}
                isStreaming={stream.isStreaming}
              />
            )}
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
