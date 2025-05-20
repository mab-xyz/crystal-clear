import React, { useState, useEffect } from "react";
import { useLocation, useNavigate } from "react-router";
import GraphLayout from "../../components/graph/GraphLayout";
import { useLocalAlert } from "@/components/ui/local-alert";
import { Button } from "@/components/ui/button";
import { getDefaultBlockRange } from "@/utils/defaultAnalyze";
import { popularContracts } from "@/utils/popularContracts";

// load sample graph data from json file
import SAMPLE_GRAPH_DATA from "./home_graph_eg.json";


export default function HomePage() {
    const [inputAddress, setInputAddress] = useState<string>("");
    const [highlightAddress, setHighlightAddress] = useState<string | null>(null);
    const [loading] = useState<boolean>(false);
    const { showLocalAlert } = useLocalAlert();
    const location = useLocation();
    const navigate = useNavigate();

    useEffect(() => {
        const searchParams = new URLSearchParams(location.search);
        const addressParam = searchParams.get('address');
        if (addressParam) {
            setInputAddress(addressParam);
        }
    }, [location]);

    // Handle form submission
    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();

        if (!inputAddress || inputAddress.trim() === "") {
            showLocalAlert("Please enter a contract address.");
            return;
        }

        try {
            // Use getDefaultBlockRange to set the from_block and to_block
            const { fromBlock, toBlock } = await getDefaultBlockRange();
            console.log("fromBlock", fromBlock);
            console.log("toBlock", toBlock);



            // Navigate to the graph page with all necessary parameters
            navigate(`/graph?address=${inputAddress}&from_block=${fromBlock}&to_block=${toBlock}`);

            // The graph page should read these parameters from its own URL
        } catch (error) {
            console.error("Error during submission:", error);
            showLocalAlert("An error occurred. Please try again.");
        }
    };

    // Handle node click for the demo graph using useCallback
    const handleNodeClick = React.useCallback((node: any) => {
        // remove the hightlight address in homepage graph
        setHighlightAddress(null);
    }, []);

    // Function to handle quick address selection
    const handleAddressSelect = (address: string, name: string): void => {
        // If the address is already selected, clear it (unselect)
        if (inputAddress === address) {
            setInputAddress("");
        } else {
            setInputAddress(address);
        }
    };

    return (
        <div
            style={{
                width: "100vw",
                minHeight: "100vh",
                display: "flex",
                flexDirection: "column",
                backgroundColor: "#fff",
                // border: "1px solid red"
            }}
        >
            {/* Header Section */}
            <header style={{
                width: "100%",
                padding: "1rem",
                backgroundColor: "white",
                textAlign: "center",
                // borderBottom: "1px solid #ddd"
            }}>
                {/* Future navigation elements will go here */}
            </header>

            <div
                style={{
                    minHeight: "100vh",
                    display: "flex",
                    flex: "1",
                    width: "100%",
                    alignItems: "center",
                    // border: "1px solid orange",
                }}
            >
                {/* Left side: Interactive network graph visualization */}
                <div style={{
                    width: "50%",
                    height: "100%",
                    overflow: "hidden",
                    position: "relative",
                    display: "flex",
                    justifyContent: "center",
                    alignItems: "center",
                    marginLeft: "2rem",
                    marginRight: "1rem",
                    padding: "1rem",
                    borderRadius: "50%",
                    // border: "1px solid red"
                }}>
                    {/* Interactive sample graph */}
                    <GraphLayout
                        jsonData={SAMPLE_GRAPH_DATA}
                        highlightAddress={highlightAddress}
                        inputAddress={"0xSampleMainContract"}
                        onNodeClick={handleNodeClick}
                        isHomepage={true}
                    />
                </div>

                {/* Right side: Name and search bar */}
                <div style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    width: "50%",
                    height: "80%",
                    overflow: "auto",
                    padding: "2rem",
                    marginRight: "2rem",
                    marginLeft: "1rem",
                    backgroundColor: "white"
                }}>
                    <div style={{
                        width: "100%",
                        backgroundColor: "white",
                        padding: "1.5rem",
                        borderRadius: "4px",
                        marginBottom: "1.5rem",

                    }}>
                        <h2 style={{ color: "#312750", marginBottom: "0.5rem", fontSize: "3rem", fontFamily: "Jersey 20, 'Funnel Sans'" }}>
                            Crystal Clear
                        </h2>
                        <p style={{ color: "#2b2b2b", marginBottom: "1rem", fontSize: "1.2rem" }}>
                            A Smart Contract Is Only as Secure as Its Weakest Dependency.
                        </p>

                        <div
                            style={{
                                display: "flex",
                                alignItems: "center",
                                paddingTop: "8px",
                                backgroundColor: "white",
                                gap: "8px",
                                justifyContent: "center",
                            }}
                        >
                            {/* Search form */}
                            <form onSubmit={handleSubmit} style={{
                                height: "100%",
                                marginTop: "1.5rem",
                                width: "80%",
                                display: "flex",
                                flexDirection: "column",
                                justifyContent: "left"
                            }}>
                                <div style={{ marginBottom: "1rem", width: "100%" }}>
                                    <div style={{
                                        display: "flex",
                                        width: "100%",
                                        gap: "0.5rem",
                                    }}>
                                        <input
                                            type="text"
                                            value={inputAddress}
                                            onChange={(e) => setInputAddress(e.target.value)}
                                            placeholder="Enter contract address (0x...)"
                                            style={{
                                                flex: 1,
                                                padding: "0.8rem",
                                                border: "1px solid #ddd",
                                                borderRadius: "4px",
                                                fontSize: "0.9rem",
                                            }}
                                            onKeyDown={(e) => {
                                                if (e.key === 'Enter') {
                                                    handleSubmit(e);
                                                }
                                            }}
                                        />
                                        <Button variant="outline"
                                            type="submit"
                                            style={{
                                                padding: "0 1.5rem",
                                                height: "auto",
                                                color: "#2b2b2b",
                                                borderRadius: "2px",
                                            }}
                                            disabled={loading}
                                        >
                                            {loading ? "Loading..." : "Analyze"}
                                        </Button>
                                    </div>
                                </div>

                                {/* Popular Protocols Section */}
                                <div
                                    style={{
                                        display: "flex",
                                        alignItems: "center",
                                        paddingTop: "8px",
                                        paddingBottom: "8px",
                                        backgroundColor: "white",
                                        gap: "8px",
                                    }}
                                >
                                    <span
                                        style={{
                                            fontSize: "14px",
                                            color: "#666",
                                            whiteSpace: "nowrap",
                                        }}
                                    >
                                        Try protocols:
                                    </span>
                                    <div style={{ display: "flex", gap: "8px", overflow: "auto", paddingBottom: "4px" }}>
                                        {popularContracts.map((contract, index) => (
                                            <Button
                                                key={index}
                                                variant="link"
                                                type="button"
                                                onClick={() =>
                                                    handleAddressSelect(contract.address, contract.name)
                                                }
                                                style={{
                                                    padding: "4px 8px",
                                                    // height: "28px",
                                                    fontSize: "14px",
                                                    whiteSpace: "nowrap",
                                                    borderRadius: "4px",

                                                }}
                                            >
                                                {contract.name}
                                            </Button>
                                        ))}
                                    </div>
                                </div>
                            </form>
                        </div>
                    </div>
                </div>
            </div>



        </div>
    );
}

