import { createFileRoute, useRouter } from "@tanstack/react-router"
import { LoginCard } from "@/features/auth/components/login-card"

export const Route = createFileRoute("/_guest/login")({
  component: LoginPage,
})

function LoginPage() {
  const router = useRouter()
  return <LoginCard onSuccess={() => router.navigate({ to: "/" })} />
}
