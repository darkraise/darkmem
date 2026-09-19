import { Link } from "@tanstack/react-router"
import { ExternalLink } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { useMemory } from "@/hooks/api"
import { LifecycleBadge } from "./lifecycle-badge"

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium",
    timeStyle: "short",
  })
}

/**
 * One memory, read without leaving the page that pointed at it.
 *
 * The surfaces that link to a memory from somewhere else -- a document's
 * related-memories card today -- are places where the memory is evidence for
 * whatever is already open. Routing to `/memories/$memoryId` to read three
 * lines of content throws that context away and makes the way back a browser
 * button, so this is a dialog. The full page is still one click on, and it is
 * where the lineage, the timeline and the editor live: this deliberately
 * renders none of them, so there is no second, drifting memory detail view.
 */
export function MemoryPeekDialog({
  memoryId,
  onClose,
}: {
  /** `null` closes it. Passing the id rather than the row means this always
   *  reads the single-get door, so what it shows is the stored memory and not
   *  a projection some other surface happened to be holding. */
  memoryId: string | null
  onClose: () => void
}) {
  const memory = useMemory(memoryId ?? "")
  if (!memoryId) return null

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <span>Memory</span>
            <span className="text-muted-foreground font-mono text-sm font-normal">
              {memoryId.slice(0, 8)}
            </span>
            <LifecycleBadge status={memory.data?.status} />
          </DialogTitle>
          <DialogDescription>
            {memory.data
              ? `${memory.data.source} · captured ${formatDateTime(memory.data.created_at)}`
              : "reading this memory…"}
          </DialogDescription>
        </DialogHeader>

        {memory.isLoading ? (
          <Skeleton className="h-24 w-full rounded-md" />
        ) : memory.isError ? (
          <p className="text-destructive text-sm">
            This memory could not be read — a failed read, not a missing
            memory.
          </p>
        ) : memory.data ? (
          <ScrollArea className="max-h-[55vh] pr-3">
            <div className="space-y-3">
              <p className="text-sm leading-relaxed whitespace-pre-wrap">
                {memory.data.content}
              </p>

              {memory.data.summary ? (
                <div>
                  <p className="text-muted-foreground pb-1 font-mono text-xs tracking-wide uppercase">
                    summary
                  </p>
                  <p className="text-muted-foreground text-sm">
                    {memory.data.summary}
                  </p>
                </div>
              ) : null}

              <div className="flex flex-wrap gap-1.5">
                {memory.data.classified_type ? (
                  <Badge variant="secondary" className="font-normal">
                    {memory.data.classified_type}
                  </Badge>
                ) : null}
                {memory.data.memory_type ? (
                  <Badge variant="outline" className="font-normal">
                    {memory.data.memory_type}
                  </Badge>
                ) : null}
                {memory.data.tags.map((tag) => (
                  <Badge key={tag} variant="outline" className="font-normal">
                    {tag}
                  </Badge>
                ))}
              </div>
            </div>
          </ScrollArea>
        ) : null}

        <Link
          to="/memories/$memoryId"
          params={{ memoryId }}
          onClick={onClose}
          className="text-primary-text hover:text-primary-text/80 inline-flex items-center gap-1.5 text-sm"
        >
          <ExternalLink aria-hidden className="size-3.5" />
          Open the full memory
        </Link>
      </DialogContent>
    </Dialog>
  )
}
