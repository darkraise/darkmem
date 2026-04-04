import { useState, useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { MessageCircle, X, ExternalLink } from "lucide-react";
import { ChatMessages } from "@/components/chat/ChatMessages";
import { ChatInput } from "@/components/chat/ChatInput";
import { useConversation } from "@/hooks/useApi";
import { useChatStream } from "@/hooks/useChatStream";

interface ChatOverlayProps {
  selectedNodeId?: string | null;
  selectedEntityId?: string | null;
}

export function ChatOverlay({ selectedNodeId, selectedEntityId }: ChatOverlayProps) {
  const [open, setOpen] = useState(false);
  const [convId, setConvId] = useState<string | null>(null);
  const [contextLabel, setContextLabel] = useState<string | null>(null);
  const navigate = useNavigate();

  const { data: convDetail } = useConversation(convId);
  const stream = useChatStream();

  const messages = convDetail?.messages ?? [];

  useEffect(() => {
    if (selectedEntityId) {
      setContextLabel(`Entity: ${selectedEntityId.slice(0, 12)}…`);
    } else if (selectedNodeId) {
      setContextLabel(`Memory: ${selectedNodeId.slice(0, 12)}…`);
    } else {
      setContextLabel(null);
    }
  }, [selectedNodeId, selectedEntityId]);

  const handleSend = useCallback(
    async (content: string) => {
      const context: Record<string, unknown> = {};
      if (selectedEntityId) context.selected_entity_id = selectedEntityId;
      else if (selectedNodeId) context.selected_node_id = selectedNodeId;

      const resultId = await stream.sendMessage(convId, content, context);
      if (!convId && resultId) setConvId(resultId);
    },
    [convId, selectedNodeId, selectedEntityId, stream],
  );

  if (!open) {
    return (
      <button
        className="fixed bottom-4 right-4 z-40 w-10 h-10 bg-gradient-to-r from-indigo-500 to-violet-500 rounded-full flex items-center justify-center text-white shadow-lg hover:from-indigo-400 hover:to-violet-400 transition-all"
        onClick={() => setOpen(true)}
      >
        <MessageCircle className="w-5 h-5" />
      </button>
    );
  }

  return (
    <div className="fixed bottom-16 right-4 z-40 w-[320px] h-[400px] bg-card border border-[rgba(99,102,241,0.15)] rounded-xl shadow-[0_0_30px_rgba(99,102,241,0.08)] flex flex-col overflow-hidden">
      <div className="flex items-center justify-between px-3 py-2 border-b border-border shrink-0">
        <span className="text-sm font-semibold">Chat</span>
        <div className="flex items-center gap-1.5">
          {convId && (
            <button
              className="text-xs text-muted-foreground hover:text-foreground flex items-center gap-1"
              onClick={() => navigate(`/chat?id=${convId}`)}
            >
              Open <ExternalLink className="w-3 h-3" />
            </button>
          )}
          <button
            className="text-muted-foreground hover:text-foreground p-0.5"
            onClick={() => setOpen(false)}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      <ChatMessages
        messages={messages}
        streamingContent={stream.streamingContent}
        streamingSources={stream.sources}
        isStreaming={stream.isStreaming}
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
  );
}
