import { useEffect, useRef } from "react"
import { useBlocker } from "@tanstack/react-router"
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "darkraise-ui/components/alert-dialog"

import type { HeldWrites } from "./block-editor"

export type { HeldWrites }

/** Asks before an in-app navigation leaves a refused block write behind.
 *
 *  Only `refused` blocks: a write merely in flight still lands, because the
 *  document's write queue outlives the editor. Leaving the tab is
 *  `BlockEditor`'s own `beforeunload` listener, so this is router-only and
 *  the editor stays router-free.
 */
export function DocumentLeaveGuard({
  held,
  restoreFocus,
  onDiscard,
}: {
  held: HeldWrites
  restoreFocus: () => void
  onDiscard: () => void
}) {
  const blocker = useBlocker({
    shouldBlockFn: () => held === "refused",
    enableBeforeUnload: false,
    withResolver: true,
  })
  // Leave closes the dialog too; its close must not reset the navigation
  // Leave just let through.
  const leaving = useRef(false)
  const refocus = useRef(false)

  // The dialog closes once the blocker has reset, and its focus trap hands
  // focus back as it closes; this effect runs after that, in the same commit.
  useEffect(() => {
    if (blocker.status !== "idle" || !refocus.current) return
    refocus.current = false
    restoreFocus()
  }, [blocker.status, restoreFocus])

  const stay = () => {
    if (leaving.current || blocker.status !== "blocked") return
    refocus.current = true
    blocker.reset()
  }
  const leave = () => {
    leaving.current = true
    onDiscard()
    blocker.proceed?.()
    leaving.current = false
  }

  return (
    <AlertDialog
      open={blocker.status === "blocked"}
      onOpenChange={(open) => {
        if (!open) stay()
      }}
    >
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Leave without saving?</AlertDialogTitle>
          <AlertDialogDescription>
            This block's edit has not been saved.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Stay</AlertDialogCancel>
          <AlertDialogAction data-variant="destructive" onClick={leave}>
            Leave and discard
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
