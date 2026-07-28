import { createFileRoute, redirect, useRouter } from "@tanstack/react-router"
import { DEMO } from "@/lib/demo-flag"
import { DemoSetupWizard } from "@/features/setup/components/demo-setup-wizard"
import { SetupWizard } from "@/features/setup/components/SetupWizard"

export const Route = createFileRoute("/_guest/setup")({
  beforeLoad: async () => {
    if (DEMO) return
    const { checkSetupStatus } = await import("@/lib/api")
    const { initialized } = await checkSetupStatus()
    if (initialized) {
      throw redirect({ to: "/login" })
    }
  },
  component: SetupPage,
})

function SetupPage() {
  const router = useRouter()
  if (DEMO) {
    return <DemoSetupWizard onFinish={() => router.navigate({ to: "/" })} />
  }
  return <SetupWizard />
}
