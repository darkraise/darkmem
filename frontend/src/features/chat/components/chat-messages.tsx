import { useEffect, useRef, useMemo } from "react"
import ReactMarkdown, { type Components } from "react-markdown"
import { Bot, User, FileText, Diamond } from "lucide-react"
import { Avatar, AvatarFallback } from "darkraise-ui/components/avatar"
import { Button } from "darkraise-ui/components/button"
import { Spinner } from "darkraise-ui/components/spinner"
import { SourceBadges } from "./source-badges"
import { findEntityMatches } from "../lib/entity-match"
import { LifecycleDot } from "@/features/memories/components/lifecycle-badge"
import type { ChatMessage, MemoryStatus } from "@/hooks/api"

interface MemoryRef {
  index: number
  id?: string
  content?: string
  source?: string
  project?: string
  status?: MemoryStatus
}

interface EntityRef {
  id?: string
  name: string
  entity_type?: string
}

interface ChatMessagesProps {
  messages: ChatMessage[]
  streamingContent?: string
  streamingSources?: {
    memories: {
      index?: number
      content?: string
      source?: string
      tags?: string[]
      score?: number
      id?: string
      project?: string
      status?: MemoryStatus
    }[]
    entities: { id?: string; name?: string; entity_type?: string }[]
  } | null
  isStreaming?: boolean
  pendingUserMessage?: string | null
  onNodeSelect?: (type: "memory" | "entity", id: string) => void
}

function formatTime(dateStr: string): string {
  const d = new Date(dateStr)
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
}

function truncateContent(content: string, maxLen = 40): string {
  if (content.length <= maxLen) return content
  const truncated = content.slice(0, maxLen)
  const lastSpace = truncated.lastIndexOf(" ")
  return (lastSpace > 20 ? truncated.slice(0, lastSpace) : truncated) + "..."
}

function AssistantAvatar() {
  return (
    <Avatar className="mt-0.5 h-7 w-7 shrink-0 rounded-lg">
      <AvatarFallback className="bg-primary/10 text-primary rounded-lg">
        <Bot className="h-4 w-4" />
      </AvatarFallback>
    </Avatar>
  )
}

function UserAvatar() {
  return (
    <Avatar className="mt-0.5 h-7 w-7 shrink-0">
      <AvatarFallback className="bg-primary/10 text-primary">
        <User className="h-4 w-4" />
      </AvatarFallback>
    </Avatar>
  )
}

function MemoryBadge({
  mem,
  onClick,
}: {
  mem: MemoryRef
  onClick?: () => void
}) {
  const label = mem.content
    ? truncateContent(mem.content)
    : `Memory ${mem.id?.slice(0, 8) ?? mem.index}`
  // Invariant 14: no citation chip may render with zero lifecycle signal.
  // LifecycleDot is always present (unlike LifecycleBadge, which renders
  // nothing for "active") — muted when there is nothing to flag, colored
  // when there is. The tooltip carries the same words for anyone who
  // can't see color.
  const lifecycleWords = `L0 · memory — status: ${mem.status ?? "active"}`
  const title = mem.content
    ? `${mem.content} (${lifecycleWords})`
    : lifecycleWords
  return (
    <Button
      variant="secondary"
      className="mx-0.5 inline-flex h-auto items-center gap-1 px-1.5 py-0.5 align-baseline"
      onClick={onClick}
      title={title}
    >
      <FileText className="h-3 w-3 shrink-0" />
      <span className="max-w-48 truncate">{label}</span>
      <LifecycleDot status={mem.status} />
    </Button>
  )
}

function EntityBadge({
  entity,
  onClick,
}: {
  entity: EntityRef
  onClick?: () => void
}) {
  return (
    <Button
      variant="outline"
      className="mx-0.5 inline-flex h-auto items-center gap-1 px-1.5 py-0.5 align-baseline"
      onClick={onClick}
    >
      <Diamond className="h-3 w-3 shrink-0" />
      <span>{entity.name}</span>
    </Button>
  )
}

