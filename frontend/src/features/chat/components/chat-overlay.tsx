import { useState, useCallback, useEffect } from "react"
import { useNavigate } from "@tanstack/react-router"
import { MessageCircle, X, ExternalLink } from "lucide-react"
import { ChatMessages } from "./chat-messages"
import { ChatInput } from "./chat-input"
import { useConversation } from "@/hooks/api"
import { useChatStream } from "../hooks/use-chat-stream"

interface ChatOverlayProps {
  selectedNodeId?: string | null
  selectedEntityId?: string | null
  onNodeSelect?: (type: "memory" | "entity", id: string) => void
}

export function ChatOverlay({
  selectedNodeId,
  selectedEntityId,
  onNodeSelect,
}: ChatOverlayProps) {
  const [open, setOpen] = useState(false)
  const [convId, setConvId] = useState<string | null>(null)
  const [contextLabel, setContextLabel] = useState<string | null>(null)
  const navigate = useNavigate()

  const { data: convDetail } = useConversation(convId)
  const stream = useChatStream()

  const messages = convDetail?.messages ?? []

  useEffect(() => {
    if (selectedEntityId) {
      setContextLabel(`Entity: ${selectedEntityId.slice(0, 12)}…`)
    } else if (selectedNodeId) {
      setContextLabel(`Memory: ${selectedNodeId.slice(0, 12)}…`)
    } else {
      setContextLabel(null)
    }
  }, [selectedNodeId, selectedEntityId])

  const handleSend = useCallback(
    async (content: string) => {
      const context: Record<string, unknown> = {}
      if (selectedEntityId) context.selected_entity_id = selectedEntityId
      else if (selectedNodeId) context.selected_node_id = selectedNodeId

      const resultId = await stream.sendMessage(convId, content, context)
      if (!convId && resultId) setConvId(resultId)
    },
    [convId, selectedNodeId, selectedEntityId, stream],
  )

  if (!open) {
    return (
      <button
        className="fixed right-4 bottom-4 z-40 flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-r from-indigo-500 to-violet-500 text-white shadow-lg transition-all hover:from-indigo-400 hover:to-violet-400"
        onClick={() => setOpen(true)}
      >
        <MessageCircle className="h-5 w-5" />
      </button>
    )
  }

  return (
    <div
      role="dialog"
      aria-modal="false"
      aria-label="Chat panel"
      className="bg-card fixed right-4 bottom-16 z-40 flex h-[680px] max-h-[calc(100vh-5rem)] w-[480px] flex-col overflow-hidden rounded-xl border border-[rgba(99,102,241,0.15)] shadow-[0_0_30px_rgba(99,102,241,0.08)]"
      onKeyDown={(e) => {
        if (e.key === "Escape") setOpen(false)
      }}
    >
      <div className="border-border flex shrink-0 items-center justify-between border-b px-3 py-2">
        <span className="text-sm font-semibold">Chat</span>
        <div className="flex items-center gap-1.5">
          {convId && (
            <button
              className="text-muted-foreground hover:text-foreground flex items-center gap-1 text-xs"
              aria-label="Open chat in dedicated page"
              onClick={() => navigate({ to: "/chat", search: { id: convId } })}
            >
              Open <ExternalLink className="h-3 w-3" aria-hidden="true" />
            </button>
          )}
          <button
            className="text-muted-foreground hover:text-foreground p-0.5"
            aria-label="Close chat panel"
            onClick={() => setOpen(false)}
          >
            <X className="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </div>

      <ChatMessages
        messages={messages}
        streamingContent={stream.streamingContent}
        streamingSources={stream.sources}
        isStreaming={stream.isStreaming}
        pendingUserMessage={stream.pendingUserMessage}
        onNodeSelect={onNodeSelect}
      />

      <ChatInput
        onSend={handleSend}
        onStop={stream.abort}
        isStreaming={stream.isStreaming}
        contextLabel={contextLabel}
        onClearContext={() => setContextLabel(null)}
        placeholder="Ask about selection..."
      />
    </div>
  )
}
