import { useMemo } from "react"
import { useDocumentContents, type DocumentListItem } from "@/hooks/api"
import { parseLedger } from "./lib/parse-ledger"
import { parseEpics } from "./lib/parse-epics"
import { parseGates, type EpicGate } from "./lib/parse-gates"
import type { Epic, EpicTask, LedgerRow } from "./types"

/** The ledger's path convention. A SUFFIX match, not equality: the corpus
 *  import files repo-relative paths, so this project's own ledger lands at
 *  `docs/planning/progress.md` while the convention names
 *  `planning/progress.md`. Mirrors `project-workspace`'s own constant. */
const LEDGER_SUFFIX = "planning/progress.md"
/** Epic files sit beside it. */
const TASKS_INFIX = "planning/tasks/"

export interface BoardTask {
  task: EpicTask
  row: LedgerRow | undefined
  epic: Epic
}

export interface ProgressCorpus {
  /** False when this project files no ledger -- every project but the one
   *  whose corpus holds these planning files. */
  present: boolean
  loading: boolean
  tasks: BoardTask[]
  epics: Epic[]
  rows: Map<string, LedgerRow>
  gates: Map<string, EpicGate>
  /** Ledger rows with no epic task behind them. Surfaced rather than
   *  dropped: a row here means the two files have drifted. */
  orphanRows: LedgerRow[]
}

/**
 * The board's whole data layer: find the planning documents this project
 * files, read their source, run the parsers.
 *
 * Nothing is stored and nothing is written -- the spec's §4 decision. The
 * board is a projection of two committed markdown files, so it fills only for
 * the project whose corpus contains them.
 */
export function useProgressCorpus(documents: DocumentListItem[]): ProgressCorpus {
  const ledgerDoc = useMemo(
    () => documents.find((d) => d.uri?.endsWith(LEDGER_SUFFIX)) ?? null,
    [documents],
  )
  const taskDocs = useMemo(
    () =>
      documents
        .filter((d) => d.uri?.includes(TASKS_INFIX) && d.uri?.endsWith(".md"))
        .sort((a, b) => (a.uri ?? "").localeCompare(b.uri ?? "")),
    [documents],
  )

  const ids = useMemo(
    () => (ledgerDoc ? [ledgerDoc.id, ...taskDocs.map((d) => d.id)] : []),
    [ledgerDoc, taskDocs],
  )
  const contents = useDocumentContents(ids)

  return useMemo(() => {
    const empty: ProgressCorpus = {
      present: Boolean(ledgerDoc),
      loading: contents.isLoading,
      tasks: [], epics: [],
      rows: new Map(), gates: new Map(), orphanRows: [],
    }
    if (!ledgerDoc || !contents.data) return empty

    const ledgerText = contents.data.get(ledgerDoc.id)
    if (!ledgerText) return empty

    const rows = new Map(parseLedger(ledgerText).map((r) => [r.id, r]))
    const gates = parseGates(ledgerText)

    const epics: Epic[] = []
    for (const doc of taskDocs) {
      const text = contents.data.get(doc.id)
      if (!text) continue
      epics.push(parseEpics(text, doc.uri?.split("/").pop() ?? doc.id))
    }

    const tasks: BoardTask[] = epics.flatMap((epic) =>
      epic.tasks.map((task) => ({ task, row: rows.get(task.id), epic })),
    )

    const seen = new Set(tasks.map((t) => t.task.id))
    return {
      present: true,
      loading: false,
      tasks,
      epics,
      rows,
      gates,
      orphanRows: [...rows.values()].filter((r) => !seen.has(r.id)),
    }
  }, [ledgerDoc, taskDocs, contents.data, contents.isLoading])
}
