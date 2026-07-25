import { createFileRoute, redirect } from "@tanstack/react-router"

// /code is no longer a page: each former tab is a dedicated route. Bare
// visits land on Repositories; legacy ?tab= URLs map to their new route,
// carrying the repo param where the target still reads it.
const TAB_ROUTES = {
  repositories: "/code/repositories",
  graph: "/code/graph",
  wiki: "/code/wiki",
} as const

type CodeTab = keyof typeof TAB_ROUTES

export const Route = createFileRoute("/_authenticated/code")({
  validateSearch: (search: Record<string, unknown>) => ({
    tab:
      typeof search.tab === "string" && search.tab in TAB_ROUTES
        ? (search.tab as CodeTab)
        : undefined,
    repo: typeof search.repo === "string" ? search.repo : undefined,
  }),
  beforeLoad: ({ search }) => {
    const tab = search.tab ?? "repositories"
    if (tab === "repositories") {
      throw redirect({ to: TAB_ROUTES.repositories })
    }
    throw redirect({ to: TAB_ROUTES[tab], search: { repo: search.repo } })
  },
})
