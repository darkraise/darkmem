import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { fireEvent, render, screen, waitFor } from "@testing-library/react"
import type { ReactNode } from "react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"
import { StepRepoPath } from "../components/StepRepoPath"
import { useSetupWizardStore } from "../setupWizardStore"

function wrapper({ children }: { children: ReactNode }) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  return <QueryClientProvider client={client}>{children}</QueryClientProvider>
}
const entry = {
  name: "app",
  path: "/repos/app",
  is_dir: true,
  is_git: true,
  has_repos: false,
  repo_count: 0,
}
let failScan = false
beforeEach(() => {
  failScan = false
  useSetupWizardStore.getState().reset()
  vi.stubGlobal(
    "fetch",
    vi.fn(async (url: string) => {
      if (url.includes("/roots"))
        return {
          ok: true,
          json: async () => ({
            roots: [{ path: "/repos", label: "Repositories" }],
          }),
        }
      const params = new URL(url, "http://localhost").searchParams
      if (failScan && params.get("detect_repos") === "true")
        return {
          ok: false,
          status: 403,
          json: async () => ({ detail: "Permission denied" }),
        }
      const path = params.get("path")
      return {
        ok: true,
        json: async () => ({
          path,
          parent: "/",
          entries: path === "/repos" ? [entry] : [],
          is_git: path === "/repos/app",
          blocked_reason: null,
        }),
      }
    }),
  )
})
afterEach(() => vi.unstubAllGlobals())

it("commits a folder only after detection and clears selection when browsing elsewhere", async () => {
  render(<StepRepoPath />, { wrapper })
  fireEvent.click(await screen.findByRole("button", { name: "Repositories" }))
  await screen.findByRole("button", { name: /app Git repository/ })
  expect(useSetupWizardStore.getState().repos.basePath).toBe("")
  fireEvent.click(screen.getByRole("button", { name: "Use this folder" }))
  await waitFor(() =>
    expect(useSetupWizardStore.getState().repos.basePath).toBe("/repos"),
  )
  expect(useSetupWizardStore.getState().repos.detected).toEqual([
    { name: "app", subPath: "app", selected: true },
  ])
  fireEvent.click(screen.getByRole("button", { name: /app Git repository/ }))
  await screen.findByText("This is a Git repository. Choose its parent folder.")
  expect(useSetupWizardStore.getState().repos.basePath).toBe("")
  expect(useSetupWizardStore.getState().repos.detected).toEqual([])
  expect(screen.getByRole("button", { name: "Use this folder" })).toBeDisabled()
})

it("supports typed paths with Enter and filtering without changing the selection", async () => {
  render(<StepRepoPath />, { wrapper })
  const input = screen.getByRole("textbox", { name: "Server folder path" })
  fireEvent.change(input, { target: { value: "/repos" } })
  fireEvent.submit(input.closest("form")!)
  await screen.findByRole("button", { name: /app Git repository/ })
  fireEvent.change(screen.getByRole("textbox", { name: "Filter folders" }), {
    target: { value: "missing" },
  })
  expect(screen.getByText("No folders match your search.")).toBeInTheDocument()
  expect(useSetupWizardStore.getState().repos.basePath).toBe("")
})

it("keeps Next ineligible when repository detection fails", async () => {
  render(<StepRepoPath />, { wrapper })
  fireEvent.click(await screen.findByRole("button", { name: "Repositories" }))
  await screen.findByRole("button", { name: /app Git repository/ })
  failScan = true
  fireEvent.click(screen.getByRole("button", { name: "Use this folder" }))
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Permission denied",
  )
  expect(useSetupWizardStore.getState().repos.basePath).toBe("")
  expect(screen.getByRole("button", { name: "Use this folder" })).toBeDisabled()
})

it("selects and scans the default folder without requiring a confirmation click", async () => {
  render(<StepRepoPath />, { wrapper })
  expect(
    screen.getByRole("textbox", { name: "Server folder path" }),
  ).toHaveValue("/app/data/repositories")
  await waitFor(() =>
    expect(useSetupWizardStore.getState().repos.basePath).toBe(
      "/app/data/repositories",
    ),
  )
  expect(fetch).toHaveBeenCalledWith(
    "/api/v1/setup/fs/list?path=%2Fapp%2Fdata%2Frepositories&detect_repos=true",
    expect.anything(),
  )
})

it("does not select an inaccessible default folder", async () => {
  failScan = true
  render(<StepRepoPath />, { wrapper })
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Could not select the default folder",
  )
  expect(useSetupWizardStore.getState().repos.basePath).toBe("")
})

it("shows a missing default folder once, in the browser's words", async () => {
  const message =
    "That folder does not exist on the server: /app/data/repositories"
  vi.mocked(fetch).mockImplementation((async (url: string) => {
    if (url.includes("/roots"))
      return { ok: true, json: async () => ({ roots: [] }) }
    return { ok: false, status: 422, json: async () => ({ detail: message }) }
  }) as unknown as typeof fetch)
  render(<StepRepoPath />, { wrapper })
  expect(await screen.findByText(message)).toBeInTheDocument()
  await waitFor(() =>
    expect(fetch).toHaveBeenCalledWith(
      expect.stringContaining("detect_repos=true"),
      expect.anything(),
    ),
  )
  // Let the default scan's rejection land before counting.
  await new Promise((resolve) => setTimeout(resolve, 50))
  await waitFor(() => expect(screen.getAllByRole("alert")).toHaveLength(1))
  expect(screen.getAllByText(new RegExp(message))).toHaveLength(1)
  expect(screen.queryByText(/Could not select the default folder/)).toBeNull()
})

it("preserves a previously selected folder", async () => {
  useSetupWizardStore.getState().setReposBasePath("/repos")
  render(<StepRepoPath />, { wrapper })
  await screen.findByRole("button", { name: /app Git repository/ })
  expect(
    screen.getByRole("textbox", { name: "Server folder path" }),
  ).toHaveValue("/repos")
  expect(useSetupWizardStore.getState().repos.basePath).toBe("/repos")
})
