import { createFileRoute, Outlet, redirect } from "@tanstack/react-router"
import { useAuthStore } from "@/features/auth"
import { DEMO } from "@/lib/demo-flag"
import { ParticleBackground } from "@/components/particle-background"
import { readPrimaryParticleColors } from "@/lib/primary-palette"

export const Route = createFileRoute("/_guest")({
  beforeLoad: async ({ location }) => {
    // Demo mode: no backend to ask about setup status, and the auth guard is
    // off — both guest screens stay reachable as viewable preview surfaces.
    if (DEMO) return
    if (useAuthStore.getState().isAuthenticated) {
      throw redirect({ to: "/" })
    }
    if (location.pathname === "/setup") {
      return
    }
    const { checkSetupStatus } = await import("@/lib/api")
    const { initialized } = await checkSetupStatus()
    if (!initialized) {
      throw redirect({ to: "/setup" })
    }
  },
  component: () => (
    <div className="bg-background relative isolate flex min-h-screen items-center justify-center px-4">
      <ParticleBackground gradient={false} colors={readPrimaryParticleColors()} />
      <Outlet />
    </div>
  ),
})
