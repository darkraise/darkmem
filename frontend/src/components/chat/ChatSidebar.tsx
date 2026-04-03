import { Button } from "@/components/ui/button";
import { Plus, Trash2 } from "lucide-react";
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
  return `${days}d ago`;
}

export function ChatSidebar({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onDelete,
}: ChatSidebarProps) {
  return (
    <div className="w-[280px] shrink-0 border-r border-border flex flex-col h-full">
      <div className="p-3 border-b border-border flex items-center justify-between">
        <span className="text-sm font-semibold">Conversations</span>
        <Button size="sm" variant="ghost" className="h-7 text-xs gap-1" onClick={onCreate}>
          <Plus className="w-3.5 h-3.5" /> New
        </Button>
      </div>
      <div className="flex-1 overflow-auto p-2 space-y-0.5">
        {conversations.length === 0 && (
          <p className="text-xs text-muted-foreground p-3 text-center">
            No conversations yet
          </p>
        )}
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`group flex items-center gap-2 rounded-md px-3 py-2 cursor-pointer text-sm transition-colors ${
              conv.id === activeId
                ? "bg-primary/20 text-primary"
                : "text-muted-foreground hover:bg-muted hover:text-foreground"
            }`}
            onClick={() => onSelect(conv.id)}
          >
            <span className="flex-1 truncate">
              {conv.title || "Untitled"}
            </span>
            <span className="text-xs opacity-50 shrink-0 group-hover:hidden">
              {timeAgo(conv.updated_at)}
            </span>
            <button
              className="hidden group-hover:block text-muted-foreground hover:text-destructive shrink-0"
              onClick={(e) => {
                e.stopPropagation();
                onDelete(conv.id);
              }}
            >
              <Trash2 className="w-3.5 h-3.5" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
