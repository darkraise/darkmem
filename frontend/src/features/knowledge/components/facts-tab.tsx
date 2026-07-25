import { useEffect, useMemo, useRef, useState } from "react"
import { Link } from "@tanstack/react-router"
import { Archive, Loader2, Search, SearchX } from "lucide-react"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { Input } from "darkraise-ui/components/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { Button } from "darkraise-ui/components/button"
import { cn } from "darkraise-ui/lib"
import { LayerChip, VerificationBadge } from "@/components/darkmem"
import { TimelineScrubber } from "@/components/timeline-scrubber"
import { dayKeyToMs, localDayKey } from "@/lib/format"
import { buildTimelineScale, dateToFraction } from "@/lib/timeline"
import { useMainVirtualizer } from "@/lib/use-main-virtualizer"
import { useDemoFacts } from "@/demo/hooks"
import {
  distinctFactProjects,
  distinctFactRelations,
  filterFacts,
} from "@/demo/knowledge"
import type { DemoFact } from "@/demo/types"
import { ListSurface } from "./list-surface"
import { AppliesWhenChips, FactTriple } from "./fact-parts"

const STATUS_OPTIONS = ["candidate", "corroborated", "confirmed", "disputed"]
const SORTS = { newest: "newest first", rung: "verification rung" } as const
type SortKey = keyof typeof SORTS

const FACTS_PAGE = 25
const ROW_GAP = 10
const ROW_ESTIMATE = 118

function FactRow({ fact, focused }: { fact: DemoFact; focused: boolean }) {
  const candidate = fact.verification_status === "candidate"
  const disputed = fact.verification_status === "disputed"
  return (
    <div
      className={cn(
        "border-border space-y-1.5 rounded-md border p-2.5",
        candidate && "bg-muted/15 border-dashed",
        focused && "ring-primary/60 ring-1",
      )}
    >
      <div className="flex flex-wrap items-center gap-2">
        <LayerChip layer={2} />
        <VerificationBadge
          status={fact.verification_status}
          detail={fact.claim}
        />
        <span className="text-muted-foreground ml-auto font-mono text-sm">
          {disputed ? (
            <Link
              to="/knowledge/facts/$factId"
              params={{ factId: fact.id }}
              className="hover:text-primary transition-colors"
            >
              view both sides →
            </Link>
          ) : (
            fact.meta
          )}
        </span>
      </div>
      <Link
        to="/knowledge/facts/$factId"
        params={{ factId: fact.id }}
        className="hover:text-primary block space-y-1 transition-colors"
      >
        <FactTriple
          subject={fact.subject_name}
          rel={fact.rel_type}
          object={fact.object_name}
        />
        <p className="text-muted-foreground text-sm">
          {disputed && fact.dispute ? fact.dispute.summary : fact.fact_text}
        </p>
      </Link>
      {fact.verification_status === "corroborated" && (
        <p className="font-mono text-sm">{fact.claim}</p>
      )}
      <AppliesWhenChips items={fact.applies_when} />
      {fact.candidate_note && (
        <p className="text-muted-foreground text-sm">{fact.candidate_note}</p>
      )}
    </div>
  )
}

