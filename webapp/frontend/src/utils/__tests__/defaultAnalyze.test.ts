import { describe, it, expect, vi, afterEach, beforeEach } from "vitest";
import type { CustomSubmitEvent } from "@/utils/defaultAnalyze";
import * as defaultAnalyzeModule from "@/utils/defaultAnalyze";

describe("getDefaultBlockRange", () => {
  let setError: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    setError = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("returns block range when API and latest block are valid", async () => {
    const result = await defaultAnalyzeModule.getDefaultBlockRange(
      setError,
      100,
      true,
    );

    expect(result).toEqual({ success: true, fromBlock: 95, toBlock: 100 });
    expect(setError).not.toHaveBeenCalled();
  });

  it("handles lower bound when latest block < default offset", async () => {
    const result = await defaultAnalyzeModule.getDefaultBlockRange(setError, 3, true);
    expect(result).toEqual({ success: true, fromBlock: 0, toBlock: 3 });
  });

  it("throws and reports when API is unavailable", async () => {
    await expect(
      defaultAnalyzeModule.getDefaultBlockRange(setError, 100, false),
    ).rejects.toThrow("API is not available at the moment.");

    expect(setError).toHaveBeenCalledWith(
      "network",
      "API is not available at the moment.",
    );
  });

  it("throws and reports when latest block is missing", async () => {
    await expect(
      defaultAnalyzeModule.getDefaultBlockRange(setError, undefined, true),
    ).rejects.toThrow("Latest block number is not available.");

    expect(setError).toHaveBeenCalledWith(
      "api",
      "Latest block number is not available.",
    );
  });
});

describe("handleDefaultAnalyze", () => {
  let setFromBlock: ReturnType<typeof vi.fn>;
  let setToBlock: ReturnType<typeof vi.fn>;
  let handleSubmit: ReturnType<typeof vi.fn>;
  let setError: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    setFromBlock = vi.fn();
    setToBlock = vi.fn();
    handleSubmit = vi.fn();
    setError = vi.fn();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  const callHandle = (overrides: {
    inputAddress?: string;
    latestBlock?: number;
    apiAvailable?: boolean;
  } = {}) =>
    defaultAnalyzeModule.handleDefaultAnalyze(
      overrides.inputAddress ?? "0x000000000000000000000000000000000000dEaD",
      setFromBlock,
      setToBlock,
      handleSubmit,
      setError,
      overrides.latestBlock ?? 123,
      overrides.apiAvailable ?? true,
    );

  it("rejects empty address", async () => {
    await callHandle({ inputAddress: "   " });

    expect(setError).toHaveBeenCalledWith(
      "form",
      "Please enter a contract address.",
    );
    expect(setFromBlock).not.toHaveBeenCalled();
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it("stops when API is offline", async () => {
    await callHandle({ apiAvailable: false });

    expect(setError).toHaveBeenCalledWith(
      "network",
      "API is not available at the moment.",
    );
    expect(setFromBlock).not.toHaveBeenCalled();
  });

  it("sets default block range and forwards submit event", async () => {
    await callHandle({ latestBlock: 200 });

    expect(setFromBlock).toHaveBeenCalledWith("195");
    expect(setToBlock).toHaveBeenCalledWith("200");
    expect(handleSubmit).toHaveBeenCalledTimes(1);

    const firstCall = handleSubmit.mock.calls.at(0);
    expect(firstCall).toBeDefined();
    const eventArg = firstCall?.[0] as CustomSubmitEvent;
    expect(eventArg?.blockRange).toEqual({ fromBlock: 195, toBlock: 200 });
  });

  it("reports runtime errors when downstream work fails", async () => {
    setFromBlock.mockImplementation(() => {
      throw new Error("boom");
    });

    await callHandle();

    expect(setError).toHaveBeenCalledWith(
      "runtime",
      "Error setting block range. Please try again.",
    );
    expect(handleSubmit).not.toHaveBeenCalled();
  });
});
