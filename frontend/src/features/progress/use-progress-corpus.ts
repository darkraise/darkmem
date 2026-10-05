import { useMemo } from "react"
import {
  useAllWorkstreams,
  useDocumentContents,
  useDocumentOutlines,
  useLedgerTexts,
  type DocumentListItem,
  type Workstream,
} from "@/hooks/api"
import { parseLedger } from "./lib/parse-ledger"
import { parseEpics } from "./lib/parse-epics"
import { parseGates, type EpicGate } from "./lib/parse-gates"
import {
  parseCompletedPlans,
  parsePlanLedger,
  parsePlanSections,
  planFromOutline,
} from "./lib/parse-plan"
import { assignPlanCodes, planStem } from "./lib/plan-code"
import { planTaskStatus, type PlanStatusSource } from "./lib/plan-status"
import type { Epic, EpicTask, LedgerRow, LedgerStatus } from "./types"

/** The ledger's path convention. A SUFFIX match, not equality: the corpus
 *  import files repo-relative paths, so this project's own ledger lands at
 *  `docs/planning/progress.md` while the convention names
 *  `planning/progress.md`. Mirrors `project-workspace`'s own constant. */
const LEDGER_SUFFIX = "planning/progress.md"
/** Epic files sit beside it. */
const TASKS_INFIX = "planning/tasks/"
/** dr-superpowers plans: `superpowers/plans/<f>.md` from the mirror,
 *  `docs/superpowers/plans/<f>.md` from this repository's own import. */
const PLANS_INFIX = "superpowers/plans/"
const COMPLETED_FILE = "completed.md"

export interface BoardTask {
  task: EpicTask
  row: LedgerRow | undefined
  epic: Epic
  /** Set for a plan task: which signal its status was read from. */
  statusFrom?: PlanStatusSource
}

export interface ProgressCorpus {
  /** False when this project files neither a ledger nor a plan. */
  present: boolean
  loading: boolean
  tasks: BoardTask[]
  epics: Epic[]
  /** Ledger rows by task id, plus a derived row per plan task. */
  rows: Map<string, LedgerRow>
  gates: Map<string, EpicGate>
  /** Ledger rows with no epic task behind them. Surfaced rather than
   *  dropped: a row here means the two files have drifted. */
  orphanRows: LedgerRow[]
}

function basename(uri: string | null | undefined): string {
  return uri?.split("/").pop() ?? ""
}

/** The workstream a plan's ledger lives in: the one whose `plan_uri` names
 *  the plan, else the one keyed by the plan's slug (the mirror's convention,
 *  `.superpowers/sdd/<plan slug>/progress.md` → workstream `<plan slug>`). */
function workstreamFor(filename: string, workstreams: Workstream[]): Workstream | undefined {
  const byUri = workstreams.find((w) => {
    const uri = w.properties?.plan_uri
    return typeof uri === "string" && basename(uri) === filename
  })
  if (byUri) return byUri
  const stem = filename.replace(/\.md$/i, "")
  const slug = planStem(filename)
  return workstreams.find((w) => w.key === stem || w.key === slug)
}

function planRow(task: EpicTask, status: LedgerStatus): LedgerRow {
  return {
    id: task.id,
    title: task.title,
    size: "",
    model: "",
    effort: "",
    version: "",
    owner: "",
    status,
    rawStatus: status,
    commit: "",
    review: "",
    note: "",
  }
}

/**
 * The board's whole data layer: find the planning documents this project
 * files, read them, run the parsers.
 *
 * Two families feed it. **Epic files and `progress.md`** (this repository's
 * own planning corpus) are read in full, as before. **dr-superpowers plans**
 * are read by outline -- each `Task N` heading is a task, referenced as
 * `<plan code>-N` -- and only a plan not yet recorded in `completed.md` is
 * read in full, for its step checkboxes. The plan's work-log ledger, when it
 * has one, supplies the statuses the agent recorded.
 *
 * Nothing is stored and nothing is written -- the spec's §4 decision.
 *
 * `enabled` false reads nothing and only answers `present`, which the
 * document list alone decides: the workspace mounts this on every tab, and
 * the reads are for the board.
 */
