import { useImperativeHandle, useRef, useState, type Ref } from "react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { useDocumentBlocks } from "@/hooks/api"
import {
  BlockEditor,
  type BlockEditorControls,
  type HeldWrites,
} from "./block-editor"
import { DocumentLeaveGuard } from "./document-leave-guard"

/** What a host calls before a switch that unmounts the editor without a
 *  router navigation: the action runs at once, or once the operator chooses
 *  Leave and discard over a refused write. */
export interface DocumentLeaveHandle {
  attempt: (action: () => void) => void
}

/** The editor needs the blocks the reader fetches, so it fetches them itself
 *  rather than lifting the query into its parent -- a surface mounts at most
 *  one of reader and editor, and TanStack dedupes the shared key anyway.
 */
export function EditableDocument({
  documentId,
  leave,
}: {
  documentId: string
  leave?: Ref<DocumentLeaveHandle>
}) {
  const blocks = useDocumentBlocks(documentId)
  const [held, setHeld] = useState<HeldWrites>("none")
  const [pending, setPending] = useState<(() => void) | null>(null)
  const controls = useRef<BlockEditorControls>(null)
  useImperativeHandle(
    leave,
    () => ({
      attempt: (action) => {
        if (held === "refused") setPending(() => action)
        else action()
      },
    }),
    [held],
  )
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
        pending={pending}
        onPendingSettled={() => setPending(null)}
      />
    </>
  )
}
