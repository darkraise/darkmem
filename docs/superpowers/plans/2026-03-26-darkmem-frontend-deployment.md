# darkmem Frontend + Deployment — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a React dashboard with dark theme, knowledge graph visualization, and all admin pages, plus production Docker Compose and build scripts.

**Architecture:** Vite + React 18 + TypeScript SPA with shadcn/ui component library, Tailwind CSS 4, React Router for navigation, TanStack Query for data fetching, native WebSocket for live updates. Served by nginx in a Docker container. Production compose uses pre-built images from Docker Hub.

**Tech Stack:** React 18, TypeScript, Vite, Tailwind CSS 4, shadcn/ui, React Router, TanStack Query, Cytoscape.js, Recharts, plotly.js

---

## Prerequisites

- Plans 1-3 complete (backend fully functional, 59 tests passing)
- Node.js 20+ installed
- Backend API running on localhost:8000

---

## File Structure

```
frontend/
├── Dockerfile
├── nginx.conf
├── package.json
├── tsconfig.json
├── tsconfig.app.json
├── tsconfig.node.json
├── vite.config.ts
├── index.html
├── components.json                    # shadcn config
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── index.css                      # Tailwind imports
│   ├── lib/
│   │   ├── api.ts                     # API client
│   │   └── utils.ts                   # shadcn cn() utility
│   ├── hooks/
│   │   ├── useApi.ts                  # TanStack Query hooks
│   │   └── useWebSocket.ts
│   ├── components/
│   │   ├── ui/                        # shadcn components (auto-generated)
│   │   ├── Sidebar.tsx
│   │   ├── MemoryCard.tsx
│   │   └── ActivityFeed.tsx
│   └── pages/
│       ├── Overview.tsx
│       ├── Memories.tsx
│       ├── KnowledgeGraph.tsx
│       ├── VectorSpace.tsx
│       ├── Search.tsx
│       ├── Analytics.tsx
│       ├── ApiKeys.tsx
│       ├── LlmConfig.tsx
│       └── Settings.tsx
├── docker-compose.yml                 # Production
├── docker-compose.dev.yml             # Already exists — MODIFY
├── scripts/
│   └── build-push.sh
├── .env.example                       # Already exists — MODIFY
```

---

### Task 1: Frontend Scaffolding

**Files:**
- Create: `frontend/` project via Vite
- Create: `frontend/src/lib/utils.ts`
- Create: `frontend/src/index.css`

- [ ] **Step 1: Create Vite React TypeScript project**

```bash
cd D:/Repositories/_local_projects/darkmem
npm create vite@latest frontend -- --template react-ts
cd frontend
npm install
```

- [ ] **Step 2: Install dependencies**

```bash
cd D:/Repositories/_local_projects/darkmem/frontend
npm install react-router-dom @tanstack/react-query tailwindcss @tailwindcss/vite recharts cytoscape react-cytoscapejs plotly.js-dist-min react-plotly.js
npm install -D @types/react-cytoscapejs @types/react-plotly.js
```

- [ ] **Step 3: Configure Tailwind CSS 4 in `frontend/vite.config.ts`**

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";
import path from "path";

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      "/api": "http://localhost:8000",
      "/ws": { target: "ws://localhost:8000", ws: true },
    },
  },
});
```

- [ ] **Step 4: Create `frontend/src/index.css`**

```css
@import "tailwindcss";

@theme {
  --color-background: #0d1117;
  --color-foreground: #c9d1d9;
  --color-card: #161b22;
  --color-card-foreground: #c9d1d9;
  --color-primary: #58a6ff;
  --color-primary-foreground: #0d1117;
  --color-secondary: #21262d;
  --color-secondary-foreground: #c9d1d9;
  --color-muted: #161b22;
  --color-muted-foreground: #8b949e;
  --color-accent: #1f2937;
  --color-accent-foreground: #c9d1d9;
  --color-destructive: #f85149;
  --color-border: #21262d;
  --color-input: #21262d;
  --color-ring: #58a6ff;
  --radius: 0.5rem;
  --font-sans: "Inter", ui-sans-serif, system-ui, sans-serif;
  --font-mono: "JetBrains Mono", ui-monospace, monospace;
}

body {
  background-color: var(--color-background);
  color: var(--color-foreground);
  font-family: var(--font-sans);
}
```

- [ ] **Step 5: Create `frontend/src/lib/utils.ts`**

```typescript
import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

Install clsx and tailwind-merge:
```bash
cd frontend && npm install clsx tailwind-merge
```

- [ ] **Step 6: Initialize shadcn/ui**

```bash
cd D:/Repositories/_local_projects/darkmem/frontend
npx shadcn@latest init
```

When prompted, select: New York style, dark theme, CSS variables. If it asks about tailwind.config, follow prompts.

Then add needed components:
```bash
npx shadcn@latest add button card input table badge dialog select textarea tabs separator
```

