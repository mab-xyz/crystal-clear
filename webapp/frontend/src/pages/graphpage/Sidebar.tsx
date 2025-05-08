import { useState, useEffect } from "react";
import LoadingSpinner from "./LoadingSpinner";
import Interactions from "./Interactions";
import type { JsonData, Node } from "../../types";

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
  const [showRiskExplanation, setShowRiskExplanation] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState(false);

  useEffect(() => {
    if (!loading && jsonData) {
      setActiveTab("Interactions");
    }
  }, [loading, jsonData, setActiveTab]);

  return (
    <div
      style={{
        flex: 1,
        backgroundColor: "#f5f5f5",
        borderLeft: "1px solid #ddd",
        display: "flex",
        flexDirection: "column",
        height: "100%",
        fontFamily: "Funnel Sans, sans-serif",
      }}
    >
      {/* Pinned information section */}
      <div
        style={{
          padding: "15px",
          borderBottom: "1px solid #ddd",
          backgroundColor: "white",
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
          style={{ marginBottom: "5px", display: "flex", alignItems: "center" }}
        >
          <span
            style={{
              fontWeight: "500",
              color: "#555",
              marginRight: "4px",
              fontSize: "14px",
            }}
          >
            Contract Address:{" "}
          </span>
          <span
            style={{
              fontFamily: "monospace",
              fontSize: "14px",
              marginRight: "8px",
              wordBreak: "break-all",
            }}
          >
            {inputAddress ? (
              <span title={inputAddress}>
                {inputAddress.length > 24
                  ? `${inputAddress.substring(0, 10)}...${inputAddress.substring(inputAddress.length - 8)}`
                  : inputAddress}
              </span>
            ) : (
              "No address selected"
            )}
          </span>
          {inputAddress && (
            <div
              style={{
                display: "flex",
                gap: "8px",
                marginLeft: "auto",
              }}
            >
              <button
                onClick={() => {
                  navigator.clipboard.writeText(inputAddress);
                  setCopyFeedback(true);
                  setTimeout(() => setCopyFeedback(false), 2000);
                }}
                style={{
                  border: "none",
                  background: "#f0f0f0",
                  padding: "4px 8px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "11px",
                  display: "flex",
                  alignItems: "center",
                  color: "#555",
                  position: "relative",
                }}
              >
                <span style={{ marginRight: "4px" }}>📋</span>
                {copyFeedback ? "Copied!" : "Copy"}
              </button>

              <a
                href={`https://etherscan.io/address/${inputAddress}`}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  border: "none",
                  background: "#f0f0f0",
                  padding: "4px 8px",
                  borderRadius: "4px",
                  cursor: "pointer",
                  fontSize: "11px",
                  display: "flex",
                  alignItems: "center",
                  color: "#555",
                  textDecoration: "none",
                }}
              >
                <span style={{ marginRight: "4px" }}>🔍</span>
                Etherscan
              </a>
            </div>
          )}
        </div>

        {/* Display block range from API response */}
        {jsonData && (jsonData.from_block || jsonData.to_block) && (
          <div
            style={{
              marginBottom: "5px",
              display: "flex",
              alignItems: "center",
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
            <span style={{ fontFamily: "monospace", fontSize: "14px" }}>
              {jsonData.from_block
                ? jsonData.from_block.toLocaleString()
                : "earliest"}{" "}
              -{" "}
              {jsonData.to_block
                ? jsonData.to_block.toLocaleString()
                : "latest"}
            </span>
          </div>
        )}

        {jsonData && (
          <div
            style={{
              marginTop: "10px",
              padding: "10px",
              backgroundColor: "#f9f9f9",
              borderRadius: "4px",
              border: "1px solid #eee",
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
                  fontWeight: "bold",
                  color: "#333",
                  display: "flex",
                  alignItems: "center",
                }}
              >
                Risk Assessment
                <div
                  style={{
                    width: "16px",
                    height: "16px",
                    borderRadius: "50%",
                    backgroundColor: "#ddd",
                    color: "#666",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "12px",
                    fontWeight: "bold",
                    cursor: "pointer",
                    marginLeft: "8px",
                    position: "relative",
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
                        width: "200px",
                        marginTop: "8px",
                        padding: "8px",
                        backgroundColor: "#f0f0f0",
                        borderRadius: "4px",
                        lineHeight: "1.4",
                        fontSize: "12px",
                        color: "#555",
                        boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
                        zIndex: 10,
                        textAlign: "left",
                        fontWeight: "normal",
                      }}
                    >
                      Risk assessment is based on multiple factors including
                      metrics for immutability, admin privileges, auditing
                      information, and contract dependencies.
                    </div>
                  )}
                </div>
              </div>
              {jsonData ? (
                <div style={{ display: "flex", alignItems: "center" }}>
                  <div
                    style={{
                      width: "12px",
                      height: "12px",
                      backgroundColor: "#4CAF50",
                      borderRadius: "50%",
                      marginRight: "8px",
                    }}
                  ></div>
                  <span>Overall Risk: Placeholder</span>
                </div>
              ) : (
                <span
                  style={{
                    fontSize: "12px",
                    color: "#666",
                    fontStyle: "italic",
                  }}
                >
                  Risk score will be computed after analysis
                </span>
              )}
            </div>
          </div>
        )}
      </div>

      {/* Tabs and content section */}
      <div
        style={{
          display: "flex",
          padding: "0 15px",
          borderBottom: "1px solid #ddd",
          backgroundColor: "white",
        }}
      >
        {["Interactions", "Risk Details", "Dependency"].map((tab) => (
          <div
            key={tab}
            className={`panel-tab ${activeTab === tab ? "active" : ""}`}
            style={{
              padding: "10px 15px",
              cursor: "pointer",
              marginRight: 5,
              borderBottom: activeTab === tab ? "2px solid #d3a2fd" : "none",
              color: activeTab === tab ? "#ff9934" : "inherit",
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
                  backgroundColor: "#e8f4fd",
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
          // padding: "5px",
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
              <div>
                <div style={{ fontWeight: "bold", marginBottom: 10 }}>
                  Risk Metrics
                </div>
                {/* Risk metrics placeholders - would be populated from API */}
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
                          index % 3 === 0
                            ? "#e74c3c"
                            : index % 3 === 1
                              ? "#f39c12"
                              : "#27ae60",
                      }}
                    >
                      {/* Placeholder values - would be replaced with actual data from API */}
                      {index % 3 === 0
                        ? "Placeholder_high"
                        : index % 3 === 1
                          ? "Placeholder_Medium"
                          : "Placeholder_Low"}
                    </span>
                  </div>
                ))}

                <div
                  style={{
                    marginTop: 20,
                    fontSize: 13,
                    color: "#666",
                    lineHeight: "1.5",
                  }}
                >
                  Risk assessment is based on risk metrics. The tools are
                  selected from the state-of-the-art research.
                </div>
              </div>
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
                  <div style={{ fontWeight: "bold" }}>Dependency Analysis</div>
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
