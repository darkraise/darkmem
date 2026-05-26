import { useAuthStore } from "../store"

export function useSession() {
  return useAuthStore((s) => ({
    token: s.token,
    isAuthenticated: s.isAuthenticated,
  }))
}
