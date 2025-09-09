// Comprehensive validation utilities for security and UX
import { isAddress } from "ethers";

// Ethereum address validation with additional security checks
export function validateEthereumAddress(address: string): {
  isValid: boolean;
  error?: string;
  sanitized?: string;
} {
  if (!address || typeof address !== "string") {
    return { isValid: false, error: "Address is required" };
  }

  // Sanitize input - remove whitespace and convert to lowercase
  const sanitized = address.trim().toLowerCase();

  // Check for basic format
  if (!sanitized.startsWith("0x")) {
    return { isValid: false, error: "Address must start with 0x" };
  }

  // Check length
  if (sanitized.length !== 42) {
    return { isValid: false, error: "Address must be 42 characters long" };
  }

  // Check for valid hex characters
  const hexPattern = /^0x[a-fA-F0-9]{40}$/;
  if (!hexPattern.test(sanitized)) {
    return { isValid: false, error: "Address contains invalid characters" };
  }

  // Use ethers.js for checksum validation
  try {
    const isValidAddress = isAddress(sanitized);
    if (!isValidAddress) {
      return { isValid: false, error: "Invalid Ethereum address checksum" };
    }

    return { isValid: true, sanitized };
  } catch (error) {
    return { isValid: false, error: "Unable to validate address" };
  }
}

// Block number validation
export function validateBlockNumber(blockNumber: string): {
  isValid: boolean;
  error?: string;
  parsed?: number;
} {
  if (!blockNumber || typeof blockNumber !== "string") {
    return { isValid: false, error: "Block number is required" };
  }

  const trimmed = blockNumber.trim();

  // Check if it's a valid number
  const parsed = parseInt(trimmed, 10);

  if (isNaN(parsed)) {
    return { isValid: false, error: "Block number must be a valid number" };
  }

  if (parsed < 0) {
    return { isValid: false, error: "Block number must be positive" };
  }

  if (parsed > Number.MAX_SAFE_INTEGER) {
    return { isValid: false, error: "Block number is too large" };
  }

  return { isValid: true, parsed };
}

// Block range validation
export function validateBlockRange(
  fromBlock: string,
  toBlock: string,
): {
  isValid: boolean;
  error?: string;
  range?: { from: number; to: number };
} {
  const fromValidation = validateBlockNumber(fromBlock);
  const toValidation = validateBlockNumber(toBlock);

  if (!fromValidation.isValid) {
    return { isValid: false, error: `From block: ${fromValidation.error}` };
  }

  if (!toValidation.isValid) {
    return { isValid: false, error: `To block: ${toValidation.error}` };
  }

  const from = fromValidation.parsed!;
  const to = toValidation.parsed!;

  if (from >= to) {
    return { isValid: false, error: "From block must be less than to block" };
  }

  // Check for reasonable range size (prevent DoS)
  const maxRange = 1000000; // 1M blocks
  if (to - from > maxRange) {
    return {
      isValid: false,
      error: `Block range too large. Maximum ${maxRange} blocks allowed.`,
    };
  }

  return { isValid: true, range: { from, to } };
}

// URL validation for API endpoints
export function validateApiUrl(url: string): {
  isValid: boolean;
  error?: string;
  sanitized?: string;
} {
  if (!url || typeof url !== "string") {
    return { isValid: false, error: "API URL is required" };
  }

  const trimmed = url.trim();

  try {
    const parsed = new URL(trimmed);

    // Only allow HTTP/HTTPS
    if (!["http:", "https:"].includes(parsed.protocol)) {
      return {
        isValid: false,
        error: "API URL must use HTTP or HTTPS protocol",
      };
    }

    // Check for localhost in production (security check)
    if (
      import.meta.env.MODE === "production" &&
      (parsed.hostname === "localhost" || parsed.hostname === "127.0.0.1")
    ) {
      return {
        isValid: false,
        error: "Localhost URLs not allowed in production",
      };
    }

    return { isValid: true, sanitized: trimmed };
  } catch (error) {
    return { isValid: false, error: "Invalid URL format" };
  }
}

// Sanitize text input to prevent XSS
export function sanitizeTextInput(input: string): string {
  if (!input || typeof input !== "string") {
    return "";
  }

  return (
    input
      .trim()
      // Remove potential HTML/script tags
      .replace(/<[^>]*>/g, "")
      // Remove potential JavaScript: URLs
      .replace(/javascript:/gi, "")
      // Remove potential data: URLs
      .replace(/data:/gi, "")
      // Limit length
      .slice(0, 1000)
  );
}

// Validate environment variables
export function validateEnvironment(): {
  isValid: boolean;
  errors: string[];
} {
  const errors: string[] = [];

  // Check required environment variables
  const apiUrl = import.meta.env.VITE_API_BASE_URL;
  if (!apiUrl) {
    errors.push("VITE_API_BASE_URL environment variable is required");
  } else {
    const urlValidation = validateApiUrl(apiUrl);
    if (!urlValidation.isValid) {
      errors.push(`VITE_API_BASE_URL is invalid: ${urlValidation.error}`);
    }
  }

  return {
    isValid: errors.length === 0,
    errors,
  };
}
