import { useMemo, useState } from "react"
import { ClipboardList } from "lucide-react"
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
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { toast } from "darkraise-ui/components/sonner"
import { Tabs, TabsList, TabsTrigger } from "darkraise-ui/components/tabs"
import { EmptyState } from "@/components/darkmem"
import {
  useBoardRecords,
  useBoardViews,
  useCreateBoardView,
  useDeleteBoardView,
  useUpdateBoardView,
  type BoardRecords,
  type BoardView as SavedView,
} from "@/hooks/api"
import {
  applyView,
  boardLanes,
  flattenRecords,
  type BoardRecord,
} from "../lib/records"
import { useRowEditor } from "../use-row-editor"
import { BoardToolbar } from "./board-toolbar"
import { BoardView } from "./board-view"
import { NoteDialog } from "./note-dialog"
import { RecordDetailSheet } from "./record-detail-sheet"
import { RecordsTable } from "./records-table"
import { ViewNameDialog } from "./view-dialogs"

export const DEFAULT_VIEW = "builtin:open-register-items"

type NameDialog = "save" | "rename" | null

/** What a source says about itself (§1.3, §1.4, §5): a parse error, a
 *  malformed row, other workstreams naming a plan, ledger tasks with no
 *  heading. The rest of the board renders regardless. */
export function sourceNotes(data: BoardRecords): string[] {
  const notes: string[] = []
  for (const r of data.registers) {
    if (r.error) notes.push(`${r.uri}: ${r.error}`)
    for (const m of r.malformed) {
      notes.push(`${r.uri}:${m.line}: malformed row (${m.reason})`)
    }
  }
  for (const p of data.plans) {
    if (p.error) notes.push(`${p.uri}: ${p.error}`)
    if (p.other_workstreams > 0) {
      notes.push(
        `${p.uri}: ${p.other_workstreams} other workstream${p.other_workstreams === 1 ? "" : "s"} name this plan`,
      )
    }
    if (p.orphans.length > 0) {
      notes.push(
        `${p.uri}: the ledger names task ${p.orphans.join(", ")} with no heading in the plan`,
      )
    }
  }
  return notes
}

function SourceNotes({ data }: { data: BoardRecords }) {
  const notes = sourceNotes(data)
  if (notes.length === 0) return null
  return (
    <ul
      aria-label="source notes"
      className="text-muted-foreground space-y-0.5 text-xs"
    >
      {notes.map((note) => (
        <li key={note}>{note}</li>
      ))}
    </ul>
  )
}

