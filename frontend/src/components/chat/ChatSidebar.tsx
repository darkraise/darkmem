import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Plus, Trash2, MessageCircle, Search } from "lucide-react";
import type { ChatConversation } from "@/hooks/useApi";

interface ChatSidebarProps {
  conversations: ChatConversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
}

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return new Date(dateStr).toLocaleDateString();
}

export function ChatSidebar({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onDelete,
}: ChatSidebarProps) {
  const [search, setSearch] = useState("");

  const filtered = search.trim()
    ? conversations.filter((c) =>
        (c.title ?? "").toLowerCase().includes(search.toLowerCase()),
      )
    : conversations;

  return (
    <div className="w-[280px] shrink-0 border-r border-border flex flex-col h-full bg-gradient-to-b from-[#0f1318] to-[#0a0e14]">
      <div className="p-3 border-b border-border space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-sm font-semibold">Conversations</span>
          <Button size="sm" className="h-7 text-xs gap-1 bg-gradient-to-r from-indigo-500 to-violet-500 hover:from-indigo-400 hover:to-violet-400 text-white border-0" onClick={onCreate}>
            <Plus className="w-3.5 h-3.5" /> New
          </Button>
        </div>
        {conversations.length > 3 && (
          <div className="relative">
            <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-muted-foreground/50" />
            <input
              type="text"
              placeholder="Search conversations..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full bg-muted/50 border border-border rounded-md pl-8 pr-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground/50 focus:outline-none focus:ring-2 focus:ring-indigo-500/30 focus:border-indigo-500/40"
            />
          </div>
        )}
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-0.5">
        {conversations.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 gap-2 text-muted-foreground">
            <MessageCircle className="w-8 h-8 text-indigo-500/30" />
            <p className="text-xs text-center">
              No conversations yet.<br />Click "New" to start one.
            </p>
          </div>
        )}
        {filtered.map((conv) => (
          <div
            key={conv.id}
            className={`group flex items-center gap-2 rounded-lg px-3 py-2.5 cursor-pointer text-sm transition-all ${
              conv.id === activeId
                ? "bg-[rgba(99,102,241,0.08)] border border-[rgba(99,102,241,0.15)] text-indigo-200 shadow-[0_0_12px_rgba(99,102,241,0.05)]"
                : "text-muted-foreground hover:bg-[rgba(99,102,241,0.04)] hover:text-foreground border border-transparent"
            }`}
            onClick={() => onSelect(conv.id)}
          >
            <div className="flex-1 min-w-0">
              <div className="truncate font-medium text-[13px]">
                {conv.title || "Untitled"}
              </div>
              <div className="flex items-center gap-2 mt-0.5">
                <span className="text-xs opacity-50">
                  {timeAgo(conv.updated_at)}
                </span>
                {conv.message_count > 0 && (
                  <span className="text-xs opacity-40">
                    {conv.message_count} msg{conv.message_count !== 1 ? "s" : ""}
                  </span>
                )}
              </div>
            </div>
            <button
              className="opacity-0 group-hover:opacity-100 text-muted-foreground hover:text-destructive shrink-0 transition-opacity"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(conv.id);
              }}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
        {search && filtered.length === 0 && (
          <p className="text-xs text-muted-foreground/50 text-center py-4">
            No matches found
          </p>
        )}
      </div>
    </div>
  );
}
