import { createFileRoute, useNavigate } from "@tanstack/react-router"
import { PageHeader } from "darkraise-ui/layout"
import { Button } from "darkraise-ui/components/button"
import { BookOpen, FolderGit2, Network } from "lucide-react"
import {
  PlaceholderTabs,
  type PlaceholderTab,
} from "@/components/placeholder-tabs"

export const Route = createFileRoute("/_authenticated/code")({
  component: CodePage,
})

function CodePage() {
  const navigate = useNavigate()

  const tabs: PlaceholderTab[] = [
    {
      value: "repositories",
      label: "Repositories",
      icon: <FolderGit2 />,
      title: "The repository manager moves here",
      description:
        "Registered repos, sync status, and reindex controls. Reshaped in Wave 3.",
      action: (
        <Button variant="outline" onClick={() => navigate({ to: "/repos" })}>
          Open the current Repositories page
        </Button>
      ),
    },
    {
      value: "graph",
      label: "Code Graph",
      icon: <Network />,
      title: "The code graph moves here",
      description:
        "Force, tree, and circles layouts over the indexed symbol graph. Reshaped in Wave 3.",
      action: (
        <Button
          variant="outline"
          onClick={() => navigate({ to: "/code-graph" })}
        >
          Open the current Code Graph page
        </Button>
      ),
    },
    {
      value: "wiki",
      label: "Wiki",
      icon: <BookOpen />,
      title: "The code wiki lands here",
      description:
        "Generated module and overview docs for indexed repositories. Built in Wave 3.",
    },
  ]

  return (
    <div className="space-y-4 p-6">
      <PageHeader
        title="Code"
        description="Indexed repositories, the symbol graph, and the generated wiki."
      />
      <PlaceholderTabs tabs={tabs} />
    </div>
  )
}
