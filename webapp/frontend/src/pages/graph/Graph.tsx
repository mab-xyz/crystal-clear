import React, { useState, useCallback } from "react";
import Header from "../../components/layout/Header";
import Sidebar from "../../components/layout/Sidebar";
import GraphLayout from "../../components/graph/GraphLayout";
import type { GraphData, Node } from "../../components/graph/GraphLayout";
import { useLocalAlert } from "@/components/ui/local-alert";
import { checkApiAvailability } from "@/utils/api";

export default function ContractGraph() {
    const [jsonData, setJsonData] = useState<GraphData | null>(null);
    const [activeTab, setActiveTab] = useState<string>("Risk Score");
    const [inputAddress, setInputAddress] = useState<string>("");
    const [loading, setLoading] = useState<boolean>(false);
    const [fromBlock, setFromBlock] = useState<string>("");
    const [toBlock, setToBlock] = useState<string>("");
    const [selectedNode, setSelectedNode] = useState<Node | null>(null);
    const [highlightAddress, setHighlightAddress] = useState<string | null>(null);
    const { showLocalAlert } = useLocalAlert();

    const fetchData = useCallback(
        async (address: string) => {
            if (!address) return;

            try {
                setLoading(true);

                // Check if API is available before proceeding
                const isAvailable = await checkApiAvailability();

                if (!isAvailable) {
                    console.error("API is not available at port 8000");
                    showLocalAlert("API unavailable. Check port 8000.");
                    setLoading(false);
                    return;
                }

                // Build the URL with optional query parameters
                let url = `http://localhost:8000/v1/analysis/${address}/dependencies`;
                const params = new URLSearchParams();

                console.log(fromBlock, toBlock);
                console.log(typeof fromBlock, typeof toBlock);

                if (fromBlock) params.append("from_block", fromBlock);
                if (toBlock) params.append("to_block", toBlock);

                console.log(params);

                // Add the query parameters to the URL if any exist
                if (params.toString()) {
                    url += `?${params.toString()}`;
                }


                console.log("Fetching data from:", url);
                const response = await fetch(url);
                const data = await response.json();
                setJsonData(data);

                // Automatically switch to Risk tab after data is loaded
                setActiveTab("Risk Details");
            } catch (err) {
                console.error("Failed to fetch data:", err);
                showLocalAlert("Failed to fetch data", 5000,
                );
            } finally {
                setLoading(false);
            }
        },
        [fromBlock, toBlock, showLocalAlert]
    );

    // Handle form submission
    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (inputAddress) {
            fetchData(inputAddress);
        }
    };

    // Handle node click from the graph
    const handleNodeClick = useCallback((node: Node) => {
        setSelectedNode(node);
        setActiveTab("Dependency");
    }, []);

    return (
        <div
            style={{
                height: "100vh",
                width: "100vw",
                display: "flex",
                flexDirection: "column",
                overflow: "hidden",
            }}
        >
            <Header
                inputAddress={inputAddress}
                setInputAddress={setInputAddress}
                fromBlock={fromBlock}
                setFromBlock={setFromBlock}
                toBlock={toBlock}
                setToBlock={setToBlock}
                handleSubmit={handleSubmit}
            />

            <div
                style={{
                    display: "flex",
                    height: "calc(100vh - 60px)",
                    width: "100%",
                    overflow: "hidden",
                }}
            >
                {/* Set explicit width to 61.8% for the graph container */}
                <div style={{ width: "61.8%", height: "100%", overflow: "hidden" }}>
                    <GraphLayout
                        jsonData={jsonData}
                        highlightAddress={highlightAddress}
                        inputAddress={inputAddress}
                        onNodeClick={handleNodeClick}
                    />
                </div>

                {/* Set explicit width to 38.2% for the sidebar */}
                <div style={{ width: "38.2%", height: "100%", overflow: "auto" }}>
                    <Sidebar
                        activeTab={activeTab}
                        setActiveTab={setActiveTab}
                        loading={loading}
                        jsonData={jsonData}
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
}