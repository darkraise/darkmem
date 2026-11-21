import { useMutation } from "@tanstack/react-query"
import { apiFetch, ApiError } from "@/lib/api"
import { rotateSession } from "@/lib/session-renewal"

export interface ChangePasswordInput {
  currentPassword: string
  newPassword: string
}

export interface ChangePasswordState {
  change: (input: ChangePasswordInput) => void
  pending: boolean
  error: string | null
  success: boolean
  reset: () => void
}

/**
 * The admin password change, on its own rather than folded into the Security
 * tab's binding.
 *
 * It moved because the control did: the form is opened from the user menu, so
 * the layout route mounts it and must not have to pull in the tab's whole
 * posture binding — four queries for security-posture, /auth/me, /setup/status
 * and the key list — to render three password fields.
 */
export function useChangePassword(): ChangePasswordState {
  const mutation = useMutation<{ ok: boolean }, Error, ChangePasswordInput>({
    // A change rotates the session token like a refresh: the renewal is
    // recorded once the answer, and so the new cookie, has arrived, and the
    // new expiry is re-read from /auth/me.
    mutationFn: (input) =>
      rotateSession(() =>
        apiFetch<{ ok: boolean }>("/auth/change-password", {
          method: "POST",
          // A 401 here means the CURRENT password was wrong, not that the
          // session died. Under the default handling it signed the operator
          // out over a typo and discarded the server's own message.
          on401: "surface",
          body: JSON.stringify({
            current_password: input.currentPassword,
            new_password: input.newPassword,
          }),
        }),
      ),
  })

  return {
    change: (input) => mutation.mutate(input),
    pending: mutation.isPending,
    error:
      mutation.error instanceof ApiError
        ? mutation.error.message
        : (mutation.error?.message ?? null),
    success: mutation.isSuccess,
    reset: () => mutation.reset(),
  }
}
