import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Input } from "darkraise-ui/components/input"
import { Label } from "darkraise-ui/components/label"

function NameForm({
  title,
  initial,
  pending,
  onSubmit,
  onCancel,
}: {
  title: string
  initial: string
  pending: boolean
  onSubmit: (name: string) => void
  onCancel: () => void
}) {
  const [name, setName] = useState(initial)
  const trimmed = name.trim()
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault()
        if (trimmed) onSubmit(trimmed)
      }}
    >
      <DialogHeader>
        <DialogTitle>{title}</DialogTitle>
      </DialogHeader>
      <div className="space-y-1.5 py-3">
        <Label htmlFor="board-view-name">Name</Label>
        <Input
          id="board-view-name"
          value={name}
          maxLength={100}
          onChange={(event) => setName(event.target.value)}
        />
      </div>
      <DialogFooter>
        <Button type="button" variant="outline" onClick={onCancel}>
          Cancel
        </Button>
        <Button type="submit" disabled={!trimmed || pending}>
          Save
        </Button>
      </DialogFooter>
    </form>
  )
}

/** Names a new view or renames a saved one. */
export function ViewNameDialog({
  open,
  title,
  initial,
  pending,
  onSubmit,
  onCancel,
}: {
  open: boolean
  title: string
  initial: string
  pending: boolean
  onSubmit: (name: string) => void
  onCancel: () => void
}) {
  return (
    <Dialog open={open} onOpenChange={(next) => !next && onCancel()}>
      <DialogContent>
        {open ? (
          <NameForm
            title={title}
            initial={initial}
            pending={pending}
            onSubmit={onSubmit}
            onCancel={onCancel}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
