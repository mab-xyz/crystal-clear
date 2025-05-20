import { useLocalAlert } from "@/components/ui/local-alert";

/**
 * Utility functions for API interactions
 */

/**
 * Checks if the API is available by making a request to the health endpoint
 * @returns Promise<boolean> - true if API is available, false otherwise
 */
export const checkApiAvailability = async (): Promise<boolean> => {
    try {
        const response = await fetch('http://localhost:8000/health', {
            method: 'GET',
            headers: { 'Content-Type': 'application/json' },
            // Set a short timeout to avoid long waits
            signal: AbortSignal.timeout(12000),
            mode: 'cors'
        });
        console.log("API availability check response:", response);
        return response.ok;
    } catch (error) {
        console.error("API availability check failed:", error);
        const { showLocalAlert } = useLocalAlert();
        showLocalAlert("API is not available at port 8000. Please check if the API is running.");
        return false;
    }
};