import { useMemo } from "react"
import { Link } from "@tanstack/react-router"
import { GitBranch, FileText } from "lucide-react"
import {
  EmptyState,
  ExclusionStrip,
  listItemClass,
  VerificationBadge,
  type VerificationStatus,
} from "@/components/darkmem"
import { DEMO } from "@/lib/demo-flag"
import { useProjectStore } from "@/stores/project-store"
import { useDemoArticles } from "@/demo/hooks"
import { liveArticles, withheldArticles } from "@/demo/knowledge"
import type { DemoArticle } from "@/demo/types"
import {
  useArticles,
  type ArticleRow as LiveArticle,
} from "@/hooks/api/use-articles-api"
import { ListSurface } from "./list-surface"
import { StaleBadge } from "./fact-parts"

/** What this tab renders, in the one shape both modes can honestly fill.
 *
 *  Not `DemoArticle`: that fixture type carries an entailed/total breakdown
 *  and a stale `since`/`reason` the live door does not serve, and adapting a
 *  real row into it would mean inventing all four. A view type carries what
 *  each source actually has, and `coverage: null` is a first-class value —
 *  with the groundedness gate open an article's coverage is *unmeasured*,
 *  which is a different statement from 0.00 and must not render as one.
 */
interface ArticleView {
  id: string
  title: string
  project: string
  excerpt: string
  /** The rung as **served**. Never recomputed here: the backend's label
   *  producer already gated it, and a fallback would assert a rung nothing
   *  certified. */
  status: VerificationStatus
  /** The backend-authored claim sentence, shown verbatim or not at all. The
   *  live door serves none today, so it is null there rather than written
   *  here — a frontend-composed claim is a second, unbacked copy. */
  claim: string | null
  stale: boolean
  staleSince: string | null
  coverage: number | null
  reviewState: string | null
  supersedes: string | null
  meta: string
}

const NO_ARTICLES: ArticleView[] = []

function fromDemo(article: DemoArticle): ArticleView {
  return {
    id: article.id,
    title: article.title,
    project: article.project,
    excerpt: article.excerpt,
    status: article.verification_status,
    claim: article.claim,
    stale: article.stale !== null,
    staleSince: article.stale?.since ?? null,
    coverage: article.coverage.ratio,
    reviewState: article.review_state,
    supersedes: article.supersedes ?? null,
    meta: article.meta,
  }
}

function fromLive(article: LiveArticle): ArticleView {
  return {
    id: article.id,
    title: article.title ?? article.subject_key,
    project: article.project,
    excerpt: article.excerpt ?? "",
    status: (article.status ?? "candidate") as VerificationStatus,
    claim: null,
    stale: article.stale,
    staleSince: null,
    coverage: article.coverage,
    reviewState: article.review_state,
    // The list carries the pointer *forward* (`superseded_by`) and a live row
    // has none by construction. The lineage backwards is on the detail read,
    // which is where a reader who wants history already is.
    supersedes: null,
    meta: article.synthesized_at ? article.synthesized_at.slice(0, 10) : "",
  }
}

/** The coverage readout. Rendered in **both** detail levels — doc 13 §5.2
 *  makes it an honesty signal rather than technical detail, which is the same
 *  distinction that made the raw fact-set fingerprint advanced-only while the
 *  stale label stayed in both (T1.48). */
function CoverageReadout({ coverage }: { coverage: number | null }) {
  if (coverage === null) return null
  return <span className="font-mono text-sm">coverage {coverage.toFixed(2)}</span>
}

function ArticleRow({ article }: { article: ArticleView }) {
  return (
    <div
      className={listItemClass({
        interactive: true,
        className: "flex flex-wrap items-start gap-3 p-2.5",
      })}
    >
      <div
        data-testid="article-badges"
        className="flex w-40 shrink-0 flex-col items-start gap-1.5"
      >
        <VerificationBadge
          status={article.status}
          detail={article.claim ?? undefined}
        />
        {article.stale && <StaleBadge />}
      </div>
      <div className="min-w-56 flex-1 space-y-1">
        <Link
          to="/knowledge/articles/$articleId"
          params={{ articleId: article.id }}
          className="hover:text-primary-text block text-sm font-semibold transition-colors"
        >
          {article.title}
        </Link>
        <p className="text-muted-foreground line-clamp-2 text-sm">
          {article.excerpt}
        </p>
        {article.stale && (
          <p className="text-muted-foreground text-sm italic">
            synthesised before the latest verified change
          </p>
        )}
        {article.supersedes && (
          <Link
            to="/knowledge/articles/$articleId"
            params={{ articleId: article.supersedes }}
            className="text-muted-foreground hover:text-primary-text flex w-fit items-center gap-1.5 text-sm transition-colors"
          >
            <GitBranch aria-hidden className="h-3.5 w-3.5" />
            supersedes 1 prior article —{" "}
            <span className="text-primary-text">view history →</span>
          </Link>
        )}
      </div>
      <div className="flex shrink-0 flex-col items-end gap-0.5">
        <CoverageReadout coverage={article.coverage} />
        <span className="text-muted-foreground font-mono text-sm">
          {article.meta}
        </span>
      </div>
    </div>
  )
}

export function ArticlesTab() {
  const demoArticles = useDemoArticles()
  const project = useProjectStore((s) => s.activeProject) ?? "all"

  const live = useArticles(
    { project: project === "all" ? undefined : project },
    { enabled: !DEMO },
  )

  const articles: ArticleView[] = useMemo(() => {
    if (DEMO) {
      return liveArticles(demoArticles, project).map(fromDemo)
    }
    return live.data ? live.data.items.map(fromLive) : NO_ARTICLES
  }, [demoArticles, live.data, project])

  const withheld = useMemo(() => {
    if (DEMO) return withheldArticles(demoArticles, project).length
    // The live list serves an open-review article like any other row, so the
    // count is read off the rows rather than from a second door.
    return live.data
      ? live.data.items.filter((a) => a.review_state === "open").length
      : 0
  }, [demoArticles, live.data, project])

  const shown = useMemo(
    () => articles.filter((a) => a.reviewState !== "open"),
    [articles],
  )

  return (
    <div className="space-y-4">
      <ListSurface
        title="Articles"
        populated={shown.length > 0}
        meta={`${shown.length} ${shown.length === 1 ? "article" : "articles"}`}
      >
        {/* An ungrounded / disputed article is withheld from this
            corroborated view and routed to Review — counted, never
            silently dropped. */}
        {withheld > 0 && (
          <ExclusionStrip
            items={[
              {
                count: withheld,
                unit: withheld === 1 ? "article" : "articles",
                reason: "awaiting review in Knowledge → Review",
              },
            ]}
          />
        )}
        {shown.length > 0 ? (
          shown.map((article) => (
            <ArticleRow key={article.id} article={article} />
          ))
        ) : (
          <EmptyState
            kind="empty"
            icon={FileText}
            title="No articles yet"
            description={
              withheld > 0
                ? "Every article here is awaiting review in Knowledge → Review."
                : "Articles appear once a subject has enough corroborated facts."
            }
          />
        )}
      </ListSurface>
    </div>
  )
}
