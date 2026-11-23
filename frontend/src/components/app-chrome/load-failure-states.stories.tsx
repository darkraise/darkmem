import type { Meta, StoryObj } from "@storybook/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useEffect, useState, type ReactNode } from "react"
import { userEvent, within } from "storybook/test"
import { useTheme } from "darkraise-ui/theme"
import { Toaster } from "darkraise-ui/components/sonner"
import { ProjectSwitcher } from "./project-switcher"
import { RealCodeGraphView } from "@/features/code/components/real-code-graph-view"
import { RealWikiView } from "@/features/code/components/real-wiki-view"
import { LLMTab } from "@/features/settings/components/llm-tab"
import { BackupsTab } from "@/features/settings/components/backups-tab"
import { RealMemoryGraphPage } from "@/features/memory-graph/components/real-memory-graph-page"
import { syntheticMemoryGraph } from "@/features/graph/lib/synthetic-graph"

type Surface = "code-graph" | "wiki" | "project-switcher" | "llm-tab" | "graph-page" | "backups"
type State = "loading" | "failed" | "empty" | "populated"
type Answer = "pending" | "failed" | { body: unknown }

const REPO = {
  id: "r1",
  name: "darkmem-backend",
  url: null,
  local_path: "/srv/darkmem/backend",
  provider: "local",
  default_branch: "main",
  last_indexed_commit: "abc1234",
  last_indexed_at: "2026-11-20T00:00:00Z",
  status: "ready",
  status_message: null,
  fetch_enabled: false,
  fetch_interval_seconds: 300,
  index_on_commit_enabled: false,
  commit_poll_seconds: 60,
  index_uncommitted: false,
  file_count: 2,
  symbol_count: 4,
  index_debt: { queued: 0, deferred_total: 0, drained_total: 0, last_defer: null, last_drain: null },
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-11-20T00:00:00Z",
}

const CODE_GRAPH = {
  nodes: [
    { id: "pipeline.py", label: "pipeline.py", kind: "file", file_path: "pipeline.py" },
    { id: "search.py", label: "search.py", kind: "file", file_path: "search.py" },
    { id: "process_batch::pipeline.py", label: "process_batch", kind: "function", file_path: "pipeline.py" },
    { id: "embed::pipeline.py", label: "embed", kind: "function", file_path: "pipeline.py" },
    { id: "rrf_fuse::search.py", label: "rrf_fuse", kind: "function", file_path: "search.py" },
    { id: "search::search.py", label: "search", kind: "function", file_path: "search.py" },
    { id: "comm:ingestion", label: "ingestion", kind: "community" },
    { id: "comm:retrieval", label: "retrieval", kind: "community" },
  ],
  edges: [
    { source: "pipeline.py", target: "process_batch::pipeline.py", type: "CONTAINS" },
    { source: "pipeline.py", target: "embed::pipeline.py", type: "CONTAINS" },
    { source: "search.py", target: "rrf_fuse::search.py", type: "CONTAINS" },
    { source: "search.py", target: "search::search.py", type: "CONTAINS" },
    { source: "process_batch::pipeline.py", target: "embed::pipeline.py", type: "CALLS" },
    { source: "search::search.py", target: "rrf_fuse::search.py", type: "CALLS" },
    { source: "process_batch::pipeline.py", target: "comm:ingestion", type: "member_of" },
    { source: "embed::pipeline.py", target: "comm:ingestion", type: "member_of" },
    { source: "search::search.py", target: "comm:retrieval", type: "member_of" },
    { source: "rrf_fuse::search.py", target: "comm:retrieval", type: "member_of" },
  ],
}

const WIKI = {
  repo_name: "darkmem-backend",
  overview: "Ingests memories through a five-phase pipeline and serves hybrid retrieval.",
  total_modules: 2,
  total_files: 2,
  modules: [
    {
      path: "app/services/pipeline",
      summary: "Embeds, extracts and writes each captured memory.",
      symbol_count: 2,
      files: [],
    },
    {
      path: "app/services/search",
      summary: "Fuses the keyword and semantic arms with reciprocal rank fusion.",
      symbol_count: 2,
      files: [],
    },
  ],
}

const project = (name: string, memories: number, documents = 0) => ({
  name,
  kind: "project",
  memory_count: memories,
  document_count: documents,
  page_count: 0,
  workstream_count: 0,
  open_workstream_count: 0,
  last_worklog_at: null,
  last_event_day: "2026-11-20",
})

const PROJECTS = [project("default", 412), project("darkmem", 1204, 88), project("homelab", 57)]

const purpose = (provider: string, model: string, extra: Record<string, unknown> = {}) => ({
  provider_name: provider,
  base_url: provider === "ollama-lan" ? "http://192.168.0.196:11434" : "https://api.deepseek.com/v1",
  model,
  api_key: provider === "ollama-lan" ? null : "***",
  dimensions: null,
  reasoning: false,
  api_kind: provider === "ollama-lan" ? "ollama" : "deepseek",
  params: {},
  ...extra,
})

