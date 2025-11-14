import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

import { fetchGraphData } from "@/utils/graphFetcher";

describe("fetchGraphData", () => {
  const originalFetch = global.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    global.fetch = originalFetch;
  });

  it("returns null when address is missing", async () => {
    const onError = vi.fn();
    const result = await fetchGraphData("", "", "", onError);

    expect(result).toBeNull();
    expect(onError).not.toHaveBeenCalled();
  });

  it("requests dependencies with optional query params", async () => {
    const mockData = { address: "0x123", nodes: [], edges: [] };
    const json = vi.fn().mockResolvedValue(mockData);
    const fetchMock = vi.fn().mockResolvedValue({ json });
    global.fetch = fetchMock as typeof global.fetch;

    const onError = vi.fn();
    const result = await fetchGraphData("0xabc", "10", "20", onError);

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const calledUrl = fetchMock.mock.calls[0][0] as string;
    expect(calledUrl).toContain("0xabc");
    expect(calledUrl).toContain("from_block=10");
    expect(calledUrl).toContain("to_block=20");

    expect(result).toEqual(mockData);
    expect(onError).not.toHaveBeenCalled();
  });

  it("propagates fetch errors and notifies via onError", async () => {
    const error = new Error("boom");
    const fetchMock = vi.fn().mockRejectedValue(error);
    global.fetch = fetchMock as typeof global.fetch;

    const onError = vi.fn();

    await expect(fetchGraphData("0xabc", "", "", onError)).rejects.toThrow(error);
    expect(onError).toHaveBeenCalledWith("Failed to fetch data");
  });
});
