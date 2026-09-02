import { Skeleton } from "darkraise-ui/components/skeleton"
import { useDocumentBlocks, useDocumentOutline } from "@/hooks/api"
import { BlockView } from "./block-view"

/** Outline rail plus the block body, in reading order.
 *
 * Reading order is what `document_blocks` serves -- a flat, `order_index`
 * sorted list -- so block-level nesting is deliberately not reconstructed
 * here. The outline is the structure the reader navigates by.
 */
export function DocumentReader({ documentId }: { documentId: string }) {
  const outline = useDocumentOutline(documentId)
  const blocks = useDocumentBlocks(documentId)

  if (blocks.isLoading) {
    return (
      <div className="space-y-2">
        <Skeleton className="h-5 w-2/3" />
        <Skeleton className="h-20 w-full" />
      </div>
    )
  }
  if (blocks.isError) {
    return (
      <p className="text-destructive text-sm">
        This document could not be read — a failed read, not an empty document.
      </p>
    )
  }

  const rows = blocks.data?.blocks ?? []
  if (rows.length === 0) {
    return (
      <p className="text-muted-foreground text-sm">
        This document is filed but holds no blocks.
      </p>
    )
  }

  return (
    <div className="flex gap-5">
      {(outline.data?.items.length ?? 0) > 0 ? (
        <nav className="hidden w-52 shrink-0 lg:block">
          <p className="text-muted-foreground pb-1.5 font-mono text-[10px] tracking-wide uppercase">
            outline
          </p>
          <ul className="space-y-0.5">
            {outline.data!.items.map((node) => (
              <li key={node.block_id}>
                <a
                  href={`#${node.block_id}`}
                  className="text-muted-foreground hover:text-foreground block truncate text-sm"
                  style={{ paddingLeft: `${Math.max(0, node.level - 1) * 10}px` }}
                >
                  {node.text}
                </a>
              </li>
            ))}
          </ul>
        </nav>
      ) : null}

      <div className="min-w-0 flex-1 space-y-2.5">
        {rows.map((block) => (
          <div key={block.block_id} id={block.block_id}>
            <BlockView block={block} />
          </div>
        ))}
      </div>
    </div>
  )
}