const LLM_CONFIG = {
  embedding: purpose("ollama-lan", "qwen3-embedding:0.6b", { dimensions: 1024 }),
  extraction: purpose("deepseek-primary", "deepseek-v4-flash"),
  classification: purpose("deepseek-primary", "deepseek-v4-flash", { classifier_kind: "llm" }),
  reasoning: purpose("deepseek-primary", "deepseek-v4-pro"),
  summarization: purpose("deepseek-primary", "deepseek-v4-flash"),
  reranker: purpose("deepseek-primary", "deepseek-v4-flash"),
  synthesis: purpose("deepseek-primary", "deepseek-v4-pro"),
  verification: { ...purpose("verification-judge", "gpt-5.5"), api_kind: "openai", base_url: "https://api.openai.com/v1" },
}

function unifiedGraph() {
  const graph = syntheticMemoryGraph(160, 6, 3)
  const clusters: Record<string, string[]> = {}
  for (const m of graph.memories) {
    if (m.cluster < 0) continue
    ;(clusters[String(m.cluster)] ??= []).push(m.id)
  }
  return {
    memories: graph.memories,
    clusters,
    cluster_names: graph.clusterNames,
    similarity_edges: graph.edges,
    total_memories: graph.memories.length,
  }
}

const EMPTY_GRAPH = { memories: [], clusters: {}, cluster_names: {}, similarity_edges: [] }

const BACKUP_DESTINATION = {
  name: "disk",
  kind: "local",
  enabled: true,
  retention_keep: 14,
  attachments_retention_keep: 3,
  age_recipient: null,
  ssh: null,
  s3: null,
  worker: null,
}

const BACKUP_HOLDING = {
  name: "disk",
  kind: "local",
  enabled: true,
  retention_keep: 14,
  attachments_retention_keep: 3,
  snapshots: [
    { name: "darkmem-app-20261120-043000.sql.gz", size: 252130697, modified_at: "2026-11-20T04:30:00Z" },
  ],
  attachment_snapshots: [],
  last_outcome: { event_type: "backup_shipped", at: "2026-11-20T04:30:00Z", sha256: "a".repeat(64), error: null },
  last_attachment_outcome: null,
  error: null,
}

/** The request each surface renders, keyed by its path under `/api/v1`. */
const SUBJECT: Record<Surface, string> = {
  "code-graph": "/repos",
  wiki: "/repos",
  "project-switcher": "/projects",
  "llm-tab": "/config/llm",
  "graph-page": "/graph/unified",
  backups: "/config/backup-destinations",
}

