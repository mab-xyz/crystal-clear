import React, { useState, useCallback, useEffect } from "react";
import { useSearchParams } from "react-router";
import Header from "../../components/layout/Header";
import Sidebar from "../../components/layout/Sidebar";
import GraphLayout from "../../components/graph/GraphLayout";
import type { GraphData, Node } from "../../components/graph/GraphLayout";
import { useLocalAlert } from "@/components/ui/local-alert";
import { fetchGraphData } from "@/utils/graphFetcher";
import '../../App.css';

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
    const [searchParams] = useSearchParams();

    const fetchData = useCallback(
        async (address: string, fromBlock: string, toBlock: string) => {
            if (!address) return;

            setLoading(true);

            console.log("address in graph", address);
            console.log("fromBlock in graph", fromBlock);
            console.log("toBlock in graph", toBlock);

            const data = await fetchGraphData(
                address,
                fromBlock,
                toBlock,
                (message) => showLocalAlert(message, 5000)
            );

            if (data) {
                setJsonData(data);
                // Automatically switch to Risk tab after data is loaded
                setActiveTab("Risk Details");
            }

            setLoading(false);
        },
        [fromBlock, toBlock, showLocalAlert]
    );

    // Read address from URL parameters when component mounts
    useEffect(() => {
        const searchParams = new URLSearchParams(location.search);
        const addressParam = searchParams.get('address');
        const fromBlockParam = searchParams.get('from_block');
        const toBlockParam = searchParams.get('to_block');

        if (addressParam) {
            setInputAddress(addressParam);
            fetchData(
                addressParam,
                fromBlockParam || "",
                toBlockParam || ""
            );
        }
    }, [searchParams, fetchData]);

    // Handle form submission
    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (inputAddress) {
            fetchData(inputAddress, fromBlock, toBlock);
        }
    };

    // Handle node click from the graph
    const handleNodeClick = useCallback((node: Node) => {
        setSelectedNode(node);
        setActiveTab("Dependency");
    }, []);

    useEffect(() => {
        // Check if the page is being reloaded
        const navigationEntries = performance.getEntriesByType("navigation") as PerformanceNavigationTiming[];
        if (navigationEntries[0]?.type === "reload") {
            // Redirect to the graph page
            window.location.href = `${window.location.origin}/graph`; // Adjust the path as needed
        }
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