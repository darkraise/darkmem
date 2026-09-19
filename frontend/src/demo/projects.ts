import type { ProjectSummary } from "@/hooks/api"

/** Busiest first, as `GET /projects` orders them. The counts mirror the demo
 *  store: 10 curated memories in `darkmem`, the 5000-row bulk fixture in
 *  `default`, and the curated knowledge fixtures in `acme-storefront`. */
export const DEMO_PROJECTS: ProjectSummary[] = [
  {
    name: "default",
    kind: "project",
    memory_count: 5000,
    document_count: 0,
    checkpoint_count: 0,
    page_count: 0,
    last_checkpoint_at: null,
    last_event_day: "2026-07-25",
  },
  {
    name: "darkmem",
    kind: "project",
    memory_count: 10,
    document_count: 12,
    checkpoint_count: 3,
    page_count: 0,
    last_checkpoint_at: "2026-07-24T14:10:00Z",
    last_event_day: "2026-07-25",
  },
  {
    name: "acme-storefront",
    kind: "project",
    memory_count: 0,
    document_count: 4,
    checkpoint_count: 0,
    page_count: 0,
    last_checkpoint_at: null,
    last_event_day: "2026-07-20",
  },
  {
    name: "notes",
    kind: "personal",
    memory_count: 0,
    document_count: 0,
    checkpoint_count: 0,
    page_count: 3,
    last_checkpoint_at: null,
    last_event_day: "2026-07-24",
  },
]
