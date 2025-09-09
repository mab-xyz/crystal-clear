// utils/defaultAnalyze.ts
import type { ErrorType } from "@/shared/utils/errorManager";

export interface BlockRangeData {
  fromBlock: number;
  toBlock: number;
}

export interface CustomSubmitEvent extends React.FormEvent {
  blockRange?: {
    fromBlock: number | null;
    toBlock: number | null;
  };
}

/** Get block range from a known latestBlock */
export const getDefaultBlockRange = async (
  setError: (type: ErrorType, message: string, showNow?: boolean) => void,
  latestBlock: number | undefined,
  apiAvailable: boolean | undefined,
): Promise<{ success: boolean; fromBlock: number; toBlock: number }> => {
  if (apiAvailable === false) {
    const msg = "API is not available at the moment.";
    setError("network", msg);
    throw new Error(msg);
  }

  const latestBlockNumber = Number(latestBlock);

  if (!latestBlock || isNaN(latestBlockNumber)) {
    const msg = "Latest block number is not available.";
    setError("api", msg);
    throw new Error(msg);
  }

  const fromBlock = Math.max(0, latestBlockNumber - 5);
  const toBlock = latestBlockNumber;

  return { success: true, fromBlock, toBlock };
};

export const handleDefaultAnalyze = async (
  inputAddress: string,
  setFromBlock: (block: string) => void,
  setToBlock: (block: string) => void,
  handleSubmit: (e: React.FormEvent | CustomSubmitEvent) => void,
  setError: (type: ErrorType, message: string, showNow?: boolean) => void,
  latestBlock: number | undefined,
  apiAvailable: boolean | undefined,
): Promise<void> => {
  try {
    if (!inputAddress.trim()) {
      setError("form", "Please enter a contract address.");
      return;
    }

    if (!apiAvailable) {
      setError("network", "API is not available at the moment.");
      return;
    }

    const blockRange = await getDefaultBlockRange(
      setError,
      latestBlock,
      apiAvailable,
    );

    setFromBlock(blockRange.fromBlock.toString());
    setToBlock(blockRange.toBlock.toString());

    const event = new CustomEvent("submit") as unknown as CustomSubmitEvent;
    event.blockRange = {
      fromBlock: blockRange.fromBlock,
      toBlock: blockRange.toBlock,
    };

    handleSubmit(event);
  } catch (err) {
    const msg = "Error setting block range. Please try again.";
    setError("runtime", msg);
  }
};
