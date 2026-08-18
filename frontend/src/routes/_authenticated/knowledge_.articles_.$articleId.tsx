import { useState } from "react"
import { createFileRoute, Link } from "@tanstack/react-router"
import { ArrowLeft, GitBranch, Library, TriangleAlert } from "lucide-react"
import { Accordion } from "darkraise-ui/components/accordion"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "@/components/darkmem"
import { Progress } from "darkraise-ui/components/progress"
import { Separator } from "darkraise-ui/components/separator"
import { useSetPageChrome } from "@/components/app-chrome"
import { DEMO } from "@/lib/demo-flag"
import {
  LayerChip,
  useDetailLevel,
  VerificationBadge,
} from "@/components/darkmem"
import { useDemoArticle, useDemoFacts } from "@/demo/hooks"
import type { ArticleCitation, ArticleSection, DemoFact } from "@/demo/types"
import { ArticleDetailLive } from "@/features/knowledge/components/article-detail-live"
import { StaleBadge } from "@/features/knowledge/components/fact-parts"
import { DetailSection } from "@/features/knowledge/components/detail-section"

export const Route = createFileRoute(
  "/_authenticated/knowledge_/articles_/$articleId",
)({
  component: ArticleDetailPage,
})

// Inline citation pill: a citation IS the mechanism that earns the
// supported badge, so it shares the primary colour family on purpose.
function CitePill({
  citeKey,
  onNavigate,
}: {
  citeKey: string
  onNavigate: (citeKey: string) => void
}) {
  return (
    <a
      href={`#cite-${citeKey}`}
      title={`grounded by citation ${citeKey}`}
      onClick={() => onNavigate(citeKey)}
      className="border-primary/40 bg-primary/10 text-primary ml-1 inline-flex h-4 min-w-5 items-center justify-center rounded-full border px-1 align-super font-mono text-[10px] font-semibold no-underline"
    >
      {citeKey}
    </a>
  )
}

