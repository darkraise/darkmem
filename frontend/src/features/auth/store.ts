import { create } from "zustand"

interface AuthState {
  token: string | null
  isAuthenticated: boolean
  setToken: (token: string) => void
  logout: () => void
}

const STORAGE_KEY = "darkmem_token"

const getStoredToken = () => {
  try {
    return localStorage.getItem(STORAGE_KEY)
  } catch {
    return null
  }
}

export const useAuthStore = create<AuthState>((set) => ({
  token: getStoredToken(),
  isAuthenticated: !!getStoredToken(),

  setToken: (token: string) => {
    localStorage.setItem(STORAGE_KEY, token)
    set({ token, isAuthenticated: true })
  },

  logout: () => {
    localStorage.removeItem(STORAGE_KEY)
    set({ token: null, isAuthenticated: false })
  },
}))
