import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react"
import type { ReactElement, ReactNode } from "react"
import { afterEach, describe, expect, it, vi } from "vitest"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))
vi.mock("darkraise-ui/components/sonner", () => ({
  toast: { error: vi.fn(), success: vi.fn() },
}))

import { apiFetch } from "@/lib/api"
import { toast } from "darkraise-ui/components/sonner"
import { FlagsTab } from "../flags-tab"
import { LLMTab } from "../llm-tab"
import { NotificationsTab } from "../notifications-tab"
import { ResearchTab } from "../research-tab"
import { BackupsTab } from "../backups-tab"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

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
  classification_labels: [{ name: "fact", description: "", area: null }],
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
    {
      name: "ppr",
      flag: "ppr_enabled",
      enabled: false,
      weight_flag: "w_ppr",
      weight: 0,
      activation: null,
    },
  ],
}

const LADDER = {
  params: [
    {
      name: "n_default",
      committed: null,
      effective: 3,
      floor: 3,
      measured: false,
      state: "default",
      note: null,
    },
  ],
  measured: [],
  row_present: true,
}

const AREAS = [
  { key: "general", display_name: "General", types: ["fact"], type_descriptions: {} },
  { key: "technical", display_name: "Technical", types: ["reference"], type_descriptions: {} },
]

const LLM = {
  reasoning: {
    provider_name: "deepseek",
    base_url: "https://api.deepseek.com/v1",
    model: "deepseek-v4-flash",
    api_key: null,
    dimensions: null,
    reasoning: false,
    api_kind: "deepseek",
    params: {},
  },
}

const PROVIDERS = {
  providers: [
    { name: "deepseek", api_kind: "deepseek", base_url: "https://api.deepseek.com/v1", api_key: "***" },
    { name: "lan-ollama", api_kind: "ollama", base_url: "http://192.0.2.5:11434", api_key: null },
  ],
}

type Write = (path: string, init: RequestInit) => Promise<unknown>

/** Every read the Settings tabs make, with writes handed to `write`. */
function serve(write: Write, overrides: Record<string, () => Promise<unknown>> = {}) {
  vi.mocked(apiFetch).mockImplementation((path: string, init?: RequestInit) => {
    if (init?.method && init.method !== "GET" && !path.endsWith("/probe-models")) {
      return write(path, init)
    }
    if (path in overrides) return overrides[path]!()
    const table: Record<string, unknown> = {
      "/config/feature-flags": FLAGS,
      "/config/verification-ladder": LADDER,
      "/config/classification-areas": AREAS,
      "/config/repo-allowlist": { patterns: ["github.com/darkraise/*"] },
      "/config/llm": LLM,
      "/config/llm-providers": PROVIDERS,
      "/health": { status: "ok" },
      "/config/auto-research": {
        enabled: false,
        max_findings_per_run: 20,
        max_content_chars: 8000,
        default_enabled: false,
      },
      "/config/auto-research/runs": { items: [], total: 0 },
      "/config/notifications": {
        telegram: { enabled: false, bot_token: "", chat_id: "" },
        notify_on: { job_failure: true },
      },
      "/config/backup-destinations": {
        destinations: [
          {
            name: "disk",
            kind: "local",
            enabled: false,
            retention_keep: 14,
            attachments_retention_keep: 3,
            age_recipient: null,
            ssh: null,
            s3: null,
          },
        ],
      },
      "/backups/inventory": { destinations: [] },
    }
    if (path.endsWith("/probe-models")) return Promise.resolve({ models: [], error: null })
    if (path.startsWith("/events")) return Promise.resolve({ items: [], total: 0 })
    if (path in table) return Promise.resolve(table[path])
    return Promise.reject(new Error(`unexpected apiFetch(${path})`))
  })
}

const refuse: Write = () =>
  Promise.reject(Object.assign(new Error("below the floor"), { status: 422 }))

afterEach(() => vi.clearAllMocks())

interface DialogCase {
  name: string
  element: () => ReactElement
  /** Opens the dialog from the tab. */
  open: () => Promise<void>
  /** Makes one edit and returns a check that the edit is still in place. */
  edit: (dialog: HTMLElement) => () => void
}

const editSection = (label: string) => async () => {
  fireEvent.click(await screen.findByRole("button", { name: `Edit ${label}` }))
}

function typeNumber(dialog: HTMLElement, label: string, value: string) {
  const input = within(dialog).getByRole("spinbutton", { name: label })
  fireEvent.change(input, { target: { value } })
  return () => expect(within(dialog).getByRole("spinbutton", { name: label })).toHaveValue(value)
}

function flipSwitch(dialog: HTMLElement, label: string) {
  const sw = within(dialog).getByRole("switch", { name: label })
  const before = sw.getAttribute("aria-checked")
  fireEvent.click(sw)
  return () =>
    expect(within(dialog).getByRole("switch", { name: label })).not.toHaveAttribute(
      "aria-checked",
      before ?? "",
    )
}

