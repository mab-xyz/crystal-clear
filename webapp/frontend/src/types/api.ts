// Centralized API response types for better type safety

export interface ApiError {
  message: string;
  code?: string;
  status?: number;
}

export interface ApiResponse<T> {
  data: T;
  success: boolean;
  error?: ApiError;
}

export interface BlockRange {
  fromBlock: number;
  toBlock: number;
}

export interface ContractInfo {
  address: string;
  name?: string;
  symbol?: string;
  decimals?: number;
}

export interface PopularContract {
  name: string;
  address: string;
  description?: string;
}

// Graph-related types
export interface GraphNode {
  id: string;
  group: "main" | "other";
  x?: number;
  y?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface GraphEdge {
  source: string;
  target: string;
  types: Record<string, number>;
}

export interface GraphData {
  address: string;
  edges: GraphEdge[];
  nodes?: Record<string, string>;
}

// Error management types
export interface ErrorState {
  [key: string]: string | null;
}

export interface ErrorManager {
  errors: ErrorState;
  setError: (key: string, message: string) => void;
  clearError: (key: string) => void;
  hasErrors: () => boolean;
}
