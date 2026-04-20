import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Button } from "darkraise-ui/components/button"

interface Props {
  open: boolean
  shadowModeOn: boolean
  onCancel: () => void
  onConfirm: () => void
  pending: boolean
}

export function UnloadConfirmDialog({ open, shadowModeOn, onCancel, onConfirm, pending }: Props) {
  return (
    <Dialog open={open} onOpenChange={(v) => !v && onCancel()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Unload all ML models?</DialogTitle>
        </DialogHeader>
        <div className="text-sm space-y-2 py-2">
          <p>
            In-flight requests finish on the currently-loaded models; the next request reloads from disk (5–30 s depending on device).
          </p>
          {shadowModeOn && (
            <p className="text-amber-400">
              Shadow mode is enabled — shadow predictions will trigger reloads after this.
            </p>
          )}
        </div>
        <DialogFooter>
          <Button variant="ghost" onClick={onCancel} disabled={pending}>Cancel</Button>
          <Button variant="destructive" onClick={onConfirm} disabled={pending}>
            {pending ? "Unloading…" : "Unload all"}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
