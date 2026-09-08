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
const DEMO_ROUTES = [
  "/",
  "/memories",
  "/activity?tab=feed",
  "/activity?tab=day",
  "/activity?tab=jobs",
  "/activity?tab=monitors",
  "/activity?tab=pipeline",
  "/activity?tab=triage",
  "/code/repositories",
  "/code/graph",
  "/knowledge/facts",
  "/documents",
  "/notes",
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

    // The login form is the *symptom* of the 401 redirect, and asserting it
    // separately is what keeps a failure legible: a bare request-list
    // assertion would say "one stray GET" where the real damage is that the
    // page the user asked for is gone.
    await expect(
      page.getByText(/sign in to continue/i),
      `demo route ${route} was redirected to /login — an unguarded ` +
        `authenticated read 401'd and handleUnauthorized navigated away`,
    ).toBeHidden()

    expect(
      attempted,
      `demo mode must issue no /api/v1 request; ${route} attempted:\n` +
        attempted.join("\n") +
        `\nGive the hook behind it \`enabled: !DEMO\`, the way ` +
        `useProjects and the usage reads do.`,
    ).toEqual([])
  })
}
