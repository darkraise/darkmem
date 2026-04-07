import { useEffect, useRef, useMemo } from "react";
import ReactMarkdown, { type Components } from "react-markdown";
import { Bot, User, FileText, Diamond } from "lucide-react";
import { SourceBadges } from "./source-badges";
import type { ChatMessage } from "@/hooks/api";

interface MemoryRef {
  index: number;
  id?: string;
  content?: string;
  source?: string;
}

interface EntityRef {
  id?: string;
  name: string;
  entity_type?: string;
}

interface ChatMessagesProps {
  messages: ChatMessage[];
  streamingContent?: string;
  streamingSources?: {
    memories: { index?: number; content?: string; source?: string; tags?: string[]; score?: number; id?: string }[];
    entities: { id?: string; name?: string; entity_type?: string }[];
  } | null;
  isStreaming?: boolean;
  pendingUserMessage?: string | null;
  onNodeSelect?: (type: "memory" | "entity", id: string) => void;
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr);
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}

function truncateContent(content: string, maxLen = 40): string {
  if (content.length <= maxLen) return content;
  const truncated = content.slice(0, maxLen);
  const lastSpace = truncated.lastIndexOf(" ");
  return (lastSpace > 20 ? truncated.slice(0, lastSpace) : truncated) + "...";
}

function AssistantAvatar() {
  return (
    <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-indigo-500/15 to-violet-500/10 flex items-center justify-center shrink-0 mt-0.5">
      <Bot className="w-4 h-4 text-indigo-300" />
    </div>
  );
}

function UserAvatar() {
  return (
    <div className="w-7 h-7 rounded-full bg-indigo-500/10 border border-indigo-500/15 flex items-center justify-center shrink-0 mt-0.5">
      <User className="w-4 h-4 text-indigo-300" />
    </div>
  );
}

function MemoryBadge({ mem, onClick }: { mem: MemoryRef; onClick?: () => void }) {
  const label = mem.content ? truncateContent(mem.content) : `Memory ${mem.id?.slice(0, 8) ?? mem.index}`;
  return (
    <button
      className="inline-flex items-center gap-1 bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 px-1.5 py-0.5 rounded text-xs hover:bg-indigo-500/20 hover:text-indigo-200 transition-colors align-baseline mx-0.5"
      onClick={onClick}
      title={mem.content || undefined}
    >
      <FileText className="w-3 h-3 shrink-0" />
      <span className="truncate max-w-48">{label}</span>
    </button>
  );
}

function EntityBadge({ entity, onClick }: { entity: EntityRef; onClick?: () => void }) {
  return (
    <button
      className="inline-flex items-center gap-1 bg-violet-500/10 text-violet-300 border border-violet-500/20 px-1.5 py-0.5 rounded text-xs hover:bg-violet-500/20 hover:text-violet-200 transition-colors align-baseline mx-0.5"
      onClick={onClick}
    >
      <Diamond className="w-3 h-3 shrink-0" />
      <span>{entity.name}</span>
    </button>
  );
}

function useMarkdownWithRefs(
  content: string,
  memories: MemoryRef[],
  entities: EntityRef[],
  onNodeSelect?: (type: "memory" | "entity", id: string) => void,
) {
  const memoryMap = useMemo(() => {
    const map = new Map<number, MemoryRef>();
    for (const m of memories) map.set(m.index, m);
    return map;
  }, [memories]);

  const entityNames = useMemo(() => {
    return entities
      .filter((e) => e.name && e.name.length > 2)
      .sort((a, b) => b.name.length - a.name.length);
  }, [entities]);

  const processed = useMemo(() => {
    return content.replace(
      /\[(\d+)\]/g,
      (match, num) => {
        const idx = parseInt(num, 10);
        if (memoryMap.has(idx)) return `[__memref:${idx}__](/ref/memory/${idx})`;
        return match;
      },
    );
  }, [content, memoryMap]);

  const components = useMemo<Components>(() => ({
    a: ({ href, children }) => {
      if (href?.startsWith("/ref/memory/")) {
        const idx = parseInt(href.split("/").pop() || "0", 10);
        const mem = memoryMap.get(idx);
        if (mem) {
          return (
            <MemoryBadge
              mem={mem}
              onClick={mem.id && onNodeSelect ? () => onNodeSelect("memory", mem.id!) : undefined}
            />
          );
        }
      }
      return <a href={href} target="_blank" rel="noopener noreferrer">{children}</a>;
    },
    p: ({ children, ...props }) => {
      const enhanced = injectEntityBadges(children, entityNames, onNodeSelect);
      return <p {...props}>{enhanced}</p>;
    },
    li: ({ children, ...props }) => {
      const enhanced = injectEntityBadges(children, entityNames, onNodeSelect);
      return <li {...props}>{enhanced}</li>;
    },
  }), [memoryMap, entityNames, onNodeSelect]);

  return { processed, components };
}

function injectEntityBadges(
  children: React.ReactNode,
  entityNames: EntityRef[],
  onNodeSelect?: (type: "memory" | "entity", id: string) => void,
): React.ReactNode {
  if (!entityNames.length) return children;

  if (!Array.isArray(children)) {
    if (typeof children === "string") {
      return replaceEntityNames(children, entityNames, onNodeSelect);
    }
    return children;
  }

  return children.map((child, i) => {
    if (typeof child === "string") {
      return <span key={i}>{replaceEntityNames(child, entityNames, onNodeSelect)}</span>;
    }
    return child;
  });
}