function useMarkdownWithRefs(
  content: string,
  memories: MemoryRef[],
  entities: EntityRef[],
  onNodeSelect?: (type: "memory" | "entity", id: string) => void,
) {
  const memoryMap = useMemo(() => {
    const map = new Map<number, MemoryRef>()
    for (const m of memories) map.set(m.index, m)
    return map
  }, [memories])

  const entityNames = useMemo(() => {
    return entities
      .filter((e) => e.name && e.name.length > 2)
      .sort((a, b) => b.name.length - a.name.length)
  }, [entities])

  const processed = useMemo(() => {
    return content.replace(/\[(\d+)\]/g, (match, num) => {
      const idx = parseInt(num, 10)
      if (memoryMap.has(idx)) return `[__memref:${idx}__](/ref/memory/${idx})`
      return match
    })
  }, [content, memoryMap])

  const components = useMemo<Components>(
    () => ({
      a: ({ href, children }) => {
        if (href?.startsWith("/ref/memory/")) {
          const idx = parseInt(href.split("/").pop() || "0", 10)
          const mem = memoryMap.get(idx)
          if (mem) {
            return (
              <MemoryBadge
                mem={mem}
                onClick={
                  mem.id && onNodeSelect
                    ? () => onNodeSelect("memory", mem.id!)
                    : undefined
                }
              />
            )
          }
        }
        return (
          <a href={href} target="_blank" rel="noopener noreferrer">
            {children}
          </a>
        )
      },
      p: ({ children, ...props }) => {
        const enhanced = injectEntityBadges(children, entityNames, onNodeSelect)
        return <p {...props}>{enhanced}</p>
      },
      li: ({ children, ...props }) => {
        const enhanced = injectEntityBadges(children, entityNames, onNodeSelect)
        return <li {...props}>{enhanced}</li>
      },
    }),
    [memoryMap, entityNames, onNodeSelect],
  )

  return { processed, components }
}

function injectEntityBadges(
  children: React.ReactNode,
  entityNames: EntityRef[],
  onNodeSelect?: (type: "memory" | "entity", id: string) => void,
): React.ReactNode {
  if (!entityNames.length) return children

  if (!Array.isArray(children)) {
    if (typeof children === "string") {
      return replaceEntityNames(children, entityNames, onNodeSelect)
    }
    return children
  }

  return children.map((child, i) => {
    if (typeof child === "string") {
      return (
        <span key={i}>
          {replaceEntityNames(child, entityNames, onNodeSelect)}
        </span>
      )
    }
    return child
  })
}

function replaceEntityNames(
  text: string,
  entityNames: EntityRef[],
  onNodeSelect?: (type: "memory" | "entity", id: string) => void,
): React.ReactNode {
  const byName = new Map(entityNames.map((e) => [e.name, e]))
  const matches = findEntityMatches(text, entityNames)
  if (matches.length === 0) return text

  const fragments: React.ReactNode[] = []
  let cursor = 0
  for (const m of matches) {
    if (m.start < cursor) continue
    const entity = byName.get(m.name)
    if (!entity) continue
    if (m.start > cursor) fragments.push(text.slice(cursor, m.start))
    fragments.push(
      <EntityBadge
        key={`entity-${entity.id}-${m.start}`}
        entity={entity}
        onClick={
          entity.id && onNodeSelect
            ? () => onNodeSelect("entity", entity.id!)
            : undefined
        }
      />,
    )
    cursor = m.end
  }
  if (cursor < text.length) fragments.push(text.slice(cursor))
  return <>{fragments}</>
}

