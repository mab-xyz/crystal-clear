// Application constants for maintainable configuration

// Layout constants
export const LAYOUT = {
  GRAPH_WIDTH_RATIO: 0.618, // Golden ratio for graph/sidebar split
  SIDEBAR_WIDTH_RATIO: 0.382,
  GRAPH_ZOOM_MIN: 0.1,
  GRAPH_ZOOM_MAX: 4.0,
  FORCE_LINK_DISTANCE: 200,
  FORCE_CHARGE_STRENGTH: -350,
} as const;

// API constants
export const API = {
  TIMEOUT_MS: 800_000, // 800 second timeout for heavy analysis
  RETRY_ATTEMPTS: 2,
  STALE_TIME_MS: 10 * 60 * 1000, // 10 minutes
  PREFETCH_STALE_TIME_MS: 5 * 60 * 1000, // 5 minutes
} as const;

// Block analysis constants
export const BLOCKS = {
  DEFAULT_RANGE: 50, // Default number of blocks to analyze
  MAX_RANGE: 7000, // Maximum allowed block range
} as const;

// Developer experience constants
export const DEV = {
  ALERT_TIMEOUT_MS: 5000, // Standard alert display duration
  ID_RANDOM_LENGTH: 9, // Length of random ID generation
} as const;

// Colors - consistent theme
export const COLORS = {
  PRIMARY: "#312750",
  PRIMARY_HOVER: "#2a1f43",
  SECONDARY: "#2b2b2b",
  ACCENT: "#C5BAFF",
  ACCENT_SECONDARY: "#91b8ff",
  FLOW_DOT: "#EFB6C8",
  BACKGROUND: "#ffffff",
  BACKGROUND_MUTED: "#f0f0f0",
  BORDER: "#e0e0e0",
  BORDER_LIGHT: "#f0f0f0",
  HOVER_BG: "#e0e0e0",
  ERROR_RED: "#ff6666",
  WARNING_ORANGE: "#ff9933",
  TEXT_PRIMARY: "#2b2b2b",
  TEXT_SECONDARY: "#666",
} as const;

// Design tokens for consistent spacing
export const SPACING = {
  XS: "0.25rem", // 4px
  SM: "0.5rem", // 8px
  MD: "1rem", // 16px
  LG: "1.5rem", // 24px
  XL: "2rem", // 32px
  XXL: "3rem", // 48px
} as const;

// Typography scale
export const TYPOGRAPHY = {
  FONT_SIZES: {
    XS: "0.75rem", // 12px
    SM: "0.875rem", // 14px
    BASE: "1rem", // 16px
    LG: "1.125rem", // 18px
    XL: "1.25rem", // 20px
    "2XL": "1.5rem", // 24px
    "3XL": "2rem", // 32px
    "4XL": "3rem", // 48px
  },
  FONT_WEIGHTS: {
    NORMAL: "400",
    MEDIUM: "500",
    SEMIBOLD: "600",
    BOLD: "700",
  },
  LINE_HEIGHTS: {
    TIGHT: "1.25",
    NORMAL: "1.5",
    RELAXED: "1.75",
  },
} as const;

// Shadow system for visual hierarchy
export const SHADOWS = {
  SM: "0 1px 2px 0 rgb(0 0 0 / 0.05)",
  BASE: "0 1px 3px 0 rgb(0 0 0 / 0.1), 0 1px 2px -1px rgb(0 0 0 / 0.1)",
  MD: "0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1)",
  LG: "0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1)",
  XL: "0 20px 25px -5px rgb(0 0 0 / 0.1), 0 8px 10px -6px rgb(0 0 0 / 0.1)",
  INNER: "inset 0 2px 4px 0 rgb(0 0 0 / 0.05)",
} as const;

// Border radius scale
export const RADIUS = {
  NONE: "0",
  SM: "0.125rem", // 2px
  BASE: "0.25rem", // 4px
  MD: "0.375rem", // 6px
  LG: "0.5rem", // 8px
  XL: "0.75rem", // 12px
  FULL: "9999px",
} as const;

// Animation constants
export const ANIMATION = {
  FLOW_DOTS_DURATION: 2000,
  TRANSITION_DURATION: 300,
} as const;

// UI text constants
export const TEXT = {
  APP_NAME: "Crystal Clear",
  TAGLINE: "A Smart Contract Is Only as Secure as Its Weakest Dependency.",
  PLACEHOLDER_ADDRESS: "Enter contract address (0x...)",
  ANALYZE_BUTTON: "Analyze",
  LOADING_TEXT: "Loading...",
  TRY_PROTOCOLS: "Try protocols:",
  NO_DEPENDENCIES:
    "No dependencies found for this contract in the selected block range.",
} as const;
