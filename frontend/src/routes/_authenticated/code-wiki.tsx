import { useState } from "react"
import { createFileRoute, Link, useNavigate } from "@tanstack/react-router"
import { useRepos } from "@/hooks/api"
import { apiFetch } from "@/lib/api"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "darkraise-ui/components/card"
import { Badge } from "darkraise-ui/components/badge"
import { Button } from "darkraise-ui/components/button"
import {
  Select,
  SelectTrigger,
  SelectValue,
  SelectContent,
  SelectItem,
} from "darkraise-ui/components/select"
import { PageHeader } from "darkraise-ui/layout"
import { EmptyState } from "darkraise-ui/components/empty-state"
import { useQuery } from "@tanstack/react-query"

export const Route = createFileRoute("/_authenticated/code-wiki")({
  component: CodeWikiPage,
})

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

function useWiki(repoId: string | null) {
  return useQuery<WikiData>({
    queryKey: ["wiki", repoId],
    queryFn: () => apiFetch(`/code/wiki/${repoId}`),
    enabled: !!repoId,
    staleTime: 5 * 60 * 1000,
  })
}

function CodeWikiPage() {
  const { data: repos } = useRepos()
  const navigate = useNavigate()
  const [selectedRepoId, setSelectedRepoId] = useState<string | null>(null)
  const { data: wiki, isLoading } = useWiki(selectedRepoId)
  const [expandedModule, setExpandedModule] = useState<string | null>(null)

  return (
    <div className="space-y-4 p-6">
      <PageHeader title="Code Wiki" />

      <div className="flex items-center gap-4">
        <Select
          value={selectedRepoId || "__none__"}
          onValueChange={(v) => {
            setSelectedRepoId(v === "__none__" ? null : v)
            setExpandedModule(null)
          }}
        >
          <SelectTrigger className="h-8 w-48">
            <SelectValue placeholder="Select a repo" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="__none__">Select a repo</SelectItem>
            {repos?.map((r) => (
              <SelectItem key={r.id} value={r.id}>
                {r.name}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {isLoading && (
        <p className="text-muted-foreground">Generating documentation...</p>
      )}

      {wiki && (
        <>
          {wiki.overview && (
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base">Overview</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-base">{wiki.overview}</p>
                <div className="text-muted-foreground mt-2 flex gap-3 text-base">
                  <span>{wiki.total_modules} modules</span>
                  <span>{wiki.total_files} files</span>
                </div>
              </CardContent>
            </Card>
          )}

          <div className="space-y-2">
            {wiki.modules.map((mod) => (
              <Card key={mod.path}>
                <div
                  className="hover:bg-accent/30 cursor-pointer px-4 py-3 transition-colors"
                  onClick={() =>
                    setExpandedModule(
                      expandedModule === mod.path ? null : mod.path,
                    )
                  }
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="font-mono text-base font-medium">
                        {mod.path}
                      </span>
                      <Badge variant="secondary" className="text-sm">
                        {mod.symbol_count} symbols
                      </Badge>
                    </div>
                    <span className="text-muted-foreground text-base">
                      {mod.files.length} files
                    </span>
                  </div>
                  {mod.summary && (
                    <p className="text-muted-foreground mt-1 text-base">
                      {mod.summary}
                    </p>
                  )}
                </div>

                {expandedModule === mod.path && (
                  <CardContent className="border-border border-t pt-3">
                    {mod.files.map((file) => (
                      <div key={file.path} className="mb-4">
                        <div className="mb-2 flex items-center gap-2">
                          <span className="font-mono text-base font-medium">
                            {file.path}
                          </span>
                          {file.language && (
                            <Badge variant="outline" className="text-sm">
                              {file.language}
                            </Badge>
                          )}
                        </div>
                        {file.symbols.length > 0 && (
                          <div className="ml-4 space-y-1">
                            {file.symbols.map((sym, i) => (
                              <div
                                key={`${sym.name}-${i}`}
                                className="text-base"
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

      {selectedRepoId && !isLoading && !wiki && (
        <EmptyState
          title="No code wiki yet"
          description="Trigger a reindex with generate_wiki enabled to populate this page."
          action={
            <Button onClick={() => navigate({ to: "/reindex" })}>
              Open reindex
            </Button>
          }
        />
      )}

      {!selectedRepoId &&
        !isLoading &&
        (repos && repos.length === 0 ? (
          <EmptyState
            title="No repositories indexed yet"
            description="Add a repository to get started."
            action={
              <Button asChild>
                <Link to="/repos">Add a repo</Link>
              </Button>
            }
          />
        ) : (
          <EmptyState
            title="Select a repository"
            description="Choose a repository from the dropdown to view its generated documentation."
          />
        ))}
    </div>
  )
}
