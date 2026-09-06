import { ListTree } from "lucide-react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { useDocumentOutline } from "@/hooks/api"

/** The open document's heading tree, as a jump list.
 *
 * Navigation is a callback carrying the block id, never an `#id` anchor. Two
 * readers can be mounted at once (the artifacts pane and the ledger) and block
 * ids are unique per document, not per page -- so `href="#block"` is ambiguous
 * exactly when both are open. The caller resolves it inside its own reader,
 * which is also what puts the focus ring on the row the reader landed on.
 */
export function DocumentOutline({
  documentId,
  activeBlockId = null,
  onNavigate,
}: {
  documentId: string
  /** The block the reader is currently focused on, if any. */
  activeBlockId?: string | null
  onNavigate: (blockId: string) => void
}) {
  const outline = useDocumentOutline(documentId)
  const items = outline.data?.items ?? []

  if (outline.isLoading) {
    return (
      <div className="space-y-1.5">
        <Skeleton className="h-3 w-2/3" />
        <Skeleton className="h-3 w-1/2" />
        <Skeleton className="h-3 w-3/4" />
      </div>
    )
  }
  // A document with no headings has no outline to show, and an empty rail
  // taking a column's width says less than nothing.
  if (items.length === 0) return null

  return (
    <nav aria-label="document outline">
      <p className="text-muted-foreground flex items-center gap-1.5 pb-2 font-mono text-[10px] tracking-wide uppercase">
        <ListTree aria-hidden className="size-3.5" />
        outline
      </p>
      <ul className="space-y-0.5">
        {items.map((node) => {
          const active = node.block_id === activeBlockId
          return (
            <li key={node.block_id}>
              <button
                type="button"
                onClick={() => onNavigate(node.block_id)}
                style={{ paddingLeft: `${6 + Math.max(0, node.level - 1) * 10}px` }}
                className={`hover:bg-muted/60 focus-visible:ring-primary/40 block w-full truncate rounded-sm py-0.5 pr-1.5 text-left text-sm transition-colors focus-visible:ring-2 focus-visible:outline-none ${
                  active
                    ? "text-foreground border-primary border-l-2 font-medium"
                    : "text-muted-foreground hover:text-foreground border-l-2 border-transparent"
                }`}
                title={node.text}
              >
                {node.text}
              </button>
            </li>
          )
        })}
      </ul>
    </nav>
  )
}
