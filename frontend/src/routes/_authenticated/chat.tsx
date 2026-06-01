import { useState, useCallback } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { ChatSidebar } from "@/features/chat/components/chat-sidebar"
import { ChatMessages } from "@/features/chat/components/chat-messages"
import { ChatInput } from "@/features/chat/components/chat-input"
import { Input } from "darkraise-ui/components/input"
import { Button } from "darkraise-ui/components/button"
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

function ChatPage() {
  const { id: initialId } = Route.useSearch()
  const [activeId, setActiveId] = useState<string | null>(initialId ?? null)
  const [editingTitle, setEditingTitle] = useState(false)

  const { data: convList } = useConversations()
  const { data: convDetail } = useConversation(activeId)
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

  const handleTitleSubmit = useCallback(
    async (newTitle: string) => {
      if (activeId && newTitle.trim()) {
        await updateConv.mutateAsync({ id: activeId, title: newTitle.trim() })
      }
      setEditingTitle(false)
    },
    [activeId, updateConv],
  )

  return (
    <div className="flex h-full">
      <ChatSidebar
        conversations={conversations}
        activeId={activeId}
        onSelect={setActiveId}
        onCreate={handleCreate}
        onDelete={handleDelete}
      />

      <div className="flex min-w-0 flex-1 flex-col">
        {activeId || stream.isStreaming ? (
          <>
            <div className="border-border flex shrink-0 items-center gap-2 border-b px-4 py-3">
              {editingTitle ? (
                <Input
                  autoFocus
                  defaultValue={convDetail?.title || ""}
                  className="border-primary h-auto flex-1 rounded-none border-b bg-transparent py-0 text-base font-semibold focus:border-indigo-400 focus:ring-0"
                  onBlur={(e) => handleTitleSubmit(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter")
                      handleTitleSubmit(e.currentTarget.value)
                    if (e.key === "Escape") setEditingTitle(false)
                  }}
                />
              ) : (
                <button
                  type="button"
                  className="hover:text-primary flex-1 cursor-pointer truncate text-left text-base font-semibold transition-colors"
                  onClick={() => setEditingTitle(true)}
                  title="Click to rename"
                  aria-label="Rename conversation"
                >
                  {convDetail?.title || "New Chat"}
                </button>
              )}
              {messages.length > 0 && (
                <span className="text-muted-foreground/40 shrink-0 text-base">
                  {messages.length} message{messages.length !== 1 ? "s" : ""}
                </span>
              )}
            </div>

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
          </>
        ) : (
          <div className="text-muted-foreground flex flex-1 flex-col items-center justify-center gap-6 px-4">
            <div
              className="flex h-20 w-20 items-center justify-center rounded-2xl"
              style={{
                background:
                  "radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)",
              }}
            >
              <Sparkles className="h-8 w-8 text-indigo-400" />
            </div>
            <div className="max-w-md text-center">
              <p className="text-foreground mb-2 text-xl font-semibold">
                Ask anything about your memories
              </p>
              <p className="text-base leading-relaxed">
                Chat with your knowledge base. Ask questions, explore
                connections, and discover insights from your stored memories and
                entities.
              </p>
            </div>

            <div className="flex max-w-lg flex-wrap justify-center gap-2">
              {[
                "What do I know about Docker?",
                "Summarize recent decisions",
                "Network topology overview",
                "What services does darkmem use?",
              ].map((prompt) => (
                <Button
                  variant="ghost"
                  key={prompt}
                  className="rounded-full border border-[rgba(99,102,241,0.1)] bg-[rgba(99,102,241,0.04)] px-4 py-2 text-base text-slate-300 transition-all hover:border-[rgba(99,102,241,0.2)] hover:bg-[rgba(99,102,241,0.1)] hover:text-indigo-200"
                  onClick={async () => {
                    const resultId = await stream.sendMessage(null, prompt)
                    if (resultId) setActiveId(resultId)
                  }}
                >
                  {prompt}
                </Button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
