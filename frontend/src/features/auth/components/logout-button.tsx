import { useRouter } from "@tanstack/react-router"
import { Button } from "darkraise-ui/components/button"
import { useLogout } from "../hooks/useLogout"

export function LogoutButton() {
  const logout = useLogout()
  const router = useRouter()
  return (
    <Button
      variant="ghost"
      onClick={async () => {
        await logout()
        router.navigate({ to: "/login" })
      }}
    >
      Sign out
    </Button>
  )
}
