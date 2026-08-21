import { useEffect, useState } from "react"
import { Link } from "@tanstack/react-router"
import {
  AlertTriangle,
  ChevronLeft,
  ChevronRight,
  EyeOff,
  Pencil,
  TrendingUp,
  UserCheck,
  XCircle,
  ClipboardCheck,
} from "lucide-react"
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
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { EmptyState } from "@/components/darkmem"
import { toast } from "darkraise-ui/components/sonner"
import {
  LayerChip,
  VerificationBadge,
  useDetailLevel,
} from "@/components/darkmem"
import { ApiError } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import { useDemoStore } from "@/demo/store"
import { useDismissSuspicion, useRatifyFact, useRejectFact } from "@/hooks/api"
import { SuppressedBadge, UnderSourcedBadge } from "./fact-parts"
import { ListSurface } from "./list-surface"
import {
  useReviewArticleRows,
  useReviewCounts,
  useReviewFactRows,
  type ReviewArticleRowData,
  type ReviewFactRowData,
} from "../use-review-queue"

const PAGE = 10

function PageControls({
  offset,
  limit,
  total,
  onPrev,
  onNext,
}: {
  offset: number
  limit: number
  total: number
  onPrev: () => void
  onNext: () => void
}) {
  if (total <= limit) return null
  return (
    <div className="flex items-center justify-end gap-2 pt-1">
      <span className="text-muted-foreground font-mono text-sm">
        {Math.min(offset + 1, total)}–{Math.min(offset + limit, total)} of{" "}
        {total}
      </span>
      <Button
        size="sm"
        variant="outline"
        disabled={offset === 0}
        onClick={onPrev}
        aria-label="Previous page"
      >
        <ChevronLeft className="size-3.5" />
      </Button>
      <Button
        size="sm"
        variant="outline"
        disabled={offset + limit >= total}
        onClick={onNext}
        aria-label="Next page"
      >
        <ChevronRight className="size-3.5" />
      </Button>
    </div>
  )
}

function ConsequenceBreakdown({ fact }: { fact: ReviewFactRowData }) {
  const c = fact.consequence
  if (!c) return null
  return (
    <div className="border-border bg-muted/10 space-y-1 rounded-md border border-dashed p-2 font-mono text-sm">
      <p>
        retrieval_frequency: component{" "}
        {c.retrieval_frequency.component.toFixed(3)} · weight{" "}
        {c.retrieval_frequency.weight} · source_memories{" "}
        {c.retrieval_frequency.source_memories} · peak_access_count{" "}
        {c.retrieval_frequency.peak_access_count} · decayed_access{" "}
        {c.retrieval_frequency.decayed_access.toFixed(3)} · half_life_days{" "}
        {c.retrieval_frequency.half_life_days}
      </p>
      <p>
        subject_salience: component {c.subject_salience.component.toFixed(3)} ·
        weight {c.subject_salience.weight} · neighbour_count{" "}
        {c.subject_salience.neighbour_count}
      </p>
      <p>
        staleness: {c.staleness.stale ? "stale" : "fresh"} — {c.staleness.label}
        {c.staleness.dispute_age_days != null &&
          ` · dispute_age_days ${c.staleness.dispute_age_days.toFixed(1)}`}{" "}
        · threshold_days {c.staleness.threshold_days}
      </p>
    </div>
  )
}

function EvidenceBlock({ fact }: { fact: ReviewFactRowData }) {
  if (fact.verification_status !== "disputed") return null
  const payload = fact.evidence?.payload
  if (!payload) {
    return (
      <p className="text-muted-foreground border-border rounded-md border border-dashed p-2 text-sm italic">
        no contradiction detail recorded for this dispute — absent means no scan
        produced one here, never that no counterpart exists
      </p>
    )
  }
  const c = payload.contradiction
  return (
    <div className="border-border bg-muted/10 space-y-1 rounded-md border border-dashed p-2 font-mono text-sm">
      <p>
        outcome {payload.outcome ?? "—"} · origin_count{" "}
        {payload.origin_count ?? "—"} · required_n {payload.required_n ?? "—"} ·
        gate_fired {payload.gate_fired ?? "—"}
      </p>
      {payload.source_kinds && payload.source_kinds.length > 0 && (
        <p>source_kinds [{payload.source_kinds.join(", ")}]</p>
      )}
      {c && (
        <p>
          counterpart: {c.counterpart_subject} → {c.counterpart_rel_type} →{" "}
          {c.counterpart_object} · rule {c.rule} · witness_origin{" "}
          {c.witness_origin}
        </p>
      )}
    </div>
  )
}

