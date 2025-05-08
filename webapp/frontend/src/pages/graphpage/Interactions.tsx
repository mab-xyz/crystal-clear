import { useState } from "react";
import type { Edge, JsonData } from "../../types";

import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuCheckboxItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Button } from "@/components/ui/button";
import { Settings } from "lucide-react";

interface InteractionsProps {
    jsonData: JsonData | null;
    inputAddress: string;
    highlightAddress: string | null;
    setHighlightAddress: (address: string | null) => void;
}

interface EnhancedEdge extends Edge {
    interactionType: "Direct" | "Indirect";
    sourceName?: string;
    targetName?: string;
}

export default function Interactions({
    jsonData,
    inputAddress,
    highlightAddress,
    setHighlightAddress,
}: InteractionsProps) {
    // Add state for sorting
    const [sortField, setSortField] = useState<string | null>(null);
    const [sortDirection, setSortDirection] = useState<"asc" | "desc">("asc");
    const [showTransitiveInteractions, setShowTransitiveInteractions] =
        useState<boolean>(true);
    const [searchQuery, setSearchQuery] = useState<string>("");
    // Add state for showing original addresses
    const [showOriginalAddresses, setShowOriginalAddresses] =
        useState<boolean>(false);

    // Get the actual address from jsonData if available, otherwise use inputAddress
    const contractAddress = jsonData?.address ? jsonData.address.toLowerCase() : inputAddress.toLowerCase();

    // Function to handle sort clicks
    const handleSort = (field: string) => {
        if (sortField === field) {
            // Toggle direction if clicking the same field
            setSortDirection(sortDirection === "asc" ? "desc" : "asc");
        } else {
            // Set new field and default to ascending
            setSortField(field);
            setSortDirection("asc");
        }
    };

    // Function to sort edges
    const sortEdges = (
        edges: EnhancedEdge[],
        field: string | null,
        direction: "asc" | "desc",
    ) => {
        if (!field) return edges;

        return [...edges].sort((a, b) => {
            let valueA: string | number;
            let valueB: string | number;

            if (field === "address") {
                // For direct interactions, sort by target
                // For indirect interactions, sort by source+target
                if (a.interactionType === "Direct" && b.interactionType === "Direct") {
                    valueA = a.target.toLowerCase();
                    valueB = b.target.toLowerCase();
                } else if (
                    a.interactionType === "Indirect" &&
                    b.interactionType === "Indirect"
                ) {
                    valueA = a.source.toLowerCase() + a.target.toLowerCase();
                    valueB = b.source.toLowerCase() + b.target.toLowerCase();
                } else {
                    // When mixing direct and indirect, use target for comparison
                    valueA = a.target.toLowerCase();
                    valueB = b.target.toLowerCase();
                }
            } else if (field === "type") {
                // Sort by interaction type (Direct or Indirect)
                valueA = a.interactionType;
                valueB = b.interactionType;
            } else {
                // Sort by call type count
                valueA = a.types[field] || 0;
                valueB = b.types[field] || 0;
            }

            if (valueA === valueB) return 0;

            const comparison = valueA > valueB ? 1 : -1;
            return direction === "asc" ? comparison : -comparison;
        });
    };

    // Get all unique call types from the edges
    const getCallTypes = (): string[] => {
        if (!jsonData || !jsonData.edges) return [];

        const types = new Set<string>();
        jsonData.edges.forEach((edge) => {
            Object.keys(edge.types).forEach((type) => types.add(type));
        });

        return Array.from(types);
    };

    const callTypes = getCallTypes();

    const filterEdges = (edges: EnhancedEdge[]): EnhancedEdge[] => {
        if (!edges) return [];

        // First filter by interaction type if needed
        let filteredEdges = edges;
        if (!showTransitiveInteractions) {
            filteredEdges = edges.filter(
                (edge) =>
                    edge.interactionType === "Direct" ||
                    edge.source.toLowerCase() === contractAddress,
            );
        }

        // Then filter by search query if present
        if (searchQuery.trim()) {
            const query = searchQuery.toLowerCase().trim();
            filteredEdges = filteredEdges.filter((edge) => {
                // Search in both source and target addresses
                return (
                    edge.source.toLowerCase().includes(query) ||
                    edge.target.toLowerCase().includes(query)
                );
            });
        }

        return filteredEdges;
    };

    // Convert edges to enhanced edges with interaction type
    const getEnhancedEdges = (): EnhancedEdge[] => {
        if (!jsonData || !jsonData.edges) return [];

        // Debug the nodes object
        console.log("Nodes data:", jsonData.nodes);

        return jsonData.edges.map((edge) => {
            const sourceLower = edge.source.toLowerCase();
            const targetLower = edge.target.toLowerCase();

            // Try both case variations
            const sourceName =
                jsonData.nodes?.[sourceLower] || jsonData.nodes?.[edge.source];
            const targetName =
                jsonData.nodes?.[targetLower] || jsonData.nodes?.[edge.target];

            return {
                ...edge,
                interactionType:
                    sourceLower === contractAddress ? "Direct" : "Indirect",
                sourceName,
                targetName,
            };
        });
    };

    //   // Handle toggle group change
    //   const handleInteractionTypeChange = (value: string) => {
    //     // If "direct" is selected, hide indirect interactions
    //     setShowTransitiveInteractions(value === "all");
    //   };

    return (
        <div
            style={{
                width: "100%",
                height: "100%",
                display: "flex",
                flexDirection: "column",
                // padding: "10px",
                boxSizing: "border-box",
            }}
        >
            {/* <div style={{ fontWeight: "bold", marginBottom: 10, textAlign: "left" }}>Contract Interactions</div> */}

            {/* Add interaction metrics with collapsible explanation */}
            <div
                style={{
                    backgroundColor: "white",
                    padding: "12px",
                    borderRadius: "4px",
                    border: "1px solid #eee",
                    marginBottom: "15px",
                    width: "100%",
                    boxSizing: "border-box",
                }}
            >
                {/* Add total direct interactions count */}
                <div
                    style={{
                        display: "flex",
                        justifyContent: "space-between",
                        marginBottom: "8px",
                    }}
                >
                    {/* <span style={{ fontWeight: "500", color: "#555" }}>Direct Interactions:</span> */}
                    <span
                        style={{
                            fontWeight: "bold",
                            color: "#312750",
                            textAlign: "left",
                            width: "100%",
                        }}
                    >
                        {jsonData && jsonData.edges ? (
                            (() => {
                                const directEdges = jsonData.edges.filter(
                                    (edge) =>
                                        edge.source.toLowerCase() === contractAddress,
                                );

                                if (directEdges.length === 0) return "No interactions found";

                                // Calculate total interactions across all direct edges
                                let totalInteractions = 0;
                                directEdges.forEach((edge) => {
                                    Object.values(edge.types).forEach((count) => {
                                        totalInteractions += count;
                                    });
                                });

                                const directDependencies = jsonData.edges.filter(
                                    (edge) =>
                                        edge.source.toLowerCase() === contractAddress,
                                );

                                // Get activity level description based on interaction count
                                const getActivityLevel = (count: number) => {
                                    if (count < 0) return "something went wrong";
                                    if (count === 0) return "no recorded interactions";
                                    if (count === 1) return "a single interaction";
                                    if (count < 10)
                                        return `minimal activity (${count} interactions)`;
                                    if (count < 100)
                                        return `moderate activity (${count.toLocaleString()} interactions)`;
                                    if (count < 1000)
                                        return `high activity (${count.toLocaleString()} interactions)`;
                                    return `significant activity (${count.toLocaleString()} interactions)`;
                                };

                                // Get plural-aware address text
                                const dependencyText =
                                    directDependencies.length === 1
                                        ? "dependency"
                                        : "dependencies";
                                const timePeriod = jsonData.from_block
                                    ? `from block ${jsonData.from_block} to ${jsonData.to_block}`
                                    : "all available blocks";

                                // Build the complete message with React elements
                                return (
                                    <>
                                        In the selected time period ({timePeriod}), this contract
                                        has{" "}
                                        <span
                                            style={{
                                                color: "#fe962e",
                                                // textShadow: "1px 1px 2px rgba(255,0,255,0.3)",
                                                // background: "#be99a8",
                                                padding: "0 4px",
                                                borderRadius: "4px",
                                            }}
                                        >
                                            {getActivityLevel(totalInteractions)}
                                        </span>
                                        {totalInteractions > 0
                                            ? ` with ${directDependencies.length} direct ${dependencyText}`
                                            : ""}
                                        .
                                    </>
                                );
                            })()
                        ) : (
                            <span style={{ color: "#545c56" }}>
                                ...Enter an address to analyze...
                            </span>
                        )}
                    </span>
                </div>

                <div
                    style={{
                        marginTop: "8px",
                        fontSize: "12px",
                        color: "#666",
                        borderTop: "1px solid #eee",
                        paddingTop: "8px",
                    }}
                ></div>

                {/* <div style={{
                    display: "flex",
                    justifyContent: "space-between",
                    marginBottom: "8px"
                }}>
                    <span style={{ fontWeight: "500", color: "#555" }}>Top 10 Interacted Contracts Ratio:</span>
                    <span style={{ fontWeight: "bold", color: "#3399ff" }}>
                        {jsonData && jsonData.edges ?
                            (() => {
                                const directEdges = jsonData.edges.filter(edge =>
                                    edge.source.toLowerCase() === inputAddress.toLowerCase()
                                );

                                if (directEdges.length === 0) return "N/A";

                                // Calculate total interactions for each target address
                                const targetCounts: Record<string, number> = {};
                                directEdges.forEach(edge => {
                                    const target = edge.target.toLowerCase();
                                    if (!targetCounts[target]) targetCounts[target] = 0;

                                    // Sum up all interaction types
                                    Object.values(edge.types).forEach(count => {
                                        targetCounts[target] += count;
                                    });
                                });

                                // Sort by interaction count and take top 10
                                const sortedTargets = Object.entries(targetCounts)
                                    .sort((a, b) => b[1] - a[1])
                                    .slice(0, 10);

                                // Calculate total interactions with top 10 contracts
                                const top10InteractionCount = sortedTargets.reduce((sum, [_, count]) => sum + count, 0);

                                // Calculate total interactions across all contracts
                                const totalInteractionCount = Object.values(targetCounts).reduce((sum, count) => sum + count, 0);

                                // Calculate the ratio as a percentage
                                return `${Math.round((top10InteractionCount / totalInteractionCount) * 100)}%`;
                            })() :
                            "N/A"}
                    </span>
                </div>
                <div style={{
                    display: "flex",
                    justifyContent: "space-between"
                }}>
                    <span style={{ fontWeight: "500", color: "#555" }}>Top 50% Interactions Contracts Number:</span>
                    <span style={{ fontWeight: "bold", color: "#3399ff" }}>
                        {jsonData && jsonData.edges ?
                            (() => {
                                const directEdges = jsonData.edges.filter(edge =>
                                    edge.source.toLowerCase() === inputAddress.toLowerCase()
                                );

                                if (directEdges.length === 0) return "N/A";

                                // Calculate total interactions for each target address
                                const targetCounts: Record<string, number> = {};
                                directEdges.forEach(edge => {
                                    const target = edge.target.toLowerCase();
                                    if (!targetCounts[target]) targetCounts[target] = 0;

                                    // Sum up all interaction types
                                    Object.values(edge.types).forEach(count => {
                                        targetCounts[target] += count;
                                    });
                                });

                                // Sort contracts by interaction count (descending)
                                const sortedTargets = Object.entries(targetCounts)
                                    .sort((a, b) => b[1] - a[1]);

                                // Calculate total interactions across all contracts
                                const totalInteractionCount = Object.values(targetCounts).reduce((sum, count) => sum + count, 0);

                                // Calculate how many contracts make up 50% of interactions
                                let runningSum = 0;
                                let contractCount = 0;

                                for (const [_, count] of sortedTargets) {
                                    runningSum += count;
                                    contractCount++;

                                    // Once we reach 50% of total interactions, return the contract count
                                    if (runningSum >= totalInteractionCount * 0.5) {
                                        break;
                                    }
                                }

                                return contractCount;
                            })() :
                            "N/A"}
                    </span>
                </div> */}

                {/* Collapsible explanation section
                <div style={{
                    marginTop: "12px",
                    padding: "10px",
                    backgroundColor: "#f9f9f9",
                    borderRadius: "4px",
                    fontSize: "12px",
                    color: "#666",
                    lineHeight: "1.4"
                }}>
                    <div
                        style={{
                            fontWeight: "500",
                            color: "#555",
                            cursor: "pointer",
                            display: "flex",
                            justifyContent: "space-between",
                            alignItems: "center"
                        }}
                        onClick={() => setShowMetricsExplanation(!showMetricsExplanation)}
                    >
                        <span>How these metrics are calculated</span>
                        <span style={{ fontSize: "14px" }}>
                            {showMetricsExplanation ? '▲' : '▼'}
                        </span>
                    </div>

                    {showMetricsExplanation && (
                        <div style={{ marginTop: "8px" }}>
                            <div style={{ marginBottom: "6px" }}>
                                <span style={{ fontWeight: "500" }}>Top 10 Interaction Ratio:</span> Percentage of total interactions that occur with the 10 most frequently called contracts. Higher percentages indicate concentration of interactions with a few contracts.
                            </div>

                            <div>
                                <span style={{ fontWeight: "500" }}>Top 50% Interaction Contracts:</span> The number of contracts that account for 50% of all interactions. Lower numbers indicate higher dependency concentration.
                            </div>
                        </div>
                    )}
                </div>
            </div> */}

                {/* Combined Interactions Table */}
                {jsonData && jsonData.edges && (
                    <div
                        style={{
                            width: "100%",
                            flex: "1",
                            display: "flex",
                            flexDirection: "column",
                            boxSizing: "border-box",
                        }}
                    >
                        <div
                            style={{
                                fontWeight: "500",
                                marginBottom: 10,
                                display: "flex",
                                alignItems: "center",
                                width: "100%",
                            }}
                        >
                            <div
                                style={{
                                    width: "8px",
                                    height: "8px",
                                    backgroundColor: "#3399ff",
                                    borderRadius: "50%",
                                    marginRight: "8px",
                                }}
                            ></div>
                            All Interactions
                        </div>

                        {/* Search bar and dropdown menu container */}
                        <div
                            style={{
                                display: "flex",
                                justifyContent: "flex-start",
                                alignItems: "center",
                                marginBottom: "15px",
                                flexWrap: "wrap",
                                gap: "10px",
                                width: "100%",
                                boxSizing: "border-box",
                            }}
                        >
                            {/* Search bar container */}
                            <div
                                style={{
                                    position: "relative",
                                    flexGrow: 1,
                                    maxWidth: "500px",
                                    display: "flex",
                                    alignItems: "center",
                                    border: "1px solid #ddd",
                                    borderRadius: "4px",
                                    padding: "0 8px",
                                    backgroundColor: "white",
                                }}
                            >
                                {/* Search icon */}
                                <div
                                    style={{
                                        color: "#999",
                                        marginRight: "8px",
                                    }}
                                >
                                    🔍
                                </div>

                                {/* Input field - no border since container has border */}
                                <input
                                    type="text"
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    placeholder="Search addresses..."
                                    style={{
                                        flex: 1,
                                        border: "none",
                                        outline: "none",
                                        padding: "8px 0",
                                        fontSize: "12px",
                                        backgroundColor: "transparent",
                                    }}
                                />

                                {/* Clear button */}
                                {searchQuery && (
                                    <div
                                        style={{
                                            color: "#888",
                                            cursor: "pointer",
                                            padding: "2px 6px",
                                            fontSize: "14px",
                                            fontWeight: "bold",
                                            borderRadius: "4px",
                                            backgroundColor: "#f0f0f0",
                                            display: "flex",
                                            alignItems: "center",
                                            justifyContent: "center",
                                            width: "16px",
                                            height: "16px",
                                            marginLeft: "8px",
                                            transition: "all 0.2s ease",
                                        }}
                                        onClick={() => setSearchQuery("")}
                                        onMouseOver={(e) => {
                                            e.currentTarget.style.backgroundColor = "#e0e0e0";
                                            e.currentTarget.style.color = "#555";
                                        }}
                                        onMouseOut={(e) => {
                                            e.currentTarget.style.backgroundColor = "#f0f0f0";
                                            e.currentTarget.style.color = "#888";
                                        }}
                                    >
                                        ×
                                    </div>
                                )}
                            </div>

                            {/* Dropdown menu for display options */}
                            <DropdownMenu>
                                <DropdownMenuTrigger asChild>
                                    <Button variant="outline" size="sm" className="h-8 gap-1">
                                        <Settings className="h-3.5 w-3.5" />
                                        <span className="text-xs">Display</span>
                                    </Button>
                                </DropdownMenuTrigger>
                                <DropdownMenuContent align="end">
                                    <DropdownMenuLabel>View Settings</DropdownMenuLabel>
                                    <DropdownMenuSeparator />
                                    <DropdownMenuCheckboxItem
                                        checked={showTransitiveInteractions}
                                        onCheckedChange={setShowTransitiveInteractions}
                                    >
                                        Show Indirect Interactions
                                    </DropdownMenuCheckboxItem>
                                    <DropdownMenuCheckboxItem
                                        checked={showOriginalAddresses}
                                        onCheckedChange={setShowOriginalAddresses}
                                    >
                                        Show Raw Addresses
                                    </DropdownMenuCheckboxItem>
                                </DropdownMenuContent>
                            </DropdownMenu>
                        </div>

                        {/* Table container - make it fill remaining space */}
                        <div
                            style={{
                                backgroundColor: "white",
                                borderRadius: "4px",
                                border: "1px solid #eee",
                                overflow: "auto",
                                flex: "1",
                                width: "100%",
                                boxSizing: "border-box",
                            }}
                        >
                            <table
                                style={{
                                    width: "100%",
                                    minWidth: "600px",
                                    borderCollapse: "collapse",
                                    fontSize: "12px",
                                    tableLayout: "fixed",
                                }}
                            >
                                <thead>
                                    <tr
                                        style={{
                                            backgroundColor: "#f5f5f5",
                                            borderBottom: "1px solid #eee",
                                        }}
                                    >
                                        <th
                                            style={{
                                                padding: "10px",
                                                textAlign: "left",
                                                cursor: "pointer",
                                                position: "relative",
                                                width: "80px",
                                            }}
                                            onClick={() => handleSort("type")}
                                        >
                                            Type
                                            {sortField === "type" && (
                                                <span style={{ marginLeft: "5px" }}>
                                                    {sortDirection === "asc" ? "↑" : "↓"}
                                                </span>
                                            )}
                                        </th>
                                        <th
                                            style={{
                                                padding: "10px",
                                                textAlign: "left",
                                                cursor: "pointer",
                                                position: "relative",
                                                width: "300px",
                                                overflow: "hidden",
                                                textOverflow: "ellipsis",
                                                whiteSpace: "nowrap",
                                            }}
                                            onClick={() => handleSort("address")}
                                        >
                                            Address
                                            {sortField === "address" && (
                                                <span style={{ marginLeft: "5px" }}>
                                                    {sortDirection === "asc" ? "↑" : "↓"}
                                                </span>
                                            )}
                                        </th>
                                        {callTypes.map((type) => (
                                            <th
                                                key={type}
                                                style={{
                                                    padding: "10px",
                                                    textAlign: "right",
                                                    cursor: "pointer",
                                                    position: "relative",
                                                    minWidth: "140px",
                                                    width: "140px",
                                                    whiteSpace: "nowrap",
                                                    overflow: "hidden",
                                                    textOverflow: "ellipsis",
                                                }}
                                                onClick={() => handleSort(type)}
                                            >
                                                {type}
                                                {sortField === type && (
                                                    <span style={{ marginLeft: "5px" }}>
                                                        {sortDirection === "asc" ? "↑" : "↓"}
                                                    </span>
                                                )}
                                            </th>
                                        ))}
                                    </tr>
                                </thead>
                                <tbody>
                                    {filterEdges(
                                        sortEdges(getEnhancedEdges(), sortField, sortDirection),
                                    ).map((edge, index) => (
                                        <tr
                                            key={`${edge.source}-${edge.target}-${index}`}
                                            style={{
                                                borderBottom: "1px solid #eee",
                                                backgroundColor:
                                                    highlightAddress &&
                                                        (edge.source.toLowerCase() ===
                                                            highlightAddress.toLowerCase() ||
                                                            edge.target.toLowerCase() ===
                                                            highlightAddress.toLowerCase())
                                                        ? "#e8f4fd"
                                                        : "white",
                                                cursor: "pointer",
                                            }}
                                            onClick={() => {
                                                if (highlightAddress === edge.target.toLowerCase()) {
                                                    setHighlightAddress(null);
                                                } else {
                                                    setHighlightAddress(edge.target.toLowerCase());
                                                }
                                            }}
                                            onMouseEnter={(e) => {
                                                if (!highlightAddress) {
                                                    e.currentTarget.style.backgroundColor = "#f9f9f9";
                                                }
                                            }}
                                            onMouseLeave={(e) => {
                                                if (
                                                    !highlightAddress ||
                                                    (edge.source.toLowerCase() !==
                                                        highlightAddress.toLowerCase() &&
                                                        edge.target.toLowerCase() !==
                                                        highlightAddress.toLowerCase())
                                                ) {
                                                    e.currentTarget.style.backgroundColor = "white";
                                                }
                                            }}
                                        >
                                            <td style={{ padding: "8px 10px" }}>
                                                <div
                                                    style={{
                                                        display: "inline-block",
                                                        padding: "2px 8px",
                                                        borderRadius: "10px",
                                                        fontSize: "11px",
                                                        backgroundColor:
                                                            edge.interactionType === "Direct"
                                                                ? "#e8f4fd"
                                                                : "#f0f0f0",
                                                        color:
                                                            edge.interactionType === "Direct"
                                                                ? "#3399ff"
                                                                : "#666",
                                                    }}
                                                >
                                                    {edge.interactionType}
                                                </div>
                                            </td>
                                            <td
                                                style={{
                                                    padding: "8px 10px",
                                                    fontFamily: "monospace",
                                                    fontSize: "11px",
                                                    overflow: "hidden",
                                                    textOverflow: "ellipsis",
                                                    whiteSpace: "nowrap",
                                                }}
                                            >
                                                {edge.interactionType === "Direct" ? (
                                                    <>
                                                        {!showOriginalAddresses && edge.targetName ? (
                                                            <div
                                                                style={{ fontWeight: "500", textAlign: "left" }}
                                                            >
                                                                {edge.targetName}
                                                            </div>
                                                        ) : (
                                                            <div style={{ textAlign: "left" }}>
                                                                {edge.target}
                                                            </div>
                                                        )}
                                                    </>
                                                ) : (
                                                    <>
                                                        {!showOriginalAddresses && edge.sourceName ? (
                                                            <div
                                                                style={{ fontWeight: "500", textAlign: "left" }}
                                                            >
                                                                {edge.sourceName}
                                                            </div>
                                                        ) : (
                                                            <div style={{ textAlign: "left" }}>
                                                                {edge.source}
                                                            </div>
                                                        )}
                                                        <div style={{ color: "#999", textAlign: "left" }}>
                                                            ↓
                                                        </div>
                                                        {!showOriginalAddresses && edge.targetName ? (
                                                            <div
                                                                style={{ fontWeight: "500", textAlign: "left" }}
                                                            >
                                                                {edge.targetName}
                                                            </div>
                                                        ) : (
                                                            <div style={{ textAlign: "left" }}>
                                                                {edge.target}
                                                            </div>
                                                        )}
                                                    </>
                                                )}
                                            </td>
                                            {callTypes.map((type) => (
                                                <td
                                                    key={type}
                                                    style={{
                                                        padding: "8px 10px",
                                                        textAlign: "right",
                                                        color: edge.types[type] ? "#333" : "#ccc",
                                                        minWidth: "120px",
                                                        width: "120px",
                                                        overflow: "hidden",
                                                        textOverflow: "ellipsis",
                                                    }}
                                                >
                                                    {edge.types[type] || 0}
                                                </td>
                                            ))}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
