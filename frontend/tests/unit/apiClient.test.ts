import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  ApiError,
  SIGNED_OUT_EVENT,
  apiFetch,
  clearToken,
  getToken,
  login,
  logout,
  setToken,
} from "../../src/api/client";

function jsonResponse(body: unknown, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 200 ? "OK" : "Error",
    json: async () => body,
    text: async () => JSON.stringify(body),
  } as unknown as Response;
}

describe("api client", () => {
  beforeEach(() => {
    clearToken();
  });

  it("sends the bearer token on protected requests", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);
    setToken("token-123");

    await apiFetch("/api/v1/dashboard/summary");

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toContain("/api/v1/dashboard/summary");
    expect((init?.headers as Record<string, string>).Authorization).toBe("Bearer token-123");
  });

  it("omits the authorization header when there is no session", async () => {
    const fetchMock = vi.fn(async (_url: string, _init?: RequestInit) => jsonResponse({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await apiFetch("/api/v1/meta");

    const [, init] = fetchMock.mock.calls[0];
    expect((init?.headers as Record<string, string>).Authorization).toBeUndefined();
  });

  it("clears the session and announces a sign-out on 401", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ detail: "Invalid session." }, 401)));
    setToken("token-123");

    const events: string[] = [];
    window.addEventListener(SIGNED_OUT_EVENT, () => events.push("signed-out"));

    await expect(apiFetch("/api/v1/records")).rejects.toBeInstanceOf(ApiError);
    expect(getToken()).toBeNull();
    expect(events).toContain("signed-out");
  });

  it("surfaces the backend error detail", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ detail: "Record not found" }, 404)));

    await expect(apiFetch("/api/v1/records/999999")).rejects.toThrow("Record not found");
  });

  it("stores the token returned by a successful login", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        jsonResponse({
          access_token: "issued-token",
          token_type: "bearer",
          expires_at: "2026-10-22T20:00:00+00:00",
          expires_in_minutes: 480,
          user: { email: "demo@traceguard.local", role: "demonstration operator" },
        }),
      ),
    );

    const result = await login("demo@traceguard.local", "Demo@123");

    expect(result.access_token).toBe("issued-token");
    expect(getToken()).toBe("issued-token");
  });

  it("clears the token on logout even when the request fails", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => jsonResponse({ detail: "boom" }, 500)));
    setToken("token-123");

    await logout();

    expect(getToken()).toBeNull();
  });
});