/** The other side of the model scan's flag (T2.112).
 *
 *  Unconditional in every detail level, like the honesty labels above it: the
 *  reviewer's lawful actions here are "reject the fact" and "dismiss the
 *  finding", and choosing between them is not possible without seeing what
 *  the finding was. An expired counterpart is rendered, never hidden — facts
 *  are invalidate-not-delete, so a flag can outlive its other side, and that
 *  is exactly the case worth telling a human about.
 */
function SuspicionBlock({ fact }: { fact: ReviewFactRowData }) {
  const s = fact.suspected_contradiction
  if (!s) return null
  const triple =
    s.counterpart_subject != null &&
    s.counterpart_rel_type != null &&
    s.counterpart_object != null
      ? `${s.counterpart_subject} → ${s.counterpart_rel_type} → ${s.counterpart_object}`
      : null
  return (
    <div className="border-border text-muted-foreground space-y-1 rounded-md border border-dashed p-2 font-mono text-xs">
      <p className="flex items-center gap-1.5">
        <AlertTriangle aria-hidden className="h-3.5 w-3.5 shrink-0" />
        <span>
          <b className="text-foreground font-semibold">
            suspected contradiction
          </b>{" "}
          · since {s.suspected_at}
        </span>
      </p>
      <p>counterpart: {triple ?? "no triple recorded for the counterpart"}</p>
      {s.counterpart_expired_at != null && (
        <p>
          counterpart withdrawn {s.counterpart_expired_at} — belief expired,
          flag stands
        </p>
      )}
    </div>
  )
}

function FactRow({
  fact,
  onRatify,
  onReject,
  onDismissSuspicion,
}: {
  fact: ReviewFactRowData
  onRatify: (fact: ReviewFactRowData) => void
  onReject: (fact: ReviewFactRowData) => void
  onDismissSuspicion: (fact: ReviewFactRowData) => void
}) {
  const level = useDetailLevel((s) => s.level)
  return (
    <div className="border-border space-y-2 rounded-md border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <LayerChip layer={2} />
        {/* Honesty labels: unconditional in every detail level. */}
        <VerificationBadge status={fact.verification_status} />
        <Badge variant="outline" size="sm" className="font-mono">
          queued: {fact.reason}
        </Badge>
        {fact.under_sourced && <UnderSourcedBadge />}
        {fact.label_suppressed != null && (
          <SuppressedBadge reason={fact.label_suppressed} />
        )}
        <span className="text-muted-foreground ml-auto font-mono text-sm">
          project: {fact.project}
        </span>
      </div>
      {fact.subject_name != null &&
      fact.rel_type != null &&
      fact.object_name != null ? (
        <p className="text-sm">
          <b className="font-semibold">{fact.subject_name}</b>{" "}
          <Badge variant="outline" size="sm" className="rounded-sm font-mono">
            {fact.rel_type}
          </Badge>{" "}
          <b className="font-semibold">{fact.object_name}</b>
        </p>
      ) : null}
      <p className="text-sm">{fact.fact_text}</p>
      <SuspicionBlock fact={fact} />
      <p className="text-muted-foreground flex items-center gap-1.5 text-sm">
        <TrendingUp aria-hidden className="h-3.5 w-3.5 shrink-0" />
        <span>
          <b className="text-foreground font-semibold">why ranked here:</b>{" "}
          {fact.rank_note}
        </span>
      </p>
      {level === "advanced" && <ConsequenceBreakdown fact={fact} />}
      {level === "advanced" && <EvidenceBlock fact={fact} />}
      <div className="border-border flex flex-wrap items-center gap-2 border-t border-dashed pt-2">
        <Button size="sm" onClick={() => onRatify(fact)}>
          <UserCheck className="mr-1.5 size-3.5" />
          Ratify → confirmed
        </Button>
        <Button size="sm" variant="outline" onClick={() => onReject(fact)}>
          <XCircle className="mr-1.5 size-3.5" />
          Reject
        </Button>
        {fact.suspected_contradiction != null && (
          <Button
            size="sm"
            variant="outline"
            onClick={() => onDismissSuspicion(fact)}
          >
            <EyeOff className="mr-1.5 size-3.5" />
            Dismiss suspicion
          </Button>
        )}
        <Button size="sm" variant="outline" asChild>
          <Link to="/knowledge/facts/$factId" params={{ factId: fact.id }}>
            <Pencil className="mr-1.5 size-3.5" />
            Edit
          </Link>
        </Button>
        <span className="text-muted-foreground ml-auto font-mono text-[10px]">
          queued since {fact.created_at} · ratify/reject are REST/UI,
          authenticated — never exposed over MCP
        </span>
      </div>
    </div>
  )
}

