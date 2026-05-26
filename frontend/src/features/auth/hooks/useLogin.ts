import { useMutation } from "@tanstack/react-query"
import { authAdapter } from "../adapter"
import { useAuthStore } from "../store"
import type { LoginInput } from "../schemas"

export function useLogin() {
  const setAuthenticated = useAuthStore((s) => s.setAuthenticated)
  return useMutation({
    mutationFn: (input: LoginInput) =>
      authAdapter.login({ password: input.password }),
    onSuccess: () => setAuthenticated(true),
  })
}
