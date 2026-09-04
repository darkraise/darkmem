import { useMemo, useState } from "react"
import { Input } from "darkraise-ui/components/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import {
  SegmentGroup,
  SegmentGroupIndicator,
  SegmentGroupItem,
} from "darkraise-ui/components/segment-group"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { ScrollArea } from "darkraise-ui/components/scroll-area"
import { EmptyState } from "@/components/darkmem"
import { LayoutGrid } from "lucide-react"
import { LEDGER_STATUSES } from "../types"
import { startableVerdict } from "../lib/startable"
import type { BoardTask, ProgressCorpus } from "../use-progress-corpus"
import { TaskCard } from "./task-card"
import { TaskDetail } from "./task-detail"

/** Workflow order, with `dropped` split off: it is resolved work and would
 *  otherwise sit as a wide column of noise beside the live ones. */
const LIVE_STATUSES = LEDGER_STATUSES.filter((s) => s !== "dropped")
const ANY = "__any__"
/** Rendered as its own column so an unrecognised status is surfaced rather
 *  than coerced into `todo` -- a typo in the file that gates merges must be
 *  visible on the board that renders it. */
const UNRECOGNISED = "unrecognised"

type Grouping = "status" | "epic" | "lane"

export function ProgressBoard({ corpus }: { corpus: ProgressCorpus }) {
  const [grouping, setGrouping] = useState<Grouping>("status")
  const [query, setQuery] = useState("")
  const [epicKey, setEpicKey] = useState(ANY)
  const [lane, setLane] = useState(ANY)
  const [owner, setOwner] = useState(ANY)
  const [model, setModel] = useState(ANY)
  const [startableOnly, setStartableOnly] = useState(false)
  const [showDropped, setShowDropped] = useState(false)
  const [open, setOpen] = useState<BoardTask | null>(null)

  const verdicts = useMemo(() => {
    const map = new Map<string, ReturnType<typeof startableVerdict>>()
    for (const entry of corpus.tasks) {
      map.set(
        entry.task.id,
        startableVerdict(
          entry.task,
          entry.row,
          entry.epic,
          corpus.gates.get(entry.epic.key),
          corpus.rows,
        ),
      )
    }
    return map
  }, [corpus])

  const options = useMemo(() => {
    const lanes = new Set<string>()
    const owners = new Set<string>()
    const models = new Set<string>()
    for (const { task, row } of corpus.tasks) {
      if (task.lane) lanes.add(task.lane)
      if (row?.owner) owners.add(row.owner)
      if (task.meta.Model) models.add(task.meta.Model)
    }
    return {
      epics: corpus.epics.map((e) => e.key),
      lanes: [...lanes].sort(),
      owners: [...owners].sort(),
      models: [...models].sort(),
    }
  }, [corpus])

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase()
    return corpus.tasks.filter(({ task, row, epic }) => {
      if (epicKey !== ANY && epic.key !== epicKey) return false
      if (lane !== ANY && task.lane !== lane) return false
      if (owner !== ANY && row?.owner !== owner) return false
      if (model !== ANY && task.meta.Model !== model) return false
      if (startableOnly && !verdicts.get(task.id)?.startable) return false
      if (q && !`${task.id} ${task.title}`.toLowerCase().includes(q)) return false
      return true
    })
  }, [corpus.tasks, epicKey, lane, owner, model, startableOnly, query, verdicts])

  const columns = useMemo(() => {
    if (grouping === "status") {
      const keys: string[] = [...LIVE_STATUSES]
      const buckets = new Map<string, BoardTask[]>(keys.map((k) => [k, []]))
      buckets.set(UNRECOGNISED, [])
      if (showDropped) buckets.set("dropped", [])

      for (const entry of visible) {
        // No row and an unreadable status are both "the ledger does not
        // classify this", which is the finding either way.
        const key: string = entry.row?.status ?? UNRECOGNISED
        if (key === "dropped" && !showDropped) continue
        const bucket = buckets.get(key)
        if (bucket) bucket.push(entry)
      }
      // An empty `unrecognised` column is noise; a populated one is a finding.
      if (buckets.get(UNRECOGNISED)?.length === 0) buckets.delete(UNRECOGNISED)
      return [...buckets.entries()]
    }

    const buckets = new Map<string, BoardTask[]>()
    for (const entry of visible) {
      // `M1` files 12 of its 33 tasks under a plain `## Tasks` heading ahead
      // of its lanes, so an unlaned bucket is a real column, not a fallback.
      const key =
        grouping === "epic" ? entry.epic.key : (entry.task.lane ?? "(no lane)")
      const bucket = buckets.get(key)
      if (bucket) bucket.push(entry)
      else buckets.set(key, [entry])
    }
    return [...buckets.entries()].sort((a, b) => a[0].localeCompare(b[0]))
  }, [visible, grouping, showDropped])

  const droppedCount = corpus.tasks.filter(
    (t) => t.row?.rawStatus === "dropped",
  ).length

  return (
    <div className="flex min-h-0 flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <SegmentGroup
          color="accent"
          value={grouping}
          onValueChange={(v) => v && setGrouping(v as Grouping)}
          aria-label="Group the board by"
        >
          <SegmentGroupIndicator />
          <SegmentGroupItem value="status">Status</SegmentGroupItem>
          <SegmentGroupItem value="epic">Epic</SegmentGroupItem>
          <SegmentGroupItem value="lane">Lane</SegmentGroupItem>
        </SegmentGroup>

        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Filter by id or title"
          aria-label="Filter by id or title"
          className="h-8 w-48"
        />

        <FilterSelect label="Epic" value={epicKey} onChange={setEpicKey} options={options.epics} />
        <FilterSelect label="Lane" value={lane} onChange={setLane} options={options.lanes} />
        <FilterSelect label="Owner" value={owner} onChange={setOwner} options={options.owners} />
        <FilterSelect label="Model" value={model} onChange={setModel} options={options.models} />

        <Button
          variant={startableOnly ? "default" : "outline"}
          size="sm"
          onClick={() => setStartableOnly((v) => !v)}
          aria-pressed={startableOnly}
        >
          Startable only
        </Button>

        {droppedCount > 0 && grouping === "status" && (
          <Button variant="ghost" size="sm" onClick={() => setShowDropped((v) => !v)}>
            {showDropped ? "Hide" : "Show"} dropped ({droppedCount})
          </Button>
        )}

        <span className="text-muted-foreground ml-auto text-xs">
          {visible.length} of {corpus.tasks.length}
        </span>
      </div>

      {visible.length === 0 ? (
        <EmptyState
          kind="empty"
          icon={LayoutGrid}
          title="No tasks match these filters"
          description="Clear a filter to widen the board."
        />
      ) : (
        <ScrollArea className="min-h-0 flex-1">
          <div className="flex items-start gap-3 pb-3">
            {columns.map(([key, entries]) => (
              <section key={key} className="w-64 shrink-0">
                <header className="flex items-center gap-1.5 pb-2">
                  <h3 className="text-[13px] font-semibold capitalize">{key}</h3>
                  <Badge variant="secondary" className="h-4 px-1 text-[10px]">
                    {entries.length}
                  </Badge>
                </header>
                <div className="space-y-2">
                  {entries.map((entry) => (
                    <TaskCard
                      key={entry.task.id}
                      entry={entry}
                      verdict={
                        verdicts.get(entry.task.id) ?? {
                          startable: false,
                          reason: null,
                        }
                      }
                      onOpen={() => setOpen(entry)}
                    />
                  ))}
                </div>
              </section>
            ))}
          </div>
        </ScrollArea>
      )}

      {corpus.orphanRows.length > 0 && (
        <p className="text-muted-foreground text-xs">
          {corpus.orphanRows.length} ledger row(s) have no task in any epic
          file — the two files have drifted.
        </p>
      )}

      <TaskDetail entry={open} onClose={() => setOpen(null)} />
    </div>
  )
}

function FilterSelect({
  label,
  value,
  onChange,
  options,
}: {
  label: string
  value: string
  onChange: (v: string) => void
  options: string[]
}) {
  if (options.length === 0) return null
  return (
    <Select value={value} onValueChange={onChange}>
      <SelectTrigger className="h-8 w-auto min-w-28" aria-label={label}>
        <SelectValue placeholder={label} />
      </SelectTrigger>
      <SelectContent>
        <SelectItem value={ANY}>{label}: any</SelectItem>
        {options.map((o) => (
          <SelectItem key={o} value={o}>
            {o}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
