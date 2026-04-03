import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { SourceBadges } from "@/components/chat/SourceBadges";
import type { ChatMessage } from "@/hooks/useApi";

interface ChatMessagesProps {
  messages: ChatMessage[];
  streamingContent?: string;
  streamingSources?: {
    memories: { index?: number; content?: string; source?: string; tags?: string[]; score?: number; id?: string }[];
    entities: { id?: string; name?: string; entity_type?: string }[];
  } | null;
  isStreaming?: boolean;
}

export function ChatMessages({
  messages,
  streamingContent = "",
  streamingSources = null,
  isStreaming = false,
}: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, streamingContent]);

  return (
    <div className="flex-1 overflow-auto p-4 space-y-4">
      {messages.map((msg) => (
        <div key={msg.id}>
          {msg.role === "user" ? (
            <div className="flex justify-end">
              <div className="bg-muted rounded-lg px-3 py-2 text-sm max-w-[80%]">
                {msg.content}
              </div>
            </div>
          ) : (
            <div>
              <div className="prose prose-invert prose-sm max-w-none text-sm">
                <ReactMarkdown>{msg.content}</ReactMarkdown>
              </div>
              {msg.context && (
                <SourceBadges
                  memories={msg.context.memories ?? []}
                  entities={msg.context.entities ?? []}
                />
              )}
            </div>
          )}
        </div>
      ))}

      {isStreaming && streamingContent && (
        <div>
          <div className="prose prose-invert prose-sm max-w-none text-sm">
            <ReactMarkdown>{streamingContent}</ReactMarkdown>
          </div>
          {streamingSources && (
            <SourceBadges
              memories={streamingSources.memories}
              entities={streamingSources.entities}
            />
          )}
        </div>
      )}

      {isStreaming && !streamingContent && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <div className="w-2 h-2 bg-primary rounded-full animate-pulse" />
          Thinking...
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
