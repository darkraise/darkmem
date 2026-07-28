import { useMutation, useQuery } from "@tanstack/react-query"
import { DEMO } from "@/demo/flag"
import { useDemoSecurity } from "@/demo/hooks"
import { apiFetch, ApiError } from "@/lib/api"

export interface ChangePasswordInput {
  currentPassword: string
  newPassword: string
}

/**
 * `T | null` fields have no real-mode source at all — no endpoint returns
 * them (verified against every route under `app/api/routes/`: `auth.py`,
 * `setup.py`, `config.py`, `system.py`). Rendered null and skipped by the
 * component (T1.45's precedent), never approximated (ruling 4). This is
 * true even for `trustProxyHeaders` (ruling 3's own example) and
 * `mcpAllowedHosts` — both are `app/config.py` settings with zero REST
 * read surface today.
 */
export interface SecurityTabBinding {
  isLoading: boolean
  blocklisted: number | null
  lockouts30d: number | null
  sessionSub: string | null
  sessionIssuedLabel: string | null
  sessionJti: string | null
  rateLimitIpSource: string
  rateLimitAttemptThreshold: number | null
  rateLimitLockoutWindow: string | null
  rateLimitJournaled: string | null
  cookieSecureValue: string | null
  cookieSecureNote: string
  /** null while the /setup/status probe is in flight — never defaulted to
   *  either true or false, since both are meaningfully different claims. */
  tofuClaimed: boolean | null
  tofuClaimedLabel: string | null
  tofuJournaled: string | null
  trustProxyHeaders: boolean | null
  mcpHosts: { host: string; wild?: boolean }[] | null
  changePassword: (input: ChangePasswordInput) => void
  changePasswordPending: boolean
  changePasswordError: string | null
  changePasswordSuccess: boolean
}

interface SetupStatusResponse {
  initialized: boolean
}

interface AuthMeResponse {
  authenticated: boolean
  sub: string
}

export function useSecurityTabBinding(): SecurityTabBinding {
  const demoSec = useDemoSecurity()

  const statusQuery = useQuery<SetupStatusResponse>({
    queryKey: ["setupStatus"],
    queryFn: () => apiFetch<SetupStatusResponse>("/setup/status"),
    enabled: !DEMO,
  })
  const meQuery = useQuery<AuthMeResponse>({
    queryKey: ["authMe"],
    queryFn: () => apiFetch<AuthMeResponse>("/auth/me"),
    enabled: !DEMO,
  })
  const changePasswordMutation = useMutation<
    { ok: boolean },
    Error,
    ChangePasswordInput
  >({
    mutationFn: (input) =>
      apiFetch<{ ok: boolean }>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify({
          current_password: input.currentPassword,
          new_password: input.newPassword,
        }),
      }),
  })

  if (DEMO) {
    return {
      isLoading: false,
      blocklisted: demoSec.blocklisted,
      lockouts30d: demoSec.lockouts_30d,
      sessionSub: "admin",
      sessionIssuedLabel: demoSec.session.issued_label,
      sessionJti: demoSec.session.jti,
      rateLimitIpSource: demoSec.rate_limit.ip_source,
      rateLimitAttemptThreshold: demoSec.rate_limit.attempt_threshold,
      rateLimitLockoutWindow: demoSec.rate_limit.lockout_window,
      rateLimitJournaled: demoSec.rate_limit.journaled,
      cookieSecureValue: demoSec.cookie_secure.value,
      cookieSecureNote: demoSec.cookie_secure.note,
      tofuClaimed: true,
      tofuClaimedLabel: demoSec.tofu.claimed_label,
      tofuJournaled: demoSec.tofu.journaled,
      trustProxyHeaders: true,
      mcpHosts: demoSec.mcp_hosts,
      changePassword: () => {},
      changePasswordPending: false,
      changePasswordError: null,
      changePasswordSuccess: false,
    }
  }

  return {
    isLoading: statusQuery.isLoading || meQuery.isLoading,
    blocklisted: null,
    lockouts30d: null,
    sessionSub: meQuery.data?.sub ?? null,
    sessionIssuedLabel: null,
    sessionJti: null,
    rateLimitIpSource:
      "X-Real-IP when trust_proxy_headers is on (the bundled-nginx posture) — the leftmost X-Forwarded-For is never trusted",
    rateLimitAttemptThreshold: null,
    rateLimitLockoutWindow: null,
    rateLimitJournaled: null,
    cookieSecureValue: null,
    cookieSecureNote:
      "Unset means Secure-only when environment=production; explicit false permits login over plain-HTTP LAN.",
    tofuClaimed: statusQuery.data?.initialized ?? null,
    tofuClaimedLabel: statusQuery.data
      ? statusQuery.data.initialized
        ? "claimed"
        : "not yet claimed"
      : null,
    tofuJournaled: null,
    trustProxyHeaders: null,
    mcpHosts: null,
    changePassword: (input) => changePasswordMutation.mutate(input),
    changePasswordPending: changePasswordMutation.isPending,
    changePasswordError:
      changePasswordMutation.error instanceof ApiError
        ? changePasswordMutation.error.message
        : changePasswordMutation.error?.message ?? null,
    changePasswordSuccess: changePasswordMutation.isSuccess,
  }
}
