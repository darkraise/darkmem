# darkmem Frontend Migration to darkraise-ui

**Date:** 2026-04-07
**Status:** Proposed
**Approach:** Clean rebuild (Approach B) — scaffold fresh frontend from template conventions, port pages incrementally

## Goal

Migrate darkmem's frontend to consume the `darkraise-ui` npm package for all UI components, theming, layout, and hooks. Adopt TanStack Router for file-based routing and the template's full dev tooling stack. The result is visual and structural consistency with other darkraise-web-template projects, plus shared maintenance of the core UI layer via the published package.

## Scope

- Replace all 19 local UI components with `darkraise-ui` imports (47 components available)
- Switch routing from `react-router-dom` v7 to `@tanstack/react-router` (file-based)
- Adopt the 6-axis theming engine (accent, surface, surface style, background, font, mode)
- Use `darkraise-ui/layout` for the app shell (sidebar layout with `NavGroup[]` config)
- Move auth state from `useState` + raw `localStorage` to Zustand store
- Reorganize domain code into `features/` modules (chat, graph, memories, code)
- Add Prettier, Husky, commitlint, lint-staged
- Preserve all 15 pages, all backend API integration, WebSocket, and SSE streaming

## Out of Scope

- Backend changes (API endpoints, database, services unchanged)
- Graph renderer internals (Sigma, Three.js, graphology canvas rendering unchanged)
- Docker/nginx deployment config (static build output unchanged)

## Project Structure

```
frontend/src/
├── app.tsx                       # Router setup only
├── main.tsx                      # React 19 entry point
├── routes/                       # TanStack Router file-based routes
│   ├── __root.tsx                # AppProviders (QueryClient + ThemeProvider + Toaster)
│   ├── _authenticated.tsx        # Auth guard + layout shell + nav config
│   ├── _authenticated/
│   │   ├── index.tsx             # Overview (dashboard)
│   │   ├── memories.tsx
│   │   ├── chat.tsx
│   │   ├── repos.tsx
│   │   ├── analytics.tsx
│   │   ├── pipeline.tsx
│   │   ├── settings.tsx
│   │   ├── llm.tsx
│   │   ├── code-wiki.tsx
│   │   ├── graph.tsx
│   │   ├── unified-graph.tsx
│   │   ├── vectors.tsx
│   │   └── code-graph.tsx
│   └── _guest/
│       ├── login.tsx
│       └── setup.tsx
├── features/                     # Domain-specific modules
│   ├── chat/
│   │   ├── components/           # ChatInput, ChatMessages, ChatSidebar, ChatOverlay, SourceBadges
│   │   └── hooks/                # use-chat-stream.ts
│   ├── graph/
│   │   ├── components/           # Graph2DRenderer, Graph3DRenderer, CodeGraphRenderer, etc.
│   │   ├── hooks/                # useGraphFilters, useGraphLayout, useGraphSelection
│   │   ├── lib/                  # graph-colors, graph-geometry, graph-utils, node-diamond-program
│   │   └── styles/               # graph-specific CSS
│   ├── memories/
│   │   └── components/           # MemoryCard
│   └── code/
│       └── components/           # Code wiki and code graph domain components
├── hooks/
│   └── api/                      # 6 API hook files (ported directly)
├── lib/
│   ├── api.ts                    # Fetch wrapper (reads token from Zustand store)
│   └── websocket.ts              # WebSocket manager (extracted from hook)
└── styles/
    └── globals.css               # @import tailwindcss + darkraise-ui/styles.css + overrides
```

## Dependency Changes

### Removed (provided by darkraise-ui)

- `@base-ui/react` — replaced by Radix UI primitives via package
- `shadcn` — components now from package
- `class-variance-authority`, `clsx`, `tailwind-merge` — bundled in package
- `@fontsource-variable/geist` — theme engine handles fonts
- `next-themes` — bundled in package
- `recharts`, `sonner`, `lucide-react` — bundled in package
- `tw-animate-css` — bundled in package
- `react-router-dom` — replaced by TanStack Router (transitive dep of darkraise-ui)
- `vis-data`, `vis-network` — unused, removed

### Added

**Production:**

- `darkraise-ui` — the UI kit (components, hooks, theme, layout, forms, data-table, errors)
- `zustand` — client state management (auth store)

**Dev:**

- `@tanstack/router-plugin` — Vite plugin for file-based route codegen
- `prettier` + `prettier-plugin-tailwindcss` — formatting with Tailwind class sorting
- `husky` — git hooks
- `@commitlint/cli` + `@commitlint/config-conventional` — commit message linting
- `lint-staged` — pre-commit linting
- `eslint-config-prettier` — ESLint/Prettier integration

