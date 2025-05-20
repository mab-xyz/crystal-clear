import Interactions from "../../components/graph/Interactions";
import LoadingSpinner from "../../components/common/LoadingSpinner";
import RiskDetails from "../../components/layout/RiskDetails";
import type { JsonData, Node } from "../../types";
import { useState, useRef } from "react";
import { useLocalAlert } from "../ui/local-alert";


interface SidebarProps {
  activeTab: string;
  setActiveTab: (tab: string) => void;
  loading: boolean;
  jsonData: JsonData | null;
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
  const [copyFeedback, setCopyFeedback] = useState(false);
  const addressContainerRef = useRef<HTMLSpanElement>(null);

  // Reusable placeholder component
  const PlaceholderMessage = ({ message }: { message: string }) => (
    <div style={{
      display: "flex",
      flexDirection: "column",
      alignItems: "center",
      padding: "2px 4px",
      backgroundColor: "#f8f9fa",
      borderRadius: "4px",
    }}>
      <span style={{
        fontStyle: "italic",
        color: "#666",
        fontSize: "12px",
        display: "flex",
        alignItems: "center",
        gap: "4px"
      }}>
        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8zm-1-13h2v6h-2zm0 8h2v2h-2z" fill="#888" />
        </svg>
        {message}
      </span>
    </div>
  );

