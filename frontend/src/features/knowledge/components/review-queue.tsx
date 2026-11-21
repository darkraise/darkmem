import { useEffect, useState } from "react"
import { Link } from "@tanstack/react-router"
import {
  AlertTriangle,
  ArrowUpRight,
  EyeOff,
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
import {
  EmptyState,
  listItemClass,
  Timestamp,
  VerificationBadge,
} from "@/components/darkmem"
import { toast } from "darkraise-ui/components/sonner"
import { ApiError } from "@/lib/api"
import { DEMO } from "@/lib/demo-flag"
import { useDemoStore } from "@/demo/store"
import { useDismissSuspicion, useRatifyFact, useRejectFact } from "@/hooks/api"
import { SuppressedBadge, UnderSourcedBadge } from "./fact-parts"
import { ListSurface, QueuePager } from "./list-surface"
import {
  useReviewArticleRows,
  useReviewFactRows,
  type ReviewArticleRowData,
  type ReviewFactRowData,
} from "../use-review-queue"

const PAGE = 10

function EvidenceBlock({ fact }: { fact: ReviewFactRowData }) {
  if (fact.verification_status !== "disputed") return null
  const c = fact.evidence?.payload?.contradiction
  if (!c) return null
  return (
    <p className="border-border bg-muted/10 rounded-md border border-dashed p-2 text-sm">
      Contradicted by: {c.counterpart_subject} {c.counterpart_rel_type}{" "}
      {c.counterpart_object}
    </p>
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
          · since <Timestamp iso={s.suspected_at} />
        </span>
      </p>
      <p>counterpart: {triple ?? "not recorded"}</p>
      {s.counterpart_expired_at != null && (
        <p>
          counterpart withdrawn <Timestamp iso={s.counterpart_expired_at} />
        </p>
      )}
    </div>
  )
}

/** How a success toast names the fact it acted on: the triple when the row
 *  has one, otherwise the readable sentence (clipped). */
function factLabel(fact: ReviewFactRowData): string {
  if (
    fact.subject_name != null &&
    fact.rel_type != null &&
    fact.object_name != null
  ) {
    return `${fact.subject_name} → ${fact.rel_type} → ${fact.object_name}`
  }
  return fact.fact_text.length > 120
    ? `${fact.fact_text.slice(0, 117)}…`
    : fact.fact_text
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
  // The reason chip only adds something when no badge already names it.
  const reasonShown =
    fact.reason !== fact.verification_status &&
    !(fact.reason === "under-sourced" && fact.under_sourced)
  return (
    <div className={listItemClass({ className: "space-y-2 p-3" })}>
      <div className="flex flex-wrap items-center gap-2">
        {/* Honesty labels: unconditional in every detail level. */}
        <VerificationBadge status={fact.verification_status} />
        {reasonShown && (
          <Badge variant="outline" size="sm" className="font-mono">
            {fact.reason}
          </Badge>
        )}
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
      <EvidenceBlock fact={fact} />
      <div className="border-border flex flex-wrap items-center gap-2 border-t border-dashed pt-2">
        <Button onClick={() => onRatify(fact)}>
          <UserCheck className="mr-1.5 size-3.5" />
          Ratify → confirmed
        </Button>
        <Button variant="outline" onClick={() => onReject(fact)}>
          <XCircle className="mr-1.5 size-3.5" />
          Reject
        </Button>
        {fact.suspected_contradiction != null && (
          <Button variant="outline" onClick={() => onDismissSuspicion(fact)}>
            <EyeOff className="mr-1.5 size-3.5" />
            Dismiss suspicion
          </Button>
        )}
        <Button variant="outline" asChild>
          {/* The detail page is read-only, so this is "open", never "edit". */}
          <Link to="/knowledge/facts/$factId" params={{ factId: fact.id }}>
            <ArrowUpRight className="mr-1.5 size-3.5" />
            Open fact
          </Link>
        </Button>
        <span className="text-muted-foreground ml-auto text-xs">
          queued <Timestamp iso={fact.created_at} />
        </span>
      </div>
    </div>
  )
}

function ArticleRow({ article }: { article: ReviewArticleRowData }) {
  return (
    <div className={listItemClass({ className: "space-y-2 p-3" })}>
      <div className="flex flex-wrap items-center gap-2">
        <Badge variant="outline" size="sm" className="font-mono">
          {article.status}
        </Badge>
        {article.reason !== "unspecified" && (
          <Badge variant="outline" size="sm" className="font-mono">
            {article.reason}
          </Badge>
        )}
        <span className="text-muted-foreground ml-auto font-mono text-sm">
          project: {article.project}
        </span>
      </div>
      <p className="text-sm font-semibold">
        {article.title ?? article.subject_key}
      </p>
      {article.resynthesis_held_at && (
        <p className="text-warning-text text-sm">
          Re-synthesis could not be grounded
          {article.resynthesis_held_coverage !== null &&
            ` (coverage ${article.resynthesis_held_coverage.toFixed(2)})`}
          ; the current article stays, marked stale.
        </p>
      )}
      {article.content_preview && (
        <p className="text-muted-foreground text-sm">
          {article.content_preview}
        </p>
      )}
      <p className="text-muted-foreground text-sm">
        {article.synthesized_at ? (
          <>
            synthesised <Timestamp iso={article.synthesized_at} />
          </>
        ) : (
          "not synthesised yet"
        )}
        {" · created "}
        <Timestamp iso={article.created_at} />
      </p>
      <div className="border-border flex flex-wrap items-center gap-2 border-t border-dashed pt-2">
        <Button variant="outline" asChild>
          <Link
            to="/knowledge/articles/$articleId"
            params={{ articleId: article.id }}
          >
            <ArrowUpRight className="mr-1.5 size-3.5" />
            Open article
          </Link>
        </Button>
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
      demoRatify(fact.queue_id, "q.tran")
      toast.success("Fact ratified as confirmed", {
        description: factLabel(fact),
      })
    } else {
      ratifyMutation.mutate(
        { factId: fact.id },
        {
          onSuccess: () => {
            toast.success("Fact ratified as confirmed", {
              description: factLabel(fact),
            })
          },
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
      demoClear(fact.queue_id)
      toast.success("Fact rejected — belief withdrawn", {
        description: factLabel(fact),
      })
    } else {
      rejectMutation.mutate(
        { factId: fact.id },
        {
          onSuccess: () => {
            toast.success("Fact rejected — belief withdrawn", {
              description: factLabel(fact),
            })
          },
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
        onSuccess: () => {
          toast.success("Contradiction flag dismissed", {
            description: factLabel(fact),
          })
        },
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

  return (
    <div className="space-y-3">
      <ListSurface
        title="Disputed / under-sourced facts"
        populated={facts.total > 0}
        meta={facts.total > 0 ? `${facts.total} open` : undefined}
      >
        {facts.error ? (
          <EmptyState
            kind="filtered"
            title="Could not load the fact queue"
            description="The request failed. Reload to try again."
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
            description="Nothing to review."
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
              <Button variant="outline" onClick={() => setFactsOffset(0)}>
                Back to the first page
              </Button>
            }
          />
        ) : (
          <>
            {facts.rows.map((fact) => (
              <FactRow
                key={fact.queue_id}
                fact={fact}
                onRatify={setRatifyTarget}
                onReject={setRejectTarget}
                onDismissSuspicion={setDismissTarget}
              />
            ))}
            <QueuePager
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
        meta={articles.total > 0 ? `${articles.total} open` : undefined}
      >
        {articles.error ? (
          <EmptyState
            kind="filtered"
            title="Could not load the article queue"
            description="The request failed. Reload to try again."
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
            description="Nothing to review."
          />
        ) : articles.rows.length === 0 ? (
          <EmptyState
            kind="filtered"
            title="This page emptied out"
            description={`${articles.total} article${
              articles.total === 1 ? "" : "s"
            } still remain${articles.total === 1 ? "s" : ""} — go back to see them.`}
            action={
              <Button variant="outline" onClick={() => setArticlesOffset(0)}>
                Back to the first page
              </Button>
            }
          />
        ) : (
          <>
            {articles.rows.map((article) => (
              <ArticleRow key={article.queue_id} article={article} />
            ))}
            <QueuePager
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
              The fact becomes confirmed, with you recorded as a source. Only
              another human action can reverse it.
            </AlertDialogDescription>
          </AlertDialogHeader>
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
                className="text-warning-text mt-0.5 h-4 w-4 shrink-0"
              />
              <span>
                Records your rejection and closes this fact&apos;s belief window
                as of now, so it is no longer served as current. Its{" "}
                <b className="font-semibold">
                  {rejectTarget?.verification_status ?? "verification"}
                </b>{" "}
                label is not changed; the fact page will show it as belief
                withdrawn.
              </span>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => rejectTarget && runReject(rejectTarget)}
            >
              <XCircle className="mr-1.5 size-3.5" />
              Reject — withdraw belief
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
              Marks the model's contradiction finding as wrong. The fact keeps
              its status, and the same flag is not raised again.
            </AlertDialogDescription>
          </AlertDialogHeader>
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