function replaceEntityNames(
  text: string,
  entityNames: EntityRef[],
  onNodeSelect?: (type: "memory" | "entity", id: string) => void,
): React.ReactNode {
  const lowerText = text.toLowerCase();
  const matches: { start: number; end: number; entity: EntityRef }[] = [];
  const matched = new Set<string>();

  for (const entity of entityNames) {
    const lowerName = entity.name.toLowerCase();
    if (matched.has(lowerName)) continue;
    const idx = lowerText.indexOf(lowerName);
    if (idx === -1) continue;
    matched.add(lowerName);
    matches.push({ start: idx, end: idx + entity.name.length, entity });
  }

  if (matches.length === 0) return text;

  matches.sort((a, b) => a.start - b.start);

  const fragments: React.ReactNode[] = [];
  let cursor = 0;
  for (const m of matches) {
    if (m.start < cursor) continue;
    if (m.start > cursor) fragments.push(text.slice(cursor, m.start));
    fragments.push(
      <EntityBadge
        key={`entity-${m.entity.id}-${m.start}`}
        entity={m.entity}
        onClick={m.entity.id && onNodeSelect ? () => onNodeSelect("entity", m.entity.id!) : undefined}
      />,
    );
    cursor = m.end;
  }
  if (cursor < text.length) fragments.push(text.slice(cursor));
  return <>{fragments}</>;
}

export function ChatMessages({
  messages,
  streamingContent = "",
  streamingSources = null,
  isStreaming = false,
  pendingUserMessage = null,
  onNodeSelect,
}: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, streamingContent]);

  return (
    <div className="flex-1 overflow-auto px-4 py-5 space-y-6">
      {messages.map((msg) => (
        <div key={msg.id} className="animate-in fade-in duration-200">
          {msg.role === "user" ? (
            <div className="flex gap-3 justify-end">
              <div className="flex flex-col items-end gap-1 max-w-[75%]">
                <div className="bg-gradient-to-br from-indigo-500/15 to-violet-500/8 border border-indigo-500/20 text-foreground rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
                  {msg.content}
                </div>
                <span className="text-xs text-muted-foreground/40 px-1">
                  {formatTime(msg.created_at)}
                </span>
              </div>
              <UserAvatar />
            </div>
          ) : (
            <AssistantMessage
              msg={msg}
              onNodeSelect={onNodeSelect}
            />
          )}
        </div>
      ))}

      {isStreaming && pendingUserMessage && (
        <div className="animate-in fade-in duration-200">
          <div className="flex gap-3 justify-end">
            <div className="flex flex-col items-end gap-1 max-w-[75%]">
              <div className="bg-gradient-to-br from-indigo-500/15 to-violet-500/8 border border-indigo-500/20 text-foreground rounded-2xl rounded-tr-sm px-4 py-2.5 text-sm">
                {pendingUserMessage}
              </div>
            </div>
            <UserAvatar />
          </div>
        </div>
      )}

      {isStreaming && streamingContent && (
        <StreamingMessage
          content={streamingContent}
          sources={streamingSources}
          onNodeSelect={onNodeSelect}
        />
      )}

      {isStreaming && !streamingContent && (
        <div className="flex gap-3 animate-in fade-in duration-200">
          <AssistantAvatar />
          <div className="flex items-center gap-1.5 py-2">
            <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-[pulse-glow_1.4s_ease-in-out_infinite] [animation-delay:0ms]" />
            <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-[pulse-glow_1.4s_ease-in-out_infinite] [animation-delay:150ms]" />
            <span className="w-1.5 h-1.5 bg-indigo-400 rounded-full animate-[pulse-glow_1.4s_ease-in-out_infinite] [animation-delay:300ms]" />
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
}

function AssistantMessage({
  msg,
  onNodeSelect,
}: {
  msg: ChatMessage;
  onNodeSelect?: (type: "memory" | "entity", id: string) => void;
}) {
  const memories: MemoryRef[] = useMemo(() =>
    (msg.context?.memories ?? []).map((m, i) => ({
      index: i + 1,
      id: m.id,
      content: m.content,
      source: m.source,
    })),
    [msg.context?.memories],
  );

  const entities: EntityRef[] = useMemo(() =>
    (msg.context?.entities ?? []).filter((e) => e.name),
    [msg.context?.entities],
  );

  const { processed, components } = useMarkdownWithRefs(msg.content, memories, entities, onNodeSelect);

  return (
    <div className="flex gap-3">
      <AssistantAvatar />
      <div className="flex-1 min-w-0">
        <div className="chat-prose">
          <ReactMarkdown components={components}>{processed}</ReactMarkdown>
        </div>
        <div className="flex items-center gap-2 mt-1">
          <span className="text-xs text-muted-foreground/40">
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
  );
}

function StreamingMessage({
  content,
  sources,
  onNodeSelect,
}: {
  content: string;
  sources?: {
    memories: { index?: number; content?: string; source?: string; tags?: string[]; score?: number; id?: string }[];
    entities: { id?: string; name?: string; entity_type?: string }[];
  } | null;
  onNodeSelect?: (type: "memory" | "entity", id: string) => void;
}) {
  const memories: MemoryRef[] = useMemo(() =>
    (sources?.memories ?? []).map((m) => ({
      index: m.index ?? 0,
      id: m.id,
      content: m.content,
      source: m.source,
    })),
    [sources?.memories],
  );

  const entities: EntityRef[] = useMemo(() =>
    (sources?.entities ?? []).filter((e): e is EntityRef => !!e.name),
    [sources?.entities],
  );

  const { processed, components } = useMarkdownWithRefs(content, memories, entities, onNodeSelect);

  return (
    <div className="flex gap-3 animate-in fade-in duration-200">
      <AssistantAvatar />
      <div className="flex-1 min-w-0">
        <div className="chat-prose">
          <ReactMarkdown components={components}>{processed}</ReactMarkdown>
        </div>
        {sources && (
          <SourceBadges
            memories={sources.memories}
            entities={sources.entities}
          />
        )}
      </div>
    </div>
  );
}
