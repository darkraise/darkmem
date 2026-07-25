import { createFileRoute, Link } from "@tanstack/react-router"
import {
  ArrowLeft,
  FileQuestion,
  GitBranch,
  Library,
  TriangleAlert,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { Progress } from "darkraise-ui/components/progress"
import { Separator } from "darkraise-ui/components/separator"
import { useSetPageChrome } from "@/components/app-chrome"
import {
  LayerChip,
  useDetailLevel,
  VerificationBadge,
} from "@/components/darkmem"
import { useDemoArticle, useDemoFacts } from "@/demo/hooks"
import type { ArticleCitation, ArticleSection, DemoFact } from "@/demo/types"
import { StaleBadge } from "@/features/knowledge/components/fact-parts"

export const Route = createFileRoute(
  "/_authenticated/knowledge_/articles/$articleId",
)({
  component: ArticleDetailPage,
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

// Inline citation pill: a citation IS the mechanism that earns the
// supported badge, so it shares the primary colour family on purpose.
function CitePill({ citeKey }: { citeKey: string }) {
  return (
    <a
      href={`#cite-${citeKey}`}
      title={`grounded by citation ${citeKey}`}
      className="border-primary/40 bg-primary/10 text-primary ml-1 inline-flex h-4 min-w-5 items-center justify-center rounded-full border px-1 align-super font-mono text-[10px] font-semibold no-underline"
    >
      {citeKey}
    </a>
  )
}

function SectionBlock({ section }: { section: ArticleSection }) {
  return (
    <div className="space-y-1.5">
      <span className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
        {section.label}
      </span>
      <p className="text-base leading-relaxed">
        {section.sentences.map((sentence, i) => (
          <span key={i}>
            {i > 0 && " "}
            {sentence.text}
            {sentence.cite && <CitePill citeKey={sentence.cite} />}
          </span>
        ))}
      </p>
    </div>
  )
}

function CitationRow({
  citation,
  fact,
}: {
  citation: ArticleCitation
  fact?: DemoFact
}) {
  const level = useDetailLevel((s) => s.level)
  return (
    <div
      id={`cite-${citation.key}`}
      className="border-border target:border-primary/60 flex flex-wrap items-center gap-2.5 rounded-md border p-2"
    >
      <span className="font-mono text-sm font-semibold">{citation.key}</span>
      <Link
        to="/knowledge/facts/$factId"
        params={{ factId: citation.fact_id }}
        className="hover:text-primary font-mono text-sm transition-colors"
      >
        fact {citation.fact_id.slice(0, 8)}
      </Link>
      {level === "advanced" && (
        <span className="text-muted-foreground font-mono text-[10px] whitespace-nowrap">
          claim_span {citation.claim_span}
        </span>
      )}
      <LayerChip layer={2} />
      {fact && (
        <VerificationBadge status={fact.verification_status} detail={fact.claim} />
      )}
      <span className="min-w-52 flex-1 text-sm">“{citation.quote}”</span>
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

function ArticleDetailPage() {
  const { articleId } = Route.useParams()
  const article = useDemoArticle(articleId)
  const facts = useDemoFacts()

  useSetPageChrome({
    icon: Library,
    title: "Article detail",
    description:
      "One L3 article — synthesised, grounded prose whose every claim links to the verified fact that entails it.",
    breadcrumbs: [
      { label: "Knowledge", href: "/knowledge" },
      { label: "Articles", href: "/knowledge?tab=articles" },
    ],
  })

  if (!article) {
    return (
      <div>
        <EmptyState
          icon={<FileQuestion aria-hidden className="h-6 w-6" />}
          title="Article not found"
          description="This article does not exist in the demo store."
          action={
            <Button variant="outline" asChild>
              <Link to="/knowledge" search={{ tab: "articles" }}>
                <ArrowLeft className="mr-2 size-4" />
                Back to Articles
              </Link>
            </Button>
          }
        />
      </div>
    )
  }

  const superseded = article.verification_status === "superseded"
  const successor = article.superseded_by

  return (
    <div className="mx-auto max-w-6xl">
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,1fr)_19rem] lg:items-start">
        {/* main column — the synthesised prose is the hero */}
        <div className="min-w-0 space-y-4">
          <Card elevation="low">
            <CardHeader className="space-y-3 pb-3">
              <div className="flex flex-wrap items-center gap-2">
                <LayerChip layer={3} />
                {/* The terminal superseded status REPLACES the rung badge; the
                    stale overlay is appended, never a replacement. */}
                <VerificationBadge
                  status={article.verification_status}
                  detail={article.claim ?? undefined}
                />
                {article.stale && <StaleBadge />}
                {article.claim && (
                  <span className="font-mono text-sm">{article.claim}</span>
                )}
                {article.stale && (
                  <span className="text-muted-foreground text-sm italic">
                    synthesised before the latest verified change
                  </span>
                )}
              </div>
              <h2 className="text-xl leading-snug font-semibold">
                {article.title}
              </h2>
              {superseded && (
                <div className="space-y-1.5">
                  {successor && (
                    <Link
                      to="/knowledge/articles/$articleId"
                      params={{ articleId: successor }}
                      className="hover:text-primary flex w-fit items-center gap-1.5 text-sm transition-colors"
                    >
                      <GitBranch
                        aria-hidden
                        className="text-muted-foreground h-3.5 w-3.5"
                      />
                      superseded_by → article {successor.slice(0, 8)} — the
                      current statement of record for this subject
                    </Link>
                  )}
                  {article.last_rung_note && (
                    <p className="text-muted-foreground text-sm">
                      {article.last_rung_note}
                    </p>
                  )}
                </div>
              )}
              {article.ungrounded_note && (
                <div className="border-warning/55 bg-warning/8 flex items-start gap-2 rounded-sm border border-dashed px-2.5 py-1.5 text-sm">
                  <TriangleAlert
                    aria-hidden
                    className="text-warning mt-0.5 h-4 w-4 shrink-0"
                  />
                  <span>
                    {article.ungrounded_note}{" "}
                    <Link
                      to="/knowledge"
                      search={{ tab: "review" }}
                      className="text-primary"
                    >
                      Open the Review queue →
                    </Link>
                  </span>
                </div>
              )}
            </CardHeader>
            <CardContent className="space-y-4">
              <Separator />
              <div className="space-y-1">
                <p className="text-sm font-semibold">
                  {superseded
                    ? "Synthesised content (retained, not the servable statement of record)"
                    : "Synthesised content"}
                </p>
                <p className="text-muted-foreground text-sm">
                  grounded prose, organised by relation and applies_when
                  context — every sentence carries an inline citation to the
                  fact that grounds it.
                </p>
              </div>
              <div className="space-y-4">
                {article.sections.map((section) => (
                  <SectionBlock key={section.label} section={section} />
                ))}
              </div>
            </CardContent>
          </Card>

          <SectionCard
            title="Citations — the article's only provenance"
            hint="article_citations.fact_id is a hard FK to knowledge_triples — safe because facts are invalidate-not-delete, so a citation can never dangle. Synthesis input is restricted to the subject's non-disputed corroborated/confirmed facts, never a raw document."
          >
            <div className="space-y-1.5">
              {article.citations.map((citation) => (
                <CitationRow
                  key={citation.key}
                  citation={citation}
                  fact={facts.find((f) => f.id === citation.fact_id)}
                />
              ))}
            </div>
          </SectionCard>
        </div>

        {/* aside — provenance metadata, coverage, staleness */}
        <div className="space-y-4">
          <SectionCard title="Record">
            <dl className="grid grid-cols-[7rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
              <MetaRow label="article">{article.id.slice(0, 8)}</MetaRow>
              <MetaRow label="subject">
                {article.subject_key} · {article.subject_kind}
              </MetaRow>
              <MetaRow label="project">{article.project}</MetaRow>
              <MetaRow label="synthesised">{article.synthesized_at}</MetaRow>
              <MetaRow label="fact_set_hash">
                {article.stale ? (
                  <span className="text-warning">
                    at synthesis {article.fact_set_hash} → current{" "}
                    {article.current_fact_set_hash} (changed → stale)
                  </span>
                ) : (
                  <span className="font-mono">{article.fact_set_hash}</span>
                )}
              </MetaRow>
              <MetaRow label="applies_when">
                {article.applies_when_label}
              </MetaRow>
            </dl>
          </SectionCard>

          <SectionCard
            title="Claim-support coverage"
            hint="confidence is labelled claim-support coverage, never a vague score — it is the entailed/total ratio over this article's candidate sentences."
          >
            <Progress
              value={Math.round(article.coverage.ratio * 100)}
              aria-label="Claim-support coverage"
            />
            <p className="text-sm">
              <b className="text-base font-semibold">
                {article.coverage.ratio.toFixed(2)}
              </b>{" "}
              claim-support coverage — {article.coverage.entailed} /{" "}
              {article.coverage.total} candidate sentences entailed by a cited
              fact
              {article.stale && (
                <span className="text-muted-foreground">
                  {" "}
                  (unchanged since synthesis — re-synthesis has not run yet)
                </span>
              )}
            </p>
            {article.coverage_note && (
              <p className="text-muted-foreground text-sm">
                {article.coverage_note}
              </p>
            )}
          </SectionCard>

          {article.stale && (
            <SectionCard title="What changed">
              <p className="border-border bg-muted/25 rounded-md border border-dashed p-2.5 text-sm">
                {article.stale.reason} The stale overlay is surfaced wherever
                this article is served — it is a label, never a suppression.
              </p>
            </SectionCard>
          )}
        </div>
      </div>
    </div>
  )
}