- [ ] **Step 7: Create minimal `frontend/src/App.tsx`**

```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex h-screen bg-background text-foreground">
          <main className="flex-1 p-6 overflow-auto">
            <h1 className="text-2xl font-bold">darkmem</h1>
            <p className="text-muted-foreground mt-2">Dashboard coming soon</p>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
```

- [ ] **Step 8: Update `frontend/src/main.tsx`**

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
```

- [ ] **Step 9: Verify dev server starts**

```bash
cd D:/Repositories/_local_projects/darkmem/frontend && npm run dev
```

Open http://localhost:5173 — should show "darkmem" heading with dark background.

- [ ] **Step 10: Commit**

```bash
cd D:/Repositories/_local_projects/darkmem
git add frontend/
git commit -m "feat(ui): scaffold React frontend with Vite, Tailwind, shadcn"
```

---

### Task 2: API Client + Layout + Routing

**Files:**
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/hooks/useApi.ts`
- Create: `frontend/src/hooks/useWebSocket.ts`
- Create: `frontend/src/components/Sidebar.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create `frontend/src/lib/api.ts`**

```typescript
const API_BASE = "/api/v1";

let apiKey: string | null = localStorage.getItem("darkmem_api_key");

export function setApiKey(key: string) {
  apiKey = key;
  localStorage.setItem("darkmem_api_key", key);
}

export function getApiKey(): string | null {
  return apiKey;
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (apiKey) {
    headers["Authorization"] = `Bearer ${apiKey}`;
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(error.detail || `API error: ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json();
}
```

- [ ] **Step 2: Create `frontend/src/hooks/useApi.ts`**

```typescript
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "@/lib/api";

export interface Memory {
  id: string;
  content: string;
  source: string;
  source_agent: string | null;
  memory_type: string | null;
  importance: number;
  metadata: Record<string, unknown>;
  tags: string[];
  created_at: string;
  updated_at: string;
  expires_at: string | null;
  is_archived: boolean;
}

export interface Tag {
  id: number;
  name: string;
  category: string | null;
  memory_count: number;
}

export interface Stats {
  memories: number;
  tags: number;
  entities: number | null;
  relationships: number | null;
  sources: string[];
}

export function useMemories() {
  return useQuery<Memory[]>({
    queryKey: ["memories"],
    queryFn: () => apiFetch("/memories/search", { method: "POST", body: JSON.stringify({ limit: 50 }) }),
  });
}

export function useMemory(id: string) {
  return useQuery<Memory>({
    queryKey: ["memory", id],
    queryFn: () => apiFetch(`/memories/${id}`),
    enabled: !!id,
  });
}

export function useCreateMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { content: string; tags?: string[]; source?: string }) =>
      apiFetch<Memory>("/memories", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["memories"] }),
  });
}

export function useDeleteMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch(`/memories/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["memories"] }),
  });
}

export function useSearchMemories() {
  return useMutation({
    mutationFn: (params: { query?: string; tags_any?: string[]; limit?: number }) =>
      apiFetch<Memory[]>("/memories/search", { method: "POST", body: JSON.stringify(params) }),
  });
}

export function useTags() {
  return useQuery<Tag[]>({ queryKey: ["tags"], queryFn: () => apiFetch("/tags") });
}

export function useStats() {
  return useQuery<Stats>({ queryKey: ["stats"], queryFn: () => apiFetch("/analytics/stats") });
}

export function useApiKeys() {
  return useQuery({ queryKey: ["apiKeys"], queryFn: () => apiFetch<any[]>("/keys") });
}

export function useCreateApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (data: { name: string; scopes?: string[] }) =>
      apiFetch("/keys", { method: "POST", body: JSON.stringify(data) }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apiKeys"] }),
  });
}

export function useDeleteApiKey() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => apiFetch(`/keys/${id}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["apiKeys"] }),
  });
}

export function useLlmConfig() {
  return useQuery({ queryKey: ["llmConfig"], queryFn: () => apiFetch("/config/llm") });
}

export function useSystemPrompts() {
  return useQuery({ queryKey: ["systemPrompts"], queryFn: () => apiFetch<any[]>("/config/system-prompt/list") });
}

export function useGraphEntities(type?: string) {
  return useQuery({
    queryKey: ["graphEntities", type],
    queryFn: () => apiFetch(`/graph/entities${type ? `?entity_type=${type}` : ""}`),
  });
}

export function useReason() {
  return useMutation({
    mutationFn: (data: { question: string; limit?: number }) =>
      apiFetch<{ answer: string; sources: any[] }>("/memories/reason", { method: "POST", body: JSON.stringify(data) }),
  });
}
```

- [ ] **Step 3: Create `frontend/src/hooks/useWebSocket.ts`**

```typescript
import { useEffect, useRef, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";

export function useWebSocket() {
  const ws = useRef<WebSocket | null>(null);
  const qc = useQueryClient();

  const connect = useCallback(() => {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const url = `${protocol}//${window.location.host}/ws`;
    ws.current = new WebSocket(url);

    ws.current.onmessage = (event) => {
      const msg = JSON.parse(event.data);
      if (msg.event?.startsWith("memory.") || msg.event?.startsWith("pipeline.")) {
        qc.invalidateQueries({ queryKey: ["memories"] });
        qc.invalidateQueries({ queryKey: ["stats"] });
        qc.invalidateQueries({ queryKey: ["tags"] });
      }
    };

    ws.current.onclose = () => {
      setTimeout(connect, 3000);
    };
  }, [qc]);

  useEffect(() => {
    connect();
    return () => ws.current?.close();
  }, [connect]);
}
```

- [ ] **Step 4: Create `frontend/src/components/Sidebar.tsx`**

```tsx
import { NavLink } from "react-router-dom";

