import { createFileRoute, redirect, useRouter, type ErrorComponentProps } from "@tanstack/react-router"
import { Button } from "darkraise-ui/components/button"
import { EmptyState } from "@/components/darkmem"
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
  errorComponent: SetupStatusFailed,
})

function SetupStatusFailed({ error, reset }: ErrorComponentProps) {
  const router = useRouter()
  return (
    <EmptyState
      kind="failed"
      scope="page"
      title="Setup status could not be read"
      description={error instanceof Error ? error.message : undefined}
      action={
        <Button
          onClick={() => {
            reset()
            void router.invalidate()
          }}
        >
          Retry
        </Button>
      }
    />
  )
}

function SetupPage() {
  const router = useRouter()
  if (DEMO) {
    return <DemoSetupWizard onFinish={() => router.navigate({ to: "/" })} />
  }
  return <SetupWizard />
}
