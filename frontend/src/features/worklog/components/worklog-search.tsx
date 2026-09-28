import { useState } from "react"
import { Badge } from "darkraise-ui/components/badge"
import { Input } from "darkraise-ui/components/input"
import { EmptyState, listItemClass } from "@/components/darkmem"
import { useWorklogSearch } from "@/hooks/api"
import { firstLine } from "./entry-timeline"

/** `worklog_search` over one project's workstreams (spec §8). A hit opens its
 *  workstream with the entry selected. */
export function WorklogSearch({
  project,
  onOpen,
}: {
  project: string
  onOpen: (workstreamKey: string, entryId: string) => void
}) {
  const [query, setQuery] = useState("")
  const search = useWorklogSearch()
  const hits = search.data?.items ?? []

  return (
    <div className="space-y-2">
      <form
        role="search"
        onSubmit={(event) => {
          event.preventDefault()
          const trimmed = query.trim()
          if (trimmed) search.mutate({ project, query: trimmed })
        }}
      >
        <Input
          type="search"
          aria-label="Search the work log"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search this project's work log by words or meaning…"
        />
      </form>
      {search.isError ? (
        <EmptyState kind="failed" title="The search failed" description={search.error.message} />
      ) : search.isSuccess && hits.length === 0 ? (
        <EmptyState kind="filtered" title="No entry matches" />
      ) : null}
      {search.isSuccess && !search.data.semantic_ran ? (
        <p className="text-muted-foreground text-xs">
          Keyword matches only: the semantic arm did not run.
        </p>
      ) : null}
      {hits.length > 0 ? (
        <ul className="space-y-1.5">
          {hits.map((hit) => (
            <li key={hit.entry.id}>
              <button
                type="button"
                onClick={() => onOpen(hit.workstream, hit.entry.id)}
                className={listItemClass({
                  interactive: true,
                  className: "bg-card flex w-full items-center gap-2 p-2 text-left text-sm",
                })}
              >
                <Badge variant="outline">{hit.entry.kind}</Badge>
                <span className="text-muted-foreground shrink-0 font-mono text-xs">
                  {hit.workstream}
                </span>
                <span className="min-w-0 flex-1 truncate">{firstLine(hit.entry.body)}</span>
              </button>
            </li>
          ))}
        </ul>
      ) : null}
    </div>
  )
}
