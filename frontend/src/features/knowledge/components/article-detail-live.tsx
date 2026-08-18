import { useMemo, useState } from "react"
import { Link } from "@tanstack/react-router"
import { ArrowLeft, GitBranch } from "lucide-react"
import { Accordion } from "darkraise-ui/components/accordion"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "@/components/darkmem"
import { Progress } from "darkraise-ui/components/progress"
import { Separator } from "darkraise-ui/components/separator"
import {
  LayerChip,
  VerificationBadge,
  useDetailLevel,
  type VerificationStatus,
} from "@/components/darkmem"
import {
  useArticle,
  type ArticleCitation,
  type ArticleDetail,
} from "@/hooks/api/use-articles-api"
import { DetailSection } from "./detail-section"
import { StaleBadge } from "./fact-parts"

/** One prose segment: either plain text, or text a citation grounds. */
interface Segment {
  text: string
  citation: ArticleCitation | null
  index: number
}

/** Cut the article's prose at its citation spans.
 *
 *  The spans are the stored `int4range` bounds, served rather than recomputed
 *  — the citation row is the hard FK doc 09 §4.3 protects, and a span this
 *  component derived from the prose could mark text the row does not ground.
 *
 *  Overlaps are resolved by taking the first span that starts, then skipping
 *  any later span that starts inside it. Overlapping citations are not
 *  expected — a claim is a sentence — but silently interleaving them would
 *  render text under a citation that does not cover it, and dropping them
 *  without saying so would hide a grounded claim. The skipped ones still
 *  appear in the citations list below, so nothing is lost from the page.
 */
export function segmentProse(
  content: string,
  citations: ArticleCitation[],
): Segment[] {
  const spans = citations
    .map((citation, index) => ({ citation, index }))
    .filter(
      ({ citation }) =>
        typeof citation.claim_span[0] === "number" &&
        typeof citation.claim_span[1] === "number" &&
        (citation.claim_span[1] as number) > (citation.claim_span[0] as number),
    )
    .sort((a, b) => a.citation.claim_span[0]! - b.citation.claim_span[0]!)

  const segments: Segment[] = []
  let cursor = 0
  for (const { citation, index } of spans) {
    const lo = Math.max(citation.claim_span[0]!, 0)
    const hi = Math.min(citation.claim_span[1]!, content.length)
    if (lo < cursor || lo >= hi) continue
    if (lo > cursor) {
      segments.push({
        text: content.slice(cursor, lo),
        citation: null,
        index: -1,
      })
    }
    segments.push({ text: content.slice(lo, hi), citation, index })
    cursor = hi
  }
  if (cursor < content.length) {
    segments.push({ text: content.slice(cursor), citation: null, index: -1 })
  }
  return segments
}

/** The claim-support coverage readout, rendered in **both** detail levels.
 *
 *  Doc 13 §5.2 calls it an honesty signal rather than technical detail, and
 *  `null` is a first-class value: with the groundedness gate open no article
 *  has a measured coverage, and 0.00 would read as "measured, and ungrounded"
 *  — the opposite of what is true. */
function Coverage({ coverage }: { coverage: number | null }) {
  if (coverage === null) {
    return (
      <p className="text-sm">
        <b className="text-base font-semibold">not measured</b> — no
        claim-support coverage has been computed for this article. Coverage is
        measured by the entailment pass, which needs a qualified verification
        judge; until one is qualified this reads as unmeasured rather than as a
        number.
      </p>
    )
  }
  return (
    <>
      <Progress
        value={Math.round(coverage * 100)}
        aria-label="Claim-support coverage"
      />
      <p className="text-sm">
        <b className="text-base font-semibold">{coverage.toFixed(2)}</b>{" "}
        claim-support coverage — the fraction of this article's sentences a
        cited fact entails.
      </p>
    </>
  )
}

