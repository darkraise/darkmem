import { test, expect } from "@playwright/test"

// Demo mode runs with **no backend**, and the cost of forgetting that is not a
// missing number — it is the whole demo going down. `apiFetch`'s 401 handler
// (`src/lib/api.ts`) calls `window.location.href = "/login"`, so one
// unguarded authenticated read on a mounted component hard-navigates the
// browser off whatever page it was on.
//
// This has now shipped twice. `useProjects` mounts in the app chrome and took
// every demo route down until it got `enabled: !DEMO`; the usage reads mounted
// in the Activity Jobs and Pipeline tabs and did it again — the gate saw it as
// a Playwright run wedging on a login form it could not explain, because the
// symptom appears on a page that never made the request.
//
// So the guard is structural rather than a remembered convention: every route
// the demo fixture claims to render must issue no `/api/v1/` request at all.
// A new hook without its `enabled: !DEMO` fails here, on the route that mounts
// it, naming the URL it tried to fetch.
const SETTINGS_TABS = [
  "flags",
  "llm",
  "security",
  "maintenance",
  "integration",
  "git-accounts",
  "notifications",
  "research",
  "backups",
  "appearance",
] as const

const DEMO_ROUTES = [
  "/",
  "/memories",
  "/memory-graph",
  "/activity?tab=feed",
  "/activity?tab=day",
  "/activity?tab=jobs",
  "/activity?tab=monitors",
  "/activity?tab=pipeline",
  "/activity?tab=triage",
  "/activity?tab=worklog",
  "/projects/darkmem?tab=progress",
  "/code/repositories",
  "/code/graph",
  "/code/wiki",
  "/knowledge/facts",
  "/knowledge/review",
  "/knowledge/topics",
  "/documents",
  "/notes",
  "/projects",
  "/chat",
  "/jobs",
  "/usage",
  ...SETTINGS_TABS.map((tab) => `/settings?tab=${tab}`),
]

for (const route of DEMO_ROUTES) {
  test(`demo mode issues no API request on ${route}`, async ({ page }) => {
    const attempted: string[] = []
    page.on("request", (request) => {
      const url = new URL(request.url())
      if (url.pathname.startsWith("/api/v1/")) {
        attempted.push(`${request.method()} ${url.pathname}${url.search}`)
      }
    })

    await page.goto(route)
    // Long enough for a mounted query to fire. React Query dispatches on
    // mount, so this is a settle window, not a race the assertion depends on.
    await page.waitForTimeout(1500)

    // Requests are asserted first: when the page was redirected to /login,
    // the list names the read that caused it, or is empty when the demo flag
    // was not on at all.
    expect(
      attempted,
      `demo mode must issue no /api/v1 request; ${route} attempted:\n` +
        attempted.join("\n") +
        `\nGive the hook behind it \`enabled: !DEMO\`, the way ` +
        `useProjects and the usage reads do.`,
    ).toEqual([])

    await expect(
      page.getByText(/sign in to continue/i),
      `demo route ${route} was redirected to /login with no /api/v1 ` +
        `request attempted — the page was served without the demo flag`,
    ).toBeHidden()
  })
}
