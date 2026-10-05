import { useEffect, useMemo, useRef, useState } from "react"
import { Link } from "@tanstack/react-router"
import { Loader2, Search, Archive } from "lucide-react"
import { Skeleton } from "darkraise-ui/components/skeleton"
import {
  EmptyState,
  listItemClass,
  useDetailLevel,
  VerificationBadge,
} from "@/components/darkmem"
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
import { TimelineScrubber } from "@/components/timeline-scrubber"
import { dayKeyToMs, formatList, localDayKey } from "@/lib/format"
import { buildTimelineScale, dateToFraction } from "@/lib/timeline"
import { useMainVirtualizer } from "@/lib/use-main-virtualizer"
import { useProjectStore } from "@/stores/project-store"
import { ALL_PROJECTS, ANY, useFactRows, type FactRowData } from "../use-facts"
import { ListSurface } from "./list-surface"
import {
  AppliesWhenChips,
  BeliefStateBadge,
  FactTriple,
  InReviewBadge,
  SuppressedBadge,
  UnderSourcedBadge,
} from "./fact-parts"

const STATUS_OPTIONS = ["candidate", "corroborated", "confirmed", "disputed"]
const SORTS = { newest: "newest first", rung: "verification rung" } as const
type SortKey = keyof typeof SORTS

// Weakest first, so "verification rung" sorts strongest-first when reversed.
// `disputed` sits below every machine rung: a contradicted fact is served
// labelled, never promoted above one nothing contradicts.
const RUNG_ORDER = ["disputed", "candidate", "corroborated", "confirmed"]
const ROW_GAP = 10
const ROW_ESTIMATE = 118

export function FactRow({
  fact,
  focused,
}: {
  fact: FactRowData
  focused: boolean
}) {
  const advanced = useDetailLevel((s) => s.level) === "advanced"
  const candidate = fact.verification_status === "candidate"
  const originMeta =
    fact.origin_count !== null
      ? `${fact.origin_count} ${fact.origin_count === 1 ? "origin" : "origins"}${
          fact.origin_kinds.length > 0
            ? ` · ${formatList(fact.origin_kinds)}`
            : ""
        }`
      : null
  return (
    <div
      // The dashed edge is now every row's, so `candidate` keeps the tint and
      // the badge that names it in words rather than a border nothing else
      // contrasts with.
      className={listItemClass({
        interactive: true,
        className: cn(
          // `relative` anchors the details link's stretched ::after, which
          // makes the whole card the click target its hover promises.
          "relative cursor-pointer space-y-1.5 p-2.5",
          candidate && "bg-muted/15",
          focused && "ring-primary/60 ring-1",
        ),
      })}
    >
      <div className="flex flex-wrap items-center gap-2">
        <VerificationBadge
          status={fact.verification_status}
          detail={fact.claim}
        />
        {fact.under_sourced && <UnderSourcedBadge />}
        {fact.label_suppressed && (
          <SuppressedBadge reason={fact.label_suppressed} />
        )}
        <BeliefStateBadge
          windowClosed={fact.window_closed}
          expired={fact.expired}
          invalidAt={advanced ? fact.invalid_at : null}
        />
        {fact.review_state === "open" && <InReviewBadge />}
        {/* Right of the badges from `sm` up; below it the same meta moves
            to the footer line, so it never wraps between badge and title. */}
        {originMeta && (
          <span className="text-muted-foreground ml-auto hidden font-mono text-sm sm:inline">
            {originMeta}
          </span>
        )}
      </div>
      {/* The raw triple is the taxonomy form of the same statement the
          sentence below already carries — technical detail, and the one
          thing simple mode collapses here. */}
      {advanced && (
        <FactTriple
          subject={fact.subject_name}
          rel={fact.rel_type}
          object={fact.object_name}
        />
      )}
      {/* Simple mode hides the triple, so the sentence becomes the row's
          heading rather than a muted line under nothing. */}
      <p
        className={cn(
          "text-sm",
          advanced ? "text-muted-foreground" : "text-foreground font-medium",
        )}
      >
        {fact.fact_text}
      </p>
      {/* A disputed claim is the two-sided form, so both sides stay on the
          row; every other claim only restates the origin count above. */}
      {fact.claim && fact.verification_status === "disputed" && (
        <p className="font-mono text-sm">{fact.claim}</p>
      )}
      <AppliesWhenChips items={fact.applies_when} />
      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
        <Link
          to="/knowledge/facts/$factId"
          params={{ factId: fact.id }}
          aria-label={`Open fact: ${fact.subject_name} ${fact.rel_type} ${fact.object_name}`}
          className="hover:text-primary-text text-muted-foreground w-fit font-mono text-sm transition-colors after:absolute after:inset-0 after:rounded-md after:content-['']"
        >
          details →
        </Link>
        {originMeta && (
          <span className="text-muted-foreground font-mono text-sm sm:hidden">
            {originMeta}
          </span>
        )}
      </div>
    </div>
  )
}

