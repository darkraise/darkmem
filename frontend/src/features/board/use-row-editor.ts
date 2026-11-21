import { useState } from "react"
import { toast } from "darkraise-ui/components/sonner"
import { useRegisterRowEdit, type RowChanges } from "@/hooks/api"
import { ApiError } from "@/lib/api"
import { planMove, type BoardRecord } from "./lib/records"

export const CONFLICT_MESSAGE =
  "This register changed since the board loaded it; the board has reloaded it. Try again."

/** A move into a state that needs a Note, waiting for one. */
export interface NotePrompt {
  record: BoardRecord
  state: string
}

/** Register row edits from the board and the table. Pessimistic: nothing
 *  moves until the PATCH answers, and every answer re-reads the records. */
export function useRowEditor(project: string) {
  const mutation = useRegisterRowEdit(project)
  const [prompt, setPrompt] = useState<NotePrompt | null>(null)
  const [refused, setRefused] = useState<Record<string, number>>({})
  const [inFlight, setInFlight] = useState<Record<string, number>>({})
  // Edits queued behind a conflict are refused with that same error; one
  // conflict is one message.
  const [reported] = useState(() => new WeakSet<object>())

  const save = (
    record: BoardRecord,
    changes: RowChanges,
    onSaved?: () => void,
    onRefused?: (error: Error) => void,
  ) => {
    if (record.type !== "register_row" || !record.contentHash) return
    const count = (delta: number) =>
      setInFlight((prev) => ({
        ...prev,
        [record.id]: (prev[record.id] ?? 0) + delta,
      }))
    count(1)
    // mutateAsync, not mutate: mutate's per-call callbacks fire only for the
    // latest call, so an earlier edit's refusal would never be reported.
    mutation
      .mutateAsync({
        documentId: record.documentId,
        number: record.number,
        expectedHash: record.contentHash,
        ...changes,
      })
      .then(
        () => onSaved?.(),
        (error: Error) => {
          setRefused((prev) => ({
            ...prev,
            [record.id]: (prev[record.id] ?? 0) + 1,
          }))
          if (!reported.has(error)) {
            reported.add(error)
            toast.error(
              error instanceof ApiError && error.code === "hash_conflict"
                ? CONFLICT_MESSAGE
                : error.message,
            )
          }
          onRefused?.(error)
        },
      )
      .finally(() => count(-1))
  }

  const move = (record: BoardRecord, toState: string) => {
    const intent = planMove(record, toState)
    if (intent === "note") setPrompt({ record, state: toState })
    else if (intent === "patch") save(record, { state: toState })
  }

  // A refusal keeps the prompt open so the typed Note survives. A hash
  // conflict closes it: the prompt holds the stale record, so every retry
  // would conflict again, and the user should see the reloaded row first.
  // Each answer closes only the prompt it was sent for: by the time it lands
  // the user may have opened another.
  const confirmPrompt = (note: string) => {
    if (!prompt) return
    const sent = prompt
    const close = () => setPrompt((open) => (open === sent ? null : open))
    save(sent.record, { state: sent.state, note }, close, (error) => {
      if (error instanceof ApiError && error.code === "hash_conflict") close()
    })
  }

  // From the per-record count, not mutation.variables: TanStack keeps only
  // the latest call's variables, so an earlier in-flight edit would unmark.
  const isPending = (id: string) => (inFlight[id] ?? 0) > 0

  return {
    save,
    move,
    prompt,
    confirmPrompt,
    cancelPrompt: () => setPrompt(null),
    isPending,
    promptPending: prompt !== null && isPending(prompt.record.id),
    /** Changes whenever a record's edit is refused, so an uncontrolled cell
     *  keyed on it drops the text the server did not accept. */
    editEpoch: (id: string) => refused[id] ?? 0,
  }
}

export type RowEditor = ReturnType<typeof useRowEditor>
