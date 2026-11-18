# UI profile

**Platform:** web
**Harness:** Storybook (`cd frontend && npx storybook dev -p 6006 --ci`) for canvas states on synthetic data; `cd frontend && VITE_DEMO=1 npx vite --port 3637` for whole pages; both driven by Playwright MCP. Never the live instance on :8000.
**UI test runner:** `cd frontend && npm test` (vitest, happy-dom) for logic; `backend/scripts/e2e/run_playwright_e2e.py <spec> --project=chromium` for browser specs. Never bare `npx playwright test`.
**UI paths:** `frontend/src/*.tsx` `frontend/src/*.ts` `frontend/src/*.css`
**Design system:** darkraise-ui 7.x (`frontend/node_modules/darkraise-ui/dist/components/`), Geist font
**Token paths:** `frontend/src/styles/globals.css`
**Viewports:** 1280x800, 1920x1080
**Themes:** light, dark
**Users:** the owner, a single technical operator, on desktop browsers
**Voice:** plain, sentence case, no developer-facing copy
**Screenshots:** local

## Decisions

- 2026-11-18 — Graph canvases are proven in Storybook on synthetic graphs up to 20,000 nodes and in demo mode; WebGL in headless Chromium renders through SwiftShader, so frame-rate figures from it are not representative.
