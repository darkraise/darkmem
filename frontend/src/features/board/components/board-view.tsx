import {
  DndContext,
  KeyboardSensor,
  MouseSensor,
  TouchSensor,
  useDroppable,
  useSensor,
  useSensors,
  type DragEndEvent,
} from "@dnd-kit/core"
import { cn } from "darkraise-ui/lib"
import type { BoardColumn, BoardLane, BoardRecord } from "../lib/records"
import { RecordCard } from "./record-card"

export const DROP_PREFIX = "state:"

/** A drop's target state, or null when it did not land on a register column. */
export function dropTarget(event: Pick<DragEndEvent, "over">): string | null {
  const id = event.over ? String(event.over.id) : ""
  return id.startsWith(DROP_PREFIX) ? id.slice(DROP_PREFIX.length) : null
}

function Column({
  column,
  droppable,
  draggable,
  isPending,
  onOpen,
}: {
  column: BoardColumn
  droppable: boolean
  draggable: boolean
  isPending: (id: string) => boolean
  onOpen: (record: BoardRecord) => void
}) {
  const { setNodeRef, isOver } = useDroppable({
    id: `${DROP_PREFIX}${column.key}`,
    disabled: !droppable,
  })
  return (
    <section
      ref={setNodeRef}
      aria-label={`column ${column.title}`}
      className={cn(
        "bg-muted/30 flex w-64 shrink-0 flex-col gap-2 rounded-md p-2",
        isOver && droppable && "ring-primary ring-2",
      )}
    >
      <h3 className="flex items-center justify-between text-sm font-semibold">
        <span>{column.title}</span>
        <span className="text-muted-foreground font-mono text-xs">
          {column.records.length}
        </span>
      </h3>
      {column.records.map((record) => (
        <RecordCard
          key={record.id}
          record={record}
          draggable={draggable && !record.blockFirst}
          pending={isPending(record.id)}
          onOpen={onOpen}
        />
      ))}
    </section>
  )
}

/** The board layout (§3 Board). Register cards drag between the register
 *  lane's state columns; nothing else is draggable or a drop target. */
export function BoardView({
  lanes,
  isPending,
  onMove,
  onOpen,
}: {
  lanes: BoardLane[]
  isPending: (id: string) => boolean
  onMove: (record: BoardRecord, toState: string) => void
  onOpen: (record: BoardRecord) => void
}) {
  const sensors = useSensors(
    // Without a distance every click is a zero-length drag and a card never opens.
    useSensor(MouseSensor, { activationConstraint: { distance: 6 } }),
    useSensor(TouchSensor, {
      activationConstraint: { delay: 220, tolerance: 6 },
    }),
    useSensor(KeyboardSensor),
  )
  const byId = new Map(
    lanes
      .flatMap((lane) => lane.columns.flatMap((c) => c.records))
      .map((r) => [r.id, r]),
  )
  const handleDragEnd = (event: DragEndEvent) => {
    const state = dropTarget(event)
    const record = byId.get(String(event.active.id))
    if (state && record) onMove(record, state)
  }
  return (
    <DndContext sensors={sensors} onDragEnd={handleDragEnd}>
      <div className="space-y-4">
        {lanes.map((lane) => {
          const registerLane = lane.type === "register_row"
          return (
            <section
              key={lane.key}
              aria-label={lane.title || "board"}
              className="space-y-2"
            >
              {lane.title ? (
                <h2 className="text-muted-foreground text-xs font-semibold tracking-wide uppercase">
                  {lane.title}
                </h2>
              ) : null}
              <div className="flex gap-3 overflow-x-auto pb-2">
                {lane.columns.map((column) => (
                  <Column
                    key={column.key}
                    column={column}
                    droppable={registerLane && column.key !== "unrecognised"}
                    draggable={registerLane}
                    isPending={isPending}
                    onOpen={onOpen}
                  />
                ))}
              </div>
            </section>
          )
        })}
      </div>
    </DndContext>
  )
}
