import { describe, it, expect, vi, beforeEach } from "vitest"
import { render, screen, within } from "@testing-library/react"
import userEvent from "@testing-library/user-event"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import type { ReactNode } from "react"

vi.mock("@/lib/demo-flag", () => ({ DEMO: false }))
vi.mock("@/lib/api", () => ({ apiFetch: vi.fn() }))

import { apiFetch } from "@/lib/api"
import { GitAccountsTab } from "../components/git-accounts-tab"
import { AddRepoDialog } from "@/features/code/components/add-repo-dialog"

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

const FORGES = [
  { provider: "github", label: "GitHub", default_host: "github.com" },
  { provider: "gitlab", label: "GitLab", default_host: "gitlab.com" },
]

const PERSONAL = {
  id: "acc-1",
  label: "Personal",
  provider: "github",
  host: "github.com",
  username: "octocat",
  token_hint: "1234",
  scopes: "repo",
  is_default: true,
  last_verified_at: "2026-08-19T09:12:00Z",
  repo_count: 2,
  created_at: "2026-06-02T10:00:00Z",
  updated_at: "2026-08-19T09:12:00Z",
}

const BOT = {
  ...PERSONAL,
  id: "acc-2",
  label: "OSS bot",
  username: "darkmem-bot",
  token_hint: "9c1b",
  scopes: null,
  is_default: false,
  repo_count: 0,
}

/** Routes each endpoint the surfaces under test call. */
function route(overrides: Record<string, unknown> = {}) {
  vi.mocked(apiFetch).mockImplementation(async (path: string) => {
    if (path.startsWith("/git-accounts")) {
      return (
        overrides["/git-accounts"] ?? {
          accounts: [PERSONAL, BOT],
          providers: FORGES,
        }
      )
    }
    if (path.startsWith("/repos")) return overrides["/repos"] ?? []
    return {}
  })
}

describe("GitAccountsTab", () => {
  beforeEach(() => vi.clearAllMocks())

  it("renders each account by name and masks the token to its hint", async () => {
    route()
    render(<GitAccountsTab />, { wrapper })

    const personal = await screen.findByText("Personal")
    const row = personal.closest("li")!
    expect(within(row).getByText(/@octocat/)).toBeInTheDocument()
    expect(within(row).getByText(/••••1234/)).toBeInTheDocument()
    // The raw token must never be in the DOM; only the server holds it.
    expect(document.body.textContent).not.toContain("ghp_")
  })

  it("badges exactly the default account and offers to promote the other", async () => {
    route()
    render(<GitAccountsTab />, { wrapper })

    const defaultRow = (await screen.findByText("Personal")).closest("li")!
    expect(
      within(defaultRow).getByText("Default for github.com"),
    ).toBeInTheDocument()
    expect(
      within(defaultRow).queryByRole("button", {
        name: /make default for github.com/i,
      }),
    ).not.toBeInTheDocument()

    const botRow = screen.getByText("OSS bot").closest("li")!
    expect(within(botRow).queryByText(/^Default for/)).not.toBeInTheDocument()
    expect(
      within(botRow).getByRole("button", {
        name: /make default for github.com/i,
      }),
    ).toBeInTheDocument()
  })

  it("promotes an account through PUT is_default", async () => {
    route()
    render(<GitAccountsTab />, { wrapper })

    const botRow = (await screen.findByText("OSS bot")).closest("li")!
    await userEvent.click(
      within(botRow).getByRole("button", {
        name: /make default for github.com/i,
      }),
    )
    // Personal already holds github.com, so the swap is confirmed first.
    expect(apiFetch).not.toHaveBeenCalledWith(
      "/git-accounts/acc-2",
      expect.objectContaining({ method: "PUT" }),
    )
    const confirm = await screen.findByRole("dialog")
    expect(
      within(confirm).getByText(/Personal is the default/),
    ).toBeInTheDocument()
    await userEvent.click(
      within(confirm).getByRole("button", { name: "Make default" }),
    )

    expect(apiFetch).toHaveBeenCalledWith(
      "/git-accounts/acc-2",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ is_default: true }),
      }),
    )
  })

  it("requires a reassignment target before deleting an account in use", async () => {
    route()
    render(<GitAccountsTab />, { wrapper })

    const personalRow = (await screen.findByText("Personal")).closest("li")!
    await userEvent.click(
      within(personalRow).getByRole("button", { name: /delete personal/i }),
    )

    // Two repositories still use it, so the confirm button stays disabled
    // until another account is picked — the server would refuse otherwise.
    const confirm = await screen.findByRole("button", { name: "Delete" })
    expect(confirm).toBeDisabled()
    expect(
      screen.getByText(/2 repositories still use this account/i),
    ).toBeInTheDocument()
  })

  it("deletes an unused account without asking for a reassignment", async () => {
    route()
    render(<GitAccountsTab />, { wrapper })

    const botRow = (await screen.findByText("OSS bot")).closest("li")!
    await userEvent.click(
      within(botRow).getByRole("button", { name: /delete oss bot/i }),
    )

    const confirm = await screen.findByRole("button", { name: "Delete" })
    expect(confirm).toBeEnabled()
    await userEvent.click(confirm)

    expect(apiFetch).toHaveBeenCalledWith(
      "/git-accounts/acc-2",
      expect.objectContaining({ method: "DELETE" }),
    )
  })

  it("shows an empty state rather than a blank panel when no account exists", async () => {
    route({ "/git-accounts": { accounts: [], providers: FORGES } })
    render(<GitAccountsTab />, { wrapper })
    expect(await screen.findByText("No git accounts")).toBeInTheDocument()
  })
})

