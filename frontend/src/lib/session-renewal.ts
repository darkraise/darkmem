import { useAuthStore } from "@/features/auth"
import { DEMO } from "@/lib/demo-flag"

/** When the last rotation landed, in this tab or another (the `storage`
 *  event carries it across). Written only once the rotation's response, and
 *  so the new cookie, has arrived. */
export const RENEWED_AT_KEY = "darkmem.session.renewed_at"
/** A 401, an expired-close or a refused handshake this soon after a renewal
 *  is a request that raced the cookie swap, not a dead session. */
export const RENEWAL_WINDOW_MS = 10_000
export const RENEW_WITHIN_MS = 60 * 60_000
export const CHECK_EVERY_MS = 60_000

const API_BASE = "/api/v1"

let started = false
let ended = false
let signIn: (() => void) | null = null
let expiresAt: number | null = null
let renewedAt = 0
let rotation: Promise<boolean> | null = null
let timer: ReturnType<typeof setInterval> | null = null
const listeners = new Set<() => void>()

class RefusedRenewal extends Error {}

function storedRenewal(): number {
  try {
    const value = Number(localStorage.getItem(RENEWED_AT_KEY))
    return Number.isFinite(value) ? value : 0
  } catch {
    return 0
  }
}

function setExpiry(iso: string | undefined) {
  const at = iso ? Date.parse(iso) : NaN
  if (Number.isFinite(at)) expiresAt = at
}

function notify() {
  for (const listener of [...listeners]) listener()
}

async function readExpiry(): Promise<void> {
  try {
    const response = await fetch(`${API_BASE}/auth/me`, { credentials: "include" })
    if (!response.ok) return
    const body = (await response.json()) as { expires_at?: string }
    setExpiry(body.expires_at)
  } catch {
    // The next check reads again.
  }
}

/** The renewal recorder: refresh and change-password both call it once their
 *  response has arrived. */
export function recordRenewal(): void {
  renewedAt = Date.now()
  try {
    localStorage.setItem(RENEWED_AT_KEY, String(renewedAt))
  } catch {
    // Private mode or a full quota: this tab still knows.
  }
  notify()
}

/** Runs a call that rotates the session token. While it is in flight a 401
 *  waits for it; on success the renewal is recorded and the new expiry
 *  stored, from the answer when it carries one, else from `/auth/me`. */
export function rotateSession<T>(
  call: () => Promise<T>,
  expiryOf?: (answer: T) => string | undefined,
): Promise<T> {
  const done = call().then((answer) => {
    const iso = expiryOf?.(answer)
    setExpiry(iso)
    recordRenewal()
    if (!iso) void readExpiry()
    return answer
  })
  const tracked = done.then(
    () => true,
    () => false,
  )
  rotation = tracked
  void tracked.then(() => {
    if (rotation === tracked) rotation = null
  })
  return done
}

/** Whether a request refused as unauthorized should be sent once more: a
 *  rotation is in flight and lands, or one landed within the window. */
export async function mayRetryAfterRenewal(): Promise<boolean> {
  if (rotation) return rotation
  return recentlyRenewed()
}

export function recentlyRenewed(now = Date.now()): boolean {
  const last = Math.max(renewedAt, storedRenewal())
  return last > 0 && now - last >= 0 && now - last <= RENEWAL_WINDOW_MS
}

/** Calls `listener` on each recorded renewal, own or another tab's. */
export function onRenewal(listener: () => void): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

async function renew(): Promise<void> {
  try {
    await rotateSession(
      async () => {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: "POST",
          credentials: "include",
        })
        if (response.status === 401) throw new RefusedRenewal()
        if (!response.ok) throw new Error(`refresh answered ${response.status}`)
        return (await response.json()) as { expires_at?: string }
      },
      (answer) => answer.expires_at,
    )
  } catch (error) {
    if (error instanceof RefusedRenewal) endSession()
    // Anything else (the network, a 5xx) is retried by the next check.
  }
}

export async function checkSession(): Promise<void> {
  if (!started || ended || rotation) return
  if (expiresAt === null) {
    // An earlier read failed or has not answered: read again, or this tab
    // would never renew.
    await readExpiry()
    if (expiresAt === null || ended || rotation) return
  }
  const left = expiresAt - Date.now()
  if (left <= 0) {
    endSession()
    return
  }
  if (left <= RENEW_WITHIN_MS) await renew()
}

function onVisible() {
  if (document.visibilityState === "visible") void checkSession()
}

function onStorage(event: StorageEvent) {
  if (event.key !== RENEWED_AT_KEY || !event.newValue) return
  const at = Number(event.newValue)
  if (!Number.isFinite(at) || at <= renewedAt) return
  renewedAt = at
  // Unknown until the re-read answers, so no check renews meanwhile.
  expiresAt = null
  notify()
  void readExpiry()
}

/** Starts the minute check, the visibility check and the cross-tab record,
 *  from the authenticated layout. `navigateToSignIn` is a router navigation,
 *  so module state (the notes draft registry) survives an ended session. */
export function startSessionRenewal(navigateToSignIn: () => void): () => void {
  if (DEMO) return () => {}
  signIn = navigateToSignIn
  ended = false
  if (!started) {
    started = true
    timer = setInterval(() => void checkSession(), CHECK_EVERY_MS)
    document.addEventListener("visibilitychange", onVisible)
    window.addEventListener("storage", onStorage)
    void readExpiry().then(() => checkSession())
  }
  return stopSessionRenewal
}

export function stopSessionRenewal(): void {
  if (timer !== null) clearInterval(timer)
  timer = null
  document.removeEventListener("visibilitychange", onVisible)
  window.removeEventListener("storage", onStorage)
  started = false
  expiresAt = null
}

/** Signs out once: the store, the timers, then the sign-in page. */
export function endSession(): void {
  useAuthStore.getState().logout()
  if (ended) return
  ended = true
  const navigate = signIn
  stopSessionRenewal()
  if (navigate) {
    navigate()
  } else if (window.location.pathname !== "/login") {
    // Outside the authenticated layout no router navigation is registered.
    const back = window.location.pathname + window.location.search
    window.location.href = `/login?redirect=${encodeURIComponent(back)}`
  } else {
    ended = false
  }
}

export function sessionExpiresAt(): number | null {
  return expiresAt
}

/** Test hook. */
export function resetSessionRenewal(): void {
  stopSessionRenewal()
  ended = false
  signIn = null
  renewedAt = 0
  rotation = null
  listeners.clear()
}
