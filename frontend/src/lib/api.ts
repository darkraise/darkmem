import { useAuthStore } from "@/features/auth"
import { endSession, mayRetryAfterRenewal } from "@/lib/session-renewal"

const API_BASE = "/api/v1"

/** A 401 burst (background queries can fire many at once) ends the session
 *  once: `endSession` signs out and navigates to sign-in a single time. */
export function handleUnauthorized() {
  endSession()
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
  // `error.code` from the ErrorEnvelope: the generic status name
  // (`not_found`, `conflict`) or a door's own reason (the board's
  // `hash_conflict`, `note_required`). Absent when the body was not an
  // envelope.
  code?: string
  // `error.candidates` on a 409 `symbol_ambiguous`: the symbols a key matched.
  candidates?: unknown[]

  constructor(
    message: string,
    status: number,
    details?: unknown[],
    code?: string,
    candidates?: unknown[],
  ) {
    super(message)
    this.name = "ApiError"
    this.status = status
    this.details = details
    this.code = code
    this.candidates = candidates
  }
}

interface ErrorBody {
  detail?: unknown
  error?: {
    message?: unknown
    details?: unknown[]
    code?: string
    candidates?: unknown[]
  }
}

function errorMessage(body: ErrorBody | null | undefined, status: number): string {
  const message = body?.error?.message
  if (typeof message === "string" && message) return message
  if (typeof body?.detail === "string" && body.detail) return body.detail
  return `API error: ${status}`
}

export interface ApiFetchOptions extends RequestInit {
  /** What a 401 from this endpoint means.
   *
   *  `"redirect"` (the default) is right almost everywhere: a 401 says the
   *  session is gone, so the app signs out and sends the caller to /login.
   *
   *  `"surface"` is for the endpoints where a 401 is the *answer to what was
   *  submitted* and says nothing about the session: `POST /auth/login`
   *  (401 for a wrong password) and `POST /auth/change-password` (401 for a
   *  wrong CURRENT password). Under the default the change-password form
   *  signed the operator out over a typo, and the login form showed a bare
   *  "Unauthorized" — both threw away the server's own message. With
   *  `"surface"` the response falls through to the normal error path, so the
   *  caller gets the real message (and a signed-in caller stays signed in). */
  on401?: "redirect" | "surface"
}

/** The one request implementation. `apiFetch` is the body-only view of it;
 *  a caller that needs a response header — today only the page block delete,
 *  whose 204 carries the page's new `content_hash` — takes this one. */
export function apiFetchWithHeaders<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<{ data: T; headers: Headers }> {
  return request<T>(path, options, false)
}

async function request<T>(
  path: string,
  options: ApiFetchOptions,
  retried: boolean,
): Promise<{ data: T; headers: Headers }> {
  const { on401 = "redirect", ...init } = options
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(init.headers as Record<string, string>),
  }

  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers,
    credentials: "include",
  })
  if (response.status === 401 && on401 === "redirect") {
    // Sent with the cookie a rotation was replacing: once more with the new.
    if (!retried && (await mayRetryAfterRenewal())) return request<T>(path, options, true)
    handleUnauthorized()
    throw new ApiError("Unauthorized", 401)
  }
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }))
    const body = (error ?? {}) as ErrorBody
    throw new ApiError(
      errorMessage(body, response.status),
      response.status,
      body.error?.details,
      body.error?.code,
      body.error?.candidates,
    )
  }
  if (response.status === 204) {
    return { data: undefined as T, headers: response.headers }
  }
  return { data: (await response.json()) as T, headers: response.headers }
}

export async function apiFetch<T>(
  path: string,
  options: ApiFetchOptions = {},
): Promise<T> {
  return (await apiFetchWithHeaders<T>(path, options)).data
}

export interface ApiUploadOptions {
  headers?: Record<string, string>
  /** Fraction of the body sent, 0 to 1. Fires only while the length is known. */
  onProgress?: (fraction: number) => void
  signal?: AbortSignal
}

/** `apiFetch` for a request whose upload progress matters.
 *
 *  XHR rather than `fetch` for one reason: `fetch` reports no upload progress,
 *  and an import body can be hundreds of megabytes. Everything else here
 *  mirrors `apiFetchWithHeaders` deliberately — the base path, the credentials,
 *  the 401 handling and the `ApiError` shape — so a caller cannot tell the two
 *  transports apart from its error handling.
 */
export function apiUpload<T>(
  path: string,
  body: Blob,
  options: ApiUploadOptions = {},
): Promise<T> {
  const { headers = {}, onProgress, signal } = options
  return new Promise<T>((resolve, reject) => {
    // An already-aborted signal fires no "abort" event, so the listener below
    // would never run and the body would go out anyway.
    if (signal?.aborted) {
      reject(new ApiError("The upload was cancelled", 0))
      return
    }
    const xhr = new XMLHttpRequest()
    xhr.open("POST", `${API_BASE}${path}`)
    xhr.withCredentials = true
    for (const [key, value] of Object.entries(headers)) {
      xhr.setRequestHeader(key, value)
    }

    if (onProgress) {
      xhr.upload.onprogress = (event: ProgressEvent) => {
        if (event.lengthComputable && event.total > 0) {
          onProgress(event.loaded / event.total)
        }
      }
    }

    const onAbort = () => xhr.abort()
    signal?.addEventListener("abort", onAbort)
    const done = () => signal?.removeEventListener("abort", onAbort)

    xhr.onload = () => {
      done()
      if (xhr.status === 401) {
        handleUnauthorized()
        reject(new ApiError("Unauthorized", 401))
        return
      }
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(
            (xhr.responseText ? JSON.parse(xhr.responseText) : undefined) as T,
          )
        } catch {
          reject(
            new ApiError("The server sent a malformed response", xhr.status),
          )
        }
        return
      }
      let message = `API error: ${xhr.status}`
      let details: unknown[] | undefined
      let code: string | undefined
      try {
        const parsed = JSON.parse(xhr.responseText) as ErrorBody
        message = errorMessage(parsed, xhr.status)
        details = parsed.error?.details
        code = parsed.error?.code
      } catch {
        // A non-JSON body (an nginx page, an empty 502) keeps the status text.
      }
      reject(new ApiError(message, xhr.status, details, code))
    }
    xhr.onerror = () => {
      done()
      reject(new ApiError("The upload could not reach the server", 0))
    }
    xhr.onabort = () => {
      done()
      reject(new ApiError("The upload was cancelled", 0))
    }
    xhr.send(body)
  })
}

/** Throws on any answer but a 2xx: an error body carries no `initialized`,
 *  which read as false and put an initialized instance into the wizard. */
export async function checkSetupStatus(): Promise<{ initialized: boolean }> {
  const response = await fetch(`${API_BASE}/setup/status`, {
    credentials: "include",
  })
  if (!response.ok) {
    throw new ApiError(`Setup status answered ${response.status}`, response.status)
  }
  return response.json()
}

/** Whether the session cookie still signs in: `false` only when the server
 *  says so (401/403). `null` means the check could not tell -- the request was
 *  aborted by a navigation, the network blipped or the server erred -- and is
 *  not a sign-out: treating it as one logged out valid sessions. */
export async function checkAuth(): Promise<boolean | null> {
  try {
    const response = await fetch(`${API_BASE}/auth/me`, {
      credentials: "include",
    })
    if (response.ok) return true
    if (response.status === 401 || response.status === 403) return false
    return null
  } catch {
    return null
  }
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
