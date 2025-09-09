import React, { useState, useCallback, useEffect, useRef, memo } from "react";
import { useLocation } from "react-router";
import { Header, Sidebar } from "@/app/index";
import { GraphLayout } from "@/domains/graph";
import { useLocalAlert } from "@/shared/components/ui";
import { useGraphAnalysis } from "@/shared/hooks/useGraphAnalysis";
import { useAppContext } from "@/app/contexts/AppContext";
import { getDeploymentInfo } from "@/domains/contracts";
import { DEV, LAYOUT } from "@/constants";
import styles from "./Graph.module.css";

import type { Node, DeploymentInfo } from "@/types";

const ContractGraph = memo(function ContractGraph() {
  const [deploymentInfo, setDeploymentInfo] = useState<DeploymentInfo | null>(
    null,
  );
  const [inputAddress, setInputAddress] = useState<string>("");
  const [fromBlock, setFromBlock] = useState<string>("");
  const [toBlock, setToBlock] = useState<string>("");
  const { showLocalAlert } = useLocalAlert();
  const { state, setCurrentTab, setGlobalError } = useAppContext();
  const location = useLocation();

  // Use custom hook for graph analysis state management
  const {
    jsonData,
    apiAvailability,
    loading,
    error,
    selectedNode,
    setSelectedNode,
    highlightAddress,
    setHighlightAddress,
    refetchData,
    hasError,
  } = useGraphAnalysis({
    inputAddress,
    fromBlock,
    toBlock,
    autoExecute: false,
  });

  // Auto-switch to Risk tab when data loads and handle errors
  useEffect(() => {
    if (jsonData) {
      setCurrentTabRef.current("Risk Details");
    }
    if (hasError && error) {
      console.error("Error fetching graph data:", error);
      setGlobalErrorRef.current(error.message);
      alertRef.current(
        "Failed to fetch graph data. Please try again later.",
        DEV.ALERT_TIMEOUT_MS,
      );
    }
  }, [jsonData, hasError, error]);

  // Read address from URL parameters when component mounts
  useEffect(() => {
    const searchParams = new URLSearchParams(location.search);
    const addressParam = searchParams.get("address");
    const fromBlockParam = searchParams.get("from_block");
    const toBlockParam = searchParams.get("to_block");

    console.log("addressParam in graph", addressParam);
    console.log("fromBlockParam in graph", fromBlockParam);
    console.log("toBlockParam in graph", toBlockParam);
    console.log("apiAvailability in graph", apiAvailability);

    if (addressParam) {
      setInputAddress(addressParam);
      setFromBlock(fromBlockParam || "");
      setToBlock(toBlockParam || "");

      // Auto-trigger analysis when URL has parameters (user navigated directly to analysis URL)
      setTimeout(() => {
        refetchData();
      }, 100); // Small delay to ensure state is set
    }
  }, [location.search]); // Only run when URL search params change

  const alertRef = useRef(showLocalAlert);
  alertRef.current = showLocalAlert;

  const setCurrentTabRef = useRef(setCurrentTab);
  setCurrentTabRef.current = setCurrentTab;

  const setGlobalErrorRef = useRef(setGlobalError);
  setGlobalErrorRef.current = setGlobalError;

  useEffect(() => {
    if (!inputAddress) return;

    const fetch = async () => {
      try {
        const info = await getDeploymentInfo(
          inputAddress,
          apiAvailability,
          // Don't pass alert function to avoid showing alerts
        );
        setDeploymentInfo((prev) => {
          if (JSON.stringify(prev) === JSON.stringify(info)) return prev;
          return info;
        });
      } catch (error) {
        console.error("Failed to fetch deployment info:", error);
        // Don't show alert, just log the error
      }
    };
    fetch();
  }, [inputAddress, apiAvailability]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    // Trigger refetch using the hook's method
    if (inputAddress) {
      refetchData();
    }
  };

  // Handle node click from the graph
  const handleNodeClick = useCallback(
    (node: Node) => {
      setSelectedNode(node);
      setCurrentTab("Dependency");
    },
    [setSelectedNode, setCurrentTab],
  );

  return (
    <div className={styles["graphPageContainer"]}>
      <Header
        inputAddress={inputAddress}
        setInputAddress={setInputAddress}
        fromBlock={fromBlock}
        setFromBlock={setFromBlock}
        toBlock={toBlock}
        setToBlock={setToBlock}
        handleSubmit={handleSubmit}
      />

      <div className={styles["graphContentContainer"]}>
        {/* Graph container with golden ratio width */}
        <div
          className={styles["graphContainer"]}
          style={{ width: `${LAYOUT.GRAPH_WIDTH_RATIO * 100}%` }}
        >
          <GraphLayout
            jsonData={jsonData || null}
            highlightAddress={highlightAddress}
            inputAddress={inputAddress}
            onNodeClick={handleNodeClick}
          />
        </div>

        {/* Sidebar container with golden ratio width */}
        <div
          className={styles["sidebarContainer"]}
          style={{ width: `${LAYOUT.SIDEBAR_WIDTH_RATIO * 100}%` }}
        >
          <Sidebar
            activeTab={state.currentTab}
            setActiveTab={setCurrentTab}
            loading={loading}
            jsonData={jsonData || null}
            deploymentInfo={deploymentInfo}
            inputAddress={inputAddress}
            setHighlightAddress={setHighlightAddress}
            highlightAddress={highlightAddress}
            fromBlock={fromBlock ? parseInt(fromBlock) : null}
            toBlock={toBlock ? parseInt(toBlock) : null}
            selectedNode={selectedNode}
            setSelectedNode={setSelectedNode}
          />
        </div>
      </div>
    </div>
  );
});

export default ContractGraph;
