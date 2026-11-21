import type { Meta, StoryObj } from "@storybook/react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { useEffect, useState, type ReactNode } from "react"
import { userEvent, within } from "storybook/test"
import { useTheme } from "darkraise-ui/theme"
import { Toaster } from "darkraise-ui/components/sonner"
import { FlagsTab } from "./flags-tab"
import { LLMTab } from "./llm-tab"
import { ResearchTab } from "./research-tab"

type Surface = "flags" | "purpose" | "research"
/** How the one write a story makes is answered. */
type Write = "pending" | "accepted" | { refused: string }

const FLAGS = {
  hybrid_search_enabled: true,
  reranker_enabled: false,
  relation_rescue: true,
  pipeline_concurrency: 5,
  embedding_batch_size: 20,
  embedding_concurrency: 1,
  entity_cache_ttl_minutes: 60,
  classification_mode: "simple",
  classification_areas: ["general"],
  classification_labels: [
    { name: "fact", description: "neutral factual information", area: null },
    { name: "decision", description: "explicit choices made", area: null },
  ],
  classification_areas_apply: false,
  confidence_rank_gamma: 0,
  w_importance: 0,
  w_heat: 0,
  w_recency: 0,
  ppr_enabled: false,
  w_ppr: 0,
  dual_level_enabled: false,
  w_dual: 0,
  numeric_bounds: {
    confidence_rank_gamma: { min: 0, max: 1 },
    w_importance: { min: 0, max: 1 },
    w_heat: { min: 0, max: 1 },
    w_recency: { min: 0, max: 1 },
    w_ppr: { min: 0, max: 1 },
    w_dual: { min: 0, max: 1 },
  },
  graph_channels: [
    { name: "ppr", flag: "ppr_enabled", enabled: false, weight_flag: "w_ppr", weight: 0, activation: null },
    { name: "dual_level", flag: "dual_level_enabled", enabled: false, weight_flag: "w_dual", weight: 0, activation: null },
  ],
}

const LADDER = {
  params: [
    { name: "n_default", committed: null, effective: 3, floor: 3, measured: false, state: "default", note: null },
    { name: "n_diverse", committed: null, effective: 2, floor: 2, measured: false, state: "default", note: null },
    { name: "time_gap_days", committed: null, effective: 7, floor: 7, measured: false, state: "default", note: null },
  ],
  measured: [],
  row_present: true,
}

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
  verification: {
    ...purpose("verification-judge", "gpt-5.5"),
    api_kind: "openai",
    base_url: "https://api.openai.com/v1",
  },
}

const PROVIDERS = {
  providers: [
    { name: "deepseek-primary", api_kind: "deepseek", base_url: "https://api.deepseek.com/v1", api_key: "***" },
    { name: "ollama-lan", api_kind: "ollama", base_url: "http://192.168.0.196:11434", api_key: null },
    { name: "verification-judge", api_kind: "openai", base_url: "https://api.openai.com/v1", api_key: "***" },
  ],
}

