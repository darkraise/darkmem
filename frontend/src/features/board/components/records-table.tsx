import {
  Editable,
  EditableArea,
  EditableInput,
  EditablePreview,
} from "darkraise-ui/components/editable"
import { MultiSelect } from "darkraise-ui/components/multi-select"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "darkraise-ui/components/table"
import type { BoardProperty, ViewDefinition } from "@/hooks/api"
import { formatWhen } from "@/lib/format"
import {
  formatProgress,
  PROPERTIES,
  PROPERTY_LABELS,
  propertyValue,
  REGISTER_STATES,
  shortName,
  type BoardRecord,
} from "../lib/records"
import type { RowEditor } from "../use-row-editor"

/** A property as a table shows it: uris by short name, times relative. */
export function displayValue(
  record: BoardRecord,
  property: BoardProperty,
): string {
  switch (property) {
    case "type":
      return record.type === "register_row" ? "row" : "task"
    case "number":
      return record.label
    case "source":
    case "plan":
    case "spec":
      return shortName(propertyValue(record, property))
    case "plan_progress":
      return formatProgress(record.planProgress) ?? ""
    case "last_activity":
      return record.lastActivity ? formatWhen(record.lastActivity) : ""
    default:
      return propertyValue(record, property) ?? ""
  }
}

function TextCell({
  record,
  column,
  editor,
}: {
  record: BoardRecord
  column: "note" | "assigned"
  editor: RowEditor
}) {
  const value = (column === "note" ? record.note : record.assigned) ?? ""
  return (
    <Editable
      // Remounts on a new server value, so a reload shows what the file holds.
      key={`${value}:${editor.editEpoch(record.id)}`}
      defaultValue={value}
      disabled={record.blockFirst || editor.isPending(record.id)}
      onValueCommit={({ value: next }) => {
        if (next !== value) editor.save(record, { [column]: next })
      }}
    >
      <EditableArea>
        <EditablePreview
          aria-label={`${PROPERTY_LABELS[column]} of ${record.label}`}
        />
        <EditableInput
          aria-label={`Edit ${PROPERTY_LABELS[column]} of ${record.label}`}
        />
      </EditableArea>
    </Editable>
  )
}

function Cell({
  record,
  property,
  editor,
  onOpen,
}: {
  record: BoardRecord
  property: BoardProperty
  editor: RowEditor
  onOpen: (record: BoardRecord) => void
}) {
  const editable = record.type === "register_row" && !record.blockFirst
  if (property === "title") {
    return (
      <button
        type="button"
        className="text-left hover:underline"
        onClick={() => onOpen(record)}
      >
        {record.title}
      </button>
    )
  }
  if (editable && property === "state") {
    return (
      <Select
        value={record.state}
        disabled={editor.isPending(record.id)}
        onValueChange={(next) => editor.move(record, next)}
      >
        <SelectTrigger
          className="h-8 w-28"
          aria-label={`State of ${record.label}`}
        >
          <SelectValue>{record.state}</SelectValue>
        </SelectTrigger>
        <SelectContent>
          {REGISTER_STATES.map((state) => (
            <SelectItem key={state} value={state}>
              {state}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    )
  }
  if (editable && (property === "note" || property === "assigned")) {
    return <TextCell record={record} column={property} editor={editor} />
  }
  return <span>{displayValue(record, property)}</span>
}

/** The table layout (§3 Table): a column chooser, header-click sort, and
 *  register rows' State, Note and Assigned edited through the same PATCH. */
export function RecordsTable({
  records,
  definition,
  onDefinitionChange,
  editor,
  onOpen,
}: {
  records: BoardRecord[]
  definition: ViewDefinition
  onDefinitionChange: (next: ViewDefinition) => void
  editor: RowEditor
  onOpen: (record: BoardRecord) => void
}) {
  const columns =
    definition.columns.length > 0 ? definition.columns : PROPERTIES
  const sortBy = (property: BoardProperty) => {
    const current = definition.sort
    const direction =
      current?.property === property && current.direction === "asc"
        ? "desc"
        : "asc"
    onDefinitionChange({ ...definition, sort: { property, direction } })
  }
  return (
    <div className="space-y-2">
      <MultiSelect
        className="max-w-xl"
        placeholder="Columns"
        items={PROPERTIES.map((p) => ({ value: p, label: PROPERTY_LABELS[p] }))}
        value={columns}
        onValueChange={({ value }) =>
          onDefinitionChange({
            ...definition,
            columns: value as BoardProperty[],
          })
        }
      />
      <Table>
        <TableHeader>
          <TableRow>
            {columns.map((property) => {
              const sorted = definition.sort?.property === property
              return (
                <TableHead
                  key={property}
                  aria-sort={
                    sorted
                      ? definition.sort?.direction === "asc"
                        ? "ascending"
                        : "descending"
                      : undefined
                  }
                >
                  <button type="button" onClick={() => sortBy(property)}>
                    {PROPERTY_LABELS[property]}
                    {sorted
                      ? definition.sort?.direction === "asc"
                        ? " ↑"
                        : " ↓"
                      : ""}
                  </button>
                </TableHead>
              )
            })}
          </TableRow>
        </TableHeader>
        <TableBody>
          {records.map((record) => (
            <TableRow
              key={record.id}
              aria-busy={editor.isPending(record.id) || undefined}
            >
              {columns.map((property) => (
                <TableCell key={property}>
                  <Cell
                    record={record}
                    property={property}
                    editor={editor}
                    onOpen={onOpen}
                  />
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
