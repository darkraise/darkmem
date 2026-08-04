import { Link } from "@tanstack/react-router"
import {
  AlertTriangle,
  ArrowLeft,
  CircleAlert,
  FileQuestion,
  Library,
  Loader2,
} from "lucide-react"
import { Accordion } from "darkraise-ui/components/accordion"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { Separator } from "darkraise-ui/components/separator"
import { useSetPageChrome } from "@/components/app-chrome"
import { LayerChip, useDetailLevel, VerificationBadge } from "@/components/darkmem"
import { DEMO } from "@/lib/demo-flag"
import { useDemoFact } from "@/demo/hooks"
import { distinctOriginCount } from "@/demo/knowledge"
import type { FactLadderEvent as DemoLadderEvent } from "@/demo/types"
import { type LiveFactDetailData, useFactDetail } from "../use-facts"
import {
  AppliesWhenChips,
  FactTriple,
  RungTransition,
  UnderSourcedBadge,
} from "./fact-parts"
import { FactSourcesGroups, sourceGroupsToFlatSources } from "./fact-sources"
import { BeliefWindowRow } from "./belief-window"
import { DisputePanel } from "./dispute-panel"
import { LiveDisputePanel } from "./live-dispute"
import { FactLadderHistory } from "./fact-ladder"
import { DetailSection } from "./detail-section"

/** `/knowledge/facts/$factId` — plain component, `factId` as a prop rather
 *  than read off `Route.useParams()`, so it renders (and tests) without a
 *  router context, the same way `ReviewQueue`/`FactRow` do. */
export function FactDetail({ factId }: { factId: string }) {
  return DEMO ? <DemoFactDetail factId={factId} /> : <LiveFactDetail factId={factId} />
}

// ───────────────────────────── demo (unchanged) ─────────────────────────────

function LadderRow({ event }: { event: DemoLadderEvent }) {
  return (
    <div className="border-border flex flex-wrap items-start gap-2.5 border-t border-dashed py-2.5 first:border-t-0 first:pt-0">
      <span className="text-muted-foreground w-40 shrink-0 pt-0.5 font-mono text-sm">
        {event.at}
      </span>
      <div className="min-w-52 flex-1 space-y-1">
        <p className="text-sm">{event.description}</p>
        {event.transition && (
          <RungTransition from={event.transition.from} to={event.transition.to} />
        )}
        {event.note && (
          <p className="text-muted-foreground text-sm">{event.note}</p>
        )}
      </div>
    </div>
  )
}

function MetaRow({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <>
      <dt className="text-muted-foreground font-mono">{label}</dt>
      <dd className="min-w-0 break-words">{children}</dd>
    </>
  )
}

