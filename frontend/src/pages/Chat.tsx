import { useState, useCallback } from "react";
import { ChatSidebar } from "@/components/chat/ChatSidebar";
import { ChatMessages } from "@/components/chat/ChatMessages";
import { ChatInput } from "@/components/chat/ChatInput";
import {
  useConversations,
  useConversation,
  useCreateConversation,
  useUpdateConversation,
  useDeleteConversation,
} from "@/hooks/useApi";
import { useChatStream } from "@/hooks/useChatStream";
import { Sparkles } from "lucide-react";

export default function Chat() {
  const [activeId, setActiveId] = useState<string | null>(null);
  const [editingTitle, setEditingTitle] = useState(false);

  const { data: convList } = useConversations();
  const { data: convDetail } = useConversation(activeId);
  const createConv = useCreateConversation();
  const updateConv = useUpdateConversation();
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

  const handleTitleSubmit = useCallback(
    async (newTitle: string) => {
      if (activeId && newTitle.trim()) {
        await updateConv.mutateAsync({ id: activeId, title: newTitle.trim() });
      }
      setEditingTitle(false);
    },
    [activeId, updateConv],
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
            <div className="px-4 py-3 border-b border-border shrink-0 flex items-center gap-2">
              {editingTitle ? (
                <input
                  autoFocus
                  defaultValue={convDetail?.title || ""}
                  className="text-sm font-semibold bg-transparent border-b border-primary focus:outline-none flex-1"
                  onBlur={(e) => handleTitleSubmit(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleTitleSubmit(e.currentTarget.value);
                    if (e.key === "Escape") setEditingTitle(false);
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
                <span className="text-[10px] text-muted-foreground/50 shrink-0">
                  {messages.length} message{messages.length !== 1 ? "s" : ""}
                </span>
              )}
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
          <div className="flex-1 flex flex-col items-center justify-center gap-6 text-muted-foreground px-4">
            <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
              <Sparkles className="w-8 h-8 text-primary/60" />
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
                  className="text-xs bg-muted hover:bg-primary/10 hover:text-primary border border-transparent hover:border-primary/20 px-4 py-2 rounded-full text-foreground transition-all"
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
