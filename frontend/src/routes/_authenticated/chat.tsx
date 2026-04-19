import { useState, useCallback } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { ChatSidebar } from "@/features/chat/components/chat-sidebar"
import { ChatMessages } from "@/features/chat/components/chat-messages"
import { ChatInput } from "@/features/chat/components/chat-input"
import { Input } from "darkraise-ui/components/input"
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

      <div className="flex-1 flex flex-col min-w-0">
        {activeId || stream.isStreaming ? (
          <>
            <div className="px-4 py-3 border-b border-border shrink-0 flex items-center gap-2">
              {editingTitle ? (
                <Input
                  autoFocus
                  defaultValue={convDetail?.title || ""}
                  className="text-sm font-semibold bg-transparent border-b border-primary focus:ring-0 focus:border-indigo-400 flex-1 h-auto py-0 rounded-none"
                  onBlur={(e) => handleTitleSubmit(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleTitleSubmit(e.currentTarget.value)
                    if (e.key === "Escape") setEditingTitle(false)
                  }}
                />
              ) : (
                <h2
                  className="text-sm font-semibold truncate flex-1 cursor-pointer hover:text-primary transition-colors"
                  onClick={() => setEditingTitle(true)}
                  title="Click to rename"
                >
                  {convDetail?.title || "New Chat"}
                </h2>
              )}
              {messages.length > 0 && (
                <span className="text-xs text-muted-foreground/40 shrink-0">
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
          <div className="flex-1 flex flex-col items-center justify-center gap-6 text-muted-foreground px-4">
            <div
              className="w-20 h-20 rounded-2xl flex items-center justify-center"
              style={{ background: "radial-gradient(circle, rgba(99,102,241,0.12) 0%, transparent 70%)" }}
            >
              <Sparkles className="w-8 h-8 text-indigo-400" />
            </div>
            <div className="text-center max-w-md">
              <p className="text-xl font-semibold text-foreground mb-2">
                Ask anything about your memories
              </p>
              <p className="text-sm leading-relaxed">
                Chat with your knowledge base. Ask questions, explore connections,
                and discover insights from your stored memories and entities.
              </p>
            </div>

            <div className="flex flex-wrap gap-2 justify-center max-w-lg">
              {[
                "What do I know about Docker?",
                "Summarize recent decisions",
                "Network topology overview",
                "What services does darkmem use?",
              ].map((prompt) => (
                <button
                  key={prompt}
                  className="text-xs bg-[rgba(99,102,241,0.04)] border border-[rgba(99,102,241,0.1)] hover:bg-[rgba(99,102,241,0.1)] hover:border-[rgba(99,102,241,0.2)] hover:text-indigo-200 px-4 py-2 rounded-full text-slate-300 transition-all"
                  onClick={async () => {
                    const resultId = await stream.sendMessage(null, prompt)
                    if (resultId) setActiveId(resultId)
                  }}
                >
                  {prompt}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