const READS: Record<string, unknown> = {
  "/config/feature-flags": FLAGS,
  "/config/verification-ladder": LADDER,
  "/config/classification-areas": [
    { key: "general", display_name: "General", types: ["fact", "decision"], type_descriptions: {} },
  ],
  "/config/repo-allowlist": { patterns: ["github.com/darkraise/*"] },
  "/config/llm": LLM_CONFIG,
  "/config/llm-providers": PROVIDERS,
  "/config/auto-research": {
    enabled: false,
    max_findings_per_run: 20,
    max_content_chars: 8000,
    max_findings_per_run_ceiling: 100,
    max_content_chars_ceiling: 100000,
    default_enabled: false,
  },
  "/config/auto-research/runs": { items: [], total: 0 },
  "/health": { status: "ok" },
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

/** Answers reads from `READS` and every write with `write`, while mounted, on
 *  a query client of its own. Installed during render: the tab's queries
 *  start before an effect would run. */
function StubbedBackend({ write, children }: { write: Write; children: ReactNode }) {
  const [client] = useState(
    () =>
      new QueryClient({
        defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
      }),
  )
  const [original] = useState(() => {
    const original = window.fetch
    window.fetch = async (input: RequestInfo | URL, init?: RequestInit) => {
      const raw = typeof input === "string" ? input : input instanceof URL ? input.href : input.url
      const path = new URL(raw, window.location.origin).pathname.replace(/^\/api\/v1/, "")
      const method = init?.method ?? "GET"
      if (path.endsWith("/probe-models")) {
        return json({ models: ["deepseek-v4-flash", "deepseek-v4-pro"], error: null })
      }
      if (method !== "GET") {
        if (write === "pending") return new Promise<Response>(() => {})
        if (write === "accepted") return json(READS[path] ?? {})
        return json(
          { error: { code: "validation_error", message: write.refused }, detail: write.refused },
          422,
        )
      }
      return json(READS[path] ?? {})
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

function SurfaceView({ surface }: { surface: Surface }) {
  switch (surface) {
    case "flags":
      return <FlagsTab />
    case "purpose":
      return <LLMTab />
    case "research":
      return <ResearchTab />
  }
}

function Board({
  surface,
  write,
  mode = "light",
}: {
  surface: Surface
  write: Write
  mode?: "light" | "dark"
}) {
  return (
    <StubbedBackend write={write}>
      <Mode mode={mode} />
      {/* Covers the shared preview's router outlet, which prints its own
          not-found line above every story. */}
      <div className="bg-background text-foreground fixed inset-0 overflow-auto">
        <div className="mx-auto max-w-5xl p-6">
          <SurfaceView surface={surface} />
        </div>
      </div>
      <Toaster />
    </StubbedBackend>
  )
}

const meta: Meta<typeof Board> = {
  title: "Settings/Save states",
  component: Board,
  parameters: { layout: "fullscreen" },
  argTypes: {
    mode: { control: "inline-radio", options: ["light", "dark"] },
  },
}
export default meta

type S = StoryObj<typeof Board>
type Page = ReturnType<typeof within>
type Step = (page: Page) => Promise<void>

/** Dialogs portal to the body, so every step reads the whole document. */
const story = (surface: Surface, write: Write, ...steps: Step[]): S => ({
  args: { surface, write },
  play: async () => {
    const page = within(document.body)
    for (const step of steps) await step(page)
  },
})

const openTunables: Step = async (page) => {
  await userEvent.click(
    await page.findByRole("button", { name: "Edit pipeline & embedding tunables" }),
  )
  await page.findByRole("dialog")
}
const typeInto = (name: string, value: string): Step => async (page) => {
  const field = page.getByRole("spinbutton", { name })
  await userEvent.clear(field)
  await userEvent.type(field, value)
}
const save: Step = async (page) => {
  await userEvent.click(page.getByRole("button", { name: "Save" }))
}

const openPurpose: Step = async (page) => {
  await userEvent.click(await page.findByRole("button", { name: "Edit reasoning" }))
  await page.findByRole("dialog")
}
const pickProvider = (name: string): Step => async (page) => {
  await userEvent.click(page.getByRole("combobox", { name: "reasoning provider_name" }))
  await userEvent.click(await page.findByRole("option", { name }))
}
const typeParams = (value: string): Step => async (page) => {
  const field = page.getByRole("textbox", { name: "reasoning params" })
  await userEvent.clear(field)
  await userEvent.type(field, value.replace(/[{[]/g, "$&$&"))
}

const SERVER_BOUND =
  "embedding_concurrency: Input should be less than or equal to 4"
const JUDGE_ONLY =
  "Provider 'verification-judge' serves the verification purpose only"

export const FlagsDialogPristine = story("flags", "accepted", openTunables)
export const FlagsDialogEdited = story("flags", "accepted", openTunables, typeInto("embedding_concurrency", "6"))
export const FlagsDialogSaving = story("flags", "pending", openTunables, typeInto("embedding_concurrency", "6"), save)
export const FlagsDialogRefused = story(
  "flags",
  { refused: SERVER_BOUND },
  openTunables,
  typeInto("embedding_concurrency", "6"),
  save,
)
export const FlagsDialogOutOfRange = story("flags", "accepted", openTunables, typeInto("pipeline_concurrency", "50"))

export const PurposeDialogPristine = story("purpose", "accepted", openPurpose)
export const PurposeDialogEdited = story("purpose", "accepted", openPurpose, typeParams('{"temperature": 0.2}'))
export const PurposeDialogSaving = story("purpose", "pending", openPurpose, typeParams('{"temperature": 0.2}'), save)
export const PurposeDialogRefused = story(
  "purpose",
  { refused: JUDGE_ONLY },
  openPurpose,
  pickProvider("verification-judge"),
  save,
)
/** The purpose dialog has no bounded number field; its field-level refusal
 *  is the parameters check, which disables Save the same way. */
export const PurposeDialogInvalidField = story("purpose", "accepted", openPurpose, typeParams('{"temperature": '))

export const ToggleReverted = story(
  "research",
  { refused: "auto_research row is held by another save" },
  async (page) => {
    await userEvent.click(await page.findByRole("button", { name: "Arm the research loop" }))
    await page.findByText("Not armed")
  },
)
