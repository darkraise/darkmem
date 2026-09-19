import { useMemo, useState } from "react"
import { EmptyState } from "@/components/darkmem"
import { MessageCircle, Plus, Search } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { Input } from "darkraise-ui/components/input"
import { cn } from "darkraise-ui/lib"
import type { DemoChatThread } from "@/demo/types"

export function DemoThreadList({
  threads,
  activeId,
  onSelect,
  onNew,
}: {
  threads: DemoChatThread[]
  activeId: string | null
  onSelect: (id: string) => void
  onNew: () => void
}) {
  const [query, setQuery] = useState("")
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    if (q === "") return threads
    return threads.filter((t) => t.title.toLowerCase().includes(q))
  }, [threads, query])

  return (
    <div className="border-border bg-card flex min-h-0 flex-col overflow-hidden rounded-md border lg:rounded-none lg:border-0 lg:bg-transparent">
      <div className="border-border flex flex-wrap items-center justify-between gap-2 border-b px-3 py-2">
        <span className="min-w-0 truncate text-sm font-semibold">Conversations</span>
        <Button className="rounded-full" onClick={onNew}>
          <Plus aria-hidden className="h-3 w-3" />
          New
        </Button>
      </div>
      <div className="p-2 pb-1">
        <Input
          prefix={<Search aria-hidden className="h-3.5 w-3.5" />}
          placeholder="Search conversations…"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          aria-label="Search conversations"
        />
      </div>
      {threads.length === 0 ? (
        <EmptyState
          kind="empty"
          icon={MessageCircle}
          title="No conversations yet"
          description="Start one with New, and it appears here."
        />
      ) : filtered.length === 0 ? (
        <p className="text-muted-foreground p-3 text-sm">
          No conversation title matches "{query}" — nothing was hidden beyond
          this filter.
        </p>
      ) : (
        <div className="flex flex-col gap-0.5 p-2">
          {filtered.map((thread) => (
            <button
              key={thread.id}
              type="button"
              onClick={() => onSelect(thread.id)}
              className={cn(
                "space-y-0.5 rounded-md border border-transparent px-2.5 py-2 text-left",
                thread.id === activeId
                  ? "bg-primary/10 border-primary/30"
                  : "hover:bg-muted/50",
              )}
            >
              <span className="block text-sm font-medium">{thread.title}</span>
              <span className="text-muted-foreground flex gap-2 text-sm">
                <span>{thread.updated_label}</span>
                <span>{thread.messages.length} msgs</span>
              </span>
            </button>
          ))}
        </div>
      )}
    </div>
  )
}
