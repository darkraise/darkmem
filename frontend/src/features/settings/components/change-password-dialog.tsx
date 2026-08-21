import { useState } from "react"
import { Check } from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"
import { useChangePassword } from "../use-change-password"
import { ConfirmGate } from "./confirm-gate"

/**
 * The admin password change, opened from the user menu.
 *
 * It lived in the Security tab's Auth card, which put the box's one credential
 * three clicks deep behind a settings tab that is otherwise a posture readout.
 * The user menu is where an account action belongs, and it is reachable from
 * every page.
 *
 * `ConfirmGate` is an inline armed panel rather than a nested dialog, so it
 * composes here: the revocation consequence still gets its own deliberate
 * step, and this dialog is not a second one stacked on a first.
 */
export function ChangePasswordDialog({
  open,
  onOpenChange,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [current, setCurrent] = useState("")
  const [next, setNext] = useState("")
  const [confirm, setConfirm] = useState("")
  const password = useChangePassword()

  const filled = current !== "" && next.length >= 8 && next === confirm

  // Why the button will not submit, said out loud. The three rules were
  // enforced silently: a short password with a mismatched confirmation greyed
  // the button out and explained nothing, leaving the operator to guess which
  // field was the problem. Reported only once a field has been touched, so an
  // untouched form is not scolded.
  const blockers = [
    next !== "" && next.length < 8 &&
      "the new password must be at least 8 characters",
    confirm !== "" && next !== confirm && "the confirmation does not match",
    current === "" && next !== "" && "the current password is required",
  ].filter(Boolean) as string[]

  const close = (nextOpen: boolean) => {
    if (!nextOpen) {
      setCurrent("")
      setNext("")
      setConfirm("")
      password.reset()
    }
    onOpenChange(nextOpen)
  }

  return (
    <Dialog open={open} onOpenChange={close}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle>Change admin password</DialogTitle>
          <DialogDescription>
            This box authenticates on one password. Changing it revokes every
            token minted before this moment.
          </DialogDescription>
        </DialogHeader>

        <div className="flex flex-col gap-2.5">
          <div className="flex flex-col gap-1">
            <Label htmlFor="pw-current" className="text-sm">
              Current password
            </Label>
            <Input
              id="pw-current"
              type="password"
              value={current}
              onChange={(e) => setCurrent(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor="pw-new" className="text-sm">
              New password
            </Label>
            <Input
              id="pw-new"
              type="password"
              value={next}
              onChange={(e) => setNext(e.target.value)}
            />
          </div>
          <div className="flex flex-col gap-1">
            <Label htmlFor="pw-confirm" className="text-sm">
              Confirm new password
            </Label>
            <Input
              id="pw-confirm"
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
            />
          </div>
        </div>

        {/* The revocation consequence stays visible next to the trigger — a
            destructive side effect is never demoted to a hover. */}
        <p className="text-warning text-sm">
          <b className="font-semibold">
            Changing your password revokes every token minted before this moment
          </b>{" "}
          — the iat check treats them as dead on arrival, so any other signed-in
          session is signed out immediately. This session is reissued and stays
          live.
        </p>

        {blockers.length > 0 && (
          <p className="text-muted-foreground text-sm">
            Not ready — {blockers.join("; ")}.
          </p>
        )}
        {password.error && (
          <p className="text-destructive text-sm">{password.error}</p>
        )}
        {password.success && (
          <p className="text-success text-sm">
            Password changed — all pre-change tokens are now dead by iat.
          </p>
        )}

        <ConfirmGate
          tone="danger"
          disabled={!filled || password.pending}
          trigger={
            <Button
              variant="outline"
              className="border-primary/60 text-primary"
              disabled={!filled || password.pending}
              tabIndex={-1}
            >
              <Check className="mr-1.5 size-3.5" />
              Change password
            </Button>
          }
          headline="Change the admin password now?"
          desc="Every token minted before this moment is revoked — the iat check treats them as dead on arrival, so any other signed-in session is signed out immediately. This is the box's only credential."
          confirmLabel="Confirm — change password"
          onConfirm={() => {
            password.change({ currentPassword: current, newPassword: next })
            setCurrent("")
            setNext("")
            setConfirm("")
          }}
        />
      </DialogContent>
    </Dialog>
  )
}