function DemoFactDetail({ factId }: { factId: string }) {
  const fact = useDemoFact(factId)

  useSetPageChrome({
    icon: Library,
    title: "Fact detail",
    description:
      "One L2 fact — its sources, ladder history, belief window, and context.",
    parent: { label: "Facts", href: "/knowledge/facts" },
  })

  if (!fact) {
    return (
      <div>
        <EmptyState
          icon={<FileQuestion aria-hidden className="h-6 w-6" />}
          title="Fact not found"
          description="This fact does not exist in the demo store."
          action={
            <Button variant="outline" asChild>
              <Link to="/knowledge/facts">
                <ArrowLeft className="mr-2 size-4" />
                Back to Facts
              </Link>
            </Button>
          }
        />
      </div>
    )
  }

  const disputed = fact.verification_status === "disputed"
  const distinctOrigins = distinctOriginCount(fact.sources)

  return (
    <div className="mx-auto max-w-3xl">
      {/* Hero — the claim and its verification state, nothing else competing.
          The status itself (badge, disputed, under-sourced) stays visible up
          here in every mode (invariant 14); only supporting detail discloses. */}
      <div className="space-y-4 pt-2 pb-6">
        <div className="flex flex-wrap items-center gap-2">
          <LayerChip layer={2} />
          {/* verification_status verbatim — never softened, never
              recomputed client-side (invariant 14). */}
          <VerificationBadge
            status={fact.verification_status}
            detail={fact.claim}
          />
          {fact.under_sourced_note && <UnderSourcedBadge />}
          {fact.code_provenance && (
            <Badge variant="outline" size="sm" className="rounded-sm font-mono">
              code@{fact.code_provenance.commit_sha}
            </Badge>
          )}
          <span className="text-muted-foreground ml-auto font-mono text-sm">
            fact {fact.id.slice(0, 8)}
          </span>
        </div>
        <FactTriple
          subject={fact.subject_name}
          rel={fact.rel_type}
          object={fact.object_name}
          className="text-lg"
        />
        <p className="max-w-[70ch] text-base leading-relaxed">
          {fact.fact_text}
        </p>
        <p className="text-muted-foreground max-w-[70ch] font-mono text-sm">
          {fact.claim}
        </p>
        {disputed && (
          <div className="border-warning/55 bg-warning/8 flex max-w-[70ch] items-start gap-2 rounded-sm border border-dashed px-2.5 py-1.5 text-sm">
            <CircleAlert
              aria-hidden
              className="text-warning mt-0.5 h-4 w-4 shrink-0"
            />
            <span>
              Dispute open — both sides on record below at strictly equal
              weight. Resolution happens only in the{" "}
              <Link to="/knowledge/review" className="text-primary">
                Review queue →
              </Link>
            </span>
          </div>
        )}
      </div>

      <Separator />

      {/* Everything supporting — on demand. The most essential section for
          this fact's state starts open; the rest starts collapsed. */}
      <Accordion
        type="multiple"
        defaultValue={[fact.dispute ? "dispute" : "sources"]}
      >
        {fact.sources.length > 0 && (
          <DetailSection
            value="sources"
            title="Sources"
            meta={`${distinctOrigins} distinct ${distinctOrigins === 1 ? "origin" : "origins"} · ${fact.sources.length} ${fact.sources.length === 1 ? "row" : "rows"}`}
            hint="fact_sources rows grouped by origin_key; the badge's K is COUNT(DISTINCT origin_key) over these groups, never the raw row count."
          >
            <FactSourcesGroups sources={fact.sources} />
            {fact.under_sourced_note && (
              <p className="text-muted-foreground text-sm">
                {fact.under_sourced_note}
              </p>
            )}
            {fact.candidate_note && (
              <p className="text-muted-foreground text-sm">
                {fact.candidate_note}
              </p>
            )}
          </DetailSection>
        )}

        {fact.dispute && (
          <DetailSection
            value="dispute"
            title={
              disputed
                ? "Both sides — strictly equal weight, no winner"
                : "Dispute history — resolved by human ratification"
            }
            meta={disputed ? "open" : "resolved"}
            hint={
              disputed
                ? "Both sides carry an overlapping validity window — that overlap is what makes this a genuine contradiction rather than a succession. Resolution happens only in the Review queue; this page never adjudicates."
                : "Both sides' origins remain on record — ratification resolved the rung, it did not erase the losing side's sources."
            }
          >
            <p className="text-sm font-semibold">{fact.dispute.summary}</p>
            <DisputePanel dispute={fact.dispute} />
            {disputed && (
              <p className="text-muted-foreground text-sm">
                Origin counts are shown on both sides without a comparative
                treatment — corroboration count does not adjudicate a dispute.{" "}
                <Link to="/knowledge/review" className="text-primary">
                  Adjudicate in Review →
                </Link>
              </p>
            )}
          </DetailSection>
        )}

        <DetailSection
          value="ladder"
          title="Verification ladder"
          meta={`${fact.ladder.length} ${fact.ladder.length === 1 ? "event" : "events"}`}
          hint="every rung transition this fact has taken — the machine ceiling is corroborated; only a human ratify reaches confirmed."
        >
          <div>
            {fact.ladder.map((event, i) => (
              <LadderRow key={i} event={event} />
            ))}
          </div>
        </DetailSection>

        {fact.windows.length > 0 && (
          <DetailSection
            value="windows"
            title="Belief window"
            meta={`${fact.windows.length} ${fact.windows.length === 1 ? "window" : "windows"}`}
            hint="valid_at / invalid_at / expired_at as a timeline, showing what the belief was at a given point in time. Closed windows are retained as history, not live claims."
          >
            <div className="space-y-2.5">
              {fact.windows.map((window, i) => (
                <BeliefWindowRow key={i} window={window} />
              ))}
            </div>
          </DetailSection>
        )}

        <DetailSection
          value="record"
          title="Record & provenance"
          meta={fact.project}
        >
          <dl className="grid grid-cols-[8rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
            <MetaRow label="fact_id">{fact.id.slice(0, 8)}</MetaRow>
            <MetaRow label="project">{fact.project}</MetaRow>
            <MetaRow label="review_state">{fact.review_state ?? "—"}</MetaRow>
            <MetaRow label="as_of">{fact.as_of}</MetaRow>
            <MetaRow label="applies_when">
              <AppliesWhenChips items={fact.applies_when} />
            </MetaRow>
            {fact.code_provenance && (
              <>
                <MetaRow label="commit_sha">
                  <span className="font-mono">
                    {fact.code_provenance.commit_sha}
                  </span>
                </MetaRow>
                <MetaRow label="basis">{fact.code_provenance.basis}</MetaRow>
                <MetaRow label="file_path">
                  <span className="font-mono">
                    {fact.code_provenance.file_path}
                  </span>
                </MetaRow>
                <MetaRow label="symbol_key">
                  <span className="font-mono">
                    {fact.code_provenance.symbol_key}
                  </span>
                </MetaRow>
              </>
            )}
          </dl>
          {fact.ratified && (
            /* div, not p — VerificationBadge renders block content and
               must never sit inside a paragraph. */
            <div className="border-border flex flex-wrap items-center gap-2 border-t border-dashed pt-2.5 text-sm">
              <VerificationBadge status="confirmed" />
              <span>
                ratified by <b className="font-semibold">{fact.ratified.by}</b>{" "}
                on {fact.ratified.on} — the ratification wrote a human-kind
                fact_source, so a later re-extraction that withdraws every
                memory source still leaves this one
              </span>
            </div>
          )}
        </DetailSection>
      </Accordion>
    </div>
  )
}

