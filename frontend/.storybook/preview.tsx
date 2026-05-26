import type { Preview } from "@storybook/react"
import React from "react"
import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import {
  createRouter,
  createRootRoute,
  createMemoryHistory,
  RouterProvider,
  Outlet,
} from "@tanstack/react-router"
import { ThemeProvider } from "darkraise-ui/theme"
import { RouterAdapterProvider } from "darkraise-ui/router"
import { tanstackRouterAdapter } from "../src/providers/router-adapter"
import { themeConfig } from "../src/theme.config"
import "../src/styles/globals.css"

const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } })

const rootRoute = createRootRoute({ component: () => <Outlet /> })
const router = createRouter({
  routeTree: rootRoute,
  history: createMemoryHistory({ initialEntries: ["/"] }),
})

const preview: Preview = {
  decorators: [
    (Story) => (
      <QueryClientProvider client={queryClient}>
        <ThemeProvider config={themeConfig}>
          <RouterAdapterProvider value={tanstackRouterAdapter}>
            <RouterProvider router={router} />
            <Story />
          </RouterAdapterProvider>
        </ThemeProvider>
      </QueryClientProvider>
    ),
  ],
}

export default preview
