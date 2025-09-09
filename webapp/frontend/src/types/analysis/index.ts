// Contract analysis types

export interface DeploymentInfo {
  address: string;
  deployer: string;
  deployer_eoa: string;
  tx_hash: string;
  block_number: number;
}

export interface RiskAnalysis {
  risk_score: number;
  factors: {
    immutability: string;
    adminPrivileges: string;
    auditingInfo: string;
    githubQuality: string;
  };
}

export interface ContractInfo {
  address: string;
  name?: string;
  symbol?: string;
  decimals?: number;
}

export interface VerificationInfo {
  address: string;
  verification: string;
  verifiedAt: string;
}

export interface ProxyInfo {
  address: string;
  type: string;
  message: string;
}

export interface PermissionInfo {
  address: string;
  function: string[];
}

export interface AuditInfo {
  contract: {
    address: string;
    protocol: string;
    version: string;
    date_added: string;
    last_updated: string;
  };
  audits: {
    protocol: string;
    version: string;
    company: string;
    url: string;
    date_added: string;
    last_updated: string;
  }[];
}