### Kept (domain-specific)

- `sigma`, `@sigma/edge-curve`, `@sigma/node-square` — 2D graph rendering
- `graphology`, `graphology-layout-forceatlas2`, `graphology-types` — graph data structures
- `react-force-graph-3d`, `three` — 3D graph rendering
- `react-markdown` — chat and wiki markdown rendering
- `@tailwindcss/typography` — prose styling for markdown
- `react`, `react-dom`, `tailwindcss`, `@tailwindcss/vite`, `@tanstack/react-query` — peer/shared deps

## Routing & Navigation

### Route Tree

TanStack Router file-based routing with two layout routes:

- `_authenticated.tsx` — sidebar layout shell with `beforeLoad` auth guard. Redirects to `/login` if `useAuthStore.getState().isAuthenticated` is false. Contains the `NavGroup[]` configuration that drives sidebar navigation.
- `_guest.tsx` — minimal layout for login and setup pages, no sidebar.

### Navigation Groups

```typescript
const nav: NavGroup[] = [
  {
    label: "Overview",
    items: [
      { label: "Dashboard",  href: "/",          icon: Home },
      { label: "Memories",   href: "/memories",   icon: Brain },
      { label: "Chat",       href: "/chat",       icon: MessageSquare },
    ],
  },
  {
    label: "Visualization",
    items: [
      { label: "Knowledge Graph", href: "/graph",         icon: Share2 },
      { label: "Unified Graph",   href: "/unified-graph", icon: GitBranch },
      { label: "Vector Space",    href: "/vectors",       icon: Orbit },
      { label: "Code Graph",      href: "/code-graph",    icon: Network },
    ],
  },
  {
    label: "Code Intelligence",
    items: [
      { label: "Repositories",  href: "/repos",      icon: FolderGit2 },
      { label: "Code Wiki",     href: "/code-wiki",  icon: BookOpen },
    ],
  },
  {
    label: "System",
    items: [
      { label: "Analytics",     href: "/analytics",  icon: BarChart3 },
      { label: "Pipeline",      href: "/pipeline",   icon: Activity },
      { label: "LLM Config",    href: "/llm",        icon: Cpu },
      { label: "Settings",      href: "/settings",   icon: Settings },
    ],
  },
]
```

### Auth Flow

- Token stored in Zustand auth store (persisted to `localStorage['darkmem_token']`)
- `_authenticated.tsx` uses `beforeLoad` hook to check auth state and redirect
- `apiFetch()` reads token from `useAuthStore.getState().token`
- 401 responses call `useAuthStore.getState().logout()` then `router.navigate({ to: '/login' })`
- No full page reloads — TanStack Router handles transitions

### Initialization Check

The current app calls `GET /auth/status` on mount to determine if initial setup is needed. In the new structure, `_guest.tsx` handles this: its `beforeLoad` hook fetches `/auth/status` and redirects to `/setup` if the app is uninitialized, or to `/login` if it is. The `_authenticated` guard also falls through to guest routes when unauthenticated, so the check is centralized in the guest layout route.

## Theming & Layout

### Theme Provider Setup

```typescript
// __root.tsx
<ThemeProvider
  defaultAccent="indigo"          // darkmem's current primary color
  defaultMode="dark"              // keep dark as default
  defaultSurfaceStyle="default"
  defaultFont="modern"            // Geist font (matches current)
>
```

### Theme Switcher

Placed in the Settings page. Four axes enabled by default:

- Accent color (17 options)
- Mode (light / dark / system)
- Font family (5 stacks)
- Surface style (default / glassmorphism)

Two axes hidden (can be enabled later):

- Surface color — defaults to "slate"
- Background style — defaults to "solid"

### CSS

The current `index.css` (120+ lines of hardcoded CSS variables, dark mode rules, animations) is replaced by a minimal `styles/globals.css`:

```css
@import "tailwindcss";
@import "darkraise-ui/styles.css";

/* darkmem-specific overrides */
.chat-prose { /* markdown styling for chat */ }
.graph-container { /* full-bleed canvas for graph pages */ }
.scrollbar-thin { /* custom scrollbar if not in package */ }
```

### Layout

Use `SidebarLayout` from `darkraise-ui/layout` as the default layout in `_authenticated.tsx`. The sidebar renders the `NavGroup[]` configuration defined above. Graph pages use the same layout shell but their content area is a full-bleed canvas.

## API Layer

The backend is unchanged. All API integration code ports directly with minimal modifications:

