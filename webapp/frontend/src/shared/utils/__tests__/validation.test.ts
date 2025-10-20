import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";

import {
  validateEthereumAddress,
  validateBlockNumber,
  validateBlockRange,
  validateApiUrl,
  sanitizeTextInput,
  validateEnvironment,
} from "@/shared/utils/validation";

const restoreEnv = () => {
  vi.unstubAllEnvs();
};

describe("validateEthereumAddress", () => {
  it("rejects empty input", () => {
    expect(validateEthereumAddress("")).toEqual({
      isValid: false,
      error: "Address is required",
    });
  });

  it("rejects missing prefix", () => {
    const result = validateEthereumAddress("123");
    expect(result.isValid).toBe(false);
    expect(result.error).toBe("Address must start with 0x");
  });

  it("rejects wrong length", () => {
    const result = validateEthereumAddress("0x1234");
    expect(result.error).toBe("Address must be 42 characters long");
  });

  it("rejects invalid characters", () => {
    const result = validateEthereumAddress("0xzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz");
    expect(result.error).toBe("Address contains invalid characters");
  });

  it("returns sanitized checksum-valid address", () => {
    const checksum = "0x000000000000000000000000000000000000dEaD";
    const result = validateEthereumAddress(` ${checksum.toUpperCase()} `);
    expect(result.isValid).toBe(true);
    expect(result.sanitized).toBe(checksum.toLowerCase());
  });
});

describe("validateBlockNumber", () => {
  it("enforces numeric string", () => {
    expect(validateBlockNumber("abc").isValid).toBe(false);
  });

  it("rejects negative numbers", () => {
    const result = validateBlockNumber("-1");
    expect(result.error).toBe("Block number must be positive");
  });

  it("accepts valid block number", () => {
    const result = validateBlockNumber("42");
    expect(result).toEqual({ isValid: true, parsed: 42 });
  });
});

describe("validateBlockRange", () => {
  it("rejects when from block >= to block", () => {
    const result = validateBlockRange("10", "10");
    expect(result.error).toBe("From block must be less than to block");
  });

  it("rejects oversized range", () => {
    const result = validateBlockRange("0", (1_000_002).toString());
    expect(result.error).toContain("Block range too large");
  });

  it("returns parsed range for valid input", () => {
    const result = validateBlockRange("5", "10");
    expect(result).toEqual({ isValid: true, range: { from: 5, to: 10 } });
  });
});

describe("validateApiUrl", () => {
  it("rejects non-http protocols", () => {
    const result = validateApiUrl("ftp://example.com");
    expect(result.error).toBe("API URL must use HTTP or HTTPS protocol");
  });

  it("accepts https URL", () => {
    const result = validateApiUrl("https://api.example.com");
    expect(result.isValid).toBe(true);
  });
});

describe("sanitizeTextInput", () => {
  it("strips html and dangerous protocols", () => {
    const sanitized = sanitizeTextInput(
      "<script>evil()</script>javascript:alert(1)Actual",
    );
    expect(sanitized).toBe("evil()alert(1)Actual");
  });

  it("returns empty string for non-string", () => {
    expect(sanitizeTextInput(undefined as unknown as string)).toBe("");
  });
});

describe("validateEnvironment", () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    restoreEnv();
  });

  it("reports missing VITE_API_BASE_URL", () => {
    vi.stubEnv("VITE_API_BASE_URL", "");
    const result = validateEnvironment();
    expect(result.isValid).toBe(false);
    expect(result.errors).toContain(
      "VITE_API_BASE_URL environment variable is required",
    );
  });

  it("validates provided API URL", () => {
    vi.stubEnv("VITE_API_BASE_URL", "https://api.example.com");
    const result = validateEnvironment();
    expect(result.isValid).toBe(true);
  });
});
