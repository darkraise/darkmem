import { useState, useCallback } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { useFullBleedContent } from "@/hooks/use-full-bleed-content"
import { ChatSidebar } from "@/features/chat/components/chat-sidebar"
import { ChatMessages } from "@/features/chat/components/chat-messages"
import { ChatInput } from "@/features/chat/components/chat-input"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { EmptyState } from "darkraise-ui/components/empty-state"
import {
  Editable,
  EditableArea,
  EditableInput,
  EditablePreview,
} from "darkraise-ui/components/editable"
import {
  useConversations,
  useConversation,
  useCreateConversation,
  useUpdateConversation,
  useDeleteConversation,
} from "@/hooks/api"
import { useChatStream } from "@/features/chat/hooks/use-chat-stream"
import { Sparkles } from "lucide-react"

export const Route = createFileRoute("/_authenticated/chat")({
  validateSearch: (search: Record<string, unknown>) => ({
    id: typeof search.id === "string" ? search.id : undefined,
  }),
  component: ChatPage,
})

const SUGGESTED_PROMPTS = [
  "What do I know about Docker?",
  "Summarize recent decisions",
  "Network topology overview",
  "What services does darkmem use?",
]

function ChatPage() {
  useFullBleedContent()
  const { id: initialId } = Route.useSearch()
  const [activeId, setActiveId] = useState<string | null>(initialId ?? null)

  const {
    data: convList,
    isLoading: convListLoading,
    isError: convListError,
    refetch: refetchConvList,
  } = useConversations()
  const {
    data: convDetail,
    isLoading: convDetailLoading,
    isError: convDetailError,
    refetch: refetchConvDetail,
  } = useConversation(activeId)
  const createConv = useCreateConversation()
  const updateConv = useUpdateConversation()
  const deleteConv = useDeleteConversation()
  const stream = useChatStream()

  const conversations = convList?.conversations ?? []
  const messages = convDetail?.messages ?? []

  const handleCreate = useCallback(async () => {
    const conv = await createConv.mutateAsync({})
    setActiveId(conv.id)
  }, [createConv])

  const handleDelete = useCallback(
    async (id: string) => {
      await deleteConv.mutateAsync(id)
      if (activeId === id) setActiveId(null)
    },
    [deleteConv, activeId],
  )

  const handleSend = useCallback(
    async (content: string) => {
      const resultId = await stream.sendMessage(activeId, content)
      if (!activeId && resultId) {
        setActiveId(resultId)
      }
    },
    [activeId, stream],
  )

  const handleTitleCommit = useCallback(
    async (newTitle: string) => {
      const trimmed = newTitle.trim()
      // Editable's submitOnEnter also triggers a blur-submit when the input
      // is CSS-hidden, re-committing the stale controlled value; the equality
      // check drops that second commit (and redundant unchanged-title saves).
      if (activeId && trimmed && trimmed !== (convDetail?.title ?? "")) {
        await updateConv.mutateAsync({ id: activeId, title: trimmed })
      }
    },
    [activeId, convDetail?.title, updateConv],
  )

  return (
    <div className="flex h-full flex-col md:flex-row">
      <ChatSidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onCreate={handleCreate}
        onDelete={handleDelete}
        isLoading={convListLoading}
        isError={convListError}
        onRetry={refetchConvList}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        {activeId || stream.isStreaming ? (
          <>
            <div className="border-border flex shrink-0 items-center gap-2 border-b px-4 py-3">
              <Editable
                value={convDetail?.title ?? ""}
                placeholder="New Chat"
                submitOnBlur
                submitOnEnter
                cancelOnEscape
                selectOnFocus
                onValueCommit={({ value }) => handleTitleCommit(value)}
                className="min-w-0 flex-1"
              >
                <EditableArea>
                  <EditablePreview
                    className="min-w-0 text-sm font-semibold"
                    title="Click to rename"
                    aria-label="Rename conversation"
                  >
                    {/* text-overflow is inert on the inline-flex preview
                        itself, so the ellipsis needs a block-level child */}
                    <span className="truncate">
                      {convDetail?.title || "New Chat"}
                    </span>
                  </EditablePreview>
                  <EditableInput className="text-sm font-semibold" />
                </EditableArea>
              </Editable>
              {messages.length > 0 && (
                <span className="text-muted-foreground/70 shrink-0 text-sm">
                  {messages.length} message{messages.length !== 1 ? "s" : ""}
                </span>
              )}
            </div>

            {convDetailLoading && !stream.isStreaming ? (
              <div className="flex-1 space-y-6 overflow-auto px-4 py-5">
                <Skeleton className="h-16 w-3/4" />
                <Skeleton className="ml-auto h-12 w-1/2" />
                <Skeleton className="h-20 w-2/3" />
              </div>
            ) : convDetailError && !stream.isStreaming ? (
              <EmptyState
                className="flex-1"
                title="Failed to load this conversation"
                action={
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => refetchConvDetail()}
                  >
                    Retry
                  </Button>
                }
              />
            ) : (
              <ChatMessages
                messages={messages}
                streamingContent={stream.streamingContent}
                streamingSources={stream.sources}
                isStreaming={stream.isStreaming}
                pendingUserMessage={stream.pendingUserMessage}
              />
            )}
            <ChatInput
              onSend={handleSend}
              onStop={stream.abort}
              isStreaming={stream.isStreaming}
            />
          </>
        ) : (
          <EmptyState
            className="flex-1"
            icon={<Sparkles className="h-8 w-8" />}
            title="Ask anything about your memories"
            description="Chat with your knowledge base. Ask questions, explore connections, and discover insights from your stored memories and entities."
            action={
              <div className="flex max-w-lg flex-wrap justify-center gap-2">
                {SUGGESTED_PROMPTS.map((prompt) => (
                  <Button
                    variant="outline"
                    key={prompt}
                    className="rounded-full whitespace-normal"
                    onClick={async () => {
                      const resultId = await stream.sendMessage(null, prompt)
                      if (resultId) setActiveId(resultId)
                    }}
                  >
                    {prompt}
                  </Button>
                ))}
              </div>
            }
          />
        )}
      </div>
    </div>
  )
}
