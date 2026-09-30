import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "darkraise-ui/components/dialog"
import { Badge } from "darkraise-ui/components/badge"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import { Square, SquareCheck } from "lucide-react"
import type { BoardTask } from "../use-progress-corpus"
import { plainText } from "../lib/plain-text"

/**
 * One task in full, including the epic file's done-when checklist.
 *
 * The checklist is labelled as the implementer's own, never as progress. The
 * corpus carries 806 unchecked boxes against 17 checked across a project that
 * has shipped through T3.28 and cleared three gates, so aggregating them into
 * a percentage would report roughly 2% done. The measurement is stated in the
 * copy rather than left for a reader to rediscover.
 */
export function TaskDetail({
  entry,
  onClose,
}: {
  entry: BoardTask | null
  onClose: () => void
}) {
  if (!entry) return null
  const { task, row, epic } = entry

  return (
    <Dialog open onOpenChange={(open) => !open && onClose()}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle className="flex items-baseline gap-2">
            <span className="text-primary-text font-mono text-base">{task.id}</span>
            <span>{plainText(task.title)}</span>
          </DialogTitle>
          <DialogDescription>
            {epic.key} — {epic.title}
            {task.lane ? ` · ${task.lane}` : ""}
          </DialogDescription>
        </DialogHeader>

        <ScrollArea className="max-h-[60vh] pr-3">
          <div className="space-y-4">
            <div className="flex flex-wrap gap-1.5">
              {row && (
                <Badge variant="outline">{row.rawStatus || "no status"}</Badge>
              )}
              {Object.entries(task.meta).map(([k, v]) => (
                <Badge key={k} variant="secondary" className="font-normal">
                  {k}: {v}
                </Badge>
              ))}
            </div>

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

            {task.doneWhen.length > 0 && (
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
            )}

            {epic.entryGate && (
              <Field label="Epic entry gate">
                <p className="text-sm leading-relaxed">{plainText(epic.entryGate)}</p>
              </Field>
            )}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
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
