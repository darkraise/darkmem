import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ThemeProvider } from "darkraise-ui/theme"
import { Toaster } from "darkraise-ui/components/sonner"
import { RouterAdapterProvider } from "darkraise-ui/router"
import {
  FloatingPanelProvider,
  FloatingPanelHost,
} from "darkraise-ui/components/floating-panel"
import { tanstackRouterAdapter } from "./router-adapter"
import { themeConfig } from "@/theme.config"
import { themePersistence } from "@/lib/theme-persistence"

const queryClient = new QueryClient({
  defaultOptions: {
    // Freshness comes from the WebSocket + explicit mutation invalidations, so a
    // window refocus shouldn't refetch every mounted query (notably the
    // expensive GET /code/graph/:id). Opt specific queries back in if needed.
    queries: { staleTime: 60 * 1000, retry: 1, refetchOnWindowFocus: false },
  },
})

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider config={themeConfig} persistence={themePersistence}>
        <RouterAdapterProvider value={tanstackRouterAdapter}>
          <FloatingPanelProvider>
            {children}
            <FloatingPanelHost />
            <Toaster />
          </FloatingPanelProvider>
        </RouterAdapterProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