// ───────────────────────────── live (T2.86) ─────────────────────────────

function LiveFactDetailChrome() {
  useSetPageChrome({
    icon: Library,
    title: "Fact detail",
    description: "One L2 fact — its sources, ladder history and context.",
    parent: { label: "Facts", href: "/knowledge/facts" },
  })
  return null
}

function BackToFacts() {
  return (
    <Button variant="outline" asChild>
      <Link to="/knowledge/facts">
        <ArrowLeft className="mr-2 size-4" />
        Back to Facts
      </Link>
    </Button>
  )
}

function LiveFactDetailBody({ fact }: { fact: LiveFactDetailData }) {
  const advanced = useDetailLevel((s) => s.level) === "advanced"
  const disputed = fact.verification_status === "disputed"
  const flatSources = sourceGroupsToFlatSources(fact.sources)
  const rowCount = fact.sources.reduce((n, group) => n + group.sources.length, 0)

  return (
    <div className="mx-auto max-w-3xl">
      {/* Hero — same discipline as the demo page: the status itself never
          moves behind the Simple/Advanced toggle (invariant 14); only the
          raw triple, and the record section's technical identifiers, do. */}
      <div className="space-y-4 pt-2 pb-6">
        <div className="flex flex-wrap items-center gap-2">
          <LayerChip layer={2} />
          <VerificationBadge status={fact.verification_status} detail={fact.claim} />
          {fact.under_sourced && <UnderSourcedBadge />}
          <span className="text-muted-foreground ml-auto font-mono text-sm">
            fact {fact.id.slice(0, 8)}
          </span>
        </div>
        {advanced && (
          <FactTriple
            subject={fact.subject_name}
            rel={fact.rel_type}
            object={fact.object_name}
            className="text-lg"
          />
        )}
        <p className="max-w-[70ch] text-base leading-relaxed">{fact.fact_text}</p>
        {fact.claim && (
          <p className="text-muted-foreground max-w-[70ch] font-mono text-sm">
            {fact.claim}
          </p>
        )}
        {disputed && (
          <div className="border-warning/55 bg-warning/8 flex max-w-[70ch] items-start gap-2 rounded-sm border border-dashed px-2.5 py-1.5 text-sm">
            <CircleAlert
              aria-hidden
              className="text-warning mt-0.5 h-4 w-4 shrink-0"
            />
            <span>
              Dispute open — both sides on record below at strictly equal
              weight. Resolution happens only in the{" "}
              <Link to="/knowledge/review" className="text-primary">
                Review queue →
              </Link>
            </span>
          </div>
        )}
      </div>

      <Separator />

      <Accordion type="multiple" defaultValue={[fact.dispute ? "dispute" : "sources"]}>
        {fact.sources.length > 0 && (
          <DetailSection
            value="sources"
            title="Sources"
            meta={`${fact.sources.length} distinct ${fact.sources.length === 1 ? "origin" : "origins"} · ${rowCount} ${rowCount === 1 ? "row" : "rows"}`}
            hint="fact_sources rows grouped by origin_key; the badge's K is COUNT(DISTINCT origin_key) over these groups, never the raw row count."
          >
            <FactSourcesGroups sources={flatSources} />
          </DetailSection>
        )}

        {fact.dispute && (
          <DetailSection
            value="dispute"
            title="Both sides — strictly equal weight, no winner"
            meta="open"
            hint="Resolution happens only in the Review queue; this page never adjudicates."
          >
            <LiveDisputePanel dispute={fact.dispute} />
            <p className="text-muted-foreground text-sm">
              Corroboration count does not adjudicate a dispute.{" "}
              <Link to="/knowledge/review" className="text-primary">
                Adjudicate in Review →
              </Link>
            </p>
          </DetailSection>
        )}

        <DetailSection
          value="ladder"
          title="Verification ladder"
          meta={
            fact.ladder.length === fact.ladder_total
              ? `${fact.ladder.length} ${fact.ladder.length === 1 ? "event" : "events"}`
              : `${fact.ladder.length} of ${fact.ladder_total} loaded`
          }
          hint={
            fact.ladder.length === fact.ladder_total
              ? "every object_type='fact' events row for this id, oldest to newest — the raw journal, not a narrative built on top of it."
              : `the ${fact.ladder.length} most recent of ${fact.ladder_total} object_type='fact' events rows for this id, oldest to newest — the earlier history exists but is not loaded here.`
          }
        >
          <FactLadderHistory events={fact.ladder} />
        </DetailSection>

        <DetailSection
          value="window"
          title="Belief window"
          meta={fact.belief_window.invalid_at ? "closed" : "open"}
        >
          <BeliefWindowRow window={fact.belief_window} />
          {fact.demotion_pending_since && (
            <p className="text-muted-foreground text-sm">
              under-sourced since {fact.demotion_pending_since}
            </p>
          )}
        </DetailSection>

        <DetailSection value="record" title="Record & provenance" meta={fact.project}>
          <dl className="grid grid-cols-[8rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
            <MetaRow label="fact_id">{fact.id.slice(0, 8)}</MetaRow>
            <MetaRow label="project">{fact.project}</MetaRow>
            <MetaRow label="review_state">{fact.review_state ?? "—"}</MetaRow>
            <MetaRow label="as_of">{fact.as_of}</MetaRow>
            <MetaRow label="applies_when">
              <AppliesWhenChips items={fact.applies_when} />
            </MetaRow>
            {advanced && (
              <>
                <MetaRow label="triple_key">
                  <span className="font-mono">{fact.triple_key}</span>
                </MetaRow>
                {fact.source_file && (
                  <MetaRow label="source_file">
                    <span className="font-mono">{fact.source_file}</span>
                  </MetaRow>
                )}
                {fact.reference_time && (
                  <MetaRow label="reference_time">{fact.reference_time}</MetaRow>
                )}
                {fact.learned_in && fact.learned_in.length > 0 && (
                  <MetaRow label="learned_in">
                    <span className="font-mono">{fact.learned_in.join(", ")}</span>
                  </MetaRow>
                )}
              </>
            )}
          </dl>
        </DetailSection>
      </Accordion>
    </div>
  )
}

