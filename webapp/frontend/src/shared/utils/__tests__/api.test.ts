import { describe, it, expect, afterEach, beforeEach, vi } from "vitest";

const setupModule = async () => {
  vi.resetModules();
  vi.stubEnv("VITE_API_BASE_URL", "https://api.example.com");
  const mod = await import("@/shared/utils/api");
  return mod;
};

describe("apiFetch", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.unstubAllEnvs();
    global.fetch = originalFetch;
    vi.useRealTimers();
  });

  it("returns JSON response on success", async () => {
    const { apiFetch } = await setupModule();

    const json = vi.fn().mockResolvedValue({ ok: true });
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json });
    global.fetch = fetchMock as typeof global.fetch;

    const alert = vi.fn();
    const result = await apiFetch("/test", alert);

    expect(fetchMock).toHaveBeenCalledWith(
      "https://api.example.com/test",
      expect.objectContaining({ headers: { "Content-Type": "application/json" } }),
    );
    expect(result).toEqual({ ok: true });
    expect(alert).not.toHaveBeenCalled();
  });

  it("rejects with response body when status not ok", async () => {
    const { apiFetch } = await setupModule();

    const text = vi.fn().mockResolvedValue("bad request");
    const fetchMock = vi.fn().mockResolvedValue({ ok: false, status: 400, text });
    global.fetch = fetchMock as typeof global.fetch;

    const alert = vi.fn();

    await expect(apiFetch("/fail", alert)).rejects.toThrow("bad request");
    expect(alert).toHaveBeenCalledWith("bad request");
  });

  it("handles network failures with friendly message", async () => {
    const { apiFetch } = await setupModule();

    const fetchMock = vi
      .fn()
      .mockRejectedValue(new TypeError("Failed to fetch"));
    global.fetch = fetchMock as typeof global.fetch;

    const alert = vi.fn();

    await expect(apiFetch("/fail", alert)).rejects.toThrow("Failed to fetch");
    expect(alert).toHaveBeenCalledWith(
      "Cannot connect to the backend. Is it running?",
    );
  });

  it("aborts long running requests and alerts timeout", async () => {
    const { apiFetch } = await setupModule();

    vi.useFakeTimers();

    const fetchMock = vi.fn().mockImplementation((_, options: RequestInit) => {
      const signal = options.signal as AbortSignal;
      return new Promise((_resolve, reject) => {
        signal.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"));
        });
      });
    });
    global.fetch = fetchMock as typeof global.fetch;

    const alert = vi.fn();
    const fetchPromise = apiFetch("/slow", alert);

    vi.advanceTimersByTime(800_000);

    await expect(fetchPromise).rejects.toThrowError(DOMException);
    expect(alert).toHaveBeenCalledWith("Request timed out.");
  });
});
