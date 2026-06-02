import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
import { useAuthStore } from "@/features/auth"
import { checkSetupStatus } from "@/lib/api"
import { ParticleBackground } from "@/components/particle-background"

export const Route = createFileRoute("/_guest")({
  beforeLoad: async ({ location }) => {
    if (useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: "/" })
    }
    if (location.pathname === "/setup") {
      return
    }
    const { initialized } = await checkSetupStatus()
    if (!initialized) {
      throw redirect({ to: "/setup" })
    }
  },
  component: () => (
    <div className="bg-background relative isolate flex min-h-screen items-center justify-center px-4">
      <ParticleBackground />
      <Outlet />
    </div>
  ),
})