const DIALOGS: DialogCase[] = [
  {
    name: "ranking arms",
    element: () => <FlagsTab />,
    open: editSection("ranking arms"),
    edit: (d) => typeNumber(d, "w_heat", "0.5"),
  },
  {
    name: "feature flags",
    element: () => <FlagsTab />,
    open: editSection("feature flags"),
    edit: (d) => flipSwitch(d, "reranker_enabled"),
  },
  {
    name: "graph augmentation",
    element: () => <FlagsTab />,
    open: editSection("graph augmentation"),
    edit: (d) => flipSwitch(d, "ppr_enabled"),
  },
  {
    name: "pipeline & embedding tunables",
    element: () => <FlagsTab />,
    open: editSection("pipeline & embedding tunables"),
    edit: (d) => typeNumber(d, "pipeline_concurrency", "8"),
  },
  {
    name: "classification",
    element: () => <FlagsTab />,
    open: editSection("classification"),
    edit: (d) => {
      fireEvent.click(within(d).getByRole("radio", { name: "expanded" }))
      return () =>
        expect(within(d).getByRole("checkbox", { name: "technical" })).toBeInTheDocument()
    },
  },
  {
    name: "repo auto-provision allowlist",
    element: () => <FlagsTab />,
    open: editSection("repo auto-provision allowlist"),
    edit: (d) => {
      const box = within(d).getByRole("textbox", { name: "repo_allowlist patterns" })
      fireEvent.change(box, { target: { value: "gitlab.example/*" } })
      return () =>
        expect(within(d).getByRole("textbox", { name: "repo_allowlist patterns" })).toHaveValue(
          "gitlab.example/*",
        )
    },
  },
  {
    name: "corroboration promotion gate",
    element: () => <FlagsTab />,
    open: editSection("corroboration promotion gate"),
    edit: (d) => typeNumber(d, "n_default", "4"),
  },
  {
    name: "LLM purpose",
    element: () => <LLMTab />,
    open: editSection("reasoning"),
    edit: (d) => {
      const params = within(d).getByRole("textbox", { name: "reasoning params" })
      fireEvent.change(params, { target: { value: '{"temperature": 0}' } })
      return () =>
        expect(within(d).getByRole("textbox", { name: "reasoning params" })).toHaveValue(
          '{"temperature": 0}',
        )
    },
  },
]

describe("settings dialogs wait for their save", () => {
  it.each(DIALOGS)(
    "a refused save keeps the dialog open with the edits and the reason ($name)",
    async (c) => {
      serve(refuse)
      render(c.element(), { wrapper })
      await c.open()
      const dialog = await screen.findByRole("dialog")
      const holds = c.edit(dialog)

      fireEvent.click(within(dialog).getByRole("button", { name: "Save" }))

      expect(await within(dialog).findByText(/below the floor/)).toBeInTheDocument()
      expect(screen.getByRole("dialog")).toBe(dialog)
      holds()
      expect(toast.success).not.toHaveBeenCalled()
    },
  )

  it.each(DIALOGS)("a successful save closes with Saved ($name)", async (c) => {
    let land: () => void = () => {}
    serve(
      () =>
        new Promise((resolve) => {
          land = () => resolve({})
        }),
    )
    render(c.element(), { wrapper })
    await c.open()
    const dialog = await screen.findByRole("dialog")
    c.edit(dialog)

    fireEvent.click(within(dialog).getByRole("button", { name: "Save" }))

    const pending = await within(dialog).findByRole("button", { name: "Saving…" })
    expect(pending).toBeDisabled()
    expect(screen.getByRole("dialog")).toBe(dialog)
    expect(toast.success).not.toHaveBeenCalled()

    await act(async () => land())

    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
    expect(toast.success).toHaveBeenCalledTimes(1)
    expect(String(vi.mocked(toast.success).mock.calls[0]?.[0])).toMatch(/^Saved/)
  })
})

describe("settings number fields", () => {
  it("typing in a number field enables Save without a blur", async () => {
    serve(refuse)
    render(<FlagsTab />, { wrapper })
    await editSection("pipeline & embedding tunables")()
    const dialog = await screen.findByRole("dialog")
    const save = within(dialog).getByRole("button", { name: "Save" })
    expect(save).toBeDisabled()

    fireEvent.change(within(dialog).getByRole("spinbutton", { name: "embedding_concurrency" }), {
      target: { value: "5" },
    })

    expect(save).toBeEnabled()
  })

  it.each([
    { kind: "ranking arm", section: "ranking arms", field: "w_heat", value: "5", range: /from 0 to 1/ },
    {
      kind: "tunable",
      section: "pipeline & embedding tunables",
      field: "pipeline_concurrency",
      value: "50",
      range: /from 1 to 20/,
    },
  ])("an out-of-range number shows an error ($kind)", async ({ section, field, value, range }) => {
    serve(refuse)
    render(<FlagsTab />, { wrapper })
    await editSection(section)()
    const dialog = await screen.findByRole("dialog")
    const input = within(dialog).getByRole("spinbutton", { name: field })

    fireEvent.change(input, { target: { value } })
    fireEvent.blur(input)

    expect(within(dialog).getByText(range)).toBeInTheDocument()
    expect(within(dialog).getByRole("button", { name: "Save" })).toBeDisabled()
    // Neither kind moves the number back on its own.
    expect(within(dialog).getByRole("spinbutton", { name: field })).toHaveValue(value)
  })
})

