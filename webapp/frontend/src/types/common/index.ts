// Common types used across the application

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

export interface ErrorState {
  [key: string]: string | null;
}

export interface ErrorManager {
  errors: ErrorState;
  setError: (key: string, message: string) => void;
  clearError: (key: string) => void;
  hasErrors: () => boolean;
}