export function FactsTab() {
  const facts = useDemoFacts()
  const [subject, setSubject] = useState("")
  const [relation, setRelation] = useState("any")
  const [status, setStatus] = useState("any")
  const [project, setProject] = useState("darkmem")
  const [sort, setSort] = useState<SortKey>("newest")
  const [limit, setLimit] = useState(FACTS_PAGE)
  const [loadingMore, setLoadingMore] = useState(false)
  const [focusedId, setFocusedId] = useState<string | null>(null)
  const [scrubFraction, setScrubFraction] = useState(0)
  const focusTimer = useRef<number | undefined>(undefined)
  const loadingRef = useRef(false)

  const relations = useMemo(() => distinctFactRelations(facts), [facts])
  const projects = useMemo(() => distinctFactProjects(facts), [facts])

  // filterFacts orders by rung; the time scrubber needs a chronological
  // axis, so "newest" re-sorts the same filtered set by as_of.
  const scoped = useMemo(() => {
    const matched = filterFacts(facts, { subject, relation, status, project })
    if (sort === "rung") return matched
    return [...matched].sort(
      (a, b) => b.as_of.localeCompare(a.as_of) || a.id.localeCompare(b.id),
    )
  }, [facts, subject, relation, status, project, sort])

  const rows = useMemo(() => scoped.slice(0, limit), [scoped, limit])
  const hasMore = scoped.length > limit
  const chronological = sort === "newest"

  const scale = useMemo(
    () => (chronological ? buildTimelineScale(scoped, (f) => f.as_of) : null),
    [scoped, chronological],
  )

  const { listRef, virtualizer, scrollMargin } = useMainVirtualizer({
    count: rows.length + 1,
    estimateSize: () => ROW_ESTIMATE,
    gap: ROW_GAP,
    getItemKey: (index) => rows[index]?.id ?? "list-footer",
  })

  const virtualItems = virtualizer.getVirtualItems()
  const scrollOffset = virtualizer.scrollOffset ?? 0
  const lastRenderedIndex = virtualItems[virtualItems.length - 1]?.index ?? -1
  const topIndex =
    virtualItems.find((item) => item.end > scrollOffset)?.index ??
    virtualItems[0]?.index ??
    0

  // Any filter change re-slices the corpus; keep paging from restarting
  // mid-list rather than leaving a stale, oversized window.
  useEffect(() => {
    setLimit(FACTS_PAGE)
  }, [subject, relation, status, project, sort])

  useEffect(() => () => window.clearTimeout(focusTimer.current), [])

  // The in-flight guard is a ref, not `loadingMore` — as an effect dep it
  // would re-run the effect the moment the flag is set and the cleanup
  // would cancel the very timer that sets it.
  useEffect(() => {
    if (!hasMore || loadingRef.current) return
    if (lastRenderedIndex < rows.length - 1) return
    loadingRef.current = true
    setLoadingMore(true)
    const timer = window.setTimeout(() => {
      loadingRef.current = false
      setLimit((n) => n + FACTS_PAGE)
      setLoadingMore(false)
    }, 250)
    return () => {
      window.clearTimeout(timer)
      loadingRef.current = false
    }
  }, [hasMore, lastRenderedIndex, rows.length])

  useEffect(() => {
    if (!scale) return
    const row = rows[topIndex]
    if (row) setScrubFraction(dateToFraction(scale, Date.parse(row.as_of)))
  }, [scale, rows, topIndex])

  // Seeking past the loaded tail grows the window first — the scrubber's
  // axis spans the whole filtered corpus, not just the loaded pages.
  const seekToDate = (dayKey: string) => {
    if (!scale || scoped.length === 0) return
    let idx = scoped.findIndex(
      (f) => localDayKey(new Date(f.as_of)) <= dayKey,
    )
    if (idx === -1) idx = scoped.length - 1
    const target = scoped[idx]
    if (!target) return
    setScrubFraction(
      dateToFraction(
        scale,
        Math.min(scale.newestMs, Math.max(scale.oldestMs, dayKeyToMs(dayKey))),
      ),
    )
    if (idx >= limit) {
      setLimit(Math.ceil((idx + 1) / FACTS_PAGE) * FACTS_PAGE + FACTS_PAGE)
    }
    setFocusedId(target.id)
    window.clearTimeout(focusTimer.current)
    focusTimer.current = window.setTimeout(() => setFocusedId(null), 1800)
    requestAnimationFrame(() =>
      virtualizer.scrollToIndex(idx, { align: "start" }),
    )
  }

  const projectLabel = project === "all" ? "all projects" : project
  const totalInProject = useMemo(
    () =>
      facts.filter((f) => project === "all" || f.project === project).length,
    [facts, project],
  )
  const filtered =
    subject.trim() !== "" || relation !== "any" || status !== "any"

  return (
    <div className="space-y-4">
      {/* Four distinct controls, never one ambiguous "filters" blob:
          subject free-texts, relation and status constrain their columns,
          project mirrors the global switcher (the isolation boundary). */}
      <div className="border-border flex flex-wrap items-center gap-2.5 border-b border-dashed pb-3">
        <Input
          prefix={<Search aria-hidden className="h-4 w-4" />}
          placeholder="subject — e.g. darkmem, hybrid_search…"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          groupClassName="min-w-56 flex-1"
          aria-label="Filter facts by subject"
        />
        <Select value={relation} onValueChange={setRelation}>
          <SelectTrigger className="w-44 rounded-full" aria-label="Relation filter">
            <SelectValue>relation: {relation}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any">any</SelectItem>
            {relations.map((rel) => (
              <SelectItem key={rel} value={rel}>
                {rel}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="w-44 rounded-full" aria-label="Status filter">
            <SelectValue>status: {status}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="any">any</SelectItem>
            {STATUS_OPTIONS.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={project} onValueChange={setProject}>
          <SelectTrigger className="w-44 rounded-full" aria-label="Project scope">
            <SelectValue>project: {projectLabel}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All projects</SelectItem>
            {projects.map((p) => (
              <SelectItem key={p} value={p}>
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select
          value={sort}
          onValueChange={(v) => setSort(v as SortKey)}
        >
          <SelectTrigger className="w-48 rounded-full" aria-label="Sort order">
            <SelectValue>sort: {SORTS[sort]}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            {(Object.keys(SORTS) as SortKey[]).map((key) => (
              <SelectItem key={key} value={key}>
                {SORTS[key]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <div
        className={cn(
          "grid grid-cols-1 items-start gap-5",
          scale && "lg:grid-cols-[3.5rem_minmax(0,1fr)]",
        )}
      >
        {/* The scrubber only rides a chronological list — over the rung
            sort its position would not track the scroll. */}
        {scale && (
          <div className="sticky top-2 hidden h-[calc(100vh-13rem)] self-start lg:block">
            <TimelineScrubber
              scale={scale}
              position={scrubFraction}
              onSeek={seekToDate}
            />
          </div>
        )}

        <ListSurface
          className="min-w-0"
          bodyClassName={rows.length > 0 ? "block" : undefined}
          title={`Facts — project: ${projectLabel}`}
          populated={rows.length > 0}
          meta={`${rows.length} of ${totalInProject} shown`}
        >
          {rows.length > 0 ? (
            <div
              ref={listRef}
              className="relative w-full"
              style={{ height: virtualizer.getTotalSize() }}
            >
              {virtualItems.map((item) => {
                const fact = rows[item.index]
                return (
                  <div
                    key={item.key}
                    data-index={item.index}
                    ref={virtualizer.measureElement}
                    className="absolute top-0 left-0 w-full"
                    style={{
                      transform: `translateY(${item.start - scrollMargin}px)`,
                    }}
                  >
                    {fact ? (
                      <FactRow fact={fact} focused={focusedId === fact.id} />
                    ) : loadingMore ? (
                      <div
                        role="status"
                        className="text-muted-foreground flex items-center justify-center gap-2 py-2.5 text-sm"
                      >
                        <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
                        loading more…
                      </div>
                    ) : (
                      <p className="text-muted-foreground py-1 text-center font-mono text-sm">
                        {hasMore
                          ? `${rows.length} of ${scoped.length} loaded`
                          : `all ${scoped.length} shown`}
                      </p>
                    )}
                  </div>
                )
              })}
            </div>
          ) : filtered ? (
            <EmptyState
              icon={<SearchX aria-hidden className="h-6 w-6" />}
              title="No facts match these filters"
              description="Nothing was hidden — no fact in this scope matches the subject, relation, and status constraints. Widen a filter to see the rest."
              action={
                <Button
                  variant="outline"
                  onClick={() => {
                    setSubject("")
                    setRelation("any")
                    setStatus("any")
                  }}
                >
                  Clear filters
                </Button>
              }
            />
          ) : (
            // Cold-start is not a generic empty state: the vault stays empty
            // of corroborated facts until distinct origins accumulate.
            <EmptyState
              icon={<Archive aria-hidden className="h-6 w-6" />}
              title="No corroborated facts yet"
              description="no corroborated facts yet; candidates are served labelled in search — corroboration takes multiple distinct origins across memory, code, and human review. Nothing here means not yet, not broken."
            />
          )}
        </ListSurface>
      </div>
    </div>
  )
}
