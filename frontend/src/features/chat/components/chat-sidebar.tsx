import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { Plus, Trash2, MessageCircle, Search } from "lucide-react"
import type { ChatConversation } from "@/hooks/api"
import { ChatGradientButton } from "./chat-gradient-button"

interface ChatSidebarProps {
  conversations: ChatConversation[]
  activeId: string | null
  onSelect: (id: string) => void
  onCreate: () => void
  onDelete: (id: string) => void
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  const days = Math.floor(hrs / 24)
  if (days < 30) return `${days}d ago`
  return new Date(dateStr).toLocaleDateString()
}

export function ChatSidebar({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onDelete,
}: ChatSidebarProps) {
  const [search, setSearch] = useState("")

  const filtered = search.trim()
    ? conversations.filter((c) =>
        (c.title ?? "").toLowerCase().includes(search.toLowerCase()),
      )
    : conversations

  return (
    <div className="border-border flex h-full w-[280px] shrink-0 flex-col border-r bg-gradient-to-b from-[#0f1318] to-[#0a0e14]">
      <div className="border-border space-y-2 border-b p-3">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold">Conversations</span>
          <ChatGradientButton
            className="h-7 gap-1 text-xs text-white"
            onClick={onCreate}
          >
            <Plus className="h-3.5 w-3.5" /> New
          </ChatGradientButton>
        </div>
        {conversations.length > 3 && (
          <div className="relative">
            <Search className="text-muted-foreground/50 absolute top-1/2 left-2.5 z-10 h-3.5 w-3.5 -translate-y-1/2" />
            <Input
              placeholder="Search conversations..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="bg-muted/50 placeholder:text-muted-foreground/50 w-full py-1.5 pr-3 pl-8 text-xs focus:border-indigo-500/40 focus:ring-2 focus:ring-indigo-500/30"
            />
          </div>
        )}
      </div>
      <div className="flex-1 space-y-0.5 overflow-auto p-2">
        {conversations.length === 0 && (
          <div className="text-muted-foreground flex flex-col items-center justify-center gap-2 py-8">
            <MessageCircle className="h-8 w-8 text-indigo-500/30" />
            <p className="text-center text-xs">
              No conversations yet.
              <br />
              Click "New" to start one.
            </p>
          </div>
        )}
        {filtered.map((conv) => (
          <div
            key={conv.id}
            className={`group flex cursor-pointer items-center gap-2 rounded-lg px-3 py-2.5 text-sm transition-all ${
              conv.id === activeId
                ? "border border-[rgba(99,102,241,0.15)] bg-[rgba(99,102,241,0.08)] text-indigo-200 shadow-[0_0_12px_rgba(99,102,241,0.05)]"
                : "text-muted-foreground hover:text-foreground border border-transparent hover:bg-[rgba(99,102,241,0.04)]"
            }`}
            onClick={() => onSelect(conv.id)}
          >
            <div className="min-w-0 flex-1">
              <div className="truncate text-[13px] font-medium">
                {conv.title || "Untitled"}
              </div>
              <div className="mt-0.5 flex items-center gap-2">
                <span className="text-xs opacity-50">
                  {timeAgo(conv.updated_at)}
                </span>
                {conv.message_count > 0 && (
                  <span className="text-xs opacity-40">
                    {conv.message_count} msg
                    {conv.message_count !== 1 ? "s" : ""}
                  </span>
                )}
              </div>
            </div>
            <Button
              variant="ghost"
              size="icon"
              className="text-muted-foreground hover:text-destructive h-6 w-6 shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
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
          <p className="text-muted-foreground/50 py-4 text-center text-xs">
            No matches found
          </p>
        )}
      </div>
    </div>
  )
}
