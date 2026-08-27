import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { EmptyState } from "@/components/darkmem"
import { MessageCircle, Plus, Search, Trash2 } from "lucide-react"
import type { ChatConversation } from "@/hooks/api"
import { relativeTime } from "@/lib/format"

interface ChatSidebarProps {
  conversations: ChatConversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onCreate: () => void
  onDelete: (id: string) => void
  isLoading?: boolean
  isError?: boolean
  onRetry?: () => void
}

export function ChatSidebar({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onDelete,
  isLoading = false,
  isError = false,
  onRetry,
}: ChatSidebarProps) {
  const [search, setSearch] = useState("")

  const filtered = search.trim()
    ? conversations.filter((c) =>
        (c.title ?? "").toLowerCase().includes(search.toLowerCase()),
      )
    : conversations

  return (
    /* This is a column of the Chat page's grid, and its only consumer is
       RealChatPage — it is not the flush left rail of a bordered panel, which
       is the shape it was written for. Two things followed from that and both
       were visible: `md:w-72` is 64px wider than the `14rem` grid track, so
       the New button rendered under the message pane; and `border-b` /
       `md:border-r` in place of a card edge left the column unbounded, with a
       stray rule hanging past its content. It now carries the same card as
       DemoThreadList and ChatContextPanel, and takes its width from the track.

       The breakpoint is `lg`, matching where the page grid actually goes
       three-column. It read `md`, so between 768px and 1023px this behaved
       like a desktop rail inside a single-column stack. */
    <div className="border-border bg-card flex max-h-56 w-full flex-col overflow-hidden rounded-md border lg:max-h-none lg:rounded-none lg:border-0 lg:bg-transparent">
      <div className="border-border space-y-2 border-b p-3">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold">Conversations</span>
          <Button className="gap-1" onClick={onCreate}>
            <Plus className="h-3.5 w-3.5" /> New
          </Button>
        </div>
        {conversations.length > 3 && (
          <div className="relative">
            <Search className="text-muted-foreground/50 absolute top-1/2 left-2.5 z-10 h-3.5 w-3.5 -translate-y-1/2" />
            <Input
              placeholder="Search conversations..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full py-1.5 pr-3 pl-8"
            />
          </div>
        )}
      </div>
      <div className="flex-1 space-y-0.5 overflow-auto p-2">
        {isLoading && (
          <div className="space-y-2 p-1">
            <Skeleton className="h-12 w-full rounded-lg" />
            <Skeleton className="h-12 w-full rounded-lg" />
            <Skeleton className="h-12 w-full rounded-lg" />
          </div>
        )}
        {!isLoading && isError && (
          <EmptyState
            kind="failed"
            title="Failed to load conversations"
            action={
              onRetry && (
                <Button variant="outline" onClick={onRetry}>
                  Retry
                </Button>
              )
            }
          />
        )}
        {!isLoading && !isError && conversations.length === 0 && (
          <EmptyState
            kind="empty"
            icon={MessageCircle}
            title="No conversations yet"
            description='Click "New" to start one.'
          />
        )}
        {filtered.map((conv) => (
          <div
            key={conv.id}
            role="button"
            tabIndex={0}
            aria-pressed={conv.id === activeId}
            className={`group flex cursor-pointer items-center gap-2 rounded-lg border px-3 py-2.5 text-sm transition-all ${
              conv.id === activeId
                ? "border-primary/15 bg-primary/10 text-foreground"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/50 border-transparent"
            }`}
            onClick={() => onSelect(conv.id)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.preventDefault()
                onSelect(conv.id)
              }
            }}
          >
            <div className="min-w-0 flex-1">
              <div className="truncate text-sm font-medium">
                {conv.title || "Untitled"}
              </div>
              <div className="mt-0.5 flex items-center gap-2">
                <span className="text-sm opacity-50">
                  {relativeTime(conv.updated_at)}
                </span>
                {(conv.message_count ?? 0) > 0 && (
                  <span className="text-sm opacity-40">
                    {conv.message_count} msg
                    {conv.message_count !== 1 ? "s" : ""}
                  </span>
                )}
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              aria-label="Delete conversation"
              className="text-muted-foreground hover:text-destructive h-8 w-8 shrink-0 opacity-0 transition-opacity group-hover:opacity-100 max-lg:opacity-100"
              onClick={(e) => {
                e.stopPropagation()
                onDelete(conv.id)
              }}
            >
              <Trash2 className="h-3.5 w-3.5" />
            </Button>
          </div>
        ))}
        {search && filtered.length === 0 && (
          <EmptyState
            kind="filtered"
            title="No matches"
            description="No conversation title matches that search."
          />
        )}
      </div>
    </div>
  )
}
