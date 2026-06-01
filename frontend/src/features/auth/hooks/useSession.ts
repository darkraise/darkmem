import { useAuthStore } from "../store"

export function useSession() {
  return useAuthStore((s) => ({
    isAuthenticated: s.isAuthenticated,
  }))
}
