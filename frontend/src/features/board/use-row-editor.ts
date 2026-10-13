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

  const save = (record: BoardRecord, changes: RowChanges) => {
    if (record.type !== "register_row" || !record.contentHash) return
    mutation.mutate(
      {
        documentId: record.documentId,
        number: record.number,
        expectedHash: record.contentHash,
        ...changes,
      },
      {
        onError: (error) =>
          toast.error(
            error instanceof ApiError && error.code === "hash_conflict"
              ? CONFLICT_MESSAGE
              : error.message,
          ),
      },
    )
  }

  const move = (record: BoardRecord, toState: string) => {
    const intent = planMove(record, toState)
    if (intent === "note") setPrompt({ record, state: toState })
    else if (intent === "patch") save(record, { state: toState })
  }

  const confirmPrompt = (note: string) => {
    if (prompt) save(prompt.record, { state: prompt.state, note })
    setPrompt(null)
  }

  const variables = mutation.isPending ? mutation.variables : undefined
  const pendingId = variables
    ? `r:${variables.documentId}:${variables.number}`
    : null

  return {
    save,
    move,
    prompt,
    confirmPrompt,
    cancelPrompt: () => setPrompt(null),
    pendingId,
  }
}

export type RowEditor = ReturnType<typeof useRowEditor>
