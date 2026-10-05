import { useMemo } from "react"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import {
  Clipboard,
  ClipboardIndicator,
  ClipboardTrigger,
} from "darkraise-ui/components/clipboard"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { Check, Copy, FileText, Square, SquareCheck } from "lucide-react"
import { AppMarkdown } from "@/components/markdown"
import { useDocumentContents } from "@/hooks/api"
import type { BoardTask } from "../use-progress-corpus"
import { parsePlanSections } from "../lib/parse-plan"
import { PLAN_STATUS_SOURCE_LABEL } from "../lib/plan-status"
import { plainText } from "../lib/plain-text"

/**
 * One task in full.
 *
 * An epic task shows its epic file's done-when checklist, labelled as the
 * implementer's own and never as progress: the corpus carries 806 unchecked
 * boxes against 17 checked across a project that has shipped through T3.28
 * and cleared three gates, so aggregating them would report roughly 2% done.
 *
 * A plan task shows its section of the plan, read when the task is opened,
 * and says which signal its status came from.
 */
export function TaskDetail({
  entry,
  onClose,
  onOpenDocument,
}: {
  entry: BoardTask | null
  onClose: () => void
  onOpenDocument?: (documentId: string, blockId: string | null) => void
}) {
  if (!entry) return null
  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-3xl">
        <TaskDetailBody entry={entry} onOpenDocument={onOpenDocument} />
      </DialogContent>
    </Dialog>
  )
}

function TaskDetailBody({
  entry,
  onOpenDocument,
}: {
  entry: BoardTask
  onOpenDocument?: (documentId: string, blockId: string | null) => void
}) {
  const { task, row, epic, statusFrom } = entry
  const isPlan = epic.kind === "plan"
  const documentId = epic.documentId ?? null

  return (
    <>
      <DialogHeader>
        <DialogTitle className="flex items-baseline gap-2 pr-6">
          <span className="text-primary-text shrink-0 font-mono text-base whitespace-nowrap">
            {task.id}
          </span>
          <Clipboard value={task.id} toast={{ success: `Copied ${task.id}` }} className="shrink-0 self-center">
            <ClipboardTrigger aria-label={`Copy reference ${task.id}`} className="size-6">
              <ClipboardIndicator
                copied={<Check className="size-3.5" />}
                fallback={<Copy className="size-3.5" />}
              />
            </ClipboardTrigger>
          </Clipboard>
          <span>{plainText(task.title)}</span>
        </DialogTitle>
        <DialogDescription>
          {isPlan ? `Task ${task.number} of plan ${epic.key} — ` : `${epic.key} — `}
          {epic.title}
          {task.lane ? ` · ${task.lane}` : ""}
        </DialogDescription>
      </DialogHeader>

      <ScrollArea className="max-h-[65vh] pr-3">
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-1.5">
            {row && <Badge variant="outline">{row.rawStatus || "no status"}</Badge>}
            {task.after && (
              <Badge variant="secondary" className="font-normal">
                after {task.after}
              </Badge>
            )}
            {Object.entries(task.meta).map(([k, v]) => (
              <Badge key={k} variant="secondary" className="font-normal">
                {k}: {v}
              </Badge>
            ))}
            {documentId && onOpenDocument && (
              <Button
                variant="outline"
                size="sm"
                className="ml-auto h-7"
                onClick={() => onOpenDocument(documentId, task.blockId ?? null)}
              >
                <FileText aria-hidden className="size-3.5" />
                Open in {isPlan ? "plan" : "epic file"}
              </Button>
            )}
          </div>

          {statusFrom && (
            <p className="text-muted-foreground text-sm">
              Status from {PLAN_STATUS_SOURCE_LABEL[statusFrom]}.
            </p>
          )}

          {row?.note && (
            <Field label="Note">
              <p className="text-sm leading-relaxed">{plainText(row.note)}</p>
            </Field>
          )}
          {row?.review && (
            <Field label="Review">
              <p className="text-sm leading-relaxed">{plainText(row.review)}</p>
            </Field>
          )}
          {row?.commit && (
            <Field label="Commit">
              <p className="font-mono text-sm">{row.commit}</p>
            </Field>
          )}

          {isPlan && documentId ? (
            <PlanSection documentId={documentId} number={task.number} />
          ) : (
            task.doneWhen.length > 0 && (
              <Field label="Done-when checklist">
                <p className="text-muted-foreground mb-2 text-sm leading-relaxed">
                  These boxes are not kept up to date; status comes from the
                  ledger.
                </p>
                <ul className="space-y-1">
                  {task.doneWhen.map((item, i) => (
                    <li key={i} className="flex items-start gap-1.5 text-sm">
                      {item.checked ? (
                        <SquareCheck aria-hidden className="text-primary-text mt-0.5 size-3.5 shrink-0" />
                      ) : (
                        <Square aria-hidden className="text-muted-foreground mt-0.5 size-3.5 shrink-0" />
                      )}
                      <span className="leading-snug">{plainText(item.text)}</span>
                    </li>
                  ))}
                </ul>
              </Field>
            )
          )}

          {epic.entryGate && (
            <Field label="Epic entry gate">
              <p className="text-sm leading-relaxed">{plainText(epic.entryGate)}</p>
            </Field>
          )}
        </div>
      </ScrollArea>
    </>
  )
}

/** The task's own section of its plan, read on open. A landed plan's source
 *  is never read for the board itself, so this is the first read of it. */
function PlanSection({ documentId, number }: { documentId: string; number: string }) {
  const ids = useMemo(() => [documentId], [documentId])
  const contents = useDocumentContents(ids)
  const section = useMemo(() => {
    const text = contents.data?.get(documentId)
    return text ? (parsePlanSections(text).get(number) ?? null) : null
  }, [contents.data, documentId, number])

  if (contents.isLoading) return <Skeleton className="h-24 w-full" />
  if (contents.isError) {
    return <p className="text-muted-foreground text-sm">The plan could not be read.</p>
  }
  if (!section?.body) {
    return <p className="text-muted-foreground text-sm">The plan has no body under this task.</p>
  }
  return (
    <Field label="Task in the plan">
      <div className="text-sm">
        <AppMarkdown>{section.body}</AppMarkdown>
      </div>
    </Field>
  )
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-muted-foreground pb-1 font-mono text-xs tracking-wide uppercase">
        {label}
      </p>
      {children}
    </div>
  )
}
