import { useState } from "react"

/** The one save path every Settings dialog takes: the dialog stays open while
 *  the write is in flight, closes once it lands, and on a refusal stays open
 *  with the edits and shows the server's reason. The binding behind `save`
 *  announces the success; a refusal is the dialog's to show. */
export function useDialogSave(close: () => void) {
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const run = (save: () => Promise<unknown>) => {
    setPending(true)
    setError(null)
    save().then(
      () => {
        setPending(false)
        close()
      },
      (reason: unknown) => {
        setPending(false)
        setError(reason instanceof Error ? reason.message : String(reason))
      },
    )
  }

  /** For the dialog's `onOpenChange`: a save in flight is not dismissed. */
  const guard = (onOpenChange: (open: boolean) => void) => (open: boolean) => {
    if (!open && pending) return
    onOpenChange(open)
  }

  return { pending, error, run, guard }
}
