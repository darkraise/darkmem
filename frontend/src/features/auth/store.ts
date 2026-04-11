import { create } from "zustand"
import { persist, createJSONStorage } from "zustand/middleware"

interface AuthState {
  isAuthenticated: boolean
  setAuthenticated: (value: boolean) => void
  logout: () => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      isAuthenticated: false,

      setAuthenticated: (value: boolean) => {
        set({ isAuthenticated: value })
      },

      logout: () => {
        set({ isAuthenticated: false })
      },
    }),
    {
      name: "darkmem-auth",
      storage: createJSONStorage(() => localStorage),
    },
  ),
)