export function FactsTab() {
  const [subject, setSubject] = useState("")
  const [relation, setRelation] = useState(ANY)
  const [status, setStatus] = useState(ANY)
  const activeProject = useProjectStore((s) => s.activeProject)
  const setScope = useProjectStore((s) => s.setProject)
  const project = activeProject ?? ALL_PROJECTS
  const [sort, setSort] = useState<SortKey>("newest")
  const [focusedId, setFocusedId] = useState<string | null>(null)
  const [scrubFraction, setScrubFraction] = useState(0)
  const focusTimer = useRef<number | undefined>(undefined)

  // Project, relation and status are **server-side** predicates: the route
  // filters and pages, so the list is never the page pretending to be the
  // corpus. `subject` is the exception and is scoped to the loaded rows on
  // purpose — the route matches `subject_name` exactly, and a substring search
  // sent as an exact filter would silently return nothing for every partial
  // word the user typed. Everything this surface says about that filter is
  // therefore said in terms of `loaded`, never `total`.
  const {
    rows: matched,
    loaded,
    total,
    loading,
    error,
    hasMore,
    fetchingMore,
    fetchMore,
    relations,
    optionsComplete,
  } = useFactRows({ project, relation, status, subject })

  const rows = useMemo(() => {
    if (sort === "rung") {
      return [...matched].sort(
        (a, b) =>
          RUNG_ORDER.indexOf(b.verification_status) -
            RUNG_ORDER.indexOf(a.verification_status) ||
          b.as_of.localeCompare(a.as_of),
      )
    }
    return [...matched].sort(
      (a, b) => b.as_of.localeCompare(a.as_of) || a.id.localeCompare(b.id),
    )
  }, [matched, sort])

  const subjectActive = subject.trim() !== ""
  const serverFiltersActive =
    relation !== ANY || status !== ANY || project !== ALL_PROJECTS
  const chronological = sort === "newest"

  const scale = useMemo(
    () => (chronological ? buildTimelineScale(rows, (f) => f.as_of) : null),
    [rows, chronological],
  )

  const footerIndex = rows.length
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

  useEffect(() => () => window.clearTimeout(focusTimer.current), [])

  // Reaching the footer loads the next page. Never while the free-text
  // needle is applied: that filter runs over loaded rows, so an unmatched
  // page keeps the footer on screen and the surface would drain the whole
  // corpus in the background to answer a question it can answer honestly
  // with what it has.
  useEffect(() => {
    if (!hasMore || fetchingMore || subjectActive) return
    if (lastRenderedIndex < footerIndex) return
    fetchMore()
  }, [
    hasMore,
    fetchingMore,
    subjectActive,
    lastRenderedIndex,
    footerIndex,
    fetchMore,
  ])

  useEffect(() => {
    if (!scale) return
    const row = rows[topIndex]
    if (row) setScrubFraction(dateToFraction(scale, Date.parse(row.as_of)))
  }, [scale, rows, topIndex])

  // The axis spans the loaded rows — the only rows whose dates this surface
  // knows — so a seek lands inside them and never past a tail it cannot see.
  const seekToDate = (dayKey: string) => {
    if (!scale || rows.length === 0) return
    let idx = rows.findIndex((f) => localDayKey(new Date(f.as_of)) <= dayKey)
    if (idx === -1) idx = rows.length - 1
    const target = rows[idx]
    if (!target) return
    setScrubFraction(
      dateToFraction(
        scale,
        Math.min(scale.newestMs, Math.max(scale.oldestMs, dayKeyToMs(dayKey))),
      ),
    )
    setFocusedId(target.id)
    window.clearTimeout(focusTimer.current)
    focusTimer.current = window.setTimeout(() => setFocusedId(null), 1800)
    requestAnimationFrame(() =>
      virtualizer.scrollToIndex(idx, { align: "start" }),
    )
  }

  // Every number here is either the server's own count behind the server-side
  // filters (`total`) or a count of rows actually fetched (`loaded`). The
  // free-text needle is reported against `loaded`, because that is the only
  // set it was run over.
  // "loaded" is only said while more pages exist; otherwise the loaded rows
  // are the whole result and the plain count is the honest one.
  const factsWord = (n: number) => (n === 1 ? "fact" : "facts")
  const headerMeta =
    error || loading
      ? undefined
      : subjectActive
        ? hasMore
          ? `${rows.length} of ${loaded} loaded`
          : `${rows.length} of ${loaded} ${factsWord(loaded)}`
        : hasMore
          ? `${loaded} of ${total} loaded`
          : `${total} ${factsWord(total)}`
  const localFiltersActive = relation !== ANY || status !== ANY
  const activeFilterNames = [
    relation !== ANY ? `relation ${relation}` : null,
    status !== ANY ? `status ${status}` : null,
  ].filter((f): f is string => f !== null)
  const clearLocalFilters = () => {
    setSubject("")
    setRelation(ANY)
    setStatus(ANY)
  }

  return (
    <div className="space-y-4">
      {/* Distinct controls, never one ambiguous "filters" blob: subject
          free-texts, relation and status constrain their columns. The project
          scope is the header switcher (the isolation boundary). */}
      <div className="border-border flex flex-wrap items-center gap-2.5 border-b border-dashed pb-3">
        <Input
          prefix={<Search aria-hidden className="h-4 w-4" />}
          placeholder="subject or object — e.g. darkmem, postgres…"
          value={subject}
          onChange={(e) => setSubject(e.target.value)}
          groupClassName="min-w-56 flex-1"
          aria-label="Filter facts by subject or object"
        />
        <Select value={relation} onValueChange={setRelation}>
          <SelectTrigger
            className="w-44 rounded-full"
            aria-label="Relation filter"
          >
            <SelectValue>relation: {relation}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ANY}>any</SelectItem>
            {relations.map((rel) => (
              <SelectItem key={rel} value={rel}>
                {rel}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger
            className="w-44 rounded-full"
            aria-label="Status filter"
          >
            <SelectValue>status: {status}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={ANY}>any</SelectItem>
            {STATUS_OPTIONS.map((s) => (
              <SelectItem key={s} value={s}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={sort} onValueChange={(v) => setSort(v as SortKey)}>
          <SelectTrigger className="w-56 rounded-full" aria-label="Sort order">
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
        {/* The option lists come from the rows fetched so far. */}
        {!optionsComplete && (
          <p className="text-muted-foreground w-full text-sm">
            Relation options cover the {loaded} facts loaded so far.
          </p>
        )}
      </div>

      <div
        className={cn(
          "grid grid-cols-1 items-start gap-5",
          // The column stays reserved while the list is chronological even
          // when no row is left to seek, so a filter that empties the list
          // does not jump the surface sideways.
          chronological && "lg:grid-cols-[3.5rem_minmax(0,1fr)]",
        )}
      >
        {/* The scrubber only rides a chronological list — over the rung
            sort its position would not track the scroll. */}
        {scale ? (
          <div className="sticky top-2 hidden self-start lg:block">
            {/* Never taller than the list it seeks over (a short result
                must not trail a long empty axis), never shorter than a
                usable rail. */}
            <div
              style={{
                height: `max(12rem, min(calc(100vh - 15rem), ${
                  virtualizer.getTotalSize() + 48
                }px))`,
              }}
            >
              <TimelineScrubber
                scale={scale}
                position={scrubFraction}
                onSeek={seekToDate}
              />
            </div>
          </div>
        ) : chronological ? (
          <div aria-hidden className="hidden lg:block" />
        ) : null}

        <ListSurface
          className="min-w-0"
          bodyClassName={rows.length > 0 ? "block" : undefined}
          title="Facts"
          populated={rows.length > 0}
          meta={headerMeta}
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
                    ) : fetchingMore ? (
                      <div
                        role="status"
                        className="text-muted-foreground flex items-center justify-center gap-2 py-2.5 text-sm"
                      >
                        <Loader2 aria-hidden className="h-4 w-4 animate-spin" />
                        loading more…
                      </div>
                    ) : hasMore ? (
                      <div className="flex flex-col items-center gap-1.5 py-1">
                        <p className="text-muted-foreground text-center font-mono text-sm">
                          {loaded} of {total} loaded
                        </p>
                        {subjectActive && (
                          <Button variant="outline" onClick={fetchMore}>
                            Load more
                          </Button>
                        )}
                      </div>
                    ) : null}
                  </div>
                )
              })}
            </div>
          ) : loading ? (
            // A pending read is not an absence. Skeleton rows in the shape
            // of the list that is coming, so the surface never claims the
            // vault is empty while it is still being read.
            <div
              className="flex flex-col gap-2 py-2"
              role="status"
              aria-label="Loading facts"
            >
              {Array.from({ length: 5 }, (_, i) => (
                <Skeleton key={i} className="h-16 w-full rounded-md" />
              ))}
            </div>
          ) : error ? (
            // Invariant 14: a failed read is never rendered as an empty vault.
            // "No facts" and "we could not tell you" are different sentences,
            // and collapsing them is how a broken surface looks healthy.
            <EmptyState
              kind="filtered"
              title="Could not load facts"
              description="The request failed. Reload to try again."
            />
          ) : total === 0 ? (
            serverFiltersActive ? (
              // Backed by the server's own count behind these predicates, so
              // this one may speak about the scope rather than the page.
              // "Clear filters" resets this page's filters only. The project
              // scope is app-wide, so widening it is its own, labelled action.
              <EmptyState
                kind="filtered"
                title="No facts match these filters"
                description={
                  activeProject
                    ? `Widen a filter to see more. Showing project ${activeProject} only; showing all projects changes the scope for the whole app.`
                    : "Widen a filter to see more."
                }
                action={
                  <div className="flex flex-wrap justify-center gap-2">
                    {localFiltersActive && (
                      <Button variant="outline" onClick={clearLocalFilters}>
                        Clear filters
                      </Button>
                    )}
                    {activeProject && (
                      <Button variant="outline" onClick={() => setScope(null)}>
                        Show all projects
                      </Button>
                    )}
                  </div>
                }
              />
            ) : (
              // Cold-start is not a generic empty state: the vault stays empty
              // of corroborated facts until independent origins accumulate.
              <EmptyState
                kind="empty"
                icon={Archive}
                title="No facts yet"
                description="Facts appear as independent sources agree on them."
              />
            )
          ) : (
            // The needle ran over the loaded rows only, so this sentence
            // counts loaded rows and never claims the vault holds no match.
            <EmptyState
              kind="filtered"
              title={
                hasMore
                  ? `No loaded fact matches “${subject.trim()}”`
                  : `No match for “${subject.trim()}”`
              }
              description={`${
                hasMore
                  ? `Searched the ${loaded} facts loaded so far; ${total - loaded} more are not loaded yet.`
                  : `Searched all ${loaded} ${factsWord(loaded)}.`
              }${
                activeFilterNames.length > 0
                  ? ` Filters: ${activeFilterNames.join(", ")}.`
                  : ""
              }`}
              action={
                <div className="flex flex-wrap justify-center gap-2">
                  {hasMore && (
                    <Button variant="outline" onClick={fetchMore}>
                      Load more
                    </Button>
                  )}
                  <Button variant="outline" onClick={() => setSubject("")}>
                    Clear subject
                  </Button>
                  {localFiltersActive && (
                    <Button variant="outline" onClick={clearLocalFilters}>
                      Clear all filters
                    </Button>
                  )}
                </div>
              }
            />
          )}
        </ListSurface>
      </div>
    </div>
  )
}