const navItems = [
  { to: "/", label: "Overview", icon: "⊞" },
  { to: "/memories", label: "Memories", icon: "◉" },
  { to: "/graph", label: "Knowledge Graph", icon: "◎" },
  { to: "/vectors", label: "Vector Space", icon: "◈" },
  { to: "/search", label: "Search", icon: "⊕" },
  null,
  { to: "/analytics", label: "Analytics", icon: "▤" },
  { to: "/keys", label: "API Keys", icon: "⊡" },
  { to: "/llm", label: "LLM Config", icon: "⊙" },
  { to: "/settings", label: "Settings", icon: "⊛" },
];

export function Sidebar() {
  return (
    <aside className="w-56 bg-card border-r border-border flex flex-col shrink-0">
      <div className="p-4 border-b border-border">
        <span className="text-lg font-bold font-mono text-foreground">darkmem</span>
      </div>
      <nav className="flex-1 py-2">
        {navItems.map((item, i) =>
          item === null ? (
            <div key={i} className="border-t border-border my-2" />
          ) : (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-2 text-sm transition-colors ${
                  isActive
                    ? "text-primary bg-accent border-l-2 border-primary"
                    : "text-muted-foreground hover:text-foreground hover:bg-accent"
                }`
              }
            >
              <span className="text-base">{item.icon}</span>
              {item.label}
            </NavLink>
          )
        )}
      </nav>
    </aside>
  );
}
```

- [ ] **Step 5: Update `frontend/src/App.tsx`**

```tsx
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Sidebar } from "@/components/Sidebar";
import { useWebSocket } from "@/hooks/useWebSocket";
import Overview from "@/pages/Overview";
import Memories from "@/pages/Memories";
import KnowledgeGraph from "@/pages/KnowledgeGraph";
import VectorSpace from "@/pages/VectorSpace";
import Search from "@/pages/Search";
import Analytics from "@/pages/Analytics";
import ApiKeys from "@/pages/ApiKeys";
import LlmConfig from "@/pages/LlmConfig";
import Settings from "@/pages/Settings";

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, refetchOnWindowFocus: false } },
});

function AppContent() {
  useWebSocket();
  return (
    <div className="flex h-screen bg-background text-foreground">
      <Sidebar />
      <main className="flex-1 overflow-auto p-6">
        <Routes>
          <Route path="/" element={<Overview />} />
          <Route path="/memories" element={<Memories />} />
          <Route path="/graph" element={<KnowledgeGraph />} />
          <Route path="/vectors" element={<VectorSpace />} />
          <Route path="/search" element={<Search />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/keys" element={<ApiKeys />} />
          <Route path="/llm" element={<LlmConfig />} />
          <Route path="/settings" element={<Settings />} />
        </Routes>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppContent />
      </BrowserRouter>
    </QueryClientProvider>
  );
}
```

- [ ] **Step 6: Create placeholder pages**

Create each page file so the app compiles. Each file follows this pattern — the implementer will fill them in subsequent tasks:

Create `frontend/src/pages/Overview.tsx`, `Memories.tsx`, `KnowledgeGraph.tsx`, `VectorSpace.tsx`, `Search.tsx`, `Analytics.tsx`, `ApiKeys.tsx`, `LlmConfig.tsx`, `Settings.tsx` — each with:

```tsx
export default function PageName() {
  return <div><h2 className="text-xl font-semibold">Page Name</h2></div>;
}
```

(Replace `PageName` with each page's actual name.)

- [ ] **Step 7: Verify app compiles and renders**

```bash
cd D:/Repositories/_local_projects/darkmem/frontend && npm run dev
```

Open http://localhost:5173 — should show sidebar navigation and placeholder pages.

- [ ] **Step 8: Commit**

```bash
git add frontend/
git commit -m "feat(ui): add layout, routing, API client, and WebSocket hooks"
```

---

### Task 3: Overview + Memories + Search Pages

**Files:**
- Create: `frontend/src/components/MemoryCard.tsx`
- Modify: `frontend/src/pages/Overview.tsx`
- Modify: `frontend/src/pages/Memories.tsx`
- Modify: `frontend/src/pages/Search.tsx`

- [ ] **Step 1: Create `frontend/src/components/MemoryCard.tsx`**

```tsx
import type { Memory } from "@/hooks/useApi";

export function MemoryCard({ memory, onDelete }: { memory: Memory; onDelete?: (id: string) => void }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <p className="text-sm text-foreground">{memory.content}</p>
      <div className="flex items-center gap-2 mt-3 flex-wrap">
        {memory.tags.map((tag) => (
          <span key={tag} className="text-xs px-2 py-0.5 rounded bg-accent text-primary">{tag}</span>
        ))}
      </div>
      <div className="flex items-center justify-between mt-3 text-xs text-muted-foreground">
        <div className="flex items-center gap-3">
          <span>{memory.source}</span>
          {memory.memory_type && <span>{memory.memory_type}</span>}
          <span>{new Date(memory.created_at).toLocaleString()}</span>
        </div>
        {onDelete && (
          <button onClick={() => onDelete(memory.id)} className="text-destructive hover:underline">delete</button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Implement `frontend/src/pages/Overview.tsx`**

```tsx
import { useStats, useMemories } from "@/hooks/useApi";
import { MemoryCard } from "@/components/MemoryCard";

function StatCard({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-xs uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="text-3xl font-bold mt-1">{value}</div>
      {sub && <div className="text-xs text-muted-foreground mt-1">{sub}</div>}
    </div>
  );
}

export default function Overview() {
  const { data: stats } = useStats();
  const { data: memories } = useMemories();

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Overview</h2>
      <div className="grid grid-cols-4 gap-4 mb-6">
        <StatCard label="Memories" value={stats?.memories ?? "—"} />
        <StatCard label="Tags" value={stats?.tags ?? "—"} />
        <StatCard label="Entities" value={stats?.entities ?? "—"} />
        <StatCard label="Relations" value={stats?.relationships ?? "—"} />
      </div>
      <h3 className="text-lg font-medium mb-3">Recent Memories</h3>
      <div className="space-y-3">
        {memories?.slice(0, 10).map((m) => <MemoryCard key={m.id} memory={m} />)}
        {!memories?.length && <p className="text-muted-foreground">No memories yet.</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Implement `frontend/src/pages/Memories.tsx`**

```tsx
import { useState } from "react";
import { useMemories, useDeleteMemory, useCreateMemory } from "@/hooks/useApi";
import { MemoryCard } from "@/components/MemoryCard";

export default function Memories() {
  const { data: memories, isLoading } = useMemories();
  const deleteMemory = useDeleteMemory();
  const createMemory = useCreateMemory();
  const [showCreate, setShowCreate] = useState(false);
  const [content, setContent] = useState("");
  const [tags, setTags] = useState("");

  const handleCreate = () => {
    if (!content.trim()) return;
    createMemory.mutate(
      { content, tags: tags.split(",").map((t) => t.trim()).filter(Boolean), source: "dashboard" },
      { onSuccess: () => { setContent(""); setTags(""); setShowCreate(false); } }
    );
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold">Memories</h2>
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm hover:opacity-90"
        >
          {showCreate ? "Cancel" : "New Memory"}
        </button>
      </div>
      {showCreate && (
        <div className="bg-card border border-border rounded-lg p-4 mb-4 space-y-3">
          <textarea
            value={content} onChange={(e) => setContent(e.target.value)}
            placeholder="Memory content..." rows={3}
            className="w-full bg-background border border-border rounded p-2 text-sm text-foreground resize-none"
          />
          <input
            value={tags} onChange={(e) => setTags(e.target.value)}
            placeholder="Tags (comma-separated)"
            className="w-full bg-background border border-border rounded p-2 text-sm text-foreground"
          />
          <button onClick={handleCreate} className="px-3 py-1.5 bg-primary text-primary-foreground rounded text-sm">Save</button>
        </div>
      )}
      {isLoading && <p className="text-muted-foreground">Loading...</p>}
      <div className="space-y-3">
        {memories?.map((m) => (
          <MemoryCard key={m.id} memory={m} onDelete={(id) => deleteMemory.mutate(id)} />
        ))}
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Implement `frontend/src/pages/Search.tsx`**

```tsx
import { useState } from "react";
import { useSearchMemories, useReason } from "@/hooks/useApi";
import { MemoryCard } from "@/components/MemoryCard";

export default function Search() {
  const [query, setQuery] = useState("");
  const search = useSearchMemories();
  const reason = useReason();
  const [mode, setMode] = useState<"search" | "reason">("search");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!query.trim()) return;
    if (mode === "search") {
      search.mutate({ query, limit: 20 });
    } else {
      reason.mutate({ question: query, limit: 10 });
    }
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Search</h2>
      <form onSubmit={handleSubmit} className="flex gap-2 mb-4">
        <input
          value={query} onChange={(e) => setQuery(e.target.value)}
          placeholder={mode === "search" ? "Search memories..." : "Ask a question..."}
          className="flex-1 bg-background border border-border rounded px-3 py-2 text-sm text-foreground"
        />
        <select value={mode} onChange={(e) => setMode(e.target.value as "search" | "reason")}
          className="bg-background border border-border rounded px-3 py-2 text-sm text-foreground">
          <option value="search">Search</option>
          <option value="reason">Reason</option>
        </select>
        <button type="submit" className="px-4 py-2 bg-primary text-primary-foreground rounded text-sm">Go</button>
      </form>
      {mode === "reason" && reason.data && (
        <div className="bg-card border border-border rounded-lg p-4 mb-4">
          <h3 className="text-sm font-medium mb-2">Answer</h3>
          <p className="text-sm text-foreground whitespace-pre-wrap">{reason.data.answer}</p>
          {reason.data.sources.length > 0 && (
            <div className="mt-3 pt-3 border-t border-border">
              <span className="text-xs text-muted-foreground">{reason.data.sources.length} sources used</span>
            </div>
          )}
        </div>
      )}
      <div className="space-y-3">
        {search.data?.map((m) => <MemoryCard key={m.id} memory={m} />)}
      </div>
    </div>
  );
}
```

- [ ] **Step 5: Verify pages render**

```bash
cd frontend && npm run dev
```

Navigate to Overview, Memories, Search pages — should render correctly (with or without API data).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/
git commit -m "feat(ui): add Overview, Memories, and Search pages"
```

---

### Task 4: Knowledge Graph + Vector Space + Analytics Pages

**Files:**
- Modify: `frontend/src/pages/KnowledgeGraph.tsx`
- Modify: `frontend/src/pages/VectorSpace.tsx`
- Modify: `frontend/src/pages/Analytics.tsx`

- [ ] **Step 1: Implement `frontend/src/pages/KnowledgeGraph.tsx`**

```tsx
import { useGraphEntities } from "@/hooks/useApi";
import CytoscapeComponent from "react-cytoscapejs";
import { useState, useMemo } from "react";

export default function KnowledgeGraph() {
  const { data: entities, isLoading } = useGraphEntities();
  const [selected, setSelected] = useState<any>(null);

  const elements = useMemo(() => {
    if (!entities || !Array.isArray(entities)) return [];
    const nodes = entities.map((e: any) => ({
      data: { id: e.id || e.name, label: e.name, type: e.entity_type },
    }));
    return nodes;
  }, [entities]);

  const typeColors: Record<string, string> = {
    person: "#58a6ff", service: "#3fb950", project: "#d2a8ff",
    technology: "#ffa657", concept: "#8b949e", organization: "#f778ba",
  };

  const stylesheet = [
    {
      selector: "node",
      style: {
        label: "data(label)",
        "background-color": "#21262d",
        color: "#c9d1d9",
        "text-valign": "bottom" as const,
        "text-margin-y": 5,
        "font-size": 10,
        width: 30,
        height: 30,
        "border-width": 2,
        "border-color": "#58a6ff",
      },
    },
    {
      selector: "edge",
      style: {
        width: 1,
        "line-color": "#30363d",
        "curve-style": "bezier" as const,
      },
    },
  ];

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Knowledge Graph</h2>
      {isLoading && <p className="text-muted-foreground">Loading graph...</p>}
      {!isLoading && elements.length === 0 && (
        <p className="text-muted-foreground">No entities in the knowledge graph yet. Create memories with the pipeline running to populate it.</p>
      )}
      {elements.length > 0 && (
        <div className="bg-card border border-border rounded-lg overflow-hidden" style={{ height: "70vh" }}>
          <CytoscapeComponent
            elements={elements}
            stylesheet={stylesheet}
            layout={{ name: "cose", animate: true }}
            style={{ width: "100%", height: "100%" }}
            cy={(cy) => {
              cy.on("tap", "node", (evt) => {
                const data = evt.target.data();
                setSelected(data);
              });
            }}
          />
        </div>
      )}
      {selected && (
        <div className="mt-4 bg-card border border-border rounded-lg p-4">
          <h3 className="font-medium">{selected.label}</h3>
          <p className="text-sm text-muted-foreground">{selected.type}</p>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 2: Implement `frontend/src/pages/VectorSpace.tsx`**

```tsx
import { useMemories } from "@/hooks/useApi";

export default function VectorSpace() {
  const { data: memories } = useMemories();

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Vector Space</h2>
      <p className="text-muted-foreground mb-4">
        2D/3D projection of memory embeddings. Requires running the pipeline with an embedding model.
      </p>
      <div className="bg-card border border-border rounded-lg p-6 text-center" style={{ height: "60vh" }}>
        <div className="flex items-center justify-center h-full">
          <div>
            <p className="text-muted-foreground text-lg">Vector visualization</p>
            <p className="text-muted-foreground text-sm mt-2">
              {memories?.length ?? 0} memories indexed.
              UMAP/t-SNE projection will be available when embedding data is accessible via API.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Implement `frontend/src/pages/Analytics.tsx`**

```tsx
import { useStats, useTags } from "@/hooks/useApi";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, PieChart, Pie, Cell } from "recharts";

const COLORS = ["#58a6ff", "#3fb950", "#d2a8ff", "#ffa657", "#f778ba", "#8b949e"];

export default function Analytics() {
  const { data: stats } = useStats();
  const { data: tags } = useTags();

  const tagData = tags?.slice(0, 10).map((t) => ({ name: t.name, count: t.memory_count })) ?? [];
  const sourceData = stats?.sources.map((s, i) => ({ name: s, value: 1 })) ?? [];

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Analytics</h2>
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-card border border-border rounded-lg p-4">
          <h3 className="text-sm font-medium mb-4">Top Tags by Memory Count</h3>
          {tagData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={tagData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#21262d" />
                <XAxis dataKey="name" tick={{ fill: "#8b949e", fontSize: 10 }} angle={-45} textAnchor="end" height={80} />
                <YAxis tick={{ fill: "#8b949e" }} />
                <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #21262d", color: "#c9d1d9" }} />
                <Bar dataKey="count" fill="#58a6ff" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="text-muted-foreground text-sm">No tag data yet.</p>}
        </div>
        <div className="bg-card border border-border rounded-lg p-4">
          <h3 className="text-sm font-medium mb-4">Sources</h3>
          {sourceData.length > 0 ? (
            <ResponsiveContainer width="100%" height={300}>
              <PieChart>
                <Pie data={sourceData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={100} label={(e) => e.name}>
                  {sourceData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                </Pie>
                <Tooltip contentStyle={{ background: "#161b22", border: "1px solid #21262d", color: "#c9d1d9" }} />
              </PieChart>
            </ResponsiveContainer>
          ) : <p className="text-muted-foreground text-sm">No source data yet.</p>}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Verify and commit**

```bash
cd frontend && npm run build
git add frontend/src/pages/
git commit -m "feat(ui): add Knowledge Graph, Vector Space, and Analytics pages"
```

---

### Task 5: API Keys + LLM Config + Settings Pages

**Files:**
- Modify: `frontend/src/pages/ApiKeys.tsx`
- Modify: `frontend/src/pages/LlmConfig.tsx`
- Modify: `frontend/src/pages/Settings.tsx`

- [ ] **Step 1: Implement `frontend/src/pages/ApiKeys.tsx`**

```tsx
import { useState } from "react";
import { useApiKeys, useCreateApiKey, useDeleteApiKey } from "@/hooks/useApi";
import { setApiKey } from "@/lib/api";

export default function ApiKeys() {
  const { data: keys, isLoading } = useApiKeys();
  const createKey = useCreateApiKey();
  const deleteKey = useDeleteApiKey();
  const [name, setName] = useState("");
  const [newKey, setNewKey] = useState<string | null>(null);

  const handleCreate = () => {
    if (!name.trim()) return;
    createKey.mutate({ name, scopes: ["read", "write", "admin"] }, {
      onSuccess: (data: any) => {
        setNewKey(data.raw_key);
        setName("");
      },
    });
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">API Keys</h2>
      <div className="bg-card border border-border rounded-lg p-4 mb-4">
        <h3 className="text-sm font-medium mb-3">Create New Key</h3>
        <div className="flex gap-2">
          <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Key name"
            className="flex-1 bg-background border border-border rounded px-3 py-2 text-sm" />
          <button onClick={handleCreate} className="px-4 py-2 bg-primary text-primary-foreground rounded text-sm">Create</button>
        </div>
        {newKey && (
          <div className="mt-3 p-3 bg-accent rounded border border-border">
            <p className="text-xs text-muted-foreground mb-1">Copy this key — it won't be shown again:</p>
            <code className="text-sm text-primary font-mono break-all">{newKey}</code>
            <button onClick={() => { setApiKey(newKey); setNewKey(null); }}
              className="block mt-2 text-xs text-primary hover:underline">Use as current key</button>
          </div>
        )}
      </div>
      <div className="bg-card border border-border rounded-lg overflow-hidden">
        <table className="w-full text-sm">
          <thead><tr className="border-b border-border text-muted-foreground">
            <th className="text-left p-3">Name</th><th className="text-left p-3">Scopes</th>
            <th className="text-left p-3">Created</th><th className="text-left p-3">Last Used</th><th className="p-3" />
          </tr></thead>
          <tbody>
            {keys?.map((k: any) => (
              <tr key={k.id} className="border-b border-border">
                <td className="p-3">{k.name}</td>
                <td className="p-3">{k.scopes?.join(", ")}</td>
                <td className="p-3 text-muted-foreground">{new Date(k.created_at).toLocaleDateString()}</td>
                <td className="p-3 text-muted-foreground">{k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : "—"}</td>
                <td className="p-3"><button onClick={() => deleteKey.mutate(k.id)} className="text-destructive text-xs hover:underline">Delete</button></td>
              </tr>
            ))}
          </tbody>
        </table>
        {isLoading && <p className="p-3 text-muted-foreground">Loading...</p>}
        {!isLoading && !keys?.length && <p className="p-3 text-muted-foreground">No API keys.</p>}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Implement `frontend/src/pages/LlmConfig.tsx`**

```tsx
import { useLlmConfig } from "@/hooks/useApi";

function PurposeCard({ title, config }: { title: string; config: any }) {
  if (!config) return null;
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <h3 className="text-sm font-medium mb-3 capitalize">{title}</h3>
      <div className="space-y-2 text-sm">
        <div className="flex justify-between"><span className="text-muted-foreground">Provider</span><span>{config.provider}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">Model</span><span className="font-mono">{config.model}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">Base URL</span><span className="font-mono text-xs">{config.base_url}</span></div>
        <div className="flex justify-between"><span className="text-muted-foreground">API Key</span><span>{config.api_key ?? "none"}</span></div>
        {config.dimensions && <div className="flex justify-between"><span className="text-muted-foreground">Dimensions</span><span>{config.dimensions}</span></div>}
        {Object.keys(config.params || {}).length > 0 && (
          <div><span className="text-muted-foreground">Params</span><pre className="mt-1 text-xs bg-background p-2 rounded">{JSON.stringify(config.params, null, 2)}</pre></div>
        )}
      </div>
    </div>
  );
}

export default function LlmConfig() {
  const { data, isLoading } = useLlmConfig();

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">LLM Configuration</h2>
      {isLoading && <p className="text-muted-foreground">Loading...</p>}
      <div className="grid grid-cols-2 gap-4">
        <PurposeCard title="Embedding" config={data?.embedding} />
        <PurposeCard title="Extraction" config={data?.extraction} />
        <PurposeCard title="Reasoning" config={data?.reasoning} />
        <PurposeCard title="Summarization" config={data?.summarization} />
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Implement `frontend/src/pages/Settings.tsx`**

```tsx
import { useState, useEffect } from "react";
import { useSystemPrompts } from "@/hooks/useApi";
import { getApiKey, setApiKey } from "@/lib/api";

export default function Settings() {
  const { data: prompts } = useSystemPrompts();
  const [key, setKey] = useState(getApiKey() ?? "");
  const [saved, setSaved] = useState(false);

  const handleSaveKey = () => {
    setApiKey(key);
    setSaved(true);
    setTimeout(() => setSaved(false), 2000);
  };

  return (
    <div>
      <h2 className="text-xl font-semibold mb-4">Settings</h2>
      <div className="bg-card border border-border rounded-lg p-4 mb-6">
        <h3 className="text-sm font-medium mb-3">API Key</h3>
        <div className="flex gap-2">
          <input value={key} onChange={(e) => setKey(e.target.value)} placeholder="dm_..."
            className="flex-1 bg-background border border-border rounded px-3 py-2 text-sm font-mono" type="password" />
          <button onClick={handleSaveKey} className="px-4 py-2 bg-primary text-primary-foreground rounded text-sm">
            {saved ? "Saved!" : "Save"}
          </button>
        </div>
        <p className="text-xs text-muted-foreground mt-2">Set the API key used for dashboard requests.</p>
      </div>
      <div className="bg-card border border-border rounded-lg p-4">
        <h3 className="text-sm font-medium mb-3">System Prompt Profiles</h3>
        <div className="space-y-3">
          {prompts?.map((p: any) => (
            <div key={p.name} className="border border-border rounded p-3">
              <div className="flex items-center gap-2">
                <span className="font-medium text-sm">{p.display_name}</span>
                <span className="text-xs px-2 py-0.5 rounded bg-accent text-muted-foreground">{p.name}</span>
                {p.is_default && <span className="text-xs text-primary">default</span>}
              </div>
              <p className="text-xs text-muted-foreground mt-1">Extraction: {p.extraction_depth}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 4: Build and verify**

```bash
cd frontend && npm run build
```

Expected: Build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/pages/
git commit -m "feat(ui): add API Keys, LLM Config, and Settings pages"
```

---

### Task 6: Production Docker Compose + Build Scripts

**Files:**
- Create: `frontend/Dockerfile`
- Create: `frontend/nginx.conf`
- Create: `docker-compose.yml` (production)
- Create: `scripts/build-push.sh`
- Modify: `docker-compose.dev.yml`

- [ ] **Step 1: Create `frontend/nginx.conf`**

```nginx
server {
    listen 80;
    root /usr/share/nginx/html;
    index index.html;

    location /api/ {
        proxy_pass http://darkmem-api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /ws {
        proxy_pass http://darkmem-api:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    location /mcp {
        proxy_pass http://darkmem-api:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location / {
        try_files $uri $uri/ /index.html;
    }
}
```

- [ ] **Step 2: Create `frontend/Dockerfile`**

```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
```

- [ ] **Step 3: Create `docker-compose.yml` (production)**

```yaml
services:
  darkmem-api:
    image: darkraise/darkmem-api:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://darkmem:${DB_PASSWORD:-darkmem}@postgres:5432/darkmem
      - QDRANT_URL=http://qdrant:6333
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD:-darkmem123}
    depends_on:
      postgres:
        condition: service_healthy
      qdrant:
        condition: service_started
      neo4j:
        condition: service_healthy
    restart: unless-stopped

  darkmem-ui:
    image: darkraise/darkmem-ui:latest
    ports:
      - "3000:80"
    depends_on:
      - darkmem-api
    restart: unless-stopped

  postgres:
    image: postgres:17-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=darkmem
      - POSTGRES_USER=darkmem
      - POSTGRES_PASSWORD=${DB_PASSWORD:-darkmem}
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "darkmem"]
      interval: 5s
      timeout: 3s
      retries: 5
    restart: unless-stopped

  qdrant:
    image: qdrant/qdrant:latest
    volumes:
      - qdrant_data:/qdrant/storage
    restart: unless-stopped

  neo4j:
    image: neo4j:5-community
    volumes:
      - neo4j_data:/data
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD:-darkmem123}
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:7474 || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
  qdrant_data:
  neo4j_data:
```

- [ ] **Step 4: Create `scripts/build-push.sh`**

```bash
#!/usr/bin/env bash
set -euo pipefail

REGISTRY="darkraise"
VERSION="${1:-latest}"
GIT_SHA=$(git rev-parse --short HEAD 2>/dev/null || echo "unknown")

echo "Building darkmem images..."
echo "  Version: $VERSION"
echo "  Git SHA: $GIT_SHA"

# Build API
echo "Building darkmem-api..."
docker build -t "${REGISTRY}/darkmem-api:${VERSION}" \
             -t "${REGISTRY}/darkmem-api:${GIT_SHA}" \
             -t "${REGISTRY}/darkmem-api:latest" \
             ./backend

# Build UI
echo "Building darkmem-ui..."
docker build -t "${REGISTRY}/darkmem-ui:${VERSION}" \
             -t "${REGISTRY}/darkmem-ui:${GIT_SHA}" \
             -t "${REGISTRY}/darkmem-ui:latest" \
             ./frontend

# Push
echo "Pushing images..."
for img in darkmem-api darkmem-ui; do
  docker push "${REGISTRY}/${img}:latest"
  docker push "${REGISTRY}/${img}:${GIT_SHA}"
  if [ "$VERSION" != "latest" ]; then
    docker push "${REGISTRY}/${img}:${VERSION}"
  fi
done

echo "Done! Images pushed:"
echo "  ${REGISTRY}/darkmem-api:${VERSION} (${GIT_SHA})"
echo "  ${REGISTRY}/darkmem-ui:${VERSION} (${GIT_SHA})"
```

```bash
chmod +x scripts/build-push.sh
```

- [ ] **Step 5: Add `frontend/` to dev compose for hot-reload**

Add to `docker-compose.dev.yml` services:

```yaml
  darkmem-ui:
    build: ./frontend
    ports:
      - "3000:80"
    depends_on:
      - darkmem-api
```

- [ ] **Step 6: Verify frontend Docker build**

```bash
cd D:/Repositories/_local_projects/darkmem
docker build -t darkmem-ui-test ./frontend
```

Expected: Build succeeds.

- [ ] **Step 7: Commit**

```bash
git add frontend/Dockerfile frontend/nginx.conf docker-compose.yml docker-compose.dev.yml scripts/
git commit -m "feat: add production Docker Compose and build scripts"
```

---

## Verification

After all tasks, the full system should work:

1. **Dev mode:** `npm run dev` in frontend/ + `uvicorn` in backend/ — full SPA with hot reload
2. **Compose dev:** `docker compose -f docker-compose.dev.yml up -d` — all containers
3. **Compose prod:** `docker compose up -d` — pulls from Docker Hub (after build-push)
4. **Frontend pages:** Overview, Memories, Knowledge Graph, Vector Space, Search, Analytics, API Keys, LLM Config, Settings
5. **Backend tests:** `cd backend && pytest -v` — 59 tests pass
6. **Frontend build:** `cd frontend && npm run build` — no errors
