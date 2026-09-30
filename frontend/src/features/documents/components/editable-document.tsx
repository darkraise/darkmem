import { Skeleton } from "darkraise-ui/components/skeleton"
import { useDocumentBlocks } from "@/hooks/api"
import { BlockEditor } from "./block-editor"

/** The editor needs the blocks the reader fetches, so it fetches them itself
 *  rather than lifting the query into its parent -- a surface mounts at most
 *  one of reader and editor, and TanStack dedupes the shared key anyway.
 */
export function EditableDocument({ documentId }: { documentId: string }) {
  const blocks = useDocumentBlocks(documentId)
  if (blocks.isLoading) return <Skeleton className="h-24 w-full" />
  if (blocks.isError) {
    return (
      <p className="text-destructive text-sm">
        This document could not be read.
      </p>
    )
  }
  return (
    <BlockEditor documentId={documentId} blocks={blocks.data?.blocks ?? []} />
  )
}