function SectionBlock({
  section,
  onNavigate,
}: {
  section: ArticleSection
  onNavigate: (citeKey: string) => void
}) {
  return (
    <div className="space-y-1.5">
      <span className="text-muted-foreground font-mono text-[10px] tracking-wide uppercase">
        {section.label}
      </span>
      <p className="max-w-[70ch] text-base leading-relaxed">
        {section.sentences.map((sentence, i) => (
          <span key={i}>
            {i > 0 && " "}
            {sentence.text}
            {sentence.cite && (
              <CitePill citeKey={sentence.cite} onNavigate={onNavigate} />
            )}
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
        <VerificationBadge
          status={fact.verification_status}
          detail={fact.claim}
        />
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
  const demoArticle = useDemoArticle(articleId)
  // Real mode reads the live door (T3.06). The two renderers stay apart
  // because the fixture type carries an entailed/total breakdown, a stale
  // reason and pre-sectioned prose the door does not serve — one renderer over
  // both would have to invent them.
  const article = DEMO ? demoArticle : undefined
  const facts = useDemoFacts()
  const level = useDetailLevel((s) => s.level)
  // Citations start disclosed so every #cite-K anchor resolves; a cite-pill
  // click re-opens the section if the reader collapsed it.
  const [openSections, setOpenSections] = useState<string[]>(["citations"])

  useSetPageChrome({
    icon: Library,
    title: "Article detail",
    description:
      "One L3 article — synthesised, grounded prose whose every claim links to the verified fact that entails it.",
    parent: { label: "Articles", href: "/knowledge/articles" },
  })

  if (!DEMO) {
    return <ArticleDetailLive articleId={articleId} />
  }

  if (!article) {
    return (
      <div>
        <EmptyState
          kind="missing"
          scope="page"
          title="Article not found"
          description={
            DEMO
              ? "This article does not exist in the demo store."
              : "Article synthesis is not shipped yet — it ships behind the groundedness gate, which is still open. There is no article channel to read."
          }
          action={
            <Button variant="outline" asChild>
              <Link to="/knowledge/articles">
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

  const revealCitations = (citeKey: string) => {
    setOpenSections((open) =>
      open.includes("citations") ? open : [...open, "citations"],
    )
    // If the section was collapsed, the anchor target mounts on the next
    // commit — re-run the jump so the citation link always resolves.
    setTimeout(() => {
      document.getElementById(`cite-${citeKey}`)?.scrollIntoView({
        block: "center",
      })
    }, 0)
  }

  return (
    <div className="mx-auto max-w-3xl">
      {/* Hero — status first (badge + stale + superseded pointer stay
          visible, invariant 14), then the grounded prose at a comfortable
          reading measure. Supporting detail discloses below. */}
      <div className="space-y-4 pt-2 pb-6">
        <div className="flex flex-wrap items-center gap-2">
          <LayerChip layer={3} />
          {/* The terminal superseded status REPLACES the rung badge; the
              stale overlay is appended, never a replacement. */}
          <VerificationBadge
            status={article.verification_status}
            detail={article.claim ?? undefined}
          />
          {article.stale && <StaleBadge />}
          {article.stale && (
            <span className="text-muted-foreground text-sm italic">
              synthesised before the latest verified change
            </span>
          )}
          <span className="text-muted-foreground ml-auto font-mono text-sm">
            article {article.id.slice(0, 8)}
          </span>
        </div>
        <h2 className="max-w-[70ch] text-2xl leading-snug font-semibold">
          {article.title}
        </h2>
        {article.claim && (
          <p className="text-muted-foreground max-w-[70ch] font-mono text-sm">
            {article.claim}
          </p>
        )}
        {superseded && successor && (
          <Link
            to="/knowledge/articles/$articleId"
            params={{ articleId: successor }}
            className="hover:text-primary flex w-fit items-center gap-1.5 text-sm transition-colors"
          >
            <GitBranch
              aria-hidden
              className="text-muted-foreground h-3.5 w-3.5"
            />
            superseded_by → article {successor.slice(0, 8)} — the current
            statement of record for this subject
          </Link>
        )}
        {article.ungrounded_note && (
          <div className="border-warning/55 bg-warning/8 flex max-w-[70ch] items-start gap-2 rounded-sm border border-dashed px-2.5 py-1.5 text-sm">
            <TriangleAlert
              aria-hidden
              className="text-warning mt-0.5 h-4 w-4 shrink-0"
            />
            <span>
              {article.ungrounded_note}{" "}
              <Link to="/knowledge/review" className="text-primary">
                Open the Review queue →
              </Link>
            </span>
          </div>
        )}

        {superseded && (
          <p className="text-muted-foreground text-sm">
            Synthesised content below is retained, not the servable statement of
            record.
          </p>
        )}
        <div className="space-y-5 pt-1">
          {article.sections.map((section) => (
            <SectionBlock
              key={section.label}
              section={section}
              onNavigate={revealCitations}
            />
          ))}
        </div>
      </div>

      <Separator />

      {/* Supporting detail on demand — citations start open (they are the
          article's only provenance and every pill anchors into them). */}
      <Accordion
        type="multiple"
        value={openSections}
        onValueChange={setOpenSections}
      >
        <DetailSection
          value="citations"
          title="Citations"
          meta={`${article.citations.length} · the article's only provenance`}
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
        </DetailSection>

        <DetailSection
          value="coverage"
          title="Claim-support coverage"
          meta={`${article.coverage.ratio.toFixed(2)} · ${article.coverage.entailed}/${article.coverage.total} entailed`}
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
        </DetailSection>

        {article.stale && (
          <DetailSection
            value="changed"
            title="What changed"
            meta={`stale since ${article.stale.since}`}
          >
            <p className="border-border bg-muted/25 rounded-md border border-dashed p-2.5 text-sm">
              {article.stale.reason} The stale overlay is surfaced wherever this
              article is served — it is a label, never a suppression.
            </p>
            {/* The stale label + reason above are the honesty signal and
                render in every mode; the raw hash comparison is a
                fingerprint, which simple mode hides (invariant 14 only
                protects the label, never the technical proof behind it). */}
            {level === "advanced" && (
              <p className="text-warning font-mono text-sm">
                fact_set_hash at synthesis {article.fact_set_hash} → current{" "}
                {article.current_fact_set_hash} (changed → stale)
              </p>
            )}
          </DetailSection>
        )}

        <DetailSection value="record" title="Record" meta={article.project}>
          <dl className="grid grid-cols-[8rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
            <MetaRow label="article">{article.id.slice(0, 8)}</MetaRow>
            <MetaRow label="subject">
              {article.subject_key} · {article.subject_kind}
            </MetaRow>
            <MetaRow label="project">{article.project}</MetaRow>
            <MetaRow label="synthesised">{article.synthesized_at}</MetaRow>
            {/* fact_set_hash is a fingerprint, not an honesty label — the
                stale overlay above already carries that signal in every
                mode, so the raw hash itself is advanced-only detail. */}
            {level === "advanced" && (
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
            )}
            <MetaRow label="applies_when">{article.applies_when_label}</MetaRow>
          </dl>
          {superseded && article.last_rung_note && (
            <p className="text-muted-foreground text-sm">
              {article.last_rung_note}
            </p>
          )}
        </DetailSection>
      </Accordion>
    </div>
  )
}