function LiveFactDetail({ factId }: { factId: string }) {
  const state = useFactDetail(factId)

  return (
    <div>
      <LiveFactDetailChrome />
      {state.status === "loading" && (
        <div className="flex justify-center py-16">
          <Loader2 aria-hidden className="text-muted-foreground h-6 w-6 animate-spin" />
        </div>
      )}
      {state.status === "not_found" && (
        <EmptyState
          icon={<FileQuestion aria-hidden className="h-6 w-6" />}
          title="Fact not found"
          description="No fact exists with this id."
          action={<BackToFacts />}
        />
      )}
      {state.status === "invalid" && (
        <EmptyState
          icon={<FileQuestion aria-hidden className="h-6 w-6" />}
          title="Not a valid fact id"
          description="This link is malformed — retrying it will not help."
          action={<BackToFacts />}
        />
      )}
      {state.status === "failed" && (
        <EmptyState
          icon={<AlertTriangle aria-hidden className="h-6 w-6" />}
          title="Couldn't load this fact"
          description="The read failed — this is a fetch problem, not a missing fact. Try again."
          action={
            <div className="flex gap-2">
              <Button variant="outline" onClick={state.retry}>
                Retry
              </Button>
              <BackToFacts />
            </div>
          }
        />
      )}
      {state.status === "ready" && <LiveFactDetailBody fact={state.fact} />}
    </div>
  )
}