export function ChatMessages({
  messages,
  streamingContent = "",
  streamingSources = null,
  isStreaming = false,
  pendingUserMessage = null,
  onNodeSelect,
}: ChatMessagesProps) {
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages.length, streamingContent])

  return (
    <div
      className="flex-1 space-y-6 overflow-auto px-4 py-5"
      role="log"
      aria-live="polite"
      aria-busy={isStreaming}
    >
      {messages.map((msg) => (
        <div key={msg.id} className="animate-in fade-in duration-200">
          {msg.role === "user" ? (
            <div className="flex justify-end gap-3">
              <div className="flex max-w-[85%] flex-col items-end gap-1 sm:max-w-[75%]">
                <div className="text-foreground border-primary/20 bg-primary/10 rounded-2xl rounded-tr-sm border px-4 py-2.5 text-sm">
                  {msg.content}
                </div>
                <span className="text-muted-foreground/70 px-1 text-sm">
                  {formatTime(msg.created_at)}
                </span>
              </div>
              <UserAvatar />
            </div>
          ) : (
            <AssistantMessage msg={msg} onNodeSelect={onNodeSelect} />
          )}
        </div>
      ))}

      {isStreaming && pendingUserMessage && (
        <div className="animate-in fade-in duration-200">
          <div className="flex justify-end gap-3">
            <div className="flex max-w-[85%] flex-col items-end gap-1 sm:max-w-[75%]">
              <div className="text-foreground border-primary/20 bg-primary/10 rounded-2xl rounded-tr-sm border px-4 py-2.5 text-sm">
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
        <div className="animate-in fade-in flex gap-3 duration-200">
          <AssistantAvatar />
          <div className="flex items-center py-2">
            <Spinner
              size="sm"
              variant="primary"
              aria-label="Assistant is thinking"
            />
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  )
}

function AssistantMessage({
  msg,
  onNodeSelect,
}: {
  msg: ChatMessage
  onNodeSelect?: (type: "memory" | "entity", id: string) => void
}) {
  const memories: MemoryRef[] = useMemo(
    () =>
      (msg.context?.memories ?? []).map((m, i) => ({
        index: i + 1,
        id: m.id,
        content: m.content,
        source: m.source,
        status: m.status,
        project: m.project,
      })),
    [msg.context?.memories],
  )

  const entities: EntityRef[] = useMemo(
    () => (msg.context?.entities ?? []).filter((e) => e.name),
    [msg.context?.entities],
  )

  const { processed, components } = useMarkdownWithRefs(
    msg.content,
    memories,
    entities,
    onNodeSelect,
  )

  return (
    <div className="flex gap-3">
      <AssistantAvatar />
      <div className="min-w-0 flex-1">
        <div className="md-prose">
          <ReactMarkdown components={components}>{processed}</ReactMarkdown>
        </div>
        <div className="mt-1 flex items-center gap-2">
          <span className="text-muted-foreground/70 text-sm">
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
  )
}

function StreamingMessage({
  content,
  sources,
  onNodeSelect,
}: {
  content: string
  sources?: {
    memories: {
      index?: number
      content?: string
      source?: string
      tags?: string[]
      score?: number
      id?: string
      project?: string
      status?: MemoryStatus
    }[]
    entities: { id?: string; name?: string; entity_type?: string }[]
  } | null
  onNodeSelect?: (type: "memory" | "entity", id: string) => void
}) {
  const memories: MemoryRef[] = useMemo(
    () =>
      (sources?.memories ?? []).map((m) => ({
        index: m.index ?? 0,
        id: m.id,
        content: m.content,
        source: m.source,
        status: m.status,
        project: m.project,
      })),
    [sources?.memories],
  )

  const entities: EntityRef[] = useMemo(
    () => (sources?.entities ?? []).filter((e): e is EntityRef => !!e.name),
    [sources?.entities],
  )

  const { processed, components } = useMarkdownWithRefs(
    content,
    memories,
    entities,
    onNodeSelect,
  )

  return (
    <div className="animate-in fade-in flex gap-3 duration-200">
      <AssistantAvatar />
      <div className="min-w-0 flex-1">
        <div className="md-prose">
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
  )
}
