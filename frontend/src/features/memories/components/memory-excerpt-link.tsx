import { Link } from "@tanstack/react-router"
import { Link2 } from "lucide-react"

/** A link to another memory that leads with what it says: the excerpt wraps
 *  to two lines and the 8-char id follows as a secondary mono line, so a
 *  narrow column (phone width, the 19rem aside) still shows the words
 *  rather than an id fragment and a few characters. */
export function MemoryExcerptLink({
  memoryId,
  excerpt,
}: {
  memoryId: string
  excerpt: string
}) {
  return (
    <Link
      to="/memories/$memoryId"
      params={{ memoryId }}
      className="hover:text-primary-text focus-visible:ring-ring flex min-w-0 flex-1 items-start gap-1.5 rounded-sm text-sm transition-colors focus-visible:ring-2 focus-visible:outline-none"
    >
      <Link2
        aria-hidden
        className="text-muted-foreground mt-0.5 h-3.5 w-3.5 shrink-0"
      />
      <span className="min-w-0">
        <span className="line-clamp-2 break-words">“{excerpt}”</span>
        <span className="text-muted-foreground block font-mono text-xs">
          memory {memoryId.slice(0, 8)}
        </span>
      </span>
    </Link>
  )
}
