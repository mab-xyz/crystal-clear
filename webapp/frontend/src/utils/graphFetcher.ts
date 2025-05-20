import type { GraphData } from "../components/graph/GraphLayout";

export const fetchGraphData = async (
    address: string,
    fromBlock: string = "",
    toBlock: string = "",
    onError: (message: string) => void
): Promise<GraphData | null> => {
    if (!address) return null;

    try {

        console.log("address", address);
        console.log("fromBlock in fetcher", fromBlock);
        console.log("toBlock in fetcher", toBlock);

        // Build the URL with optional query parameters
        let url = `http://localhost:8000/v1/analysis/${address}/dependencies`;

        const params = new URLSearchParams();

        if (fromBlock) params.append("from_block", fromBlock);
        if (toBlock) params.append("to_block", toBlock);

        console.log("params", params);

        // Add the query parameters to the URL if any exist
        if (params.toString()) {
            url += `?${params.toString()}`;
        }

        console.log("Fetching data from:", url);
        const response = await fetch(url);
        const data = await response.json();
        return data;
    } catch (err) {
        console.error("Failed to fetch data:", err);
        onError("Failed to fetch data");
        return null;
    }
};