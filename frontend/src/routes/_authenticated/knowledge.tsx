import { createFileRoute, redirect } from "@tanstack/react-router"

// /knowledge is no longer a page: each former tab is a dedicated route.
// Bare visits land on Facts; legacy ?tab= URLs map to their new route.
const TAB_ROUTES = {
  facts: "/knowledge/facts",
  articles: "/knowledge/articles",
  topics: "/knowledge/topics",
  review: "/knowledge/review",
} as const

type KnowledgeTab = keyof typeof TAB_ROUTES

export const Route = createFileRoute("/_authenticated/knowledge")({
  validateSearch: (search: Record<string, unknown>) => ({
    tab:
      typeof search.tab === "string" && search.tab in TAB_ROUTES
        ? (search.tab as KnowledgeTab)
        : undefined,
  }),
  beforeLoad: ({ search }) => {
    throw redirect({ to: TAB_ROUTES[search.tab ?? "facts"] })
  },
})