describe("settings toggles that save at once", () => {
  it("a toggle that saves at once reverts on failure (research arm)", async () => {
    serve(() => Promise.reject(new Error("auto_research row is locked")))
    render(<ResearchTab />, { wrapper })
    const arm = await screen.findByRole("button", { name: "Arm the research loop" })

    fireEvent.click(arm)

    await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1))
    expect(JSON.stringify(vi.mocked(toast.error).mock.calls[0])).toMatch(/auto_research row is locked/)
    expect(screen.getByText("disarmed")).toBeInTheDocument()
    expect(screen.getByRole("button", { name: "Arm the research loop" })).toBeEnabled()
  })

  it("a toggle that saves at once reverts on failure (backup destination)", async () => {
    serve(() => Promise.reject(new Error("disk: the directory is not writable")))
    render(<BackupsTab />, { wrapper })
    const sw = await screen.findByRole("switch", { name: "Enable disk" })
    expect(sw).toHaveAttribute("aria-checked", "false")

    fireEvent.click(sw)

    await waitFor(() => expect(toast.error).toHaveBeenCalledTimes(1))
    expect(JSON.stringify(vi.mocked(toast.error).mock.calls[0])).toMatch(/not writable/)
    expect(screen.getByRole("switch", { name: "Enable disk" })).toHaveAttribute(
      "aria-checked",
      "false",
    )
  })
})

describe("settings dialogs and their lists", () => {
  it("Escape closes a dialog whose list popover is closed", async () => {
    serve(refuse)
    render(<LLMTab />, { wrapper })
    await editSection("reasoning")()
    const dialog = await screen.findByRole("dialog")
    const trigger = within(dialog).getByRole("combobox", { name: "reasoning provider_name" })
    fireEvent.click(trigger)
    const listbox = await screen.findByRole("listbox")
    await act(async () => {})

    fireEvent.keyDown(listbox, { key: "Escape" })
    await act(async () => {})

    expect(trigger).toHaveAttribute("aria-expanded", "false")
    expect(screen.getByRole("dialog")).toBe(dialog)

    fireEvent.keyDown(trigger, { key: "Escape" })
    await waitFor(() => expect(screen.queryByRole("dialog")).not.toBeInTheDocument())
  })

  it("no dialog keeps its own Escape workaround", () => {
    const sources = import.meta.glob<string>("/src/**/*.{ts,tsx}", {
      query: "?raw",
      import: "default",
      eager: true,
    })
    const users = Object.entries(sources)
      .filter(([file]) => !file.includes("__tests__"))
      .filter(([, text]) => text.includes("keepDialogOpenOnListEscape"))
      .map(([file]) => file)
    expect(users).toEqual([])
  })
})

describe("the notifications tab", () => {
  it("asks for the token again once the chat id changes", async () => {
    serve(refuse, {
      "/config/notifications": () =>
        Promise.resolve({
          telegram: { enabled: true, bot_token: "***", chat_id: "42" },
          notify_on: { job_failure: true },
        }),
    })
    render(<NotificationsTab />, { wrapper })
    expect(await screen.findByText(/a token is stored/i)).toBeInTheDocument()

    fireEvent.change(screen.getByLabelText("Telegram chat id"), { target: { value: "77" } })
    expect(screen.queryByText(/a token is stored/i)).not.toBeInTheDocument()
    expect(screen.getByText(/enter the bot token again/i)).toBeInTheDocument()
  })
})

describe("settings tabs share one failure style", () => {
  it.each([
    { name: "Notifications", element: () => <NotificationsTab />, path: "/config/notifications" },
    { name: "Research", element: () => <ResearchTab />, path: "/config/auto-research" },
    { name: "Flags", element: () => <FlagsTab />, path: "/config/feature-flags" },
  ])("$name shows a rejected load with the library empty-state and Retry", async ({ element, path }) => {
    let fail = true
    serve(refuse, {
      [path]: () => (fail ? Promise.reject(new Error("server unreachable")) : Promise.resolve({})),
    })
    const { container } = render(element(), { wrapper })

    const retry = await screen.findByRole("button", { name: "Retry" })
    expect(container.querySelector(".dr-empty-state")).toContainElement(retry)
    expect(screen.getByText("server unreachable")).toBeInTheDocument()

    const reads = () => vi.mocked(apiFetch).mock.calls.filter(([p]) => p === path).length
    const before = reads()
    fail = true
    fireEvent.click(retry)
    await waitFor(() => expect(reads()).toBe(before + 1))
  })
})
