import { useState } from "react"
import { Button } from "darkraise-ui/components/button"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Label } from "darkraise-ui/components/label"
import { Input } from "darkraise-ui/components/input"
import { isBlankNote } from "../lib/records"
import type { NotePrompt } from "../use-row-editor"

function NoteForm({
  prompt,
  pending,
  onCancel,
  onConfirm,
}: {
  prompt: NotePrompt
  pending: boolean
  onCancel: () => void
  onConfirm: (note: string) => void
}) {
  const [note, setNote] = useState(prompt.record.note ?? "")
  return (
    <>
      <DialogHeader>
        <DialogTitle>
          Move {prompt.record.label} to {prompt.state}
        </DialogTitle>
        <DialogDescription>
          A row in {prompt.state} needs a Note saying why. A dash counts as
          blank.
        </DialogDescription>
      </DialogHeader>
      <div className="space-y-1.5">
        <Label htmlFor="board-note">Note</Label>
        {/* One line: a register cell cannot hold a line break. */}
        <Input
          id="board-note"
          value={note}
          onChange={(event) => setNote(event.target.value)}
        />
      </div>
      <DialogFooter>
        <Button variant="outline" disabled={pending} onClick={onCancel}>
          Cancel
        </Button>
        <Button
          disabled={pending || isBlankNote(note)}
          onClick={() => onConfirm(note.trim())}
        >
          Move
        </Button>
      </DialogFooter>
    </>
  )
}

/** The Note a move into verify, deferred or n/a needs (§3). Confirm stays
 *  disabled while the Note is blank, the rule the server enforces too. */
export function NoteDialog({
  prompt,
  pending = false,
  onCancel,
  onConfirm,
}: {
  prompt: NotePrompt | null
  pending?: boolean
  onCancel: () => void
  onConfirm: (note: string) => void
}) {
  return (
    // No dismissal while the edit is in flight: its answer belongs to this
    // prompt, and the user should see it.
    <Dialog
      open={prompt !== null}
      onOpenChange={(open) => !open && !pending && onCancel()}
    >
      <DialogContent>
        {prompt ? (
          <NoteForm
            key={`${prompt.record.id}:${prompt.state}`}
            prompt={prompt}
            pending={pending}
            onCancel={onCancel}
            onConfirm={onConfirm}
          />
        ) : null}
      </DialogContent>
    </Dialog>
  )
}