  return (
    <div
      style={{
        flex: 1,
        backgroundColor: "#f5f5f5",
        borderLeft: "1px solid #2b2b2b",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        fontFamily: "Funnel Sans, sans-serif",
      }}
    >
      {/* Pinned information section */}
      <div
        style={{
          padding: "20px",
          borderBottom: "1px solid #e0e0e0",
          backgroundColor: "white",
          boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
        }}
      >
        <div
          style={{
            fontWeight: "bold",
            fontSize: "16px",
            marginBottom: "10px",
            textAlign: "left",
          }}
        >
          Contract Information
        </div>

        <div
          style={{
            marginBottom: "5px",
            display: "flex",
            alignItems: "center",
            width: "100%",
            minHeight: "24px",
          }}
        >
          <span
            style={{
              fontWeight: "500",
              color: "#555",
              marginRight: "4px",
              fontSize: "14px",
              textAlign: "left"
            }}
          >
            Contract Address:{" "}
          </span>

          {!selectedNode && !inputAddress ? (
            <PlaceholderMessage message="Waiting for an address..." />
          ) : (
            <span
              style={{
                fontSize: "14px",
                marginRight: "8px",
                cursor: "help",
              }}
              title={jsonData?.address || inputAddress || ""}
              ref={addressContainerRef}
            >
              {jsonData && jsonData.address ? (
                `${jsonData.address.substring(0, 10)}...${jsonData.address.substring(jsonData.address.length - 8)}`
              ) : inputAddress ? (
                `${inputAddress.substring(0, 10)}...${inputAddress.substring(inputAddress.length - 8)}`
              ) : (
                <span style={{ fontStyle: "italic", color: "#666", marginLeft: "4px" }}>No address selected</span>
              )}
            </span>
          )}
          {(jsonData?.address || inputAddress) && (
            <div
              style={{
                display: "flex",
                gap: "8px",
                marginLeft: "auto"
              }}
            >
              <button
                onClick={() => {
                  navigator.clipboard.writeText(jsonData?.address || inputAddress);
                  setCopyFeedback(true);
                  setTimeout(() => setCopyFeedback(false), 2000);
                }}
                style={{
                  border: "none",
                  background: "#fff",
                  borderRadius: "0px",
                  cursor: "pointer",
                  fontSize: "11px",
                  display: "flex",
                  alignItems: "center",
                  color: "#555",
                  position: "relative",
                }}
              >
                <span style={{ margin: "4px" }}>
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path fill-rule="evenodd" clip-rule="evenodd" d="M21 6H7V22H15V20H17V18H15V16H17V18H19V16H21V6ZM9 20V8H19V14H13V20H9ZM3 18H5V4H17V2H5H3V4V18Z" fill="#2b2b2b" />
                  </svg>
                </span>
                {copyFeedback && (
                  <div style={{
                    position: "absolute",
                    bottom: "100%",
                    left: "50%",
                    transform: "translateX(-50%)",
                    marginBottom: "8px",
                    backgroundColor: "#7469B6",
                    color: "white",
                    padding: "4px 8px",
                    borderRadius: "4px",
                    fontSize: "11px",
                    whiteSpace: "nowrap",
                    zIndex: 10,
                  }}>
                    Copied!
                  </div>
                )}
              </button>

              {/* Etherscan link */}
              <a
                href={`https://etherscan.io/address/${jsonData?.address || inputAddress}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  border: "none",
                  background: "#fff",
                  borderRadius: "0px",
                  cursor: "pointer",
                  display: "flex",
                  alignItems: "center",
                  color: "#555",
                  textDecoration: "none",
                }}
              >
                <svg fill="none" height="16" width="16" viewBox="-2.19622685 .37688013 124.38617733 125.52740941" xmlns="http://www.w3.org/2000/svg"><path d="m25.79 58.415a5.157 5.157 0 0 1 5.181-5.156l8.59.028a5.164 5.164 0 0 1 5.164 5.164v32.48c.967-.287 2.209-.593 3.568-.913a4.3 4.3 0 0 0 3.317-4.187v-40.291a5.165 5.165 0 0 1 5.164-5.165h8.607a5.165 5.165 0 0 1 5.164 5.165v37.393s2.155-.872 4.254-1.758a4.311 4.311 0 0 0 2.632-3.967v-44.578a5.164 5.164 0 0 1 5.163-5.164h8.606a5.164 5.164 0 0 1 5.164 5.164v36.71c7.462-5.408 15.024-11.912 21.025-19.733a8.662 8.662 0 0 0 1.319-8.092 60.792 60.792 0 0 0 -58.141-40.829 60.788 60.788 0 0 0 -51.99 91.064 7.688 7.688 0 0 0 7.334 3.8c1.628-.143 3.655-.346 6.065-.63a4.3 4.3 0 0 0 3.815-4.268z" fill="#21325b" /><path d="m25.602 110.51a60.813 60.813 0 0 0 63.371 5.013 60.815 60.815 0 0 0 33.212-54.203c0-1.4-.065-2.785-.158-4.162-22.219 33.138-63.244 48.63-96.423 53.347" fill="#979695" /></svg>
              </a>
            </div>
          )}
        </div>

        {/* Display block range */}
        <div
          style={{
            marginBottom: "5px",
            display: "flex",
            alignItems: "center",
            minHeight: "24px",
          }}
        >
          <span
            style={{
              fontWeight: "500",
              color: "#555",
              marginRight: "4px",
              fontSize: "14px",
            }}
          >
            Block Range:{" "}
          </span>
          <span style={{
            fontSize: "14px"
          }}>
            {loading ? (
              <PlaceholderMessage message="Block range will be displayed here..." />
            ) : (
              jsonData && (jsonData.from_block || jsonData.to_block) ? (
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
              )
            )}
          </span>
        </div>

        {/* Risk score panel - always visible */}
        <div
          style={{
            marginTop: "10px",
            padding: "15px",
            backgroundColor: "#f9f9f9",
            borderRadius: "6px",
            border: "1px solid #eee",
            // boxShadow: "0 1px 3px rgba(0,0,0,0.05)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "5px",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "center",
                width: "100%",
              }}
            >
              {(() => {
                const riskLevel = jsonData ? "High Risk" : "Risk Level";
                const riskScore = jsonData ? "59/100" : "Risk Score";
                const riskColor = jsonData ? "#e74c3c" : "#2b2b2b";
                const riskBg = jsonData ? "rgba(231, 76, 60, 0.1)" : "rgba(119, 119, 119, 0.1)";
                const riskTextColor = jsonData ? "#e74c3c" : "#777";
                const reportDisabled = !jsonData;

                return (
                  <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", width: "100%" }}>
                    <span style={{ fontWeight: "bold", color: riskColor, fontSize: "16px", display: "flex", alignItems: "center" }}>
                      {riskScore}
                      <div
                        style={{
                          width: "18px",
                          height: "18px",
                          borderRadius: "50%",
                          backgroundColor: "#f0f0f0",
                          color: "#777",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          fontSize: "12px",
                          fontWeight: "bold",
                          cursor: "pointer",
                          marginLeft: "10px",
                          position: "relative",
                          border: "1px solid #ddd",
                        }}
                        onClick={() => setShowRiskExplanation(!showRiskExplanation)}
                      >
                        ?
                        {showRiskExplanation && (
                          <div
                            style={{
                              position: "absolute",
                              top: "100%",
                              left: "0",
                              width: "220px",
                              marginTop: "8px",
                              padding: "10px 12px",
                              backgroundColor: "#fff",
                              borderRadius: "6px",
                              lineHeight: "1.5",
                              fontSize: "12px",
                              color: "#555",
                              boxShadow: "0 3px 8px rgba(0,0,0,0.15)",
                              zIndex: 10,
                              textAlign: "left",
                              fontWeight: "normal",
                              border: "1px solid #eee",
                            }}
                          >
                            Risk assessment is based on multiple factors including
                            metrics for immutability, admin privileges, auditing
                            information, and contract dependencies.
                          </div>
                        )}
                      </div>
                    </span>

                    <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                      <span
                        style={{
                          fontWeight: "500",
                          color: riskTextColor,
                          backgroundColor: riskBg,
                          padding: "4px 10px",
                          borderRadius: "4px",
                          fontSize: "13px"
                        }}
                      >
                        {riskLevel}
                      </span>

                      <button
                        onClick={() => {
                          if (!reportDisabled) {
                            showLocalAlert("This functionality is under construction.");
                          }
                        }}
                        disabled={reportDisabled}
                        style={{
                          border: "1px solid #ddd",
                          background: "white",
                          cursor: reportDisabled ? "default" : "pointer",
                          display: "flex",
                          alignItems: "center",
                          justifyContent: "center",
                          padding: "4px 8px",
                          borderRadius: "4px",
                          color: reportDisabled ? "#aaa" : "#555",
                          boxShadow: "0 1px 2px rgba(0,0,0,0.05)",
                          opacity: reportDisabled ? 0.7 : 1,
                          transition: "all 0.2s ease",
                        }}
                        title={reportDisabled ? "Report not available" : "Download report"}
                        onMouseOver={(e) => {
                          if (!reportDisabled) e.currentTarget.style.backgroundColor = "#f5f5f5";
                        }}
                        onMouseOut={(e) => {
                          if (!reportDisabled) e.currentTarget.style.backgroundColor = "white";
                        }}
                      >
                        <svg style={{ marginRight: "4px" }} fill="none" height="16px" width="16px" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
                          <path d="M11 4h2v8h2v2h-2v2h-2v-2H9v-2h2V4zm-2 8H7v-2h2v2zm6 0v-2h2v2h-2zM4 18h16v2H4v-2z" fill="currentColor" />
                        </svg>
                        <span style={{ fontSize: "12px", fontWeight: "500" }}>Report</span>
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
      <div
        style={{
          display: "flex",
          padding: "0 15px",
          borderBottom: "1px solid #2b2b2b",
          backgroundColor: "white",
        }}
      >
        {["Risk Details", "Interactions", "Dependency"].map((tab) => (
          <div
            key={tab}
            className={`panel-tab ${activeTab === tab ? "active" : ""}`}
            style={{
              padding: "10px 15px",
              cursor: "pointer",
              marginRight: 5,
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
              <span
                style={{
                  fontSize: "10px",
                  backgroundColor: "white",
                  color: "#3399ff",
                  padding: "2px 5px",
                  borderRadius: "10px",
                  marginLeft: "5px",
                }}
              >
                1
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Scrollable content area */}
      <div
        style={{
          overflowY: "auto",
          flex: 1,
        }}
      >
        {loading ? (
          <LoadingSpinner
            inputAddress={inputAddress}
            fromBlock={fromBlock}
            toBlock={toBlock}
          />
        ) : (
          <>
            {activeTab === "Interactions" && (
              <Interactions
                jsonData={jsonData}
                inputAddress={inputAddress}
                highlightAddress={highlightAddress}
                setHighlightAddress={setHighlightAddress}
              />
            )}

            {activeTab === "Risk Details" && (
              <RiskDetails
                jsonData={jsonData}
              />
            )}

            {activeTab === "Dependency" && selectedNode && (
              <div>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    marginBottom: 15,
                  }}
                >
                  <div style={{ fontWeight: "bold", marginLeft: 10 }}>Dependency Analysis</div>
                  <button
                    onClick={() => {
                      setSelectedNode(null);
                      setActiveTab("Risk Details");
                    }}
                    style={{
                      border: "none",
                      background: "none",
                      color: "#999",
                      cursor: "pointer",
                      fontSize: "12px",
                      display: "flex",
                      alignItems: "center",
                    }}
                  >
                    <span style={{ marginRight: "5px" }}>×</span>
                    Clear
                  </button>
                </div>

                <div
                  style={{
                    padding: "12px",
                    backgroundColor: "white",
                    borderRadius: "4px",
                    border: "1px solid #eee",
                    marginBottom: "15px",
                  }}
                >
                  <div style={{ fontWeight: "500", marginBottom: "8px" }}>
                    Selected Contract
                  </div>
                  <div
                    style={{
                      fontFamily: "monospace",
                      fontSize: "13px",
                      padding: "5px 8px",
                      backgroundColor: "#f5f5f5",
                      borderRadius: "3px",
                      wordBreak: "break-all",
                    }}
                  >
                    {selectedNode.id}
                  </div>
                </div>

                <div style={{ fontWeight: "bold", marginBottom: 10 }}>
                  Risk Metrics
                </div>
                {[
                  "Immutability",
                  "Admin Privileges",
                  "Auditing Information",
                  "GitHub Quality",
                ].map((item, index) => (
                  <div
                    key={index}
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      padding: "8px 10px",
                      marginBottom: 5,
                      backgroundColor: "white",
                      borderRadius: "4px",
                      border: "1px solid #eee",
                    }}
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

                <div style={{ marginTop: 15, marginBottom: 15 }}>
                  <div style={{ fontWeight: "bold", marginBottom: 10 }}>
                    Interaction Types
                  </div>
                  <div
                    style={{
                      display: "flex",
                      flexWrap: "wrap",
                      gap: "8px",
                    }}
                  >
                    {["some_type", "some_type", "some_type"].map(
                      (type, index) => (
                        <div
                          key={index}
                          style={{
                            padding: "5px 10px",
                            backgroundColor: "#e8f4fd",
                            color: "#3399ff",
                            borderRadius: "15px",
                            fontSize: "12px",
                            fontWeight: "500",
                          }}
                        >
                          {type}
                        </div>
                      ),
                    )}
                  </div>
                </div>

                <div
                  style={{
                    marginTop: 20,
                    fontSize: 13,
                    color: "#666",
                    lineHeight: "1.5",
                    textAlign: "left"
                  }}
                >
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
