import type {
  CompareResponse,
  LoginResponse,
  MetaResponse,
  SessionResponse,
} from "./types";

export const API_BASE = "http://127.0.0.1:8000";

/**
 * The demonstration token is kept in `sessionStorage` so it lives only as long as
 * the browser tab.  Nothing is written to `localStorage` and no cookie is used.
 */
const TOKEN_STORAGE_KEY = "traceguard.demo.session.token";

export const SIGNED_OUT_EVENT = "traceguard:signed-out";

export class ApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

export function getToken(): string | null {
  try {
    return window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
  } catch {
    return null;
  }
}

export function setToken(token: string | null): void {
  try {
    if (token) window.sessionStorage.setItem(TOKEN_STORAGE_KEY, token);
    else window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
  } catch {
    /* storage disabled - the session simply will not survive a reload */
  }
}

export function clearToken(): void {
  setToken(null);
}

function extractMessage(body: string, fallback: string): string {
  try {
    const parsed = JSON.parse(body);
    if (typeof parsed?.detail === "string") return parsed.detail;
    if (Array.isArray(parsed?.detail) && parsed.detail.length) {
      const first = parsed.detail[0];
      if (typeof first?.msg === "string") return first.msg;
    }
  } catch {
    /* not JSON - fall through */
  }
  return fallback;
}

export async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...((init?.headers as Record<string, string>) || {}),
  };
  const token = getToken();
  if (token) headers.Authorization = `Bearer ${token}`;

  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, { ...init, headers });
  } catch {
    throw new ApiError(
      0,
      `Cannot reach the backend at ${API_BASE}. Start FastAPI with "python -m uvicorn backend.app.main:app --port 8000".`,
    );
  }

  if (!response.ok) {
    const body = await response.text();
    if (response.status === 401 && token) {
      clearToken();
      window.dispatchEvent(new CustomEvent(SIGNED_OUT_EVENT));
    }
    throw new ApiError(response.status, extractMessage(body, `${response.status} ${response.statusText}`));
  }

  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

export async function login(email: string, password: string): Promise<LoginResponse> {
  const result = await apiFetch<LoginResponse>("/api/v1/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
  setToken(result.access_token);
  return result;
}

export async function restoreSession(): Promise<SessionResponse> {
  return apiFetch<SessionResponse>("/api/v1/auth/session");
}

export async function logout(): Promise<void> {
  try {
    await apiFetch("/api/v1/auth/logout", { method: "POST" });
  } catch {
    /* the local session is cleared regardless of the server response */
  } finally {
    clearToken();
  }
}

export async function fetchMeta(): Promise<MetaResponse> {
  return apiFetch<MetaResponse>("/api/v1/meta");
}

export async function fetchModelInfo(): Promise<{ engine_version: string; engine_type: string; model_type: string; data_mode: string; training_version: string; metrics: any; methodology_principle: string }> {
  return apiFetch("/api/v1/model/info");
}

export async function compareEngines(recordId: number): Promise<CompareResponse> {
  return apiFetch<CompareResponse>(`/api/v1/analysis/compare/${recordId}`);
}
