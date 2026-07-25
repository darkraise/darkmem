import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft, FileQuestion, Library } from "lucide-react"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { Separator } from "darkraise-ui/components/separator"
import { useSetPageChrome } from "@/components/app-chrome"
import { LayerChip, VerificationBadge } from "@/components/darkmem"
import { useDemoFact } from "@/demo/hooks"
import type { FactLadderEvent } from "@/demo/types"
import {
  AppliesWhenChips,
  FactTriple,
  RungTransition,
  UnderSourcedBadge,
} from "@/features/knowledge/components/fact-parts"
import { FactSourcesGroups } from "@/features/knowledge/components/fact-sources"
import { BeliefWindowRow } from "@/features/knowledge/components/belief-window"
import { DisputePanel } from "@/features/knowledge/components/dispute-panel"

export const Route = createFileRoute("/_authenticated/knowledge_/facts/$factId")({
  component: FactDetailPage,
})

function SectionCard({
  title,
  hint,
  children,
}: {
  title: string
  hint?: string
  children: React.ReactNode
}) {
  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-semibold">{title}</CardTitle>
        {hint && <CardDescription className="text-sm">{hint}</CardDescription>}
      </CardHeader>
      <CardContent className="space-y-2">{children}</CardContent>
    </Card>
  )
}

function LadderRow({ event }: { event: FactLadderEvent }) {
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

function FactDetailPage() {
  const { factId } = Route.useParams()
  const fact = useDemoFact(factId)

  useSetPageChrome({
    icon: Library,
    title: "Fact detail",
    description:
      "One L2 fact — its sources, ladder history, belief window, and context.",
    breadcrumbs: [
      { label: "Knowledge", href: "/knowledge" },
      { label: "Facts", href: "/knowledge?tab=facts" },
    ],
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
              <Link to="/knowledge" search={{ tab: "facts" }}>
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

  return (
    <div className="mx-auto max-w-6xl">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_19rem] lg:items-start">
        {/* main column — the claim and its verification are the hero */}
        <div className="min-w-0 space-y-4">
          <Card elevation="low">
            <CardHeader className="space-y-3 pb-3">
              <div className="flex flex-wrap items-center gap-2">
                <LayerChip layer={2} />
                {/* verification_status verbatim — never softened, never
                    recomputed client-side (invariant 14). */}
                <VerificationBadge
                  status={fact.verification_status}
                  detail={fact.claim}
                />
                {fact.code_provenance && (
                  <Badge
                    variant="outline"
                    size="sm"
                    className="rounded-sm font-mono"
                  >
                    code@{fact.code_provenance.commit_sha}
                  </Badge>
                )}
                {fact.under_sourced_note && <UnderSourcedBadge />}
                <span className="text-muted-foreground ml-auto font-mono text-sm">
                  fact {fact.id.slice(0, 8)}
                </span>
              </div>
              <FactTriple
                subject={fact.subject_name}
                rel={fact.rel_type}
                object={fact.object_name}
                className="text-base"
              />
            </CardHeader>
            <CardContent className="space-y-3">
              <p className="text-base leading-relaxed">{fact.fact_text}</p>
              <Separator />
              <p className="font-mono text-sm">{fact.claim}</p>
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
            </CardContent>
          </Card>

          {fact.sources.length > 0 && (
            <SectionCard
              title="Sources — grouped by origin_key"
              hint="fact_sources rows grouped by origin_key; the badge's K is COUNT(DISTINCT origin_key) over these groups, never the raw row count."
            >
              <FactSourcesGroups sources={fact.sources} />
            </SectionCard>
          )}

          {fact.dispute && (
            <SectionCard
              title={
                disputed
                  ? "Both sides — strictly equal weight, no winner"
                  : "Dispute history — resolved by human ratification"
              }
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
                  <Link
                    to="/knowledge"
                    search={{ tab: "review" }}
                    className="text-primary"
                  >
                    Adjudicate in Review →
                  </Link>
                </p>
              )}
            </SectionCard>
          )}

          <SectionCard
            title="Verification ladder"
            hint="every rung transition this fact has taken — the machine ceiling is corroborated; only a human ratify reaches confirmed."
          >
            <div>
              {fact.ladder.map((event, i) => (
                <LadderRow key={i} event={event} />
              ))}
            </div>
          </SectionCard>

          {fact.windows.length > 0 && (
            <SectionCard
              title="Belief window"
              hint="valid_at / invalid_at / expired_at as a timeline — what did we believe as of X. Closed windows are retained as history, not live claims."
            >
              <div className="space-y-2.5">
                {fact.windows.map((window, i) => (
                  <BeliefWindowRow key={i} window={window} />
                ))}
              </div>
            </SectionCard>
          )}
        </div>

        {/* aside — record metadata, context, provenance, ratification */}
        <div className="space-y-4">
          <SectionCard title="Record">
            <dl className="grid grid-cols-[7rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
              <MetaRow label="fact_id">{fact.id.slice(0, 8)}</MetaRow>
              <MetaRow label="project">{fact.project}</MetaRow>
              <MetaRow label="review_state">{fact.review_state ?? "—"}</MetaRow>
              <MetaRow label="as of">{fact.as_of}</MetaRow>
            </dl>
          </SectionCard>

          <SectionCard title="applies_when">
            <AppliesWhenChips items={fact.applies_when} />
          </SectionCard>

          {fact.code_provenance && (
            <SectionCard title="Code provenance">
              <dl className="grid grid-cols-[6rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
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
              </dl>
            </SectionCard>
          )}

          {fact.ratified && (
            <SectionCard title="Ratification">
              {/* div, not p — VerificationBadge renders block content and
                  must never sit inside a paragraph. */}
              <div className="flex flex-wrap items-center gap-2 text-sm">
                <VerificationBadge status="confirmed" />
                <span>
                  ratified by{" "}
                  <b className="font-semibold">{fact.ratified.by}</b> on{" "}
                  {fact.ratified.on} — the ratification wrote a human-kind
                  fact_source, so a later re-extraction that withdraws every
                  memory source still leaves this one
                </span>
              </div>
            </SectionCard>
          )}
        </div>
      </div>
    </div>
  )
}
