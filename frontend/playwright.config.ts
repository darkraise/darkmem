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
//
// theme-switcher.spec.ts and layout-switcher.spec.ts (T1.64) were retired,
// not fixed, and are gone from this array along with their files: both
// asserted DOM contracts the app never implements (`data-accent-color`,
// `data-layout`) against UI that is not wired into any route (`ThemeSwitcher`
// has no importer under src/, and the only `top-nav` references are a
// stylesheet and the layout route's own internal switch, never exposed
// through a control). See docs/planning/tasks/E1-engine-core.md's amendment
// log for the evidence and the named follow-up that owns real coverage.
// knowledge.spec.ts joined the list with T2.36's fix round: the Facts tab's
// render clauses (both axes, both sides of a dispute, virtualization, the
// detail-level rule) are the same components on both producers, and the
// fixture is the corpus there, so the spec needs no backend.
const DEMO_FIXTURE_SPECS = [
  "activity.spec.ts",
  "demo-makes-no-api-calls.spec.ts",
  "activity-pipeline.spec.ts",
  "code-index-debt.spec.ts",
  "dashboard.spec.ts",
  "knowledge.spec.ts",
  "memories-command-palette.spec.ts",
  "honesty/exclusions-on-empty.spec.ts",
  "honesty/labels-always-render.spec.ts",
  "honesty/no-silent-drop.spec.ts",
]

export default defineConfig({
  testDir: "./tests",
  use: {
    // `on-first-retry` traces the *retry*, which passes. The failing attempt
    // is the one nobody has ever seen: `activity.spec.ts:10` has now flaked
    // three times across seven `gate.sh --full` runs and left only an
    // error-context with no page snapshot, so what the page actually rendered
    // at failure is still unknown. Retain the failing attempt's trace and
    // screenshot instead — the next occurrence answers the question below
    // instead of costing another investigation.
    trace: "retain-on-failure",
    screenshot: "only-on-failure",
  },
  // **This is not the fix for the flake, and the flake is not fixed.** Raising
  // the bound was hypothesis 4 of 4 and it was refuted by the next gate run:
  // `activity.spec.ts:10` failed again at the new 15000ms with the same
  // "element(s) not found". Waiting 3x longer changes nothing, so the element
  // is never appearing rather than appearing late. Recorded here rather than
  // reverted because the margin measurement below is real and 5000ms was an
  // unchosen default either way — but nobody should read this number as
  // having closed anything.
  //
  // **Where the investigation actually got to.** `activity.tsx` renders
  // `<Tabs value={tab ?? "pipeline"}>`, so a `tab` that is undefined at render
  // time shows the *pipeline* panel and "Days are UTC" never mounts — at any
  // timeout, which is exactly the observed shape. `DayTab` has no early return
  // and the asserted string is unconditional shell text, so the remaining
  // question is why the `?tab=day` search param would not be resolved when the
  // page settles. The `_authenticated` guard is not it: `beforeLoad` returns
  // immediately under DEMO. That is the next thing to check, and the
  // `retain-on-failure` capture above is what will answer it.
  //
  // Playwright's default expect timeout is 5000ms and nobody chose it. Two
  // tests flaked across six `gate.sh --full` runs on 2026-08-10 —
  // `code-real-mode.spec.ts:74` and `activity.spec.ts:10`, both
  // `getByText(...)` reporting "element(s) not found" — and both passed on
  // the retry below, so the gate is green *through a retry* rather than
  // cleanly.
  //
  // Measured before changing anything, because a timeout raised to make a
  // symptom go away hides a real regression just as well as it hides a slow
  // machine. First render of `/activity?tab=day` to the asserted text:
  // **0.8-1.4s idle, 1.8-2.2s under 24 CPU burners on 12 cores, 1.4s with
  // `node_modules/.vite` deleted**. The asserted string is static shell text,
  // not behind a query, so nothing is waiting on data. Three hypotheses were
  // tested and disproven: cold-start module transform (absorbed by the
  // `webServer.url` wait), a data-gated assertion (the text renders
  // unconditionally), and a Vite dep-optimizer reload (pre-bundling completes
  // before the port opens; no reload is logged even cold). 84 executions of
  // the flaking test, including the whole project serially three times in the
  // gate's own configuration, did not reproduce it.
  //
  // The margin was real — ~2.3x between a load-sensitive operation and a bound
  // nobody picked, on a host that idles at load 5-6 of 12 cores and to which
  // the gate adds a Postgres, a uvicorn running 21 job loops, two Vite dev
  // servers and a Chromium — and 15s is sized against the measured worst case
  // with room for a host several times slower. It costs nothing on a passing
  // run (`toBeVisible` polls and returns as soon as the element appears; the
  // project still runs in 12.5s). It simply was not the cause. The retry below
  // stays, and is still doing the absorbing.
  expect: { timeout: 15000 },
  // T1.64: against a disposable stack, every "chromium"-project spec that
  // authenticates (auth.spec.ts, code-real-mode.spec.ts, code-wiki-empty.spec.ts,
  // setup-wizard-refresh.spec.ts) shares the one live, stateful backend
  // stack.py boots — concurrent workers race its session/rate-limiter/job-lock
  // state (measured live this task: login/logout and setup-redirect
  // assertions flake under the default parallel worker count against a real
  // backend, never having had one to race against in gate.sh --full before,
  // since every real-mode spec soft-skipped until this task). Demo-fixture
  // specs need no such serialization — they never share mutable server state.
  workers: process.env.E2E_DISPOSABLE_STACK ? 1 : undefined,
  // One retry against a disposable stack only: even serialized, a handful of
  // real-mode specs sharing one live backend/vite-proxy pair occasionally hit
  // a transient WS-proxy reset under this sandboxed environment's load — a
  // real, deterministic failure (a broken guard, a wrong assertion) still
  // fails after one retry, but a one-off proxy hiccup does not fail the gate
  // on a rerun that would have passed.
  retries: process.env.E2E_DISPOSABLE_STACK ? 1 : 0,
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
