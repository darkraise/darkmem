import { apiFetch } from "@/lib/api"

export interface AuthAdapter {
  login(input: { password: string }): Promise<void>
}

export const authAdapter: AuthAdapter = {
  login: ({ password }) =>
    apiFetch<void>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ password }),
      // A 401 here is the verdict on the typed password, not a lost session.
      on401: "surface",
    }),
}
