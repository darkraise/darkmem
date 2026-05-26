import { create } from "zustand"
import { persist, createJSONStorage } from "zustand/middleware"

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  login: (token: string) => void
  setAuthenticated: (value: boolean) => void
  logout: () => void
}

function safeStorage(): Storage {
  try {
    const probe = "__darkmem_probe__"
    localStorage.setItem(probe, "1")
    localStorage.removeItem(probe)
    return localStorage
  } catch {
    return {
      length: 0,
      key: () => null,
      getItem: () => null,
      setItem: () => undefined,
      removeItem: () => undefined,
      clear: () => undefined,
    }
  }
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      isAuthenticated: false,

      login: (token: string) => {
        set({ token, isAuthenticated: true })
      },

      setAuthenticated: (value: boolean) => {
        set({ isAuthenticated: value })
      },

      logout: () => {
        set({ token: null, isAuthenticated: false })
      },
    }),
    {
      name: "darkmem-auth",
      storage: createJSONStorage(safeStorage),
    },
  ),
)
