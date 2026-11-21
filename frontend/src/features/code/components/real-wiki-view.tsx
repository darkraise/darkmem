import { useState } from "react"
import { useQuery } from "@tanstack/react-query"
import { FolderGit2,
  BookOpen,
} from "lucide-react"
import { Button } from "darkraise-ui/components/button"
import { toast } from "darkraise-ui/components/sonner"
import { Badge } from "darkraise-ui/components/badge"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { EmptyState } from "@/components/darkmem"
import { apiFetch } from "@/lib/api"
import { useRepos, useReindexRepo } from "@/hooks/api"
import type { ReindexInput } from "../schemas"
import { RealReindexDialog } from "./real-reindex-dialog"

interface WikiData {
  repo_name: string
  overview: string | null
  modules: Array<{
    path: string
    summary: string | null
    symbol_count: number
    files: Array<{
      path: string
      language: string | null
      symbols: Array<{
        name: string
        kind: string
        signature: string | null
        summary: string | null
        line_start: number
      }>
    }>
  }>
  total_modules: number
  total_files: number
}

// Plain GET, no mutation — GET /code/wiki/{repoId} is read-only by the
// route's own docstring and must never trigger generation on browse.
function useWiki(repoId: string | null) {
  return useQuery<WikiData | null>({
    queryKey: ["wiki", repoId],
    queryFn: () => apiFetch(`/code/wiki/${repoId}`),
    enabled: !!repoId,
    staleTime: 5 * 60 * 1000,
  })
}

// The real-backend counterpart of the demo Code section's WikiTab. Ported
// from features/repos/components/code-wiki-panel.tsx's useWiki hook shape
// (T1.59) — this view issues no mutation of its own; the only way a wiki
// gets generated is the reindex dialog's own generate_wiki toggle, opened
// here but never called directly.
export function RealWikiView({
  repoId,
  onRepoChange,
}: {
  repoId: string | undefined
  onRepoChange: (id: string) => void
}) {
  const { data: repos, isLoading: reposLoading } = useRepos()
  const repo = repos?.find((r) => r.id === repoId) ?? repos?.find(() => true)
  const { data: wiki, isLoading, isError, refetch } = useWiki(repo?.id ?? null)
  const [expandedModule, setExpandedModule] = useState<string | null>(null)
  const [reindexOpen, setReindexOpen] = useState(false)
  const reindexRepo = useReindexRepo()

  if (reposLoading) {
    return (
      <p className="text-muted-foreground p-3 text-sm">Loading repositories…</p>
    )
  }

  if (!repo) {
    return (
      <EmptyState
        kind="empty"
          icon={FolderGit2}
        title="No repositories indexed yet"
        description="Add a repository to get started."
      />
    )
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2.5">
        <Select value={repo.id} onValueChange={onRepoChange}>
          <SelectTrigger className="w-56" aria-label="Repository">
            <SelectValue>
              <span className="flex items-center gap-2">
                <FolderGit2 aria-hidden className="h-3.5 w-3.5" />
                {repo.name}
              </span>
            </SelectValue>
          </SelectTrigger>
          <SelectContent>
            {repos?.map((r) => (
              <SelectItem key={r.id} value={r.id}>
                {r.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading && (
        <p className="text-muted-foreground text-sm">Loading wiki…</p>
      )}

      {isError && (
        <EmptyState
          kind="failed"
          title="Failed to load wiki"
          description="Something went wrong while loading the generated documentation."
          action={<Button onClick={() => refetch()}>Retry</Button>}
        />
      )}

      {wiki && (
        <>
          {wiki.overview && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Overview</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{wiki.overview}</p>
                <div className="text-muted-foreground mt-2 flex gap-3 text-sm">
                  <span>{wiki.total_modules} modules</span>
                  <span>{wiki.total_files} files</span>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="space-y-2">
            {wiki.modules.map((mod) => (
              <Card key={mod.path}>
                <button
                  type="button"
                  aria-expanded={expandedModule === mod.path}
                  className="hover:bg-accent/30 w-full cursor-pointer px-4 py-3 text-left transition-colors"
                  onClick={() =>
                    setExpandedModule(
                      expandedModule === mod.path ? null : mod.path,
                    )
                  }
                >
                  <div className="flex min-w-0 items-center justify-between">
                    <div className="flex min-w-0 items-center gap-2">
                      <span className="truncate font-mono text-sm font-medium">
                        {mod.path}
                      </span>
                      <Badge variant="secondary" className="shrink-0 text-sm">
                        {mod.symbol_count} symbols
                      </Badge>
                    </div>
                    <span className="text-muted-foreground shrink-0 text-sm">
                      {mod.files.length} files
                    </span>
                  </div>
                  {mod.summary && (
                    <p className="text-muted-foreground mt-1 text-sm">
                      {mod.summary}
                    </p>
                  )}
                </button>

                {expandedModule === mod.path && (
                  <CardContent className="border-border border-t pt-3">
                    {mod.files.map((file) => (
                      <div key={file.path} className="mb-4">
                        <div className="mb-2 flex min-w-0 items-center gap-2">
                          <span className="truncate font-mono text-sm font-medium">
                            {file.path}
                          </span>
                          {file.language && (
                            <Badge
                              variant="outline"
                              className="shrink-0 text-sm"
                            >
                              {file.language}
                            </Badge>
                          )}
                        </div>
                        {file.symbols.length > 0 && (
                          <div className="ml-4 space-y-1">
                            {file.symbols.map((sym, i) => (
                              <div
                                key={`${sym.name}-${i}`}
                                className="text-sm break-words"
                              >
                                <span className="text-muted-foreground">
                                  {sym.kind}
                                </span>{" "}
                                <span className="font-mono font-medium">
                                  {sym.name}
                                </span>
                                {sym.signature && (
                                  <span className="text-muted-foreground">
                                    {sym.signature}
                                  </span>
                                )}
                                {sym.summary && (
                                  <p className="text-muted-foreground mt-0.5 ml-4">
                                    {sym.summary}
                                  </p>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    ))}
                  </CardContent>
                )}
              </Card>
            ))}
          </div>
        </>
      )}

      {!isLoading && !isError && !wiki && (
        <EmptyState
          kind="empty"
          icon={BookOpen}
          title="No wiki generated yet for this repository"
          description="Run a reindex with Generate wiki on to build one."
          action={
            <Button onClick={() => setReindexOpen(true)}>
              Open reindex dialog
            </Button>
          }
        />
      )}

      <RealReindexDialog
        repo={repo}
        open={reindexOpen}
        onOpenChange={setReindexOpen}
        emphasizeWiki
        onConfirm={async (v: ReindexInput) => {
          try {
            await reindexRepo.mutateAsync({ id: repo.id, options: v })
          } catch (err) {
            toast.error(
              `Wiki generation failed: ${err instanceof Error ? err.message : String(err)}`,
            )
          }
        }}
      />
    </div>
  )
}
