import { checkApiAvailability } from "@/utils/api";


// Interface for the block range data
export interface BlockRangeData {
    fromBlock: number;
    toBlock: number;
}

// Interface for custom submit events
export interface CustomSubmitEvent extends React.FormEvent {
    blockRange?: {
        fromBlock: number | null;
        toBlock: number | null;
    };
}

/**
 * Gets the default block range for analysis (latest block and 20 blocks before)
 * @returns A promise that resolves to the block range data
 */
export const getDefaultBlockRange = async (): Promise<{ success: boolean; fromBlock: number; toBlock: number }> => {
    try {
        const isAvailable = await checkApiAvailability();

        if (!isAvailable) {
            console.error("API is not available at port 8000");
            return {
                success: false,
                fromBlock: 0,
                toBlock: 0
            };
        }

        // Fetch the latest block number from the API
        const response = await fetch('http://localhost:8000/info/block-latest');
        if (!response.ok) {
            throw new Error('Failed to fetch latest block');
        }

        const data = await response.json();
        console.log("data", data);
        const latestBlock = parseInt(data.block_number);

        // Calculate a range of 20 blocks
        const fromBlock = Math.max(0, latestBlock - 20);
        const toBlock = latestBlock;

        return {
            success: true,
            fromBlock,
            toBlock
        };
    } catch (error) {
        console.error("Error getting default block range:", error);
        return {
            success: false,
            fromBlock: 0,
            toBlock: 0
        };
    }
};

/**
 * Handles the default analyze action with a 20-block range
 * @param inputAddress The contract address to analyze
 * @param setFromBlock Function to update the fromBlock state
 * @param setToBlock Function to update the toBlock state
 * @param handleSubmit Function to handle the form submission
 * @param showAlert Function to display alerts to the user
 * @returns A promise that resolves when the operation is complete
 */
export const handleDefaultAnalyze = async (
    inputAddress: string,
    setFromBlock: (block: string) => void,
    setToBlock: (block: string) => void,
    handleSubmit: (e: React.FormEvent | CustomSubmitEvent) => void,
    showAlert: (message: string) => void
): Promise<void> => {
    try {
        if (!inputAddress || inputAddress.trim() === "") {
            showAlert("Please enter a contract address.");
            return;
        }
        const blockRange = await getDefaultBlockRange();

        if (!blockRange.success) {
            showAlert("Failed to get block range. Please try again.");
            return;
        }

        console.log("blockRange", blockRange);
        setFromBlock(blockRange.fromBlock.toString());
        setToBlock(blockRange.toBlock.toString());

        // Create a new event with block range data
        const event = new CustomEvent("submit") as unknown as CustomSubmitEvent;
        event.blockRange = {
            fromBlock: blockRange.fromBlock,
            toBlock: blockRange.toBlock,
        };
        handleSubmit(event);
    } catch (error) {
        console.error("Error setting default block range:", error);
        showAlert("Error setting block range. Please try again.");
    }
};