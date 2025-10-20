import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

vi.mock("@/shared/utils/api", () => {
  return {
    default: "http://mock-api",
    apiFetch: vi.fn(),
  };
});

import {
  getApiAvailability,
  getLatestBlock,
  getRiskAnalysis,
  getVerificationInfo,
  getProxyInfo,
  getPermissionInfo,
  getAuditInfo,
  getDeploymentInfo,
  depolyedBlockInfo,
  deployerInfo,
  deployerEOAInfo,
} from "@/utils/queries";
import { apiFetch } from "@/shared/utils/api";

describe("queries utilities", () => {
  const apiFetchMock = vi.mocked(apiFetch);

  beforeEach(() => {
    apiFetchMock.mockReset();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("determines API availability from health endpoint", async () => {
    apiFetchMock.mockResolvedValueOnce({ status: "healthy" });
    await expect(getApiAvailability()).resolves.toBe(true);
    expect(apiFetchMock).toHaveBeenCalledWith("/health", expect.any(Function));

    apiFetchMock.mockResolvedValueOnce({ status: "degraded" });
    await expect(getApiAvailability()).resolves.toBe(false);
  });

  it("returns false when health check rejects", async () => {
    apiFetchMock.mockRejectedValueOnce(new Error("fail"));
    await expect(getApiAvailability()).resolves.toBe(false);
  });

  it("returns zero latest block when API unavailable", async () => {
    await expect(getLatestBlock(false)).resolves.toBe(0);
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("fetches latest block number", async () => {
    apiFetchMock.mockResolvedValueOnce({ block_number: 42 });
    await expect(getLatestBlock(true)).resolves.toBe(42);
    expect(apiFetchMock).toHaveBeenCalledWith(
      "/info/block-latest",
      expect.any(Function),
    );
  });

  it("fetches risk analysis score", async () => {
    apiFetchMock.mockResolvedValueOnce({ risk_score: 88 });
    await expect(getRiskAnalysis("0xabc", true)).resolves.toBe(88);

    await expect(getRiskAnalysis("0xabc", false)).resolves.toBeNull();
  });

  it("fetches verification info", async () => {
    const verification = { address: "0x", verification: "verified", verifiedAt: "now" };
    apiFetchMock.mockResolvedValueOnce(verification);
    await expect(getVerificationInfo("0xabc", true)).resolves.toEqual(verification);
  });

  it("fetches proxy info", async () => {
    const proxy = { address: "0x", type: "UUPS", message: "ok" };
    apiFetchMock.mockResolvedValueOnce(proxy);
    await expect(getProxyInfo("0xabc", true)).resolves.toEqual(proxy);
  });

  it("fetches permission info", async () => {
    const permissions = { address: "0x", function: ["foo"] };
    apiFetchMock.mockResolvedValueOnce(permissions);
    await expect(getPermissionInfo("0xabc", true)).resolves.toEqual(permissions);
  });

  it("fetches audit info", async () => {
    const audits = { contract: { address: "0x", protocol: "A", version: "1", date_added: "", last_updated: "" }, audits: [] };
    apiFetchMock.mockResolvedValueOnce(audits);
    await expect(getAuditInfo("0xabc", true)).resolves.toEqual(audits);
  });

  it("handles deployment info when API offline", async () => {
    const showAlert = vi.fn();
    const result = await getDeploymentInfo("0xabc", false, showAlert);

    expect(result).toBeNull();
    expect(showAlert).toHaveBeenCalledWith("API is offline. Please try again later.");
    expect(apiFetchMock).not.toHaveBeenCalled();
  });

  it("returns deployment info when available", async () => {
    const deployment = {
      address: "0xabc",
      deployer: "0x123",
      deployer_eoa: "0x456",
      tx_hash: "0x789",
      block_number: 12,
    };
    apiFetchMock.mockResolvedValueOnce(deployment);

    const showAlert = vi.fn();
    const result = await getDeploymentInfo("0xabc", true, showAlert);

    expect(result).toEqual(deployment);
    expect(showAlert).not.toHaveBeenCalled();
  });

  it("reports errors when deployment fetch fails", async () => {
    const showAlert = vi.fn();
    apiFetchMock.mockRejectedValueOnce(new Error("fail"));

    const result = await getDeploymentInfo("0xabc", true, showAlert);

    expect(result).toBeNull();
    expect(showAlert).toHaveBeenCalledWith(
      "Error fetching deployment info. Please try again.",
    );
  });

  it("formats deployment helpers", () => {
    const info = {
      address: "0xabc",
      deployer: "0x123",
      deployer_eoa: "0x456",
      tx_hash: "0x789",
      block_number: 99,
    };
    expect(depolyedBlockInfo(info)).toBe(99);
    expect(deployerInfo(info)).toBe("0x123");
    expect(deployerEOAInfo(info)).toBe("0x456");
  });
});
