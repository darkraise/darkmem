import { useMemo, useState } from "react"
import { Link } from "@tanstack/react-router"
import { FileText, GitBranch } from "lucide-react"
import { EmptyState } from "darkraise-ui/components/empty-state"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { ExclusionStrip, LayerChip, VerificationBadge } from "@/components/darkmem"
import { useDemoArticles } from "@/demo/hooks"
import { liveArticles, withheldArticles } from "@/demo/knowledge"
import type { DemoArticle } from "@/demo/types"
import { ListSurface } from "./list-surface"
import { StaleBadge } from "./fact-parts"

function ArticleRow({ article }: { article: DemoArticle }) {
  return (
    <div className="border-border flex flex-wrap items-start gap-3 rounded-md border p-2.5">
      <div className="flex shrink-0 flex-col items-start gap-1.5">
        <LayerChip layer={3} />
        <VerificationBadge
          status={article.verification_status}
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
        <span className="font-mono text-sm">
          claim-support coverage {article.coverage.ratio.toFixed(2)}
        </span>
        <span className="text-muted-foreground font-mono text-sm">
          {article.meta}
        </span>
      </div>
    </div>
  )
}

export function ArticlesTab() {
  const articles = useDemoArticles()
  const [project, setProject] = useState("darkmem")

  const projects = useMemo(
    () => [...new Set(articles.map((a) => a.project))].sort(),
    [articles],
  )
  const live = useMemo(
    () => liveArticles(articles, project),
    [articles, project],
  )
  const withheld = useMemo(
    () => withheldArticles(articles, project),
    [articles, project],
  )

  const projectLabel = project === "all" ? "all projects" : project

  return (
    <div className="space-y-4">
      <div className="border-border flex flex-wrap items-center gap-2.5 border-b border-dashed pb-3">
        <Select value={project} onValueChange={setProject}>
          <SelectTrigger className="w-44 rounded-full" aria-label="Project scope">
            <SelectValue>project: {projectLabel}</SelectValue>
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All projects</SelectItem>
            {projects.map((p) => (
              <SelectItem key={p} value={p}>
                {p}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <span className="text-muted-foreground ml-auto font-mono text-sm">
          sorted by priority — verified-fact count · read-heat · centrality
        </span>
      </div>

      <ListSurface
        title={`Articles — project: ${projectLabel}`}
        populated={live.length > 0}
        meta={`${live.length} ${live.length === 1 ? "subject" : "subjects"}`}
      >
        {/* An ungrounded / disputed article is withheld from this
            corroborated view and routed to Review — counted, never
            silently dropped. */}
        {withheld.length > 0 && (
          <ExclusionStrip
            items={[
              {
                count: withheld.length,
                unit: withheld.length === 1 ? "article" : "articles",
                reason:
                  "review_state=open — withheld from the corroborated view and routed to Knowledge → Review; nothing was deleted.",
                tag: "by_review_state",
              },
            ]}
          />
        )}
        {live.length > 0 ? (
          live.map((article) => (
            <ArticleRow key={article.id} article={article} />
          ))
        ) : (
          <EmptyState
            icon={<FileText aria-hidden className="h-6 w-6" />}
            title="No articles yet"
            description="Articles are synthesised once corroborated facts exist for a subject — none do here yet. No corroborated or confirmed facts means nothing for the synthesiser to ground a claim in, so it produces no draft rather than an ungrounded one."
          />
        )}
      </ListSurface>
    </div>
  )
}
