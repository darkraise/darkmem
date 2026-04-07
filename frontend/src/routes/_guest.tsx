import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
import { useAuthStore } from "@/features/auth"
import { checkSetupStatus } from "@/lib/api"

export const Route = createFileRoute("/_guest")({
  beforeLoad: async () => {
    if (useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: "/" })
    }
    try {
      const { initialized } = await checkSetupStatus()
      if (!initialized) {
        throw redirect({ to: "/setup" })
      }
    } catch (e) {
      if (e instanceof Error && "to" in (e as Record<string, unknown>)) throw e
    }
  },
  component: () => (
    <div className="flex min-h-screen items-center justify-center bg-background">
      <Outlet />
    </div>
  ),
})
