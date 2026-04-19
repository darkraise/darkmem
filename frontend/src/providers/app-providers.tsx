import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { ThemeProvider } from "darkraise-ui/theme"
import { Toaster } from "darkraise-ui/components/sonner"
import { RouterAdapterProvider } from "darkraise-ui/router"
import { tanstackRouterAdapter } from "./router-adapter"

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
})

export function AppProviders({ children }: { children: React.ReactNode }) {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider
        config={{
          defaults: {
            accentColor: "lime",
            surfaceColor: "purple",
            surfaceStyle: "glassmorphism",
            backgroundStyle: "gradient",
            mode: "system",
            fontFamily: "default",
          },
          switcher: {
            enabled: true,
            axes: {
              accentColor: true,
              surfaceColor: true,
              surfaceStyle: true,
              backgroundStyle: true,
              mode: true,
              fontFamily: false,
            },
          },
        }}
      >
        <RouterAdapterProvider value={tanstackRouterAdapter}>
          {children}
          <Toaster position="bottom-right" richColors />
        </RouterAdapterProvider>
      </ThemeProvider>
    </QueryClientProvider>
  )
}
