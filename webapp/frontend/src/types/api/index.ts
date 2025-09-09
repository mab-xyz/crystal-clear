// API-specific types and interfaces

export interface PopularContract {
  name: string;
  address: string;
  description?: string;
}

export interface HealthResponse {
  status: string;
}

export interface BlockResponse {
  block_number: number;
}

export interface RiskResponse {
  risk_score: number;
}

// Re-export analysis types that are returned by API
export type {
  DeploymentInfo,
  VerificationInfo,
  ProxyInfo,
  PermissionInfo,
  AuditInfo,
} from "../analysis";

// Re-export graph types that are returned by API
export type { GraphData } from "../graph";
