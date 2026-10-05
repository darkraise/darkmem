import { apiFetch } from "@/lib/api"
import type { User } from "./types"

export interface AuthAdapter {
  login(input: { password: string }): Promise<void>
  logout(): Promise<void>
  me(): Promise<User | null>
}

export const authAdapter: AuthAdapter = {
  login: ({ password }) =>
    apiFetch<void>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ password }),
      // A 401 here is the verdict on the typed password, not a lost session.
      on401: "surface",
    }),
  logout: () => apiFetch<void>("/auth/logout", { method: "POST" }),
  me: () => apiFetch<User | null>("/auth/me", { method: "GET" }),
}
