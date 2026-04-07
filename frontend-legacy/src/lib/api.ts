const API_BASE = "/api/v1";

let authToken: string | null = localStorage.getItem("darkmem_token");

export function setAuthToken(token: string) {
  authToken = token;
  localStorage.setItem("darkmem_token", token);
}

export function getAuthToken(): string | null {
  return authToken;
}

export function clearAuthToken() {
  authToken = null;
  localStorage.removeItem("darkmem_token");
}

export function isAuthenticated(): boolean {
  return localStorage.getItem("darkmem_token") !== null;
}

export async function checkSetupStatus(): Promise<{ initialized: boolean }> {
  const response = await fetch(`${API_BASE}/auth/status`);
  return response.json();
}

export async function login(password: string): Promise<string> {
  const response = await fetch(`${API_BASE}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error((error as { detail?: string }).detail || "Login failed");
  }
  const data = await response.json();
  setAuthToken(data.token);
  return data.token;
}

export async function setup(password: string): Promise<string> {
  const response = await fetch(`${API_BASE}/auth/setup`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ password }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error((error as { detail?: string }).detail || "Setup failed");
  }
  const data = await response.json();
  setAuthToken(data.token);
  return data.token;
}

export async function apiFetch<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  if (authToken) {
    headers["Authorization"] = `Bearer ${authToken}`;
  }

  const response = await fetch(`${API_BASE}${path}`, { ...options, headers });
  if (response.status === 401) {
    clearAuthToken();
    window.location.reload();
    return undefined as T;
  }
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error((error as { detail?: string }).detail || `API error: ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
