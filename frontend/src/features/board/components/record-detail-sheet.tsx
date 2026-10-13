import { Button } from "darkraise-ui/components/button"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "darkraise-ui/components/sheet"
import { plainText } from "@/lib/plain-text"
import {
  PROPERTIES,
  PROPERTY_LABELS,
  shortName,
  type BoardRecord,
} from "../lib/records"
import { displayValue } from "./records-table"

/** Every property of one record, its links, and a plan task's step checklist
 *  (§3 Detail sheet). The checklist is the implementer's, never progress. */
export function RecordDetailSheet({
  record,
  onClose,
  onOpenDocument,
  onShowInWorkLog,
}: {
  record: BoardRecord | null
  onClose: () => void
  onOpenDocument: (uri: string) => void
  onShowInWorkLog: (workstreamKey: string, task: number) => void
}) {
  return (
    <Sheet open={record !== null} onOpenChange={(open) => !open && onClose()}>
      <SheetContent side="right" className="w-full overflow-y-auto sm:max-w-lg">
        {record ? (
          <>
            <SheetHeader>
              <SheetTitle>
                {record.label}{" "}
                {record.type === "register_row" ? record.title : ""}
              </SheetTitle>
              <SheetDescription>{shortName(record.source)}</SheetDescription>
            </SheetHeader>
            <div className="space-y-4 p-4">
              <div className="flex flex-wrap gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onOpenDocument(record.source)}
                >
                  {record.type === "register_row"
                    ? "Open register"
                    : "Open plan"}
                </Button>
                {record.type === "register_row" && record.plan ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onOpenDocument(record.plan!)}
                  >
                    Open plan
                  </Button>
                ) : null}
                {record.spec ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => onOpenDocument(record.spec!)}
                  >
                    Open spec
                  </Button>
                ) : null}
                {record.type === "plan_task" && record.workstreamKey ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() =>
                      onShowInWorkLog(record.workstreamKey!, record.number)
                    }
                  >
                    Show in Work log
                  </Button>
                ) : null}
              </div>
              <dl className="grid grid-cols-[8rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
                {PROPERTIES.map((property) => (
                  <div key={property} className="contents">
                    <dt className="text-muted-foreground">
                      {PROPERTY_LABELS[property]}
                    </dt>
                    <dd className="break-words whitespace-pre-wrap">
                      {displayValue(record, property) || "—"}
                    </dd>
                  </div>
                ))}
              </dl>
              {record.steps.length > 0 ? (
                <section
                  aria-label="implementer's checklist"
                  className="space-y-1.5"
                >
                  <h3 className="text-sm font-semibold">
                    Implementer's checklist (not progress)
                  </h3>
                  <ul className="space-y-1 text-sm">
                    {record.steps.map((step, index) => (
                      <li key={index} className="flex gap-2">
                        <span aria-hidden>{step.checked ? "☑" : "☐"}</span>
                        <span>{plainText(step.text)}</span>
                      </li>
                    ))}
                  </ul>
                </section>
              ) : null}
            </div>
          </>
        ) : null}
      </SheetContent>
    </Sheet>
  )
}
