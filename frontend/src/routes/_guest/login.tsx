import { createFileRoute, useRouter } from "@tanstack/react-router"
import { LoginCard } from "@/features/auth/components/login-card"
import { safeRedirect } from "@/features/auth/safe-redirect"

export const Route = createFileRoute("/_guest/login")({
  validateSearch: (search: Record<string, unknown>): { redirect?: string } => {
    const redirect = safeRedirect(search.redirect)
    return redirect ? { redirect } : {}
  },
  component: LoginPage,
})

function LoginPage() {
  const router = useRouter()
  const { redirect } = Route.useSearch()
  return (
    <LoginCard
      onSuccess={() =>
        redirect ? router.history.push(redirect) : router.navigate({ to: "/" })
      }
    />
  )
}
