import { createFileRoute, redirect } from "@tanstack/react-router"
import { checkSetupStatus } from "@/lib/api"
import { SetupWizard } from "@/components/setup/SetupWizard"

export const Route = createFileRoute("/_guest/setup")({
  beforeLoad: async () => {
    const { initialized } = await checkSetupStatus()
    if (initialized) {
      throw redirect({ to: "/login" })
    }
  },
  component: SetupWizard,
})
