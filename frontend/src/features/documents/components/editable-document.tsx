import { useRef, useState } from "react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { useDocumentBlocks } from "@/hooks/api"
import {
  BlockEditor,
  type BlockEditorControls,
  type HeldWrites,
} from "./block-editor"
import { DocumentLeaveGuard } from "./document-leave-guard"

/** The editor needs the blocks the reader fetches, so it fetches them itself
 *  rather than lifting the query into its parent -- a surface mounts at most
 *  one of reader and editor, and TanStack dedupes the shared key anyway.
 */
export function EditableDocument({ documentId }: { documentId: string }) {
  const blocks = useDocumentBlocks(documentId)
  const [held, setHeld] = useState<HeldWrites>("none")
  const controls = useRef<BlockEditorControls>(null)
  if (blocks.isLoading) return <Skeleton className="h-24 w-full" />
  if (blocks.isError) {
    return (
      <p className="text-destructive-text text-sm">
        This document could not be read.
      </p>
    )
  }
  return (
    <>
      <BlockEditor
        documentId={documentId}
        blocks={blocks.data?.blocks ?? []}
        onHeldWritesChange={setHeld}
        controls={controls}
      />
      <DocumentLeaveGuard
        held={held}
        restoreFocus={() => controls.current?.restoreFocus()}
        onDiscard={() => controls.current?.discardHeld()}
      />
    </>
  )
}
