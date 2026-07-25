import { useState } from "react"
import { Link } from "@tanstack/react-router"
import {
  ChevronDown,
  ClipboardCheck,
  History,
  Link2,
  Pencil,
  TrendingUp,
  UserCheck,
  XCircle,
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
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "darkraise-ui/components/collapsible"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { cn } from "darkraise-ui/lib"
import { LayerChip, VerificationBadge } from "@/components/darkmem"
import { useDemoReviewItems } from "@/demo/hooks"
import { useDemoStore } from "@/demo/store"
import type { DemoReviewItem } from "@/demo/types"
import { ListSurface } from "./list-surface"
import { UnderSourcedBadge } from "./fact-parts"

const RATIFIED_BY = "q.tran"

function DisputeSides({
  sides,
}: {
  sides: NonNullable<DemoReviewItem["dispute_sides"]>
}) {
  const [first, second] = sides
  const side = (s: typeof first) => (
    <div className="border-border space-y-1.5 rounded-md border p-2.5">
      <VerificationBadge status="disputed" />
      <p className="text-sm">{s.assertion}</p>
      <p className="text-muted-foreground text-sm">{s.origins}</p>
    </div>
  )
  return (
    <div className="grid grid-cols-1 gap-2 md:grid-cols-[1fr_auto_1fr]">
      {side(first)}
      <div className="text-muted-foreground flex items-center justify-center font-mono text-sm uppercase">
        vs
      </div>
      {side(second)}
    </div>
  )
}

function ReviewItemCard({
  item,
  onRatify,
}: {
  item: DemoReviewItem
  onRatify: (item: DemoReviewItem) => void
}) {
  const reground = useDemoStore((s) => s.regroundReviewItem)
  const clear = useDemoStore((s) => s.clearReviewItem)

  const detailLink =
    item.kind === "fact" ? (
      <Link to="/knowledge/facts/$factId" params={{ factId: item.target_id }}>
        <Pencil className="mr-1.5 size-3.5" />
        Edit
      </Link>
    ) : (
      <Link
        to="/knowledge/articles/$articleId"
        params={{ articleId: item.target_id }}
      >
        <Pencil className="mr-1.5 size-3.5" />
        Edit
      </Link>
    )

  return (
    <div className="border-border space-y-2 rounded-md border p-3">
      <div className="flex flex-wrap items-center gap-2">
        <LayerChip layer={item.layer} />
        <span className="text-sm font-semibold">{item.title}</span>
        <span className="text-muted-foreground ml-auto font-mono text-sm">
          {item.state_tag}
        </span>
      </div>
      {item.claim_line && (
        <p className="text-sm font-semibold">{item.claim_line}</p>
      )}
      <div className="flex flex-wrap items-center gap-2">
        {item.badge && !item.dispute_sides && (
          <VerificationBadge status={item.badge} />
        )}
        {item.under_sourced && <UnderSourcedBadge />}
        {item.decayed && (
          <Badge
            variant="outline"
            size="sm"
            className="text-muted-foreground gap-1 font-mono"
          >
            <History aria-hidden className="h-3 w-3" />
            {item.decayed_note ?? "decayed — still served labelled"}
          </Badge>
        )}
        {item.coverage_pct != null && (
          <Badge
            variant="outline"
            size="sm"
            className="text-muted-foreground gap-1 border-dashed font-mono"
          >
            <ClipboardCheck aria-hidden className="h-3 w-3" />
            claim-support coverage: {item.coverage_pct}%
          </Badge>
        )}
      </div>
      {/* Disputed items show BOTH conflicting sides — no picked winner. */}
      {item.dispute_sides && <DisputeSides sides={item.dispute_sides} />}
      {item.note && <p className="text-muted-foreground text-sm">{item.note}</p>}
      <p className="text-muted-foreground flex items-center gap-1.5 text-sm">
        <TrendingUp aria-hidden className="h-3.5 w-3.5 shrink-0" />
        <span>
          <b className="text-foreground font-semibold">why ranked here:</b>{" "}
          {item.rank_note}
        </span>
      </p>
      <div className="border-border flex flex-wrap items-center gap-2 border-t border-dashed pt-2">
        <Button size="sm" onClick={() => onRatify(item)}>
          <UserCheck className="mr-1.5 size-3.5" />
          Ratify → confirmed
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={item.reground_queued}
          onClick={() => reground(item.id)}
        >
          <Link2 className="mr-1.5 size-3.5" />
          {item.reground_queued ? "Re-ground queued" : "Re-ground"}
        </Button>
        <Button size="sm" variant="outline" asChild>
          {detailLink}
        </Button>
        <Button size="sm" variant="outline" onClick={() => clear(item.id)}>
          <XCircle className="mr-1.5 size-3.5" />
          Clear
        </Button>
        <span className="text-muted-foreground ml-auto font-mono text-[10px]">
          ratify is REST/UI, authenticated — never exposed over MCP
        </span>
      </div>
      {item.reground_queued && (
        <p className="text-muted-foreground text-sm italic">
          re-ground queued — the verification pass will recompute sources on
          its next cycle; the item stays open until it lands.
        </p>
      )}
    </div>
  )
}

export function ReviewQueue() {
  const items = useDemoReviewItems()
  const ratify = useDemoStore((s) => s.ratifyReviewItem)
  const [ratifyTarget, setRatifyTarget] = useState<DemoReviewItem | null>(null)
  const [decayedOpen, setDecayedOpen] = useState(false)

  const active = items.filter((i) => !i.decayed)
  const decayed = items.filter((i) => i.decayed)

  return (
    <div className="space-y-3">
      <ListSurface
        title="Review queue"
        populated={items.length > 0}
        meta={`${active.length} open · consequence-ranked, not FIFO`}
      >
        {items.length === 0 ? (
          // Empty is reassurance, not absence: caught up, not never-disputed.
          <EmptyState
            icon={<ClipboardCheck aria-hidden className="h-6 w-6" />}
            title="No disputes to adjudicate"
            description="The review queue is caught up — every disputed fact and ungrounded article was ratified, re-grounded, edited, or cleared."
          />
        ) : (
          <>
            <div className="border-border bg-muted/15 text-muted-foreground rounded-md border border-dashed px-2.5 py-1.5 text-sm">
              Every row below is{" "}
              <b className="text-foreground font-semibold">served labelled</b>{" "}
              to retrieval right now, exactly as shown — queue position never
              withholds a fact or article from search results.
            </div>
            {active.map((item) => (
              <ReviewItemCard
                key={item.id}
                item={item}
                onRatify={setRatifyTarget}
              />
            ))}
            {decayed.length > 0 && (
              <Collapsible open={decayedOpen} onOpenChange={setDecayedOpen}>
                <div className="border-border bg-muted/10 rounded-md border border-dashed">
                  <CollapsibleTrigger className="flex w-full items-center gap-2 px-3 py-2.5 text-sm font-semibold">
                    <History aria-hidden className="text-muted-foreground h-4 w-4" />
                    Decayed — still served labelled ({decayed.length})
                    <ChevronDown
                      aria-hidden
                      className={cn(
                        "text-muted-foreground ml-auto h-4 w-4 transition-transform",
                        decayedOpen && "rotate-180",
                      )}
                    />
                  </CollapsibleTrigger>
                  <CollapsibleContent>
                    <div className="border-border space-y-2.5 border-t border-dashed p-3">
                      <p className="text-muted-foreground text-sm">
                        Unreviewed past dispute_stale_days: priority decays off
                        the active queue above, but status is unchanged and the
                        item is still served with both sides —{" "}
                        <b className="text-foreground font-semibold">
                          a priority change, not a resolution
                        </b>
                        . Nothing here is silently resolved.
                      </p>
                      {decayed.map((item) => (
                        <ReviewItemCard
                          key={item.id}
                          item={item}
                          onRatify={setRatifyTarget}
                        />
                      ))}
                    </div>
                  </CollapsibleContent>
                </div>
              </Collapsible>
            )}
          </>
        )}
      </ListSurface>

      {/* Ratify-to-confirmed is the single most consequential action here:
          the machine ceiling is corroborated — only a human ratify reaches
          confirmed — so it gets the strongest confirmation treatment. */}
      <AlertDialog
        open={ratifyTarget != null}
        onOpenChange={(open) => {
          if (!open) setRatifyTarget(null)
        }}
      >
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>
              Ratify this {ratifyTarget?.kind ?? "item"}?
            </AlertDialogTitle>
            <AlertDialogDescription>
              This records you as a human origin; the {ratifyTarget?.kind}{" "}
              will render as confirmed. A later re-extraction that withdraws
              every memory source still leaves the human fact_source, so the
              record survives. Any dispute resolves in favour of the side you
              are ratifying — the other side's origins remain on record, they
              simply no longer block the rung. This cannot be undone by the
              machine; only another human action can reverse it.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <p className="text-muted-foreground border-border border-t border-dashed pt-2 font-mono text-sm">
            POST /api/v1/knowledge/{ratifyTarget?.kind === "article" ? "articles" : "facts"}/
            {ratifyTarget?.target_id}/ratify · authenticated · never exposed
            over the unauthenticated MCP surface
          </p>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={() => {
                if (ratifyTarget) ratify(ratifyTarget.id, RATIFIED_BY)
                setRatifyTarget(null)
              }}
            >
              <UserCheck className="mr-1.5 size-3.5" />
              Ratify as confirmed
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