export function useProgressCorpus(
  documents: DocumentListItem[],
  project: string,
  enabled = true,
): ProgressCorpus {
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
  const planDocs = useMemo(
    () =>
      documents
        .filter((d) => d.uri?.includes(PLANS_INFIX) && d.uri?.endsWith(".md"))
        .filter((d) => basename(d.uri) !== COMPLETED_FILE)
        // Newest first: the plan in flight leads the board.
        .sort((a, b) => basename(b.uri).localeCompare(basename(a.uri))),
    [documents],
  )
  const completedDoc = useMemo(
    () =>
      documents.find(
        (d) => d.uri?.includes(PLANS_INFIX) && basename(d.uri) === COMPLETED_FILE,
      ) ?? null,
    [documents],
  )
  const codes = useMemo(
    () => assignPlanCodes(planDocs.map((d) => basename(d.uri))),
    [planDocs],
  )

  const outlines = useDocumentOutlines(
    useMemo(() => (enabled ? planDocs.map((d) => d.id) : []), [planDocs, enabled]),
  )
  const workstreams = useAllWorkstreams(project, enabled && planDocs.length > 0)

  const ids = useMemo(
    () =>
      enabled
        ? [
            ...(ledgerDoc ? [ledgerDoc.id, ...taskDocs.map((d) => d.id)] : []),
            ...(completedDoc ? [completedDoc.id] : []),
          ]
        : [],
    [ledgerDoc, taskDocs, completedDoc, enabled],
  )
  const contents = useDocumentContents(ids)

  const completed = useMemo(() => {
    const text = completedDoc ? contents.data?.get(completedDoc.id) : undefined
    return text ? parseCompletedPlans(text) : new Set<string>()
  }, [completedDoc, contents.data])

  const plans = useMemo(() => {
    if (!outlines.data) return []
    return planDocs
      .map((doc) => {
        const filename = basename(doc.uri)
        const nodes = outlines.data.get(doc.id)
        if (!nodes) return null
        return planFromOutline(nodes, {
          code: codes.get(filename) ?? filename,
          filename,
          documentId: doc.id,
          title: doc.title,
        })
      })
      .filter((p): p is Epic => p !== null && p.tasks.length > 0)
  }, [planDocs, outlines.data, codes])

  const planLedgers = useMemo(() => {
    const byPlan = new Map<string, string>()
    for (const plan of plans) {
      const ws = workstreamFor(plan.filename, workstreams.data ?? [])
      if (ws) byPlan.set(plan.filename, ws.id)
    }
    return byPlan
  }, [plans, workstreams.data])
  const ledgers = useLedgerTexts(useMemo(() => [...new Set(planLedgers.values())], [planLedgers]))

  // A plan's source is read only while it is unfinished: a landed plan's
  // tasks are all done, and its steps are fetched when one is opened.
  const activePlanIds = useMemo(
    () =>
      contents.isLoading
        ? []
        : plans.filter((p) => !completed.has(p.filename)).map((p) => p.documentId ?? ""),
    [plans, completed, contents.isLoading],
  )
  const planContents = useDocumentContents(activePlanIds)

  const loading =
    contents.isLoading ||
    outlines.isLoading ||
    workstreams.isLoading ||
    ledgers.isLoading ||
    planContents.isLoading

  return useMemo(() => {
    const present = Boolean(ledgerDoc) || planDocs.length > 0
    const empty: ProgressCorpus = {
      present,
      loading,
      tasks: [], epics: [],
      rows: new Map(), gates: new Map(), orphanRows: [],
    }
    if (loading) return empty

    const epics: Epic[] = []
    const tasks: BoardTask[] = []
    const rows = new Map<string, LedgerRow>()
    let gates = new Map<string, EpicGate>()
    let orphanRows: LedgerRow[] = []

    for (const plan of plans) {
      const ledgerId = planLedgers.get(plan.filename)
      const ledgerText = ledgerId ? ledgers.data?.get(ledgerId) : undefined
      const ledger = ledgerText ? parsePlanLedger(ledgerText) : undefined
      const source = plan.documentId ? planContents.data?.get(plan.documentId) : undefined
      const sections = source ? parsePlanSections(source) : undefined
      const isCompleted = completed.has(plan.filename)

      const withSteps: Epic = {
        ...plan,
        tasks: plan.tasks.map((t) => ({ ...t, doneWhen: sections?.get(t.number)?.steps ?? [] })),
      }
      epics.push(withSteps)
      for (const task of withSteps.tasks) {
        const { status, source: statusFrom } = planTaskStatus({
          number: task.number,
          completed: isCompleted,
          ledger,
          steps: sections?.get(task.number)?.steps,
        })
        const row = planRow(task, status)
        rows.set(task.id, row)
        tasks.push({ task, row, epic: withSteps, statusFrom })
      }
    }

    const ledgerText = ledgerDoc ? contents.data?.get(ledgerDoc.id) : undefined
    if (ledgerText) {
      const ledgerRows = parseLedger(ledgerText)
      for (const r of ledgerRows) rows.set(r.id, r)
      gates = parseGates(ledgerText)

      const epicTasks: BoardTask[] = []
      for (const doc of taskDocs) {
        const text = contents.data?.get(doc.id)
        if (!text) continue
        const epic = { ...parseEpics(text, basename(doc.uri) || doc.id), documentId: doc.id }
        epics.push(epic)
        for (const task of epic.tasks) epicTasks.push({ task, row: rows.get(task.id), epic })
      }
      tasks.push(...epicTasks)

      const seen = new Set(epicTasks.map((t) => t.task.id))
      orphanRows = ledgerRows.filter((r) => !seen.has(r.id))
    }

    return { present, loading: false, tasks, epics, rows, gates, orphanRows }
  }, [
    ledgerDoc, taskDocs, planDocs, contents.data, plans, planLedgers, ledgers.data,
    planContents.data, completed, loading,
  ])
}
