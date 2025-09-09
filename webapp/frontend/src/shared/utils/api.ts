// Core API utility for backend communication
// Handles timeout, error management, and response processing

// Backend API base URL from environment variables
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL as string;

export default API_BASE_URL;

// Generic API fetch function with error handling and timeout management
// Returns typed responses and displays user-friendly error messages
export const apiFetch = async <T>(
  path: string,
  alert: (msg: string) => void,
  options: RequestInit = {},
): Promise<T> => {
  console.log("Starting API request...");
  console.log(`Calling API with path: ${path}`);
  console.log(`API_BASE_URL: ${API_BASE_URL}`);
  console.log(`Full URL: ${API_BASE_URL}${path}`);
  console.log(`Request options:`, options);

  // Request timeout and abort controller for long-running operations
  const controller = new AbortController();
  const timeoutId = setTimeout(() => {
    console.log("Request timed out after 30 seconds");
    controller.abort();
  }, 800_000); // 800 second timeout for heavy graph analysis

  try {
    console.log("Sending request...");
    const response = await fetch(`${API_BASE_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      signal: controller.signal,
      ...options,
    });

    console.log("Received response");
    console.log("Response status:", response.status);
    console.log("Response headers:", response.headers);

    if (!response.ok) {
      console.log("Response was not OK");
      const errorText = await response.text();
      console.error("Error response body:", errorText);
      alert(errorText || `Request failed with status ${response.status}`);
      throw new Error(
        errorText || `Request failed with status ${response.status}`,
      );
    }

    return await response.json();
  } catch (error) {
    console.error("Request error:", error);

    if (error instanceof DOMException && error.name === "AbortError") {
      console.log("Request was aborted");
      alert("Request timed out.");
    } else if (
      error instanceof TypeError &&
      error.message.includes("Failed to fetch")
    ) {
      console.log("Network error:", error);
      alert("Cannot connect to the backend. Is it running?");
    } else if (error instanceof Error) {
      console.log("Error details:", error);
      alert(error.message);
    } else {
      console.log("Unknown error:", error);
      alert("Unknown error occurred.");
    }
    throw error;
  } finally {
    console.log("Request completed or error occurred");
    clearTimeout(timeoutId);
  }
};
