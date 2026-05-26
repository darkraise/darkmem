import { useQueryClient } from "@tanstack/react-query"
import { authAdapter } from "../adapter"
import { useAuthStore } from "../store"

export function useLogout() {
  const qc = useQueryClient()
  const clear = useAuthStore((s) => s.logout)
  return async () => {
    try {
      await authAdapter.logout()
    } catch {
      // server may already have invalidated the session
    }
    clear()
    qc.clear()
  }
}
