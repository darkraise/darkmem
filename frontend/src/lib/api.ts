import { useAuthStore } from "@/features/auth"

const API_BASE = "/api/v1"

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
    useAuthStore.getState().logout()
    window.location.href = "/login"
    throw new Error("Unauthorized")
  }
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }))
    throw new Error(
      (error as { detail?: string }).detail || `API error: ${response.status}`,
    )
  }
  if (response.status === 204) return undefined as T
  return response.json() as Promise<T>
}

export async function checkSetupStatus(): Promise<{ initialized: boolean }> {
  const response = await fetch(`${API_BASE}/auth/status`, {
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

export async function setup(password: string): Promise<void> {
  const response = await fetch(`${API_BASE}/auth/setup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
    credentials: "include",
  })
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }))
    throw new Error((error as { detail?: string }).detail || "Setup failed")
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
