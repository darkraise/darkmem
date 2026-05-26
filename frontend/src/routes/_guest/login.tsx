import { createFileRoute, useRouter } from "@tanstack/react-router"
import { PageHeader } from "darkraise-ui/layout"
import { LoginForm } from "@/features/auth"

export const Route = createFileRoute("/_guest/login")({
  component: LoginPage,
})

function LoginPage() {
  const router = useRouter()
  return (
    <div className="mx-auto mt-24 max-w-md">
      <PageHeader title="darkmem" description="Sign in to continue." />
      <LoginForm onSuccess={() => router.navigate({ to: "/" })} />
    </div>
  )
}
