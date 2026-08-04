import { useAuthStore } from "@/features/auth"

const API_BASE = "/api/v1"

// Guards a 401 burst (background queries can fire many at once) so a single
// expired session triggers exactly one logout + redirect instead of N
// full-page reloads. Reset once we're on /login so a later re-login works.
let handling401 = false

function handleUnauthorized() {
  useAuthStore.getState().logout()
  if (handling401) return
  handling401 = true
  // Router beforeLoad guards redirect on the next navigation once the store
  // flips, but a user idle on a page triggers none — fall back to a single
  // location change, skipped if we're already on /login to avoid a loop.
  if (window.location.pathname !== "/login") {
    window.location.href = "/login"
  } else {
    handling401 = false
  }
}

// Carries the HTTP status alongside the message so a caller that needs to
// tell a contractual status apart from a generic failure (e.g. the job
// board's 409-on-held-lock, which must render as "busy", never as an error)
// can do it without parsing the message string.
export class ApiError extends Error {
  status: number
  // `error.details` from the app's ErrorEnvelope (app/schemas/envelope.py),
  // populated only when the backend's `detail` was a list — e.g. the dream
  // digest's 409 body, whose per-action blocked reasons live nowhere else on
  // the wire (app/main.py flattens a list `detail` to `error.details`, never
  // to the top-level `detail` string). Absent on every other error shape.
  details?: unknown[]

  constructor(message: string, status: number, details?: unknown[]) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.details = details
  }
}

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers,
    credentials: "include",
  })
  if (response.status === 401) {
    handleUnauthorized()
    throw new ApiError("Unauthorized", 401)
  }
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }))
    const body = error as { detail?: string; error?: { details?: unknown[] } }
    throw new ApiError(
      body.detail || `API error: ${response.status}`,
      response.status,
      body.error?.details,
    )
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function checkSetupStatus(): Promise<{ initialized: boolean }> {
  const response = await fetch(`${API_BASE}/setup/status`, {
    credentials: "include",
  })
  return response.json()
}

export async function checkAuth(): Promise<boolean> {
  try {
    const response = await fetch(`${API_BASE}/auth/me`, {
      credentials: "include",
    })
    return response.ok
  } catch {
    return false
  }
}

export async function login(password: string): Promise<void> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
    credentials: "include",
  })
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }))
    throw new Error((error as { detail?: string }).detail || "Login failed")
  }
  useAuthStore.getState().setAuthenticated(true)
}

export async function logout(): Promise<void> {
  try {
    await fetch(`${API_BASE}/auth/logout`, {
      method: "POST",
      credentials: "include",
    })
  } catch {
    // Best-effort — clear client state regardless
  }
  useAuthStore.getState().logout()
}
