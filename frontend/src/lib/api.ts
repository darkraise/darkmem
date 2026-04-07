import { useAuthStore } from "@/features/auth"

const API_BASE = "/api/v1"

export async function apiFetch<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = useAuthStore.getState().token
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }
  if (token) {
    headers["Authorization"] = `Bearer ${token}`
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (response.status === 401) {
    useAuthStore.getState().logout()
    window.location.href = "/login"
    return undefined as T
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

export function getAuthToken(): string | null {
  return useAuthStore.getState().token
}

export async function checkSetupStatus(): Promise<{ initialized: boolean }> {
  const response = await fetch(`${API_BASE}/auth/status`)
  return response.json()
}

export async function login(password: string): Promise<string> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  })
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }))
    throw new Error((error as { detail?: string }).detail || "Login failed")
  }
  const data = await response.json()
  useAuthStore.getState().setToken(data.token)
  return data.token
}

export async function setup(password: string): Promise<string> {
  const response = await fetch(`${API_BASE}/auth/setup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  })
  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: response.statusText }))
    throw new Error((error as { detail?: string }).detail || "Setup failed")
  }
  const data = await response.json()
  useAuthStore.getState().setToken(data.token)
  return data.token
}
