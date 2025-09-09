import { Interactions } from "@/domains/graph";
import { LoadingSpinner } from "@/shared/components/common";
import RiskDetails from "./RiskDetails";
import type { GraphData, Node, DeploymentInfo } from "@/types";
import { useState, useRef, useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import { useLocalAlert } from "@/shared/components/ui";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/shared/components/ui";
import { useSearchParams } from "react-router";
import { getRiskAnalysis } from "@/domains/contracts";
import { API } from "@/constants";
interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  loading: boolean;
  jsonData: GraphData | null;
  deploymentInfo: DeploymentInfo | null;
  inputAddress: string;
  fromBlock: number | null;
  toBlock: number | null;
  selectedNode: Node | null;
  setSelectedNode: (node: Node | null) => void;
  highlightAddress: string | null;
  setHighlightAddress: (address: string | null) => void;
}

export default function Sidebar({
  activeTab,
  setActiveTab,
  loading,
  jsonData,
  deploymentInfo,
  inputAddress,
  fromBlock,
  toBlock,
  selectedNode,
  setSelectedNode,
  highlightAddress,
  setHighlightAddress,
}: SidebarProps) {
  const { showLocalAlert } = useLocalAlert();
  const [showRiskExplanation, setShowRiskExplanation] = useState(false);
  const [addressCopied, setAddressCopied] = useState(false);
  const [deployerCopied, setDeployerCopied] = useState(false);
  const addressContainerRef = useRef<HTMLSpanElement>(null);
  const [searchParams] = useSearchParams();
  const addressFromParams = searchParams.get("address") || "";
  const [riskScore, setRiskScore] = useState<number | null>(null);
  // Reusable placeholder component
  const PlaceholderMessage = ({
    message,
    bgColor = "bg-gray-50",
    textColor = "text-gray-600",
  }: {
    message: string;
    bgColor?: string;
    textColor?: string;
  }) => (
    <div
      className={`flex flex-col items-center rounded ${bgColor} px-1 py-0.5`}
    >
      <span className={`flex items-center gap-1 text-xs ${textColor} italic`}>
        <svg
          width="12"
          height="12"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
        >
          <path
            d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z"
            fill="currentColor"
          />
        </svg>
        {message}
      </span>
    </div>
  );

  // Cache risk analysis data using TanStack Query
  const { data: riskScoreData } = useQuery({
    queryKey: ["riskAnalysis", jsonData?.address],
    queryFn: () => getRiskAnalysis(jsonData!.address, true),
    enabled: !!jsonData?.address,
    staleTime: API.STALE_TIME_MS,
    gcTime: API.STALE_TIME_MS * 2, // Keep cache for 20 minutes
    retry: API.RETRY_ATTEMPTS,
  });

  useEffect(() => {
    if (riskScoreData !== undefined) {
      setRiskScore(riskScoreData);
    }
  }, [riskScoreData]);

  const getRiskLevel = (score: number | null) => {
    if (score === null) return "Risk Level";
    if (score >= 80) return "High Risk";
    if (score >= 50) return "Medium Risk";
    return "Low Risk";
  };

  const getRiskColor = (score: number | null) => {
    if (score === null) return "#777";
    if (score >= 80) return "#e74c3c";
    if (score >= 50) return "#f39c12";
    return "#27ae60";
  };

  const getRiskBg = (score: number | null) => {
    if (score === null) return "rgba(119, 119, 119, 0.1)";
    if (score >= 80) return "rgba(231, 76, 60, 0.1)";
    if (score >= 50) return "rgba(243, 156, 18, 0.1)";
    return "rgba(39, 174, 96, 0.1)";
  };

  return (
    <div className="flex h-full flex-1 flex-col border-l border-[#2b2b2b] bg-white font-['Funnel_Sans,sans-serif']">
      {/* Pinned information section */}
      <div className="border-b border-gray-300 bg-white p-5 px-4 py-2 shadow-sm">
        <div className="mb-2.5 text-left text-base font-bold">
          Contract Information
        </div>

        <div className="mb-1.5 flex min-h-6 w-full items-center">
          <span className="mr-1 text-left text-sm font-medium text-gray-600">
            Contract Address:{" "}
          </span>

          {!selectedNode && !addressFromParams ? (
            <PlaceholderMessage message="Waiting for an address..." />
          ) : (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span
                    className="mr-2 cursor-pointer rounded text-sm"
                    ref={addressContainerRef}
                  >
                    {jsonData && jsonData.address ? (
                      `${jsonData.address.substring(0, 10)}...${jsonData.address.substring(jsonData.address.length - 8)}`
                    ) : addressFromParams ? (
                      `${addressFromParams.substring(0, 10)}...${addressFromParams.substring(addressFromParams.length - 8)}`
                    ) : (
                      <span className="ml-1 text-gray-600 italic">
                        No address selected
                      </span>
                    )}
                  </span>
                </TooltipTrigger>
                <TooltipContent
                  side="top"
                  sideOffset={-10}
                  className="max-w-full rounded-sm bg-gray-700/90 px-2 py-2 font-mono text-xs break-all text-white shadow-lg"
                >
                  <p>{jsonData?.address || addressFromParams || ""}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          )}
          {(jsonData?.address || addressFromParams) && (
            <div className="ml-auto flex gap-2">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(
                    jsonData?.address || addressFromParams,
                  );
                  setAddressCopied(true);
                  setTimeout(() => setAddressCopied(false), 2000);
                }}
                className="relative flex cursor-pointer items-center rounded-none border-none bg-white text-xs text-gray-600"
              >
                <span className="m-1">
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      fill-rule="evenodd"
                      clip-rule="evenodd"
                      d="M21 6H7V22H15V20H17V18H15V16H17V18H19V16H21V6ZM9 20V8H19V14H13V20H9ZM3 18H5V4H17V2H5H3V4V18Z"
                      fill="#2b2b2b"
                    />
                  </svg>
                </span>
                {addressCopied && (
                  <div className="absolute bottom-full left-1/2 z-10 mb-2 -translate-x-1/2 transform rounded bg-purple-500 px-2 py-1 text-xs whitespace-nowrap text-white">
                    Copied!
                  </div>
                )}
              </button>

              {/* Etherscan link */}
              <a
                href={`https://etherscan.io/address/${jsonData?.address || addressFromParams}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex cursor-pointer items-center rounded-none border-none bg-white text-gray-600 no-underline"
              >
                <svg
                  fill="none"
                  height="16"
                  width="16"
                  viewBox="-2.19622685 .37688013 124.38617733 125.52740941"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="m25.79 58.415a5.157 5.157 0 0 1 5.181-5.156l8.59.028a5.164 5.164 0 0 1 5.164 5.164v32.48c.967-.287 2.209-.593 3.568-.913a4.3 4.3 0 0 0 3.317-4.187v-40.291a5.165 5.165 0 0 1 5.164-5.165h8.607a5.165 5.165 0 0 1 5.164 5.165v37.393s2.155-.872 4.254-1.758a4.311 4.311 0 0 0 2.632-3.967v-44.578a5.164 5.164 0 0 1 5.163-5.164h8.606a5.164 5.164 0 0 1 5.164 5.164v36.71c7.462-5.408 15.024-11.912 21.025-19.733a8.662 8.662 0 0 0 1.319-8.092 60.792 60.792 0 0 0 -58.141-40.829 60.788 60.788 0 0 0 -51.99 91.064 7.688 7.688 0 0 0 7.334 3.8c1.628-.143 3.655-.346 6.065-.63a4.3 4.3 0 0 0 3.815-4.268z"
                    fill="#21325b"
                  />
                  <path
                    d="m25.602 110.51a60.813 60.813 0 0 0 63.371 5.013 60.815 60.815 0 0 0 33.212-54.203c0-1.4-.065-2.785-.158-4.162-22.219 33.138-63.244 48.63-96.423 53.347"
                    fill="#979695"
                  />
                </svg>
              </a>
            </div>
          )}
        </div>

        {/* Display deployer info */}
        <div className="mb-1.5 flex min-h-6 items-center">
          <span className="mr-1 text-sm font-medium text-gray-600">
            Deployer:{" "}
          </span>

          {!selectedNode && !addressFromParams ? (
            <PlaceholderMessage message="Waiting for an address..." />
          ) : deploymentInfo && deploymentInfo.deployer ? (
            <TooltipProvider>
              <Tooltip>
                <TooltipTrigger asChild>
                  <span className="mr-2 cursor-pointer rounded px-1 py-0.5 text-sm">
                    {`${deploymentInfo.deployer.substring(0, 10)}...${deploymentInfo.deployer.substring(deploymentInfo.deployer.length - 8)}`}
                  </span>
                </TooltipTrigger>
                <TooltipContent
                  side="top"
                  sideOffset={-10}
                  className="max-w-full rounded-sm bg-gray-800 px-2.5 py-1.5 font-mono text-xs break-all text-white shadow-lg"
                >
                  <p>{deploymentInfo.deployer}</p>
                </TooltipContent>
              </Tooltip>
            </TooltipProvider>
          ) : deploymentInfo === null &&
            (jsonData?.address || addressFromParams) ? (
            <PlaceholderMessage
              message="Cannot get deployer info"
              bgColor="bg-yellow-100"
              textColor="text-yellow-800"
            />
          ) : (
            <span className="ml-1 text-xs text-gray-500 italic">
              Waiting for deployer info...
            </span>
          )}

          {deploymentInfo && deploymentInfo.deployer && (
            <div className="ml-auto flex gap-2">
              <button
                onClick={() => {
                  navigator.clipboard.writeText(deploymentInfo.deployer);
                  setDeployerCopied(true);
                  setTimeout(() => setDeployerCopied(false), 2000);
                }}
                className="relative flex cursor-pointer items-center rounded-none border-none bg-white text-xs text-gray-600"
              >
                <span className="m-1">
                  <svg
                    width="16"
                    height="16"
                    viewBox="0 0 24 24"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      fill-rule="evenodd"
                      clip-rule="evenodd"
                      d="M21 6H7V22H15V20H17V18H15V16H17V18H19V16H21V6ZM9 20V8H19V14H13V20H9ZM3 18H5V4H17V2H5H3V4V18Z"
                      fill="#2b2b2b"
                    />
                  </svg>
                </span>
                {deployerCopied && (
                  <div className="absolute bottom-full left-1/2 z-10 mb-2 -translate-x-1/2 transform rounded bg-purple-500 px-2 py-1 text-xs whitespace-nowrap text-white">
                    Copied!
                  </div>
                )}
              </button>

              <a
                href={`https://etherscan.io/address/${deploymentInfo.deployer}`}
                target="_blank"
                rel="noopener noreferrer"
                className="flex cursor-pointer items-center rounded-none border-none bg-white text-gray-600 no-underline"
              >
                <svg
                  fill="none"
                  height="16"
                  width="16"
                  viewBox="-2.19622685 .37688013 124.38617733 125.52740941"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="m25.79 58.415a5.157 5.157 0 0 1 5.181-5.156l8.59.028a5.164 5.164 0 0 1 5.164 5.164v32.48c.967-.287 2.209-.593 3.568-.913a4.3 4.3 0 0 0 3.317-4.187v-40.291a5.165 5.165 0 0 1 5.164-5.165h8.607a5.165 5.165 0 0 1 5.164 5.165v37.393s2.155-.872 4.254-1.758a4.311 4.311 0 0 0 2.632-3.967v-44.578a5.164 5.164 0 0 1 5.163-5.164h8.606a5.164 5.164 0 0 1 5.164 5.164v36.71c7.462-5.408 15.024-11.912 21.025-19.733a8.662 8.662 0 0 0 1.319-8.092 60.792 60.792 0 0 0 -58.141-40.829 60.788 60.788 0 0 0 -51.99 91.064 7.688 7.688 0 0 0 7.334 3.8c1.628-.143 3.655-.346 6.065-.63a4.3 4.3 0 0 0 3.815-4.268z"
                    fill="#21325b"
                  />
                  <path
                    d="m25.602 110.51a60.813 60.813 0 0 0 63.371 5.013 60.815 60.815 0 0 0 33.212-54.203c0-1.4-.065-2.785-.158-4.162-22.219 33.138-63.244 48.63-96.423 53.347"
                    fill="#979695"
                  />
                </svg>
              </a>
            </div>
          )}
        </div>

        {/* Display block range */}
        <div className="mb-1.5 flex min-h-6 items-center">
          <span className="mr-1 text-sm font-medium text-gray-600">
            Block Range:{" "}
          </span>
          <span className="text-sm">
            {loading ? (
              <PlaceholderMessage message="Block range will be displayed here..." />
            ) : jsonData && (jsonData.from_block || jsonData.to_block) ? (
              <>
                {jsonData.from_block
                  ? jsonData.from_block.toLocaleString()
                  : "earliest"}{" "}
                -{" "}
                {jsonData.to_block
                  ? jsonData.to_block.toLocaleString()
                  : "latest"}
              </>
            ) : (
              <PlaceholderMessage message="Block range will be displayed here..." />
            )}
          </span>
        </div>

        {/* Risk score panel - always visible */}
        <div className="!mt-2.5 !mb-2.5 rounded-md border border-gray-200 bg-gray-50 p-4 !px-2 !py-2">
          <div className="mb-1.5 flex items-center justify-between">
            <div className="flex w-full items-center">
              {(() => {
                const riskLevel = getRiskLevel(riskScore);
                const riskColor = getRiskColor(riskScore);
                const riskBg = getRiskBg(riskScore);
                const riskTextColor = riskColor;
                const reportDisabled = riskScore === null;

                return (
                  <div className="flex w-full items-center justify-between gap-1">
                    <span
                      className="flex items-center text-base font-bold"
                      style={{ color: riskColor }}
                    >
                      {riskScore !== null ? `${riskScore}/100` : "Risk Score"}

                      <div
                        className="relative ml-1 flex h-4.5 w-4.5 cursor-pointer items-center justify-center rounded-full border border-gray-300 bg-gray-50 text-xs font-bold text-gray-500"
                        onClick={() =>
                          setShowRiskExplanation(!showRiskExplanation)
                        }
                      >
                        ?
                        {showRiskExplanation && (
                          <div className="absolute top-full left-0 z-50 mt-2 w-55 rounded-md border border-gray-200 bg-white px-3 py-2 text-left text-xs leading-4 font-normal text-gray-600 shadow-lg">
                            Risk assessment is based on multiple factors
                            including metrics for immutability, admin
                            privileges, auditing information, and contract
                            dependencies.
                          </div>
                        )}
                      </div>
                    </span>

                    <div className="flex items-center gap-2.5">
                      <span
                        className="rounded px-2 py-1 text-sm font-medium"
                        style={{
                          color: riskTextColor,
                          backgroundColor: riskBg,
                        }}
                      >
                        {riskLevel}
                      </span>

                      <button
                        onClick={() => {
                          if (!reportDisabled) {
                            showLocalAlert(
                              "This functionality is under construction.",
                            );
                          }
                        }}
                        disabled={reportDisabled}
                        className={`flex items-center justify-center rounded border border-gray-300 bg-white px-2 py-1 shadow-sm transition-all duration-200 ${
                          reportDisabled
                            ? "cursor-default text-gray-400 opacity-70"
                            : "cursor-pointer text-gray-600 hover:bg-gray-50"
                        }`}
                        title={
                          reportDisabled
                            ? "Report not available"
                            : "Download report"
                        }
                        onMouseOver={(e) => {
                          if (!reportDisabled)
                            e.currentTarget.style.backgroundColor = "#f5f5f5";
                        }}
                        onMouseOut={(e) => {
                          if (!reportDisabled)
                            e.currentTarget.style.backgroundColor = "white";
                        }}
                      >
                        <svg
                          className="mr-1"
                          fill="none"
                          height="16px"
                          width="16px"
                          xmlns="http://www.w3.org/2000/svg"
                          viewBox="0 0 24 24"
                        >
                          <path
                            d="M11 4h2v8h2v2h-2v2h-2v-2H9v-2h2V4zm-2 8H7v-2h2v2zm6 0v-2h2v2h-2zM4 18h16v2H4v-2z"
                            fill="currentColor"
                          />
                        </svg>
                        <span className="text-xs font-medium">Report</span>
                      </button>
                    </div>
                  </div>
                );
              })()}
            </div>
          </div>
        </div>
      </div>

      {/* Tabs and content section */}
      <div className="flex gap-4 border-b border-[#2b2b2b] bg-white px-4 py-2">
        {["Risk Details", "Interactions", "Dependency"].map((tab) => (
          <div
            key={tab}
            className={`panel-tab mr-1.5 cursor-pointer px-4 py-2.5 ${activeTab === tab ? "active" : ""}`}
            style={{
              borderBottom: activeTab === tab ? "2px solid #c9e0be" : "none",
              color: activeTab === tab ? "#287c84" : "inherit",
              fontWeight: activeTab === tab ? "500" : "normal",
              opacity: tab === "Dependency" && !selectedNode ? 0.5 : 1,
            }}
            onClick={() => {
              if (tab !== "Dependency" || selectedNode) {
                setActiveTab(tab);
              }
            }}
          >
            {tab}
            {tab === "Dependency" && selectedNode && (
              <span className="ml-1.5 rounded-full bg-white px-1.5 py-0.5 text-xs text-blue-500">
                1
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Scrollable content area */}
      <div className="flex-1 overflow-y-auto">
        {loading ? (
          <div className="flex h-full items-center justify-center">
            <LoadingSpinner />
          </div>
        ) : (
          <>
            <div
              style={{
                display: activeTab === "Interactions" ? "block" : "none",
              }}
            >
              <Interactions
                jsonData={jsonData}
                inputAddress={inputAddress}
                highlightAddress={highlightAddress}
                setHighlightAddress={setHighlightAddress}
              />
            </div>

            <div
              style={{
                display: activeTab === "Risk Details" ? "block" : "none",
              }}
            >
              <RiskDetails address={jsonData?.address} />
            </div>

            {activeTab === "Dependency" && selectedNode && (
              <div>
                <div className="mb-4 flex items-center justify-between">
                  <div className="ml-2.5 font-bold">Dependency Analysis</div>
                  <button
                    onClick={() => {
                      setSelectedNode(null);
                      setActiveTab("Risk Details");
                    }}
                    className="flex cursor-pointer items-center border-none bg-transparent text-xs text-gray-400"
                  >
                    <span className="mr-1.5">×</span>
                    Clear
                  </button>
                </div>

                <div className="mb-4 rounded border border-gray-200 bg-white p-3">
                  <div className="mb-2 font-medium">Selected Contract</div>
                  <div className="rounded-sm bg-gray-100 px-2 py-1.5 font-mono text-sm break-all">
                    {selectedNode.id}
                  </div>
                </div>

                <div className="mb-2.5 font-bold">Risk Metrics</div>
                {[
                  "Immutability",
                  "Admin Privileges",
                  "Auditing Information",
                  "GitHub Quality",
                ].map((item, index) => (
                  <div
                    key={index}
                    className="mb-1.5 flex justify-between rounded border border-gray-200 bg-white px-2.5 py-2"
                  >
                    <span>{item}</span>
                    <span
                      style={{
                        fontWeight: "500",
                        color:
                          Math.random() > 0.6
                            ? "#e74c3c"
                            : Math.random() > 0.3
                              ? "#f39c12"
                              : "#27ae60",
                      }}
                    >
                      {Math.random() > 0.6
                        ? "High_placeholder"
                        : Math.random() > 0.3
                          ? "Medium_placeholder"
                          : "Low_placeholder"}
                    </span>
                  </div>
                ))}

                <div className="mt-4 mb-4">
                  <div className="mb-2.5 font-bold">Interaction Types</div>
                  <div className="flex flex-wrap gap-2">
                    {["some_type", "some_type", "some_type"].map(
                      (type, index) => (
                        <div
                          key={index}
                          className="rounded-full bg-blue-50 px-2.5 py-1.5 text-xs font-medium text-blue-500"
                        >
                          {type}
                        </div>
                      ),
                    )}
                  </div>
                </div>

                <div className="mt-5 text-left text-sm leading-relaxed text-gray-500">
                  Dependency risks can propagate through the contract network.
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
