import { useEffect, useRef } from "react";
import ReactMarkdown from "react-markdown";
import { Bot, User } from "lucide-react";
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

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function AssistantAvatar() {
  return (
    <div className="w-7 h-7 rounded-full bg-primary/20 flex items-center justify-center shrink-0 mt-0.5">
      <Bot className="w-4 h-4 text-primary" />
    </div>
  );
}

function UserAvatar() {
  return (
    <div className="w-7 h-7 rounded-full bg-muted flex items-center justify-center shrink-0 mt-0.5">
      <User className="w-4 h-4 text-muted-foreground" />
    </div>
  );
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
    <div className="flex-1 overflow-auto px-4 py-5 space-y-5">
      {messages.map((msg) => (
        <div key={msg.id} className="animate-in fade-in duration-200">
          {msg.role === "user" ? (
            <div className="flex gap-3 justify-end">
              <div className="flex flex-col items-end gap-1 max-w-[75%]">
                <div className="bg-primary/15 text-foreground rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
                  {msg.content}
                </div>
                <span className="text-[10px] text-muted-foreground/50 px-1">
                  {formatTime(msg.created_at)}
                </span>
              </div>
              <UserAvatar />
            </div>
          ) : (
            <div className="flex gap-3">
              <AssistantAvatar />
              <div className="flex-1 min-w-0">
                <div className="prose prose-invert prose-sm max-w-none text-sm [&_pre]:bg-[#1a1b26] [&_pre]:border [&_pre]:border-border [&_pre]:rounded-lg [&_pre]:p-3 [&_code]:text-primary [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_pre_code]:text-foreground [&_a]:text-primary [&_a]:no-underline hover:[&_a]:underline [&_table]:border-collapse [&_th]:border [&_th]:border-border [&_th]:px-3 [&_th]:py-1.5 [&_td]:border [&_td]:border-border [&_td]:px-3 [&_td]:py-1.5 [&_blockquote]:border-l-primary/50 [&_blockquote]:text-muted-foreground [&_hr]:border-border">
                  <ReactMarkdown>{msg.content}</ReactMarkdown>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-[10px] text-muted-foreground/50">
                    {formatTime(msg.created_at)}
                  </span>
                </div>
                {msg.context && (
                  <SourceBadges
                    memories={msg.context.memories ?? []}
                    entities={msg.context.entities ?? []}
                  />
                )}
              </div>
            </div>
          )}
        </div>
      ))}

      {isStreaming && streamingContent && (
        <div className="flex gap-3 animate-in fade-in duration-200">
          <AssistantAvatar />
          <div className="flex-1 min-w-0">
            <div className="prose prose-invert prose-sm max-w-none text-sm [&_pre]:bg-[#1a1b26] [&_pre]:border [&_pre]:border-border [&_pre]:rounded-lg [&_pre]:p-3 [&_code]:text-primary [&_code]:bg-muted [&_code]:px-1.5 [&_code]:py-0.5 [&_code]:rounded [&_code]:text-xs [&_pre_code]:bg-transparent [&_pre_code]:p-0 [&_pre_code]:text-foreground [&_a]:text-primary">
              <ReactMarkdown>{streamingContent}</ReactMarkdown>
            </div>
            {streamingSources && (
              <SourceBadges
                memories={streamingSources.memories}
                entities={streamingSources.entities}
              />
            )}
          </div>
        </div>
      )}

      {isStreaming && !streamingContent && (
        <div className="flex gap-3 animate-in fade-in duration-200">
          <AssistantAvatar />
          <div className="flex items-center gap-1.5 py-2">
            <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 bg-primary/60 rounded-full animate-bounce [animation-delay:300ms]" />
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}
