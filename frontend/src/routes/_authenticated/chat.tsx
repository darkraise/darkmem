import { useState, useCallback, useRef, useEffect } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { ChatSidebar } from "@/features/chat/components/chat-sidebar"
import { ChatMessages } from "@/features/chat/components/chat-messages"
import { ChatInput } from "@/features/chat/components/chat-input"
import {
  MemoryContextPanel,
  WakeUpButton,
  WingSelector,
} from "@/features/chat/components/memory-context-panel"
import { Input } from "darkraise-ui/components/input"
import {
  useConversations,
  useConversation,
  useCreateConversation,
  useUpdateConversation,
  useDeleteConversation,
  useMemoryLayers,
  useMemoryWings,
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

  const [selectedWing, setSelectedWing] = useState<string | undefined>(undefined)
  const [layersEnabled, setLayersEnabled] = useState(false)
  const [loadedLayers, setLoadedLayers] = useState<import("@/hooks/api").MemoryLayers | null>(null)

  const { data: convList } = useConversations()
  const { data: convDetail } = useConversation(activeId)
  const createConv = useCreateConversation()
  const updateConv = useUpdateConversation()
  const deleteConv = useDeleteConversation()
  const stream = useChatStream()

  const { data: wings = [] } = useMemoryWings()
  const layersQuery = useMemoryLayers(selectedWing, layersEnabled)

  const conversations = convList?.conversations ?? []
  const messages = convDetail?.messages ?? []

  const prevLayersDataRef = useRef<import("@/hooks/api").MemoryLayers | undefined>(undefined)

  useEffect(() => {
    if (layersEnabled && layersQuery.data && layersQuery.data !== prevLayersDataRef.current) {
      prevLayersDataRef.current = layersQuery.data
      setLoadedLayers(layersQuery.data)
    }
  }, [layersEnabled, layersQuery.data])

  const handleWakeUp = useCallback(() => {
    if (layersQuery.data && !layersQuery.isFetching) {
      setLoadedLayers(layersQuery.data)
      return
    }
    setLayersEnabled(true)
  }, [layersQuery.data, layersQuery.isFetching])

  const handleClearLayers = useCallback(() => {
    setLoadedLayers(null)
    setLayersEnabled(false)
  }, [])

  const handleWingChange = useCallback((wing: string | undefined) => {
    setSelectedWing(wing)
    if (loadedLayers) {
      setLoadedLayers(null)
      setLayersEnabled(false)
    }
  }, [loadedLayers])

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
      const context = loadedLayers
        ? {
            system_prefix: [loadedLayers.l0, loadedLayers.l1].join("\n\n"),
            memory_layers: { l0: loadedLayers.l0, l1: loadedLayers.l1 },
          }
        : undefined

      const resultId = await stream.sendMessage(activeId, content, context)
      if (!activeId && resultId) {
        setActiveId(resultId)
      }
    },
    [activeId, stream, loadedLayers],
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

  const isWakingUp = layersEnabled && layersQuery.isFetching

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
              <div className="flex items-center gap-1.5 shrink-0">
                <WingSelector
                  wings={wings}
                  selected={selectedWing}
                  onChange={handleWingChange}
                />
                <WakeUpButton
                  loading={isWakingUp}
                  loaded={!!loadedLayers}
                  wing={loadedLayers ? selectedWing : undefined}
                  onWakeUp={handleWakeUp}
                />
              </div>
            </div>

            {loadedLayers && (
              <MemoryContextPanel
                layers={loadedLayers}
                wing={selectedWing}
                onClear={handleClearLayers}
              />
            )}

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
              contextLabel={loadedLayers ? `Memory L0+L1 ~${loadedLayers.token_count}t` : null}
              onClearContext={handleClearLayers}
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

            <div className="flex items-center gap-2">
              <WingSelector
                wings={wings}
                selected={selectedWing}
                onChange={handleWingChange}
              />
              <WakeUpButton
                loading={isWakingUp}
                loaded={!!loadedLayers}
                wing={loadedLayers ? selectedWing : undefined}
                onWakeUp={handleWakeUp}
              />
            </div>

            {loadedLayers && (
              <div className="w-full max-w-lg">
                <MemoryContextPanel
                  layers={loadedLayers}
                  wing={selectedWing}
                  onClear={handleClearLayers}
                />
              </div>
            )}

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
                    const context = loadedLayers
                      ? {
                          system_prefix: [loadedLayers.l0, loadedLayers.l1].join("\n\n"),
                          memory_layers: { l0: loadedLayers.l0, l1: loadedLayers.l1 },
                        }
                      : undefined
                    const resultId = await stream.sendMessage(null, prompt, context)
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
