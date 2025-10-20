import { describe, it, expect, beforeEach, vi } from "vitest";

import {
  handleBlockRangeSelect,
  handleBlockRangeTypeChange,
  validateBlockRange,
} from "../blockRange";
import { BLOCKS } from "@/constants";
import {
  getDeploymentInfo,
  depolyedBlockInfo,
  getLatestBlock,
} from "@/utils/queries";

vi.mock("@/utils/queries", () => ({
  getDeploymentInfo: vi.fn(),
  depolyedBlockInfo: vi.fn(),
  getLatestBlock: vi.fn(),
}));

const getLatestBlockMock = vi.mocked(getLatestBlock);
const getDeploymentInfoMock = vi.mocked(getDeploymentInfo);
const depolyedBlockInfoMock = vi.mocked(depolyedBlockInfo);

describe("handleBlockRangeSelect", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("clears range when the same preset is selected twice", async () => {
    const setFromBlock = vi.fn();
    const setToBlock = vi.fn();
    const setLastSelectedRange = vi.fn();
    const updateUrl = vi.fn();
    const handleSubmit = vi.fn();

    await handleBlockRangeSelect(
      100,
      150,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      50,
      "0xabc",
      updateUrl,
      handleSubmit,
    );

    expect(setFromBlock).toHaveBeenCalledWith("");
    expect(setToBlock).toHaveBeenCalledWith("");
    expect(setLastSelectedRange).toHaveBeenCalledWith(null);
    expect(updateUrl).not.toHaveBeenCalled();
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it("sets range and submits when a new preset is chosen", async () => {
    const setFromBlock = vi.fn();
    const setToBlock = vi.fn();
    const setLastSelectedRange = vi.fn();
    const updateUrl = vi.fn();
    const handleSubmit = vi.fn();

    await handleBlockRangeSelect(
      200,
      260,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      null,
      "0xdef",
      updateUrl,
      handleSubmit,
    );

    expect(setFromBlock).toHaveBeenCalledWith("200");
    expect(setToBlock).toHaveBeenCalledWith("260");
    expect(setLastSelectedRange).toHaveBeenCalledWith(60);
    expect(updateUrl).toHaveBeenCalledWith("0xdef", "200", "260");

    expect(handleSubmit).toHaveBeenCalledTimes(1);
    const eventArg = handleSubmit.mock.calls[0][0] as { blockRange?: any };
    expect(eventArg?.blockRange).toEqual({ fromBlock: 200, toBlock: 260 });
  });

  it("does not update URL or submit when no address is provided", async () => {
    const setFromBlock = vi.fn();
    const setToBlock = vi.fn();
    const setLastSelectedRange = vi.fn();
    const updateUrl = vi.fn();
    const handleSubmit = vi.fn();

    await handleBlockRangeSelect(
      10,
      20,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      null,
      "",
      updateUrl,
      handleSubmit,
    );

    expect(setFromBlock).toHaveBeenCalledWith("10");
    expect(setToBlock).toHaveBeenCalledWith("20");
    expect(setLastSelectedRange).toHaveBeenCalledWith(10);
    expect(updateUrl).not.toHaveBeenCalled();
    expect(handleSubmit).not.toHaveBeenCalled();
  });
});

describe("handleBlockRangeTypeChange", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const baseArgs = () => {
    const setBlockRangeType = vi.fn();
    const setFromBlock = vi.fn();
    const setToBlock = vi.fn();
    const setLastSelectedRange = vi.fn();
    const updateUrl = vi.fn();
    const handleSubmit = vi.fn();
    const showAlert = vi.fn();
    return {
      setBlockRangeType,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      updateUrl,
      handleSubmit,
      showAlert,
    };
  };

  it("returns early when no address is supplied", async () => {
    const {
      setBlockRangeType,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      updateUrl,
      handleSubmit,
      showAlert,
    } = baseArgs();

    await handleBlockRangeTypeChange(
      "deep",
      setBlockRangeType,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      null,
      "",
      updateUrl,
      handleSubmit,
      showAlert,
      true,
    );

    expect(setBlockRangeType).toHaveBeenCalledWith("deep");
    expect(getLatestBlockMock).not.toHaveBeenCalled();
    expect(setFromBlock).not.toHaveBeenCalled();
    expect(setToBlock).not.toHaveBeenCalled();
    expect(updateUrl).not.toHaveBeenCalled();
  });

  it("applies the deep range preset when latest block exists", async () => {
    getLatestBlockMock.mockResolvedValueOnce(1000);

    const {
      setBlockRangeType,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      updateUrl,
      handleSubmit,
      showAlert,
    } = baseArgs();

    await handleBlockRangeTypeChange(
      "deep",
      setBlockRangeType,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      null,
      "0x123",
      updateUrl,
      handleSubmit,
      showAlert,
      true,
    );

    const expectedFrom = (1000 - BLOCKS.DEFAULT_RANGE).toString();
    expect(setBlockRangeType).toHaveBeenCalledWith("deep");
    expect(getLatestBlockMock).toHaveBeenCalledWith(true);
    expect(setFromBlock).toHaveBeenCalledWith(expectedFrom);
    expect(setToBlock).toHaveBeenCalledWith("1000");
    expect(setLastSelectedRange).toHaveBeenCalledWith(
      1000 - Number(expectedFrom),
    );
    expect(updateUrl).toHaveBeenCalledWith("0x123", expectedFrom, "1000");
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it("does not update blocks when deep preset cannot resolve latest block", async () => {
    getLatestBlockMock.mockResolvedValueOnce(0);

    const {
      setBlockRangeType,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      updateUrl,
      handleSubmit,
      showAlert,
    } = baseArgs();

    await handleBlockRangeTypeChange(
      "deep",
      setBlockRangeType,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      null,
      "0x123",
      updateUrl,
      handleSubmit,
      showAlert,
      true,
    );

    expect(setBlockRangeType).toHaveBeenCalledWith("deep");
    expect(setFromBlock).not.toHaveBeenCalled();
    expect(setToBlock).not.toHaveBeenCalled();
    expect(setLastSelectedRange).not.toHaveBeenCalled();
    expect(updateUrl).not.toHaveBeenCalled();
  });

  it("applies the ultimate preset using deployment info", async () => {
    const deploymentInfo = { block_number: 42 } as const;
    getDeploymentInfoMock.mockResolvedValueOnce(deploymentInfo as any);
    depolyedBlockInfoMock.mockReturnValueOnce(42);
    getLatestBlockMock.mockResolvedValueOnce(242);

    const {
      setBlockRangeType,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      updateUrl,
      handleSubmit,
      showAlert,
    } = baseArgs();

    await handleBlockRangeTypeChange(
      "ultimate",
      setBlockRangeType,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      null,
      "0x456",
      updateUrl,
      handleSubmit,
      showAlert,
      true,
    );

    expect(setBlockRangeType).toHaveBeenCalledWith("ultimate");
    expect(getDeploymentInfoMock).toHaveBeenCalledWith(
      "0x456",
      true,
      expect.any(Function),
    );
    expect(depolyedBlockInfoMock).toHaveBeenCalledWith(deploymentInfo);
    expect(setFromBlock).toHaveBeenCalledWith("42");
    expect(setToBlock).toHaveBeenCalledWith("242");
    expect(setLastSelectedRange).toHaveBeenCalledWith(200);
    expect(updateUrl).toHaveBeenCalledWith("0x456", "42", "242");
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it("skips updates when ultimate preset lacks deployment info", async () => {
    getDeploymentInfoMock.mockResolvedValueOnce(null);

    const {
      setBlockRangeType,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      updateUrl,
      handleSubmit,
      showAlert,
    } = baseArgs();

    await handleBlockRangeTypeChange(
      "ultimate",
      setBlockRangeType,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      null,
      "0x456",
      updateUrl,
      handleSubmit,
      showAlert,
      true,
    );

    expect(setBlockRangeType).toHaveBeenCalledWith("ultimate");
    expect(setFromBlock).not.toHaveBeenCalled();
    expect(setToBlock).not.toHaveBeenCalled();
    expect(updateUrl).not.toHaveBeenCalled();
  });

  it("sets block range type to custom without additional work", async () => {
    const {
      setBlockRangeType,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      updateUrl,
      handleSubmit,
      showAlert,
    } = baseArgs();

    await handleBlockRangeTypeChange(
      "custom",
      setBlockRangeType,
      setFromBlock,
      setToBlock,
      setLastSelectedRange,
      null,
      "0x999",
      updateUrl,
      handleSubmit,
      showAlert,
      true,
    );

    expect(setBlockRangeType).toHaveBeenCalledWith("custom");
    expect(setFromBlock).not.toHaveBeenCalled();
    expect(setToBlock).not.toHaveBeenCalled();
    expect(updateUrl).not.toHaveBeenCalled();
  });
});

describe("validateBlockRange", () => {
  it("rejects ranges with toBlock equal to zero", () => {
    expect(validateBlockRange(10, 0)).toEqual({
      valid: false,
      reason: "Range check: To block cannot be 0.",
    });
  });

  it("rejects ranges containing non-numeric values", () => {
    expect(validateBlockRange("abc", 20)).toEqual({
      valid: false,
      reason: "Range check: Block range contains NaN.",
    });
  });

  it("rejects ranges where from block is greater than to block", () => {
    expect(validateBlockRange(30, 20)).toEqual({
      valid: false,
      reason: "Range check: From block must be less than to block.",
    });
  });

  it("rejects ranges that exceed the maximum allowed span", () => {
    expect(
      validateBlockRange(0, BLOCKS.MAX_RANGE + 1),
    ).toMatchObject({ valid: false });
  });

  it("accepts valid ranges", () => {
    expect(validateBlockRange(10, 20)).toEqual({ valid: true });
  });
});