function ArticleRow({ article }: { article: ReviewArticleRowData }) {
  return (
    <div className="border-border space-y-2 rounded-md border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <LayerChip layer={3} />
        <Badge variant="outline" size="sm" className="font-mono">
          {article.status}
        </Badge>
        <Badge variant="outline" size="sm" className="font-mono">
          queued: {article.reason}
        </Badge>
        <span className="text-muted-foreground ml-auto font-mono text-sm">
          project: {article.project}
        </span>
      </div>
      <p className="text-sm font-semibold">
        {article.title ?? article.subject_key}
      </p>
      {article.resynthesis_held_at && (
        /* Queued, not withheld. The row says what was measured so a reviewer
           sees the finding rather than only its name — and says plainly that
           the article is still being served, because a queue entry that looks
           like a suppression is the confusion this marker exists to avoid. */
        <p className="text-warning text-sm">
          re-synthesis attempted and held
          {article.resynthesis_held_coverage !== null &&
            ` at claim-support coverage ${article.resynthesis_held_coverage.toFixed(2)}`}
          {
            " — the standing article is still served, labelled stale; its subject's verified facts could not ground a replacement."
          }
        </p>
      )}
      {article.content_preview && (
        <p className="text-muted-foreground text-sm">
          {article.content_preview}
        </p>
      )}
      <p className="text-muted-foreground font-mono text-sm">
        {article.synthesized_at
          ? `synthesized ${article.synthesized_at}`
          : "not yet synthesized — article_synthesis is still a placeholder job"}
        {" · "}created {article.created_at}
      </p>
      <div className="border-border flex flex-wrap items-center gap-2 border-t border-dashed pt-2">
        <Button size="sm" variant="outline" asChild>
          <Link
            to="/knowledge/articles/$articleId"
            params={{ articleId: article.id }}
          >
            <Pencil className="mr-1.5 size-3.5" />
            Edit
          </Link>
        </Button>
        <span className="text-muted-foreground ml-auto font-mono text-[10px]">
          articles have no ratify/reject door yet — read-only here
        </span>
      </div>
    </div>
  )
}