describe("AddRepoDialog account picker", () => {
  beforeEach(() => vi.clearAllMocks())

  // The trigger and the submit button share a name, so everything after the
  // open is scoped to the dialog.
  const openDialog = async () => {
    render(<AddRepoDialog />, { wrapper })
    await userEvent.click(
      screen.getByRole("button", { name: /add repository/i }),
    )
    return within(await screen.findByRole("dialog"))
  }

  const fillNameAndSubmit = async (
    dialog: ReturnType<typeof within>,
    name: string,
  ) => {
    await userEvent.type(dialog.getAllByRole("textbox")[0], name)
    await userEvent.click(
      dialog.getByRole("button", { name: "Add Repository" }),
    )
  }

  /** The provider picker comes first, so the account one is the last combobox. */
  const chooseAccount = async (
    dialog: ReturnType<typeof within>,
    option: RegExp,
  ) => {
    const combos = dialog.getAllByRole("combobox")
    await userEvent.click(combos[combos.length - 1])
    // The listbox portals out of the dialog, so it is found on the screen.
    await userEvent.click(await screen.findByText(option))
  }

  it("labels every field so it is announced and focusable by its label", async () => {
    route()
    const dialog = await openDialog()
    expect(dialog.getByLabelText("Name *")).toHaveAttribute("required")
    expect(dialog.getByLabelText("URL")).toBeInTheDocument()
    expect(dialog.getByLabelText("Default branch")).toBeInTheDocument()
    expect(
      dialog.getByRole("combobox", { name: "Provider" }),
    ).toBeInTheDocument()
    expect(
      dialog.getByRole("combobox", { name: "Account" }),
    ).toBeInTheDocument()
  })

  it("preselects the provider's default account", async () => {
    route()
    const dialog = await openDialog()
    expect(
      await dialog.findByText(/Personal · @octocat \(default\)/),
    ).toBeInTheDocument()
  })

  it("sends the selected account id on create", async () => {
    route()
    const dialog = await openDialog()
    await dialog.findByText(/Personal · @octocat \(default\)/)
    await fillNameAndSubmit(dialog, "my-repo")

    expect(apiFetch).toHaveBeenCalledWith(
      "/repos",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"git_account_id":"acc-1"'),
      }),
    )
  })

  it("keeps a custom-token choice instead of snapping back to the default", async () => {
    route()
    const dialog = await openDialog()
    await dialog.findByText(/Personal · @octocat \(default\)/)
    await chooseAccount(dialog, /Custom token for this repo/)

    expect(dialog.getByText("Auth token")).toBeInTheDocument()
    await userEvent.type(
      dialog.getByPlaceholderText(/this repository only/i),
      "ghp_secret",
    )
    await fillNameAndSubmit(dialog, "token-repo")

    expect(apiFetch).toHaveBeenCalledWith(
      "/repos",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"auth_token":"ghp_secret"'),
      }),
    )
  })

  it("keeps a non-default account choice", async () => {
    route()
    const dialog = await openDialog()
    await dialog.findByText(/Personal · @octocat \(default\)/)
    await chooseAccount(dialog, /OSS bot · @darkmem-bot/)
    await fillNameAndSubmit(dialog, "bot-repo")

    expect(apiFetch).toHaveBeenCalledWith(
      "/repos",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"git_account_id":"acc-2"'),
      }),
    )
  })

  it("sends an explicit null rather than omitting the field when no account is chosen", async () => {
    route({ "/git-accounts": { accounts: [], providers: FORGES } })
    const dialog = await openDialog()
    await fillNameAndSubmit(dialog, "public-repo")

    // Omitting it would make the server stamp its default; the operator
    // chose none, and that has to survive the round trip.
    expect(apiFetch).toHaveBeenCalledWith(
      "/repos",
      expect.objectContaining({
        method: "POST",
        body: expect.stringContaining('"git_account_id":null'),
      }),
    )
  })
})
