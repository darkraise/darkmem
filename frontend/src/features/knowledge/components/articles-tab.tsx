import { useMemo } from "react"
import { Link } from "@tanstack/react-router"
import { GitBranch, FileText } from "lucide-react"
import {
  EmptyState,
  ExclusionStrip,
  LayerChip,
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
  if (coverage === null) {
    return (
      <span className="text-muted-foreground font-mono text-sm">
        claim-support coverage not measured
      </span>
    )
  }
  return (
    <span className="font-mono text-sm">
      claim-support coverage {coverage.toFixed(2)}
    </span>
  )
}

function ArticleRow({ article }: { article: ArticleView }) {
  return (
    <div
      className={listItemClass({
        interactive: true,
        className: "flex flex-wrap items-start gap-3 p-2.5",
      })}
    >
      <div className="flex shrink-0 flex-col items-start gap-1.5">
        <LayerChip layer={3} />
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
          className="hover:text-primary block text-sm font-semibold transition-colors"
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
            className="text-muted-foreground hover:text-primary flex w-fit items-center gap-1.5 text-sm transition-colors"
          >
            <GitBranch aria-hidden className="h-3.5 w-3.5" />
            supersedes 1 prior article —{" "}
            <span className="text-primary">view history →</span>
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

  const projectLabel = project === "all" ? "all projects" : project

  return (
    <div className="space-y-4">
      <div className="border-border flex flex-wrap items-center gap-2.5 border-b border-dashed pb-3">
        <span className="text-muted-foreground ml-auto font-mono text-sm">
          sorted by priority — verified-fact count · read-heat · centrality
        </span>
      </div>

      <ListSurface
        title={`Articles — project: ${projectLabel}`}
        populated={shown.length > 0}
        meta={`${shown.length} ${shown.length === 1 ? "subject" : "subjects"}`}
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
                reason:
                  "review_state=open — withheld from the corroborated view and routed to Knowledge → Review; nothing was deleted.",
                tag: "by_review_state",
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
              DEMO
                ? "Articles are synthesised once corroborated facts exist for a subject — none do here yet. No corroborated or confirmed facts means nothing for the synthesiser to ground a claim in, so it produces no draft rather than an ungrounded one."
                : withheld > 0
                  ? // Saying "nothing is being withheld" directly beneath a
                    // strip counting withheld articles is the surface calling
                    // itself a liar. When every article is in review, the empty
                    // list has a cause and the copy names it.
                    "Every article for this scope is in review — none is being shown here, and the strip above says how many and why. They are readable in Knowledge → Review; nothing was deleted."
                  : "No articles have been synthesised for this project yet. Synthesis runs in the background over subjects that hold enough corroborated facts to ground one — nothing is being withheld from you here."
            }
          />
        )}
      </ListSurface>
    </div>
  )
}
