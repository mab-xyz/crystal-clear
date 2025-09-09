import type { CustomSubmitEvent } from "@/utils/defaultAnalyze";
import {
  getDeploymentInfo,
  depolyedBlockInfo,
  getLatestBlock,
} from "@/utils/queries";
import { BLOCKS } from "@/constants";
// Define block range types
export type BlockRangeType = "deep" | "ultimate" | "custom";

// Define interface for block range data
export interface BlockRange {
  fromBlock: number | null;
  toBlock: number | null;
}

// Function to handle preset block range selection
export const handleBlockRangeSelect = async (
  fromBlock: number,
  toBlock: number,
  setFromBlock: (block: string) => void,
  setToBlock: (block: string) => void,
  setLastSelectedRange: (range: number | null) => void,
  lastSelectedRange: number | null,
  inputAddress: string,
  updateUrlWithParams: (address: string, from?: string, to?: string) => void,
  handleSubmit: (e: React.FormEvent | CustomSubmitEvent) => void,
): Promise<void> => {
  try {
    // Check if the same range is clicked again (toggle behavior)
    const currentRange = toBlock - fromBlock;
    const isSameRange = lastSelectedRange === currentRange;

    if (isSameRange) {
      setFromBlock("");
      setToBlock("");
      setLastSelectedRange(null);
      return;
    }
    // set the input value
    setFromBlock(fromBlock.toString());
    setToBlock(toBlock.toString());
    setLastSelectedRange(currentRange);

    console.log("Set fromBlock:", fromBlock);
    console.log("Set toBlock:", toBlock);

    if (inputAddress) {
      // update the url parameters
      updateUrlWithParams(inputAddress, String(fromBlock), String(toBlock));

      // create the event object and add the block range data
      const event = new CustomEvent("submit") as unknown as CustomSubmitEvent;
      event.blockRange = {
        fromBlock,
        toBlock,
      };
      handleSubmit(event);
    }
  } catch (error) {
    console.error("Error setting block range:", error);
  }
};

// Function to handle block range type selection
export const handleBlockRangeTypeChange = async (
  newType: BlockRangeType,
  setBlockRangeType: (type: BlockRangeType) => void,
  setFromBlock: (block: string) => void,
  setToBlock: (block: string) => void,
  setLastSelectedRange: (range: number | null) => void,
  _lastSelectedRange: number | null,
  inputAddress: string,
  updateUrlWithParams: (address: string, from?: string, to?: string) => void,
  _handleSubmit: (e: CustomSubmitEvent) => void,
  showLocalAlert: (msg: string) => void,
  apiAvailability: boolean,
): Promise<void> => {
  setBlockRangeType(newType);
  console.log("newType", newType);

  if (!inputAddress) return;

  if (newType === "deep") {
    try {
      const latestBlock = await getLatestBlock(apiAvailability);

      if (!latestBlock || latestBlock === 0) {
        console.warn("No latest block found.");
        return;
      }

      const toBlock = latestBlock;
      const fromBlock = toBlock - BLOCKS.DEFAULT_RANGE;

      setFromBlock(fromBlock.toString());
      setToBlock(toBlock.toString());
      setLastSelectedRange(toBlock - fromBlock);

      console.log("fromBlock", fromBlock);
      console.log("toBlock", toBlock);
      console.log("lastSelectedRange", toBlock - fromBlock);

      updateUrlWithParams(
        inputAddress,
        fromBlock.toString(),
        toBlock.toString(),
      );

      // handleSubmit({
      //     blockRange: { fromBlock, toBlock },
      //     preventDefault: () => { },
      // } as CustomSubmitEvent);
    } catch (error) {
      console.error("Error fetching latest block for deep:", error);
    }
  } else if (newType === "ultimate") {
    const deploymentInfo = await getDeploymentInfo(
      inputAddress,
      apiAvailability,
      (msg: string) => showLocalAlert(msg),
    );

    if (!deploymentInfo) {
      console.warn("No deployment info found.");
      return;
    }

    const deployedBlockNumber = depolyedBlockInfo(deploymentInfo);
    const latestBlock = await getLatestBlock(apiAvailability);

    console.log("latestBlock", latestBlock);
    if (!latestBlock) {
      console.warn("No latest block found.");
      return;
    }

    const fromBlock = deployedBlockNumber;
    const toBlock = latestBlock;

    setFromBlock(String(fromBlock));
    setToBlock(String(toBlock));
    setLastSelectedRange(toBlock - fromBlock);

    updateUrlWithParams(inputAddress, String(fromBlock), String(toBlock));

    // handleSubmit({
    //     blockRange: { fromBlock: fromBlock, toBlock: toBlock },
    //     preventDefault: () => { },
    // } as CustomSubmitEvent);
  } else if (newType === "custom") {
    console.log("Custom type selected, ready for user input.");
  }
};

export function validateBlockRange(
  fromBlock: unknown,
  toBlock: unknown,
): { valid: boolean; reason?: string } {
  console.log("fromBlockinvalidateBlockRange", fromBlock, typeof fromBlock);
  console.log("toBlockinvalidateBlockRange", toBlock, typeof toBlock);

  if (toBlock === 0) {
    return { valid: false, reason: "Range check: To block cannot be 0." };
  }

  if (isNaN(Number(fromBlock)) || isNaN(Number(toBlock))) {
    return { valid: false, reason: "Range check: Block range contains NaN." };
  }
  if (Number(fromBlock) > Number(toBlock)) {
    return {
      valid: false,
      reason: "Range check: From block must be less than to block.",
    };
  }
  const blockRange = Number(toBlock) - Number(fromBlock);
  if (blockRange > BLOCKS.MAX_RANGE) {
    return {
      valid: false,
      reason: `Block range is larger than ${BLOCKS.MAX_RANGE}, please select a smaller range.`,
    };
  }
  return { valid: true };
}