export function ReviewQueue({ project }: { project?: string }) {
  const [factsOffset, setFactsOffset] = useState(0)
  const [articlesOffset, setArticlesOffset] = useState(0)
  const [ratifyTarget, setRatifyTarget] = useState<ReviewFactRowData | null>(
    null,
  )
  const [rejectTarget, setRejectTarget] = useState<ReviewFactRowData | null>(
    null,
  )
  const [dismissTarget, setDismissTarget] = useState<ReviewFactRowData | null>(
    null,
  )

  useEffect(() => {
    setFactsOffset(0)
    setArticlesOffset(0)
  }, [project])

  const counts = useReviewCounts({ project })
  const facts = useReviewFactRows({ project, limit: PAGE, offset: factsOffset })
  const articles = useReviewArticleRows({
    project,
    limit: PAGE,
    offset: articlesOffset,
  })

  const ratifyMutation = useRatifyFact()
  const rejectMutation = useRejectFact()
  const dismissMutation = useDismissSuspicion()
  const demoRatify = useDemoStore((s) => s.ratifyReviewItem)
  const demoClear = useDemoStore((s) => s.clearReviewItem)

  // Neither door had an `onError` before this fix: a 500 or a stale-id 404
  // closed the confirm dialog and left the queue looking unchanged, a failed
  // action indistinguishable from a slow one (F2).
  //
  // `ApiError` means the backend answered with an error status; `get_session`
  // rolls back on that path, so "the fact was not changed" is a claim this
  // client can stand behind. Any other rejection (a dropped connection, no
  // response at all) leaves the outcome unknown — the request may have
  // committed with no answer reaching this client — so it gets its own,
  // non-committal wording instead. Same split as `runUndo` in
  // hygiene-queue.tsx (F3).
  const runRatify = (fact: ReviewFactRowData) => {
    if (DEMO) {
      demoRatify(fact.id, "q.tran")
    } else {
      ratifyMutation.mutate(
        { factId: fact.id },
        {
          onError: (error) => {
            if (error instanceof ApiError) {
              toast.error("Ratify failed — the fact was not changed", {
                description: error.message,
              })
              return
            }
            toast.error("Ratify failed — state unknown", {
              description: `${
                error instanceof Error
                  ? error.message
                  : "the request did not complete"
              }. Re-check the fact before retrying.`,
            })
          },
        },
      )
    }
    setRatifyTarget(null)
  }
  const runReject = (fact: ReviewFactRowData) => {
    if (DEMO) {
      demoClear(fact.id)
    } else {
      rejectMutation.mutate(
        { factId: fact.id },
        {
          onError: (error) => {
            if (error instanceof ApiError) {
              toast.error("Reject failed — the fact was not changed", {
                description: error.message,
              })
              return
            }
            toast.error("Reject failed — state unknown", {
              description: `${
                error instanceof Error
                  ? error.message
                  : "the request did not complete"
              }. Re-check the fact before retrying.`,
            })
          },
        },
      )
    }
    setRejectTarget(null)
  }
  // No demo arm: the fixture carries no suspicion, so `SuspicionBlock` and
  // this button never render there. A demo branch here would be a path no
  // fixture can reach.
  const runDismiss = (fact: ReviewFactRowData) => {
    dismissMutation.mutate(
      { factId: fact.id },
      {
        onError: (error) => {
          if (error instanceof ApiError) {
            toast.error("Dismiss failed — the flag was not cleared", {
              description: error.message,
            })
            return
          }
          toast.error("Dismiss failed — state unknown", {
            description: `${
              error instanceof Error
                ? error.message
                : "the request did not complete"
            }. Re-check the fact before retrying.`,
          })
        },
      },
    )
    setDismissTarget(null)
  }

  const countsLine = counts.error
    ? "counts unavailable"
    : counts.loading
      ? "counts loading…"
      : `${counts.facts} fact${counts.facts === 1 ? "" : "s"} · ${counts.articles} article${
          counts.articles === 1 ? "" : "s"
        } open`

  return (
    <div className="space-y-3">
      <div className="border-border bg-muted/15 text-muted-foreground rounded-md border border-dashed px-2.5 py-1.5 text-sm">
        Every row below is{" "}
        <b className="text-foreground font-semibold">served labelled</b> to
        retrieval right now, exactly as shown — queue position never withholds a
        fact or article from search results.{" "}
        <span className="font-mono">{countsLine}</span>
      </div>

      <ListSurface
        title="Disputed / under-sourced facts"
        populated={facts.total > 0}
        meta="consequence-ranked, not FIFO"
      >
        {facts.error ? (
          <EmptyState
            kind="filtered"
            title="Could not load the fact queue"
            description="The vault did not answer. This is a failed read, not an empty queue."
          />
        ) : facts.loading && facts.rows.length === 0 ? (
          // A pending read is not an absence — skeleton rows in the shape
          // of the queue that is coming.
          <div
            className="flex flex-col gap-2 py-2"
            role="status"
            aria-label="Loading the review queue"
          >
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-md" />
            ))}
          </div>
        ) : facts.total === 0 ? (
          <EmptyState
            kind="empty"
            icon={ClipboardCheck}
            title="No disputed or under-sourced facts"
            description="The fact half of the review queue is caught up."
          />
        ) : facts.rows.length === 0 ? (
          // Rows shrank underneath a stale offset (a page-2 ratify/reject) —
          // never rendered as "caught up": the count above still says facts
          // remain, and this line must agree with it (F1, invariant 14).
          <EmptyState
            kind="filtered"
            title="This page emptied out"
            description={`${facts.total} fact${facts.total === 1 ? "" : "s"} still remain${
              facts.total === 1 ? "s" : ""
            } — go back to see them.`}
            action={
              <Button
                size="sm"
                variant="outline"
                onClick={() => setFactsOffset(0)}
              >
                Back to the first page
              </Button>
            }
          />
        ) : (
          <>
            {facts.rows.map((fact) => (
              <FactRow
                key={fact.id}
                fact={fact}
                onRatify={setRatifyTarget}
                onReject={setRejectTarget}
                onDismissSuspicion={setDismissTarget}
              />
            ))}
            <PageControls
              offset={factsOffset}
              limit={PAGE}
              total={facts.total}
              onPrev={() => setFactsOffset((o) => Math.max(0, o - PAGE))}
              onNext={() => setFactsOffset((o) => o + PAGE)}
            />
          </>
        )}
      </ListSurface>

      <ListSurface
        title="Ungrounded articles"
        populated={articles.total > 0}
        meta="arrival order — no consequence ranking for articles yet"
      >
        {articles.error ? (
          <EmptyState
            kind="filtered"
            title="Could not load the article queue"
            description="The vault did not answer. This is a failed read, not an empty queue."
          />
        ) : articles.loading && articles.rows.length === 0 ? (
          // A pending read is not an absence — skeleton rows in the shape
          // of the queue that is coming.
          <div
            className="flex flex-col gap-2 py-2"
            role="status"
            aria-label="Loading the article queue"
          >
            {Array.from({ length: 4 }, (_, i) => (
              <Skeleton key={i} className="h-16 w-full rounded-md" />
            ))}
          </div>
        ) : articles.total === 0 ? (
          <EmptyState
            kind="empty"
            icon={ClipboardCheck}
            title="No ungrounded articles"
            description="The article half of the review queue is caught up. article_synthesis is still a placeholder job, so this arm has no live producer yet."
          />
        ) : articles.rows.length === 0 ? (
          <EmptyState
            kind="filtered"
            title="This page emptied out"
            description={`${articles.total} article${
              articles.total === 1 ? "" : "s"
            } still remain${articles.total === 1 ? "s" : ""} — go back to see them.`}
            action={
              <Button
                size="sm"
                variant="outline"
                onClick={() => setArticlesOffset(0)}
              >
                Back to the first page
              </Button>
            }
          />
        ) : (
          <>
            {articles.rows.map((article) => (
              <ArticleRow key={article.id} article={article} />
            ))}
            <PageControls
              offset={articlesOffset}
              limit={PAGE}
              total={articles.total}
              onPrev={() => setArticlesOffset((o) => Math.max(0, o - PAGE))}
              onNext={() => setArticlesOffset((o) => o + PAGE)}
            />
          </>
        )}
      </ListSurface>

      <AlertDialog
        open={ratifyTarget != null}
        onOpenChange={(open) => {
          if (!open) setRatifyTarget(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Ratify this fact?</AlertDialogTitle>
            <AlertDialogDescription>
              This records you as a human origin; the fact will render as
              confirmed. A later re-extraction that withdraws every memory
              source still leaves the human fact_source, so the record survives.
              This cannot be undone by the machine; only another human action
              can reverse it.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <p className="text-muted-foreground border-border border-t border-dashed pt-2 font-mono text-sm">
            POST /api/v1/knowledge/facts/{ratifyTarget?.id}/ratify ·
            authenticated · never exposed over the unauthenticated MCP surface
          </p>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => ratifyTarget && runRatify(ratifyTarget)}
            >
              <UserCheck className="mr-1.5 size-3.5" />
              Ratify as confirmed
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={rejectTarget != null}
        onOpenChange={(open) => {
          if (!open) setRejectTarget(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Reject this fact?</AlertDialogTitle>
            <AlertDialogDescription className="flex items-start gap-2">
              <AlertTriangle
                aria-hidden
                className="text-warning mt-0.5 h-4 w-4 shrink-0"
              />
              <span>
                Withdraws belief in this fact (the same primitive a source
                withdrawal uses) and journals a human_verdict event. This does
                not change verification_status or review_state directly — it is
                a belief-axis action, not a rung change.
              </span>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <p className="text-muted-foreground border-border border-t border-dashed pt-2 font-mono text-sm">
            POST /api/v1/review-queue/facts/{rejectTarget?.id}/reject ·
            authenticated
          </p>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => rejectTarget && runReject(rejectTarget)}
            >
              <XCircle className="mr-1.5 size-3.5" />
              Reject
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>

      <AlertDialog
        open={dismissTarget != null}
        onOpenChange={(open) => {
          if (!open) setDismissTarget(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Dismiss this contradiction flag?
            </AlertDialogTitle>
            <AlertDialogDescription>
              Says the model scan's finding was wrong — not that the fact is.
              The fact keeps its rung either way; the flag never moved one. The
              dismissal is journalled, and that record is what keeps the next
              recompute from raising the same flag again.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <p className="text-muted-foreground border-border border-t border-dashed pt-2 font-mono text-sm">
            POST /api/v1/review-queue/facts/{dismissTarget?.id}
            /dismiss-suspicion · authenticated · not a human_verdict — it
            adjudicates the finding, not the fact
          </p>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => dismissTarget && runDismiss(dismissTarget)}
            >
              <EyeOff className="mr-1.5 size-3.5" />
              Dismiss suspicion
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
