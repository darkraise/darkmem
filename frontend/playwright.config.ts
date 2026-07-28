import { defineConfig, devices } from "@playwright/test"

// T1.58 Step 5: these specs assert against surfaces that only render
// without login in demo mode (their own soft-skip guards read "not
// reachable without login" / "likely needs login") — real mode's default
// (T1.58 Step 6) makes every one of those guards fire and silently retire
// the spec's evidence. They get their own project, served by its own
// VITE_DEMO=1 dev server on a distinct port, so flipping the app's default
// never touches what they exercise. auth.spec.ts and
// setup-wizard-refresh.spec.ts need the opposite — the real, unauthenticated
// default — and stay on the unmodified project/server.
//
// The plan's own enumeration named eight; the honesty/ suite (three more
// files, six test cases — exclusions-on-empty, labels-always-render's four
// cases, no-silent-drop) carries the identical pattern and was not in that
// count. labels-always-render.spec.ts's own header even says so outright:
// "Exercised against the demo store ... DEMO defaults on until T1.58."
// Found live (Ruling 5's "if you find a ninth, handle it the same way").
// code-wiki-empty.spec.ts left DEMO_FIXTURE_SPECS in T1.59: it used to
// target the legacy /repos page's demo-mode Code Wiki tab, but that page is
// deleted and its replacement, /code/wiki, needs the real, authenticated
// backend (RealWikiView) to exercise anything meaningful — see
// code-real-mode.spec.ts's header for why a real-mode spec must never move
// into this array.
const DEMO_FIXTURE_SPECS = [
  "activity.spec.ts",
  "activity-pipeline.spec.ts",
  "code-index-debt.spec.ts",
  "dashboard.spec.ts",
  "memories-command-palette.spec.ts",
  "layout-switcher.spec.ts",
  "theme-switcher.spec.ts",
  "honesty/exclusions-on-empty.spec.ts",
  "honesty/labels-always-render.spec.ts",
  "honesty/no-silent-drop.spec.ts",
]

export default defineConfig({
  testDir: "./tests",
  use: {
    trace: "on-first-retry",
  },
  projects: [
    {
      name: "chromium",
      testIgnore: DEMO_FIXTURE_SPECS,
      use: { ...devices["Desktop Chrome"], baseURL: "http://localhost:3636" },
    },
    {
      name: "demo-fixture",
      testMatch: DEMO_FIXTURE_SPECS,
      use: { ...devices["Desktop Chrome"], baseURL: "http://localhost:3637" },
    },
  ],
  webServer: [
    {
      command: "npm run dev",
      url: "http://localhost:3636",
      reuseExistingServer: !process.env.CI,
    },
    {
      // Inline, not `env:` — Playwright's webServer.env replaces
      // process.env rather than merging with it (measured live this
      // session: with `env: { VITE_DEMO: "1" }`, PATH survived enough for
      // the shell to find npm, but VITE_DEMO itself never reached vite and
      // every demo-fixture spec silently soft-skipped instead of exercising
      // its real assertions — exactly the regression this project split
      // exists to prevent). Setting the var inline in the command is
      // unambiguous regardless of that merge behavior.
      command: "VITE_DEMO=1 npm run dev -- --port 3637",
      url: "http://localhost:3637",
      reuseExistingServer: !process.env.CI,
    },
  ],
})