- `lib/api.ts` — same `apiFetch<T>()` wrapper, same `API_BASE = "/api/v1"`. Token source changes from raw `localStorage` to Zustand store. 401 handling changes from `window.location.reload()` to `router.navigate()`.
- `hooks/api/` — all 6 hook files (memory, chat, graph, repo, analytics, pipeline) port with no logic changes. Only import paths change.
- `lib/websocket.ts` — extracted from `useWebSocket` hook. Same WebSocket URL, same event handling, same exponential backoff reconnection. Toast import changes to `darkraise-ui/components/sonner`.
- `features/chat/hooks/use-chat-stream.ts` — SSE streaming logic unchanged. Same event types (sources, token, done, error). Moved from `hooks/` to `features/chat/hooks/`.

### Vite Proxy

Unchanged:

```typescript
proxy: {
  '/api':    'http://localhost:8000',
  '/health': 'http://localhost:8000',
  '/ws':     { target: 'ws://localhost:8000', ws: true },
}
```

## Page Migration

### Tier 1 — Direct Port (forms and config)

- **Login** — auth form using `darkraise-ui/forms` field components
- **Setup** — initial setup form, same pattern as login
- **Settings** — config form + `ThemeSwitcher` from `darkraise-ui/theme`
- **LLM Config** — provider config form with `SelectField`, `TextField`, `Card`

### Tier 2 — Moderate (data display + interactions)

- **Overview** — stat cards + activity chart (recharts via package) + top tags. Use template card patterns.
- **Memories** — search bar + tag filter + paginated card grid. Keep `MemoryCard` as domain component in `features/memories/`. Use darkraise-ui `Input`, `Badge`, `Select` for filter chrome.
- **Repositories** — repo list with add dialog + status tracking. Candidate for `DataTable` with row actions.
- **Analytics** — stats + log table + reprocess actions. Log table may use `DataTable`.
- **Pipeline** — processing status and logs. SSE reprocessing stream logic unchanged.
- **Code Wiki** — markdown rendering with `react-markdown` + `@tailwindcss/typography`. Surrounding chrome swaps to darkraise-ui.

### Tier 3 — Higher Effort (complex interactivity)

- **Chat** — conversation sidebar + message list + streaming input + source badges. All 5 chat components move to `features/chat/components/`. SSE streaming hook unchanged. Custom split-panel layout within the page content area.
- **Graph pages (×4)** — Knowledge Graph, Unified Graph, Vector Space, Code Graph. All 8 graph components move to `features/graph/components/`. Canvas/WebGL rendering untouched. Toolbar and filter panels swap to darkraise-ui buttons, selects, badges. Graph-specific CSS stays scoped in `features/graph/styles/`.

### Migration Order

1. **Phase 1:** Scaffold + providers + Login + Setup + Settings + LLM Config
2. **Phase 2:** Overview + Memories + Repositories + Analytics + Pipeline
3. **Phase 3:** Chat (full feature) + Code Wiki
4. **Phase 4:** Graph pages (×4) + graph components (×8)

## Dev Tooling

### Prettier

`.prettierrc` with `prettier-plugin-tailwindcss` for automatic Tailwind class sorting.

### ESLint

Flat config (`eslint.config.js`) with `typescript-eslint`, `react-hooks`, `react-refresh`, and `eslint-config-prettier`.

### Git Hooks

- **Pre-commit (Husky + lint-staged):** runs `eslint --fix` + `prettier --write` on staged `.ts`/`.tsx` files, `prettier --write` on `.json`/`.css`/`.md` files.
- **Commit-msg (commitlint):** enforces conventional commit format (`feat`, `fix`, `docs`, `style`, `refactor`, `test`, `chore`, `perf`).

### Scripts

```json
{
  "dev":       "vite",
  "build":     "tsc --noEmit && vite build",
  "lint":      "eslint src/",
  "format":    "prettier --write \"src/**/*.{ts,tsx,css}\"",
  "typecheck": "tsc --noEmit",
  "preview":   "vite preview",
  "prepare":   "husky"
}
```

## Vite Config

```typescript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { TanStackRouterVite } from '@tanstack/router-plugin/vite'

export default defineConfig({
  plugins: [TanStackRouterVite(), react(), tailwindcss()],
  resolve: { alias: { '@': './src' } },
  server: {
    host: '0.0.0.0',
    port: 3636,
    proxy: {
      '/api':    'http://localhost:8000',
      '/health': 'http://localhost:8000',
      '/ws':     { target: 'ws://localhost:8000', ws: true },
    },
  },
})
```

## Docker & Deployment

No changes. The `Dockerfile` and `nginx.conf` continue to work as-is. The build output remains static files in `dist/` served by nginx.
