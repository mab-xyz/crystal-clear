// Environment validation and configuration
// Ensures the application has all required environment variables and configuration

import { validateApiUrl } from "./validation";

interface EnvConfig {
  apiBaseUrl: string;
  isDevelopment: boolean;
  isProduction: boolean;
  nodeEnv: string;
}

interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
  config?: EnvConfig;
}

/**
 * Validates all environment variables and returns configuration
 */
export function validateEnvironment(): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];

  // Get environment variables
  const apiBaseUrl = import.meta.env.VITE_API_BASE_URL;
  const nodeEnv = import.meta.env.MODE || "development";
  const isDevelopment = nodeEnv === "development";
  const isProduction = nodeEnv === "production";

  // Validate required environment variables
  if (!apiBaseUrl) {
    errors.push("VITE_API_BASE_URL environment variable is required");
  } else {
    const urlValidation = validateApiUrl(apiBaseUrl);
    if (!urlValidation.isValid) {
      errors.push(`VITE_API_BASE_URL is invalid: ${urlValidation.error}`);
    }
  }

  // Production-specific validations
  if (isProduction) {
    // Ensure HTTPS in production
    if (apiBaseUrl && !apiBaseUrl.startsWith("https://")) {
      errors.push("API URL must use HTTPS in production");
    }

    // Check for development/localhost URLs
    if (
      apiBaseUrl &&
      (apiBaseUrl.includes("localhost") || apiBaseUrl.includes("127.0.0.1"))
    ) {
      errors.push("localhost/127.0.0.1 URLs are not allowed in production");
    }

    // Warn about debug configurations
    if (import.meta.env["VITE_DEBUG"] === "true") {
      warnings.push("Debug mode is enabled in production");
    }
  }

  // Development-specific warnings
  if (isDevelopment) {
    if (
      !apiBaseUrl?.includes("localhost") &&
      !apiBaseUrl?.includes("127.0.0.1")
    ) {
      warnings.push("Consider using localhost for development API URL");
    }
  }

  // Build configuration object
  const config: EnvConfig = {
    apiBaseUrl: apiBaseUrl || "",
    isDevelopment,
    isProduction,
    nodeEnv,
  };

  const result: ValidationResult = {
    isValid: errors.length === 0,
    errors,
    warnings,
  };

  if (errors.length === 0) {
    result.config = config;
  }

  return result;
}

/**
 * Initialize application environment validation
 * Should be called at application startup
 */
export function initializeEnvironment(): EnvConfig {
  const validation = validateEnvironment();

  // Log validation results
  if (validation.errors.length > 0) {
    console.error("❌ Environment validation failed:");
    validation.errors.forEach((error) => console.error(`  • ${error}`));

    // In development, show user-friendly error
    if (!validation.config?.isProduction) {
      const errorMessage = `
Environment Configuration Error

The following environment variables are missing or invalid:
${validation.errors.map((error) => `• ${error}`).join("\n")}

Please check your .env file and ensure all required variables are set.
`;
      alert(errorMessage);
    }

    throw new Error("Environment validation failed");
  }

  if (validation.warnings.length > 0) {
    console.warn("⚠️  Environment warnings:");
    validation.warnings.forEach((warning) => console.warn(`  • ${warning}`));
  }

  console.log("✅ Environment validation passed");
  console.log(`🚀 Running in ${validation.config!.nodeEnv} mode`);
  console.log(`🌐 API Base URL: ${validation.config!.apiBaseUrl}`);

  return validation.config!;
}

/**
 * Get current environment configuration
 * Returns cached configuration after initialization
 */
let _envConfig: EnvConfig | null = null;

export function getEnvConfig(): EnvConfig {
  if (!_envConfig) {
    _envConfig = initializeEnvironment();
  }
  return _envConfig;
}

/**
 * Check if running in development mode
 */
export function isDevelopment(): boolean {
  return getEnvConfig().isDevelopment;
}

/**
 * Check if running in production mode
 */
export function isProduction(): boolean {
  return getEnvConfig().isProduction;
}

/**
 * Get the API base URL with validation
 */
export function getApiBaseUrl(): string {
  const config = getEnvConfig();

  // Additional runtime validation
  if (!config.apiBaseUrl) {
    throw new Error("API base URL not configured");
  }

  return config.apiBaseUrl;
}