function routesFor(surface: Surface, state: State): Record<string, Answer> {
  const subject = SUBJECT[surface]
  if (state === "loading") return { [subject]: "pending" }
  if (state === "failed") return { [subject]: "failed" }
  if (state === "empty") {
    const body =
      surface === "llm-tab"
        ? {}
        : surface === "graph-page"
          ? EMPTY_GRAPH
          : surface === "backups"
            ? { destinations: [] }
            : []
    return { [subject]: { body } }
  }
  return {
    "/repos": { body: [REPO] },
    "/code/graph/r1": { body: CODE_GRAPH },
    "/code/wiki/r1": { body: WIKI },
    "/projects": { body: PROJECTS },
    "/config/llm": { body: LLM_CONFIG },
    "/graph/unified": { body: unifiedGraph() },
    "/config/backup-destinations": { body: { destinations: [BACKUP_DESTINATION] } },
    "/backups/inventory": { body: { destinations: [BACKUP_HOLDING] } },
    "/events": { body: { items: [], total: 0 } },
  }
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

/** Answers the app's requests from `routes` while mounted, on a query client
 *  of its own so no story reads another's cache. Installed during render: the
 *  surface's queries start before an effect would run. */
function StubbedBackend({
  routes,
  children,
}: {
  routes: Record<string, Answer>
  children: ReactNode
}) {
  const [client] = useState(
    () => new QueryClient({ defaultOptions: { queries: { retry: false } } }),
  )
  const [original] = useState(() => {
    const original = window.fetch
    window.fetch = async (input: RequestInfo | URL) => {
      const raw = typeof input === "string" ? input : input instanceof URL ? input.href : input.url
      const path = new URL(raw, window.location.origin).pathname.replace(/^\/api\/v1/, "")
      const match = Object.keys(routes)
        .filter((p) => path === p || path.startsWith(`${p}/`) || path.startsWith(`${p}?`))
        .sort((a, b) => b.length - a.length)[0]
      const answer: Answer = (match && routes[match]) || {
        body: path === "/health" ? { status: "ok" } : [],
      }
      if (answer === "pending") return new Promise<Response>(() => {})
      if (answer === "failed") {
        return json({ error: { code: "internal", message: "Internal server error" } }, 500)
      }
      return json(answer.body)
    }
    return original
  })
  useEffect(
    () => () => {
      window.fetch = original
    },
    [original],
  )
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}

function Mode({ mode }: { mode: "light" | "dark" }) {
  const { setAxis } = useTheme()
  useEffect(() => {
    setAxis("mode", mode)
  }, [mode, setAxis])
  return null
}

const noop = () => {}

function SurfaceView({ surface }: { surface: Surface }) {
  switch (surface) {
    case "code-graph":
      return (
        <div className="flex h-screen flex-col p-4">
          <RealCodeGraphView repoId={undefined} onRepoChange={noop} onOpenRepositories={noop} />
        </div>
      )
    case "wiki":
      return (
        <div className="mx-auto max-w-4xl p-6">
          <RealWikiView repoId={undefined} onRepoChange={noop} />
        </div>
      )
    case "project-switcher":
      return (
        <div className="border-border flex justify-end border-b p-3">
          <ProjectSwitcher />
        </div>
      )
    case "llm-tab":
      return (
        <div className="mx-auto max-w-5xl p-6">
          <LLMTab />
        </div>
      )
    case "graph-page":
      return (
        <div className="h-screen">
          <RealMemoryGraphPage />
        </div>
      )
    case "backups":
      return (
        <div className="mx-auto max-w-4xl p-6">
          <BackupsTab />
        </div>
      )
  }
}

function Board({
  surface,
  state,
  mode = "light",
  failing = [],
}: {
  surface: Surface
  state: State
  mode?: "light" | "dark"
  /** Paths that answer a 500 on top of `state`'s routes: one failed read
   *  beside reads that succeed. */
  failing?: string[]
}) {
  const routes = {
    ...routesFor(surface, state),
    ...Object.fromEntries(failing.map((path) => [path, "failed" as const])),
  }
  return (
    <StubbedBackend key={`${surface}-${state}-${failing.join(",")}`} routes={routes}>
      <Mode mode={mode} />
      {/* Covers the shared preview's router outlet, which prints its own
          not-found line above every story. */}
      <div className="bg-background text-foreground fixed inset-0 overflow-auto">
        <SurfaceView surface={surface} />
      </div>
      <Toaster />
    </StubbedBackend>
  )
}

const meta: Meta<typeof Board> = {
  title: "App chrome/Load-failure states",
  component: Board,
  parameters: { layout: "fullscreen" },
  argTypes: {
    mode: { control: "inline-radio", options: ["light", "dark"] },
  },
}
export default meta

type S = StoryObj<typeof Board>

const story = (surface: Surface, state: State): S => ({ args: { surface, state } })

/** The switcher's list lives in a popover; opening it is what the story shows. */
const openSwitcher = (surface: Surface, state: State): S => ({
  ...story(surface, state),
  play: async ({ canvasElement }) => {
    await userEvent.click(
      within(canvasElement).getByRole("button", { name: /project scope/i }),
    )
  },
})

export const CodeGraphLoading = story("code-graph", "loading")
export const CodeGraphFailed = story("code-graph", "failed")
export const CodeGraphEmpty = story("code-graph", "empty")
export const CodeGraphPopulated = story("code-graph", "populated")

export const WikiLoading = story("wiki", "loading")
export const WikiFailed = story("wiki", "failed")
export const WikiEmpty = story("wiki", "empty")
export const WikiPopulated = story("wiki", "populated")

export const ProjectSwitcherLoading = openSwitcher("project-switcher", "loading")
export const ProjectSwitcherFailed = openSwitcher("project-switcher", "failed")
export const ProjectSwitcherEmpty = openSwitcher("project-switcher", "empty")
export const ProjectSwitcherPopulated = openSwitcher("project-switcher", "populated")

export const LlmTabLoading = story("llm-tab", "loading")
export const LlmTabFailed = story("llm-tab", "failed")
export const LlmTabEmpty = story("llm-tab", "empty")
export const LlmTabPopulated = story("llm-tab", "populated")

export const GraphPageLoading = story("graph-page", "loading")
export const GraphPageFailed = story("graph-page", "failed")
export const GraphPageEmpty = story("graph-page", "empty")
export const GraphPagePopulated = story("graph-page", "populated")

/** One failed Backups read at a time, beside the two that succeed. */
const backupsFailing = (path: string): S => ({
  args: { surface: "backups", state: "populated", failing: [path] },
})

export const BackupsDestinationsFailed = backupsFailing("/config/backup-destinations")
export const BackupsInventoryFailed = backupsFailing("/backups/inventory")
export const BackupsOutcomesFailed = backupsFailing("/events")