function PanelBody({
  project,
  view,
  views,
  data,
  onViewChange,
  onOpenDocument,
  onShowInWorkLog,
}: {
  project: string
  view: SavedView
  views: SavedView[]
  data: BoardRecords
  onViewChange: (id: string) => void
  onOpenDocument: (uri: string) => void
  onShowInWorkLog: (workstreamKey: string, task: number) => void
}) {
  const [definition, setDefinition] = useState(view.definition)
  const [text, setText] = useState("")
  const [openId, setOpenId] = useState<string | null>(null)
  const [naming, setNaming] = useState<NameDialog>(null)
  const [deleting, setDeleting] = useState(false)
  const editor = useRowEditor(project)
  const create = useCreateBoardView(project)
  const update = useUpdateBoardView(project)
  const remove = useDeleteBoardView(project)

  const records = useMemo(() => flattenRecords(data), [data])
  const shown = useMemo(
    () => applyView(records, definition, text),
    [records, definition, text],
  )
  const lanes = useMemo(
    () => boardLanes(shown, definition.group_by, definition.show_untracked),
    [shown, definition.group_by, definition.show_untracked],
  )
  const open: BoardRecord | null = records.find((r) => r.id === openId) ?? null
  const dirty = JSON.stringify(definition) !== JSON.stringify(view.definition)
  const fail = (error: Error) => toast.error(error.message)

  return (
    <div className="space-y-3">
      <div className="flex flex-wrap items-center gap-2">
        <Tabs value={view.id} onValueChange={onViewChange}>
          <TabsList>
            {views.map((v) => (
              <TabsTrigger key={v.id} value={v.id}>
                {v.name}
              </TabsTrigger>
            ))}
          </TabsList>
        </Tabs>
        <Button variant="outline" size="sm" onClick={() => setNaming("save")}>
          Save as view
        </Button>
        {!view.builtin && dirty ? (
          <Button
            size="sm"
            disabled={update.isPending}
            onClick={() =>
              update.mutate({ id: view.id, definition }, { onError: fail })
            }
          >
            Update view
          </Button>
        ) : null}
        {!view.builtin ? (
          <>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setNaming("rename")}
            >
              Rename
            </Button>
            <Button variant="ghost" size="sm" onClick={() => setDeleting(true)}>
              Delete
            </Button>
          </>
        ) : null}
      </div>
      <BoardToolbar
        records={records}
        definition={definition}
        onChange={setDefinition}
        text={text}
        onTextChange={setText}
      />
      <SourceNotes data={data} />
      {shown.length === 0 ? (
        <EmptyState
          kind="filtered"
          scope="panel"
          title="No records match this view"
        />
      ) : definition.layout === "board" ? (
        <BoardView
          lanes={lanes}
          pendingId={editor.pendingId}
          onMove={editor.move}
          onOpen={(record) => setOpenId(record.id)}
        />
      ) : (
        <RecordsTable
          records={shown}
          definition={definition}
          onDefinitionChange={setDefinition}
          editor={editor}
          onOpen={(record) => setOpenId(record.id)}
        />
      )}
      <NoteDialog
        prompt={editor.prompt}
        pending={editor.promptPending}
        onCancel={editor.cancelPrompt}
        onConfirm={editor.confirmPrompt}
      />
      <RecordDetailSheet
        record={open}
        onClose={() => setOpenId(null)}
        onOpenDocument={onOpenDocument}
        onShowInWorkLog={(key, task) => {
          setOpenId(null)
          onShowInWorkLog(key, task)
        }}
      />
      <ViewNameDialog
        open={naming !== null}
        title={naming === "rename" ? "Rename view" : "Save as view"}
        initial={
          naming === "rename"
            ? view.name
            : view.builtin
              ? `${view.name} copy`
              : ""
        }
        pending={create.isPending || update.isPending}
        onCancel={() => setNaming(null)}
        onSubmit={(name) => {
          if (naming === "rename") {
            update.mutate(
              { id: view.id, name },
              { onSuccess: () => setNaming(null), onError: fail },
            )
          } else {
            create.mutate(
              { name, definition },
              {
                onSuccess: (saved) => {
                  setNaming(null)
                  onViewChange(saved.id)
                },
                onError: fail,
              },
            )
          }
        }}
      />
      <AlertDialog open={deleting} onOpenChange={setDeleting}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Delete the view {view.name}?</AlertDialogTitle>
            <AlertDialogDescription>
              Only the saved layout goes; no register or plan changes.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              data-variant="destructive"
              onClick={() =>
                remove.mutate(view.id, {
                  onSuccess: () => {
                    setDeleting(false)
                    onViewChange(DEFAULT_VIEW)
                  },
                  onError: fail,
                })
              }
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

/** The Progress tab's board (§3): views over register rows and plan tasks. */
export function BoardPanel({
  project,
  viewId,
  onViewChange,
  onOpenDocument,
  onShowInWorkLog,
}: {
  project: string
  viewId: string | undefined
  onViewChange: (id: string) => void
  onOpenDocument: (uri: string) => void
  onShowInWorkLog: (workstreamKey: string, task: number) => void
}) {
  const records = useBoardRecords(project)
  const views = useBoardViews(project)
  if (records.isError || views.isError) {
    return (
      <EmptyState
        kind="failed"
        scope="panel"
        title="Could not read the board"
        description={(records.error ?? views.error)?.message}
      />
    )
  }
  if (!records.data || !views.data) return <Skeleton className="h-48 w-full" />
  if (records.data.registers.length === 0 && records.data.plans.length === 0) {
    return (
      <EmptyState
        kind="empty"
        icon={ClipboardList}
        scope="panel"
        title="No registers or plans"
        description="The board reads the registers and plans the dr-forge mirror files under superpowers/registers/ and superpowers/plans/."
      />
    )
  }
  const view =
    views.data.find((v) => v.id === viewId) ??
    views.data.find((v) => v.id === DEFAULT_VIEW) ??
    views.data[0]!
  return (
    <PanelBody
      // A new view starts from its own saved definition, not the last draft.
      key={view.id}
      project={project}
      view={view}
      views={views.data}
      data={records.data}
      onViewChange={onViewChange}
      onOpenDocument={onOpenDocument}
      onShowInWorkLog={onShowInWorkLog}
    />
  )
}
