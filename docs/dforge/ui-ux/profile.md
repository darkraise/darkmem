# UI profile

**Platform:** web
**Harness:** Storybook (`cd frontend && npx storybook dev -p 6006 --ci`) for canvas states on synthetic data; `cd frontend && VITE_DEMO=1 npx vite --port 3637` for whole pages; both driven by Playwright MCP; and the live memory graph page at `http://127.0.0.1:8000/memory-graph` with the cloned 192.168.0.199 corpus, read-only, signed in by minting a session inside the container (the `darkmem_session` cookie plus `localStorage['darkmem-auth']`).
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
- 2026-11-18 — The memory graph is also proven on the live page with the cloned corpus (owner: "Fixture + live (Recommended)"); the page is read-only, nothing is written, and Playwright specs never run against :8000.
