import { useState, useCallback } from "react";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatMessages } from "@/components/chat/ChatMessages";
import { ChatInput } from "@/components/chat/ChatInput";
import {
  useConversations,
  useConversation,
  useCreateConversation,
  useDeleteConversation,
} from "@/hooks/useApi";
import { useChatStream } from "@/hooks/useChatStream";
import { MessageCircle } from "lucide-react";

export default function Chat() {
  const [activeId, setActiveId] = useState<string | null>(null);

  const { data: convList } = useConversations();
  const { data: convDetail } = useConversation(activeId);
  const createConv = useCreateConversation();
  const deleteConv = useDeleteConversation();
  const stream = useChatStream();

  const conversations = convList?.conversations ?? [];
  const messages = convDetail?.messages ?? [];

  const handleCreate = useCallback(async () => {
    const conv = await createConv.mutateAsync({});
    setActiveId(conv.id);
  }, [createConv]);

  const handleDelete = useCallback(
    async (id: string) => {
      await deleteConv.mutateAsync(id);
      if (activeId === id) setActiveId(null);
    },
    [deleteConv, activeId],
  );

  const handleSend = useCallback(
    async (content: string) => {
      const resultId = await stream.sendMessage(activeId, content);
      if (!activeId && resultId) {
        setActiveId(resultId);
      }
    },
    [activeId, stream],
  );

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
            <div className="px-4 py-3 border-b border-border shrink-0">
              <h2 className="text-sm font-semibold truncate">
                {convDetail?.title || "New Chat"}
              </h2>
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
            />
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center gap-4 text-muted-foreground">
            <MessageCircle className="w-12 h-12 opacity-20" />
            <div className="text-center">
              <p className="text-lg font-medium text-foreground mb-1">
                Ask anything about your memories
              </p>
              <p className="text-sm">
                Start a new conversation or select one from the sidebar
              </p>
            </div>
            <div className="flex gap-2 mt-2">
              {["What do I know about Docker?", "Summarize recent decisions", "Network topology overview"].map((prompt) => (
                <button
                  key={prompt}
                  className="text-xs bg-muted hover:bg-muted/80 px-3 py-1.5 rounded-full text-foreground transition-colors"
                  onClick={async () => {
                    const resultId = await stream.sendMessage(null, prompt);
                    if (resultId) setActiveId(resultId);
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
  );
}
