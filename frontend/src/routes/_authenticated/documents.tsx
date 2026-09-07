import { useState } from "react"
import { createFileRoute } from "@tanstack/react-router"
import { FileText } from "lucide-react"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "darkraise-ui/components/select"
import { Skeleton } from "darkraise-ui/components/skeleton"
import { PageChrome } from "@/components/app-chrome"
import { DocumentsView } from "@/features/documents/components/documents-view"
import { useProjects } from "@/hooks/api"

export const Route = createFileRoute("/_authenticated/documents")({
  component: DocumentsPage,
})

function DocumentsPage() {
  const { data, isLoading, isError } = useProjects()
  // The notes space has its own route and its own workspace (`/notes`); this
  // is the corpus browser, so the personal project never appears here.
  const rows = (data ?? []).filter((p) => p.kind !== "personal")
  // `useProjects` orders busiest-first by total item count across memories,
  // documents and checkpoints, which is a different measure than "holds
  // documents" -- a memory-heavy, document-empty project would win that
  // order and land the page on an empty tree.
  const defaultProject = rows.find((p) => p.document_count > 0)?.name ?? rows[0]?.name
  const [selected, setSelected] = useState<string | null>(null)
  const project = selected ?? defaultProject

  return (
    <div className="space-y-4">
      <PageChrome
        icon={FileText}
        title="Documents"
        description="Horizon: grounded answers, single-document summaries and emergent connections over your filed documents."
      />
      {isError ? (
        <p className="text-destructive text-sm">
          Projects could not be loaded — a failed read, not an empty corpus.
        </p>
      ) : isLoading ? (
        <Skeleton className="h-64 w-full" />
      ) : rows.length === 0 ? (
        <p className="text-muted-foreground text-sm">
          No project holds any documents yet.
        </p>
      ) : (
        <>
          <Select value={project} onValueChange={setSelected}>
            <SelectTrigger className="w-auto min-w-52" aria-label="project">
              <SelectValue>{project}</SelectValue>
            </SelectTrigger>
            <SelectContent>
              {rows.map((row) => (
                <SelectItem key={row.name} value={row.name}>
                  {row.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <DocumentsView project={project} />
        </>
      )}
    </div>
  )
}
