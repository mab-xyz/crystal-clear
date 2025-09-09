// src/hooks/queries.ts
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/shared/utils/api";
import type { GraphData } from "@/types/graph";

/** Check if API is online */
export const getApiAvailability = async () => {
  console.log("useApiAvailability called");

  try {
    // use API fetch to check if API is online
    const res = await apiFetch<{ status: string }>("/health", (msg) =>
      console.log(msg),
    );

    console.log("res", res);
    console.log("res.status", res.status);

    if (res.status === "healthy") {
      console.log("API is online");
      return true;
    } else {
      console.log("API is offline");
      return false;
    }
  } catch (error) {
    console.error("Error checking API health", error);
    return false;
  }
};

// return useQuery({
//     queryKey: ['apiHealth'],
//     queryFn: async () => {
//         try {
//             console.log("Checking API health");
//             const ok = await apiFetch<boolean>('/health', (msg) => console.log(msg));
//             return ok;
//         } catch (error) {
//             console.error("API health check failed", error);
//             return false;
//         }
//     },
//     staleTime: 1000,
//     enabled: true,
// });

export const getLatestBlock = async (apiHealth?: boolean) => {
  console.log("apiHealth", apiHealth);
  if (!apiHealth) return 0;

  const res = await apiFetch<{ block_number: number }>(
    "/info/block-latest",
    (msg) => console.log(msg),
  );
  return res.block_number;
};

export const getRiskAnalysis = async (address: string, apiHealth?: boolean) => {
  console.log("apiHealth", apiHealth);
  if (!apiHealth) return null;

  const res = await apiFetch<{ risk_score: number }>(
    `/v1/analysis/${address}/risk`,
    (msg) => console.log(msg),
  );
  const risk_score = res.risk_score;
  return risk_score;
};

export const getVerificationInfo = async (
  address: string,
  apiHealth?: boolean,
) => {
  console.log("apiHealth", apiHealth);
  if (!apiHealth) return null;

  const res = await apiFetch<{
    address: string;
    verification: string;
    verifiedAt: string;
  }>(`/info/verification/${address}`, (msg) => console.log(msg));
  console.log("resofverification", res);
  return res;
};

export const getProxyInfo = async (address: string, apiHealth?: boolean) => {
  console.log("apiHealth", apiHealth);
  if (!apiHealth) return null;

  const res = await apiFetch<{
    address: string;
    type: string;
    message: string;
  }>(`/info/proxy/${address}`, (msg) => console.log(msg));
  console.log("resofproxy", res);
  return res;
};

export const getPermissionInfo = async (
  address: string,
  apiHealth?: boolean,
) => {
  console.log("apiHealth", apiHealth);
  if (!apiHealth) return null;

  const res = await apiFetch<{ address: string; function: string[] }>(
    `/info/permissions/${address}`,
    (msg) => console.log(msg),
  );
  console.log("resofpermission", res);
  return res;
};

export const getAuditInfo = async (address: string, apiHealth?: boolean) => {
  console.log("apiHealth", apiHealth);
  if (!apiHealth) return null;

  const res = await apiFetch<{
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
  }>(`/contract/${address}/audits`, (msg) => console.log(msg));
  console.log("resofaudit", res);
  return res;
};

/** Fetch deployment info */
export interface DeploymentInfo {
  address: string;
  deployer: string;
  deployer_eoa: string;
  tx_hash: string;
  block_number: number;
}

/**
 * Fetches deployment information for a given contract address
 * @param address The contract address to get deployment info for
 * @param chainId The chain ID where the contract is deployed
 * @returns Promise resolving to deployment information
 */
export async function getDeploymentInfo(
  address: string,
  apiAvailability: boolean | undefined,
  showAlert?: (message: string) => void,
): Promise<DeploymentInfo | null> {
  try {
    if (apiAvailability === false) {
      console.log("API is offline, cannot fetch deployment info");
      return null;
    }

    // If apiAvailability is undefined, still try to fetch (it might be loading)
    const data = await apiFetch<DeploymentInfo>(
      `/info/deployment/${address}`,
      (msg) => console.log(msg),
    );
    console.log("deployment info data", data);
    return data;
  } catch (error) {
    console.error("Error fetching deployment info:", error);
    // Only show alert if explicitly requested (for backward compatibility)
    if (showAlert) {
      showAlert("Error fetching deployment info. Please try again.");
    }
    return null;
  }
}

/**
 * Creates a formatted string representation of deployment info
 * @param info The deployment info object
 * @returns Formatted string with deployment details
 */
export function depolyedBlockInfo(info: DeploymentInfo): number {
  const deployedBlock = info.block_number;
  console.log("deployedBlock", deployedBlock);
  return deployedBlock;
}

export function deployerInfo(info: DeploymentInfo): string {
  const deployer = info.deployer;
  return deployer;
}

export function deployerEOAInfo(info: DeploymentInfo): string {
  const deployerEOA = info.deployer_eoa;
  return deployerEOA;
}

/** Fetch graph dependency analysis */
export const getGraphData = (
  address: string,
  fromBlock?: string,
  toBlock?: string,
  enabled = true,
) =>
  useQuery({
    queryKey: ["graphData", address, fromBlock, toBlock],
    queryFn: () => {
      const params = new URLSearchParams();
      if (fromBlock) params.append("from_block", fromBlock);
      if (toBlock) params.append("to_block", toBlock);

      const url = `/v1/analysis/${address}/dependencies${params.toString() ? `?${params}` : ""}`;
      return apiFetch<GraphData>(url, (msg) => console.error(msg));
    },
    enabled: !!address && enabled,
  });