function CitationRow({
  citation,
  ordinal,
}: {
  citation: ArticleCitation
  ordinal: number
}) {
  return (
    <div
      id={`cite-${ordinal}`}
      className="border-border flex flex-wrap items-baseline gap-2 rounded-md border border-dashed p-2"
    >
      <span className="font-mono text-sm font-semibold">{ordinal}</span>
      <Link
        to="/knowledge/facts/$factId"
        params={{ factId: citation.fact_id }}
        className="text-primary font-mono text-sm hover:underline"
      >
        fact {citation.fact_id.slice(0, 8)}
      </Link>
      <span className="text-muted-foreground font-mono text-sm">
        {citation.subject_name} {citation.rel_type} {citation.object_name}
      </span>
      <span className="min-w-52 flex-1 text-sm">“{citation.fact}”</span>
      {!citation.believed && (
        <span className="text-warning font-mono text-sm">
          belief window closed — retained, no longer believed
        </span>
      )}
    </div>
  )
}

function Detail({ article }: { article: ArticleDetail }) {
  const level = useDetailLevel((s) => s.level)
  const [openSections, setOpenSections] = useState<string[]>(["citations"])

  const segments = useMemo(
    () => segmentProse(article.content, article.citations),
    [article.content, article.citations],
  )

  // A pill click must land on a citation row that exists, so re-open the
  // section first: an anchor into a collapsed accordion resolves to nothing.
  const revealCitations = (ordinal: number) => {
    setOpenSections((open) =>
      open.includes("citations") ? open : [...open, "citations"],
    )
    setTimeout(() => {
      document
        .getElementById(`cite-${ordinal}`)
        ?.scrollIntoView({ block: "center" })
    }, 0)
  }

  const uncited = segments.every((segment) => segment.citation === null)

  return (
    <div className="mx-auto max-w-3xl">
      <div className="space-y-4 pt-2 pb-6">
        <div className="flex flex-wrap items-center gap-2">
          <LayerChip layer={3} />
          <VerificationBadge
            status={(article.status ?? "candidate") as VerificationStatus}
          />
          {article.stale && <StaleBadge />}
          {article.stale && (
            <span className="text-muted-foreground text-sm italic">
              synthesised before the latest verified change
            </span>
          )}
          {/* The bare stale label cannot distinguish "refresh pending" from
              "refresh attempted and failed", which is the invariant-14 gap the
              §4.4 amendment names. Rendered in both detail levels: it is an
              honesty signal about what the system tried, not a fingerprint. */}
          {article.resynthesis_held_at && (
            <span className="text-warning text-sm">
              a re-synthesis was attempted and held
              {article.resynthesis_held_coverage !== null &&
                ` at coverage ${article.resynthesis_held_coverage.toFixed(2)}`}
            </span>
          )}
          <span className="text-muted-foreground ml-auto font-mono text-sm">
            article {article.id.slice(0, 8)}
          </span>
        </div>
        <h2 className="max-w-[70ch] text-2xl leading-snug font-semibold">
          {article.title ?? article.subject_key}
        </h2>
        {article.label_suppressed && (
          <p className="text-muted-foreground max-w-[70ch] font-mono text-sm">
            rung withheld: {article.label_suppressed}
          </p>
        )}
        {article.superseded_by && (
          <Link
            to="/knowledge/articles/$articleId"
            params={{ articleId: article.superseded_by }}
            className="hover:text-primary flex w-fit items-center gap-1.5 text-sm transition-colors"
          >
            <GitBranch
              aria-hidden
              className="text-muted-foreground h-3.5 w-3.5"
            />
            superseded_by → article {article.superseded_by.slice(0, 8)} — the
            current statement of record for this subject
          </Link>
        )}
        {article.supersedes && (
          <Link
            to="/knowledge/articles/$articleId"
            params={{ articleId: article.supersedes }}
            className="text-muted-foreground hover:text-primary flex w-fit items-center gap-1.5 text-sm transition-colors"
          >
            <GitBranch aria-hidden className="h-3.5 w-3.5" />
            supersedes article {article.supersedes.slice(0, 8)} — view history
          </Link>
        )}

        <p className="max-w-[70ch] leading-relaxed">
          {segments.map((segment, i) =>
            segment.citation ? (
              <a
                key={i}
                href={`#cite-${segment.index + 1}`}
                onClick={() => revealCitations(segment.index + 1)}
                title={`grounded by citation ${segment.index + 1}`}
                className="decoration-primary/50 hover:decoration-primary underline decoration-dotted underline-offset-4"
              >
                {segment.text}
                <sup className="text-primary ml-0.5 font-mono text-xs">
                  {segment.index + 1}
                </sup>
              </a>
            ) : (
              <span key={i}>{segment.text}</span>
            ),
          )}
        </p>
        {uncited && article.citations.length === 0 && (
          <p className="text-muted-foreground max-w-[70ch] text-sm">
            No citation rows are recorded for this article, so no sentence on
            this page is linked to the fact that grounds it.
          </p>
        )}
      </div>

      <Separator />

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
            {article.citations.map((citation, i) => (
              <CitationRow
                key={citation.id}
                citation={citation}
                ordinal={i + 1}
              />
            ))}
          </div>
        </DetailSection>

        <DetailSection
          value="coverage"
          title="Claim-support coverage"
          meta={
            article.coverage === null
              ? "not measured"
              : article.coverage.toFixed(2)
          }
          hint="confidence is labelled claim-support coverage, never a vague score — it is the fraction of this article's sentences a cited fact entails."
        >
          <Coverage coverage={article.coverage} />
        </DetailSection>

        <DetailSection value="record" title="Record" meta={article.project}>
          <dl className="grid grid-cols-[8rem_minmax(0,1fr)] gap-x-3 gap-y-1.5 text-sm">
            <dt className="text-muted-foreground font-mono">article</dt>
            <dd className="min-w-0 break-words">{article.id.slice(0, 8)}</dd>
            <dt className="text-muted-foreground font-mono">subject</dt>
            <dd className="min-w-0 break-words">{article.subject_key}</dd>
            <dt className="text-muted-foreground font-mono">project</dt>
            <dd className="min-w-0 break-words">{article.project}</dd>
            <dt className="text-muted-foreground font-mono">synthesised</dt>
            <dd className="min-w-0 break-words">
              {article.synthesized_at ?? "—"}
            </dd>
            {/* The stale label above is the honesty signal and renders in every
                mode; the raw hash is a fingerprint, which simple mode collapses
                (T1.48's distinction, kept). */}
            {level === "advanced" && (
              <>
                <dt className="text-muted-foreground font-mono">
                  fact_set_hash
                </dt>
                <dd className="min-w-0 font-mono break-words">
                  {article.fact_set_hash ?? "—"}
                </dd>
              </>
            )}
          </dl>
        </DetailSection>
      </Accordion>
    </div>
  )
}

/** The live article detail (T3.06). Kept beside the demo renderer rather than
 *  merged into it: the fixture type carries an entailed/total breakdown, a
 *  stale reason and pre-sectioned prose the door does not serve, and one
 *  renderer over both would have to invent them. */
export function ArticleDetailLive({ articleId }: { articleId: string }) {
  const { data: article, isPending, isError } = useArticle(articleId)

  if (isPending) {
    return <p className="text-muted-foreground p-6 text-sm">Loading article…</p>
  }

  if (isError || !article) {
    return (
      <EmptyState
        kind="missing"
        scope="page"
        title="Article not found"
        description="No article with this id exists in the vault. A superseded article stays readable through its lineage, so a missing one was never written rather than replaced."
        action={
          <Button variant="outline" asChild>
            <Link to="/knowledge/articles">
              <ArrowLeft className="mr-2 size-4" />
              Back to Articles
            </Link>
          </Button>
        }
      />
    )
  }

  return <Detail article={article} />
}
