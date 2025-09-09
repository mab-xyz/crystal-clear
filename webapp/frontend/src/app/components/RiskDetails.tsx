import { useState, useEffect, useCallback } from "react";
import { useQuery } from "@tanstack/react-query";
import InfoCard from "@/shared/components/common/InfoCard";
import {
  getProxyInfo,
  getPermissionInfo,
  getVerificationInfo,
  getAuditInfo,
} from "@/utils/queries";
import { API } from "@/constants";

interface RiskDetailsProps {
  address: string | undefined;
}

interface RiskMetric {
  name: string;
  value: string;
  level: "high" | "medium" | "low" | "unknown";
  note?: string;
  detail?: string;
}

export default function RiskDetails({ address }: RiskDetailsProps) {
  const [riskMetrics, setRiskMetrics] = useState<RiskMetric[]>([]);

  // Cache risk analysis data using TanStack Query
  const {
    data: proxyData,
    error: proxyError,
    isLoading: proxyLoading,
  } = useQuery({
    queryKey: ["proxyInfo", address],
    queryFn: () => getProxyInfo(address!, true),
    enabled: !!address,
    staleTime: API.STALE_TIME_MS,
    gcTime: API.STALE_TIME_MS * 2, // Keep cache for 20 minutes
    retry: (failureCount, error: any) => {
      // Don't retry on 500 errors, only on network failures
      if (error?.status === 500) return false;
      return failureCount < API.RETRY_ATTEMPTS;
    },
  });

  const {
    data: permissionData,
    error: permissionError,
    isLoading: permissionLoading,
  } = useQuery({
    queryKey: ["permissionInfo", address],
    queryFn: () => getPermissionInfo(address!, true),
    enabled: !!address,
    staleTime: API.STALE_TIME_MS,
    gcTime: API.STALE_TIME_MS * 2, // Keep cache for 20 minutes
    retry: (failureCount, error: any) => {
      // Don't retry on 500 errors, only on network failures
      if (error?.status === 500) return false;
      return failureCount < API.RETRY_ATTEMPTS;
    },
  });

  const {
    data: verificationData,
    error: verificationError,
    isLoading: verificationLoading,
  } = useQuery({
    queryKey: ["verificationInfo", address],
    queryFn: () => getVerificationInfo(address!, true),
    enabled: !!address,
    staleTime: API.STALE_TIME_MS,
    gcTime: API.STALE_TIME_MS * 2, // Keep cache for 20 minutes
    retry: (failureCount, error: any) => {
      // Don't retry on 500 errors, only on network failures
      if (error?.status === 500) return false;
      return failureCount < API.RETRY_ATTEMPTS;
    },
  });

  const {
    data: auditData,
    error: auditError,
    isLoading: auditLoading,
  } = useQuery({
    queryKey: ["auditInfo", address],
    queryFn: () => getAuditInfo(address!, true),
    enabled: !!address,
    staleTime: API.STALE_TIME_MS,
    gcTime: API.STALE_TIME_MS * 2, // Keep cache for 20 minutes
    retry: (failureCount, error: any) => {
      // Don't retry on 500 errors, only on network failures
      if (error?.status === 500) return false;
      return failureCount < API.RETRY_ATTEMPTS;
    },
  });

  const updateRiskMetrics = useCallback(() => {
    const updated: RiskMetric[] = [];

    // Proxy (Immutability)
    const isProxy =
      proxyData && proxyData.type?.toLowerCase() !== "not a proxy";
    const proxyLevel = proxyError ? "unknown" : isProxy ? "high" : "low";
    const proxyRiskMetric: RiskMetric = {
      name: "Immutability",
      value: proxyError ? "Error" : isProxy ? "Proxy" : "Immutable",
      level: proxyLevel,
    };
    if (proxyError) {
      proxyRiskMetric.detail = "Failed to fetch proxy information";
    } else if (proxyData) {
      proxyRiskMetric.detail = `Proxy Type: ${proxyData.type || "N/A"}\nProxy message: ${proxyData.message || "No additional message."}`;
    }
    updated.push(proxyRiskMetric);

    // Permission
    const permissionLevel = permissionError
      ? "unknown"
      : permissionData
        ? "high"
        : "low";
    const permissionRiskMetric: RiskMetric = {
      name: "Admin Privileges",
      value: permissionError
        ? "Error"
        : permissionData
          ? `${permissionData.function?.length || 0} functions`
          : "N/A",
      level: permissionLevel,
    };
    if (permissionError) {
      permissionRiskMetric.detail = "Failed to fetch permission information";
    }
    updated.push(permissionRiskMetric);

    // Verification
    const verified = verificationData !== null;
    const verificationLevel = verificationError
      ? "unknown"
      : verified
        ? "low"
        : "high";
    const verificationRiskMetric: RiskMetric = {
      name: "Verification",
      value: verificationError
        ? "Error"
        : verified
          ? "Verified"
          : "Not Verified",
      level: verificationLevel,
    };
    if (verificationError) {
      verificationRiskMetric.detail =
        "Failed to fetch verification information";
    } else if (verificationData) {
      verificationRiskMetric.detail =
        (verificationData.verification
          ? `Verification status: ${verificationData.verification}\n`
          : "") +
        (verificationData.verifiedAt
          ? `Verified at: ${verificationData.verifiedAt}`
          : "No verification time found.");
    } else {
      verificationRiskMetric.detail =
        "This contract is not verified on Sourcify.";
    }
    updated.push(verificationRiskMetric);

    // Audit
    const audits = Array.isArray(auditData) ? auditData : [];
    const hasAudits = audits.length > 0;
    const auditLevel = auditError ? "unknown" : hasAudits ? "low" : "medium";
    const auditRiskMetric: RiskMetric = {
      name: "Audit",
      value: auditError ? "Error" : hasAudits ? "Audited" : "Not Audited",
      level: auditLevel,
    };
    if (auditError) {
      auditRiskMetric.detail = "Failed to fetch audit information";
    } else if (hasAudits) {
      const protocol = audits[0]?.protocol || "Unknown";
      const version = audits[0]?.version || "Unknown";
      const auditDetails = audits
        .map((a, i) => {
          return `🔹 Audit ${i + 1} by ${a.company}${a.url ? `\n ` : ""}`;
        })
        .join("");
      auditRiskMetric.detail = `Protocol: ${protocol}\nVersion: ${version}\n\n${auditDetails}`;
    } else {
      auditRiskMetric.detail = "No audit found for this contract.";
    }
    updated.push(auditRiskMetric);

    setRiskMetrics(updated);
  }, [
    proxyData,
    proxyError,
    permissionData,
    permissionError,
    verificationData,
    verificationError,
    auditData,
    auditError,
  ]);

  useEffect(() => {
    if (
      address &&
      !proxyLoading &&
      !permissionLoading &&
      !verificationLoading &&
      !auditLoading
    ) {
      updateRiskMetrics();
    }
  }, [
    address,
    proxyLoading,
    permissionLoading,
    verificationLoading,
    auditLoading,
    updateRiskMetrics,
  ]);

  // Show loading while any query is loading OR while we have data but no processed metrics yet
  const isLoading =
    address &&
    (proxyLoading ||
      permissionLoading ||
      verificationLoading ||
      auditLoading ||
      (riskMetrics.length === 0 &&
        !proxyLoading &&
        !permissionLoading &&
        !verificationLoading &&
        !auditLoading));

  return (
    <div className="h-fit min-h-full w-full bg-white">
      {isLoading ? (
        <div className="flex flex-col items-center justify-center py-10">
          <div className="mt-[100px] animate-pulse rounded-md border border-gray-200 bg-red-100 px-4 py-4 text-sm text-gray-500 italic shadow-sm">
            🔍 Fetching Risk Details...
          </div>
        </div>
      ) : (
        <div className="flex w-full flex-col gap-2 px-4 py-2">
          {riskMetrics.map((metric, index) => (
            <InfoCard
              className="w-full"
              key={index}
              header={
                <div className="flex w-full max-w-none items-center border-b border-[#497D74] py-1">
                  <span className="text-l mr-2 text-sm font-medium text-gray-800">
                    {metric.name}
                  </span>
                  <div className="flex items-center gap-2">
                    {/* Risk Level Badge */}
                    <span
                      className={`rounded-md px-2 py-[3px] font-bold tracking-wide uppercase ${
                        metric.level === "high"
                          ? "bg-red-500 text-white"
                          : metric.level === "medium"
                            ? "bg-orange-500 text-white"
                            : metric.level === "unknown"
                              ? "bg-gray-500 text-white"
                              : "bg-green-500 text-white"
                      } `}
                    >
                      {metric.level} risk
                    </span>
                    {/* Value Badge */}
                    <span
                      className={`rounded-md px-2 py-[3px] text-xs font-medium ${
                        metric.level === "high"
                          ? "border border-red-200 bg-red-50 text-red-700"
                          : metric.level === "medium"
                            ? "border border-orange-200 bg-orange-50 text-orange-700"
                            : metric.level === "unknown"
                              ? "border border-gray-200 bg-gray-50 text-gray-700"
                              : "border border-green-200 bg-green-50 text-green-700"
                      } `}
                    >
                      {metric.value}
                    </span>
                  </div>
                </div>
              }
              content={
                <div className="px-4 text-sm break-words whitespace-pre-wrap text-gray-600">
                  {metric.detail || (
                    <span className="text-gray-400 italic">
                      No further details available.
                    </span>
                  )}
                </div>
              }
            />
          ))}
        </div>
      )}
    </div>
  );
}
