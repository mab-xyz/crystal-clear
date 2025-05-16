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
            signal: AbortSignal.timeout(5000)
        });
        return response.ok;
    } catch (error) {
        console.error("API availability check failed:", error);
        return false;
    }
};