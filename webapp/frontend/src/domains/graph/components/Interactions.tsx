import { useState, useMemo, useCallback } from "react";
import type { Edge, GraphData } from "@/types";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuCheckboxItem,
  DropdownMenuTrigger,
  Button,
} from "@/shared/components/ui";

// Better type definitions
interface DisplayOptions {
  showDirectOnly: boolean;
  showOriginalAddresses: boolean;
}

interface SortConfig {
  field: string | null;
  direction: "asc" | "desc";
}

interface InteractionsProps {
  jsonData: GraphData | null;
  inputAddress: string;
  highlightAddress: string | null;
  setHighlightAddress: (address: string | null) => void;
}

interface EnhancedEdge extends Edge {
  interactionType: "Direct" | "Indirect";
  sourceName: string | undefined;
  targetName: string | undefined;
}

export default function Interactions({
  jsonData,
  inputAddress,
  highlightAddress,
  setHighlightAddress,
}: InteractionsProps) {
  // State management with better types
  const [sortConfig, setSortConfig] = useState<SortConfig>({
    field: null,
    direction: "asc",
  });
  const [displayOptions, setDisplayOptions] = useState<DisplayOptions>({
    showDirectOnly: false,
    showOriginalAddresses: false,
  });
  const [searchQuery, setSearchQuery] = useState<string>("");

  // Memoized contract address
  const contractAddress = useMemo(
    () => jsonData?.address?.toLowerCase() ?? inputAddress.toLowerCase(),
    [jsonData?.address, inputAddress],
  );

  // Memoized call types extraction
  const callTypes = useMemo((): string[] => {
    if (!jsonData?.edges) return [];

    const types = new Set<string>();
    jsonData.edges.forEach((edge) => {
      Object.keys(edge.types).forEach((type) => types.add(type));
    });

    return Array.from(types);
  }, [jsonData?.edges]);

  // Optimized sort handler with useCallback
  const handleSort = useCallback((field: string) => {
    setSortConfig((prev) => ({
      field,
      direction:
        prev.field === field && prev.direction === "asc" ? "desc" : "asc",
    }));
  }, []);

  // Memoized sort function
  const sortEdges = useMemo(
    () =>
      (
        edges: EnhancedEdge[],
        field: string | null,
        direction: "asc" | "desc",
      ): EnhancedEdge[] => {
        if (!field) return edges;

        return [...edges].sort((a, b) => {
          let valueA: string | number;
          let valueB: string | number;

          if (field === "address") {
            // For direct interactions, sort by target
            // For indirect interactions, sort by source+target
            if (
              a.interactionType === "Direct" &&
              b.interactionType === "Direct"
            ) {
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
      },
    [],
  );

  // Memoized filter function
  const filterEdges = useCallback(
    (edges: EnhancedEdge[]): EnhancedEdge[] => {
      if (!edges) return [];

      // First filter by interaction type if needed
      let filteredEdges = edges;
      if (displayOptions.showDirectOnly) {
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
    },
    [displayOptions.showDirectOnly, contractAddress, searchQuery],
  );

  // Memoized enhanced edges calculation
  const enhancedEdges = useMemo((): EnhancedEdge[] => {
    if (!jsonData?.edges) return [];

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
          sourceLower === contractAddress
            ? ("Direct" as const)
            : ("Indirect" as const),
        sourceName,
        targetName,
      };
    });
  }, [jsonData?.edges, jsonData?.nodes, contractAddress]);

  // Memoized processed edges (filtered and sorted)
  const processedEdges = useMemo(() => {
    const filtered = filterEdges(enhancedEdges);
    return sortEdges(filtered, sortConfig.field, sortConfig.direction);
  }, [enhancedEdges, filterEdges, sortEdges, sortConfig]);

  //   // Handle toggle group change
  //   const handleInteractionTypeChange = (value: string) => {
  //     // If "direct" is selected, hide indirect interactions
  //     setShowTransitiveInteractions(value === "all");
  //   };

  return (
    <div className="box-border flex h-full w-full flex-col px-4">
      {/* Add interaction metrics with collapsible explanation */}
      <div className="mb-4 box-border h-full w-full rounded bg-white p-3 py-2">
        {/* Add total direct interactions count */}
        <div className="mb-2 flex justify-between">
          <span className="w-full text-left font-bold text-[#312750]">
            {jsonData && jsonData.edges ? (
              (() => {
                const directEdges = jsonData.edges.filter(
                  (edge) => edge.source.toLowerCase() === contractAddress,
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
                  (edge) => edge.source.toLowerCase() === contractAddress,
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
                // const timePeriod = jsonData.from_block
                //     ? `from block ${jsonData.from_block} to ${jsonData.to_block}`
                //     : "all available blocks";

                // Build the complete message with React elements
                return (
                  <>
                    {/* ({timePeriod}) */}
                    In the selected time period, this contract has{" "}
                    <span className="rounded px-1 text-[#7469B6]">
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
              <div className="flex flex-col items-center gap-2 py-6 text-center text-gray-600">
                <div className="text-xl">
                  <span role="img" aria-label="robot">
                    🤖
                  </span>
                </div>
                <div>Ready to explore the interaction universe?</div>
                <div className="text-sm text-gray-500 italic">
                  Type an Ethereum address above and let's dive in!
                </div>
              </div>
            )}
          </span>
        </div>

        <div className="mt-2 border-t border-gray-200 pt-2 text-xs text-gray-600"></div>

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
          <div className="box-border flex w-full flex-1 flex-col py-1">
            <div className="mb-2 flex w-full items-center font-medium">
              <div className="mr-2 h-2 w-2 rounded-full bg-[#bec9e0]"></div>
              Interactions
            </div>

            {/* Search bar and dropdown menu container */}
            <div className="mb-3 box-border flex w-full flex-wrap items-center justify-between gap-2 py-2">
              {/* Search bar container */}
              <div className="relative flex h-8 max-w-lg flex-grow items-center rounded-none border border-gray-800 bg-white px-2">
                {/* Search icon */}
                <div className="mr-2 text-gray-400">
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
                      d="M6 2H14V4H6V2ZM4 6V4H6V6H4ZM4 14H2V6H4V14ZM6 16H4V14H6V16ZM14 16V18H6V16H14ZM16 14H14V16H16V18H18V20H20V22H22V20H20V18H18V16H16V14ZM16 6H18V14H16V6ZM16 6V4H14V6H16Z"
                      fill="#2b2b2b"
                    />
                  </svg>
                </div>

                {/* Input field - no border since container has border */}
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="Search addresses..."
                  className="flex-1 border-none bg-transparent py-2 text-sm outline-none"
                />

                {/* Clear button */}
                {searchQuery && (
                  <div
                    className="txt-[#888] ml-2 flex h-4 w-4 cursor-pointer items-center justify-center rounded bg-[#f0f0f0] px-1 py-1 text-sm font-bold transition-all duration-200 ease-in-out"
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
                  <Button
                    variant="outline"
                    className="group h-8 rounded-sm border-[#2b2b2b]"
                  >
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
                        d="M8 6H16V8H8V6ZM4 10V8H8V10H4ZM2 12V10H4V12H2ZM2 14V12H0V14H2ZM4 16H2V14H4V16ZM8 18H4V16H8V18ZM16 18V20H8V18H16ZM20 16V18H16V16H20ZM22 14V16H20V14H22ZM22 12H24V14H22V12ZM20 10H22V12H20V10ZM20 10V8H16V10H20ZM10 11H14V15H10V11Z"
                        fill="#2b2b2b"
                        className="transition-colors group-hover:fill-white"
                      />
                    </svg>

                    <span className="text-xs">Display</span>
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent
                  align="end"
                  className="rounded-sm border-[#2b2b2b] bg-[#e3e1f0]"
                >
                  <DropdownMenuCheckboxItem
                    checked={displayOptions.showDirectOnly}
                    onCheckedChange={(checked) =>
                      setDisplayOptions((prev) => ({
                        ...prev,
                        showDirectOnly: checked || false,
                      }))
                    }
                    className="my-2 py-1 pr-2 pl-6"
                  >
                    <span>Only Direct Dependencies</span>
                  </DropdownMenuCheckboxItem>

                  <DropdownMenuCheckboxItem
                    checked={displayOptions.showOriginalAddresses}
                    onCheckedChange={(checked) =>
                      setDisplayOptions((prev) => ({
                        ...prev,
                        showOriginalAddresses: checked || false,
                      }))
                    }
                    className="my-2 py-1 pr-2 pl-6"
                  >
                    <span>Show Raw Addresses</span>
                  </DropdownMenuCheckboxItem>
                  {/* </div> */}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* Table container - make it fill remaining space */}
            <div className="box-border w-full flex-1 overflow-auto rounded-sm border border-[#2b2b2b] bg-white">
              <table className="w-full min-w-[600px] table-auto border-collapse text-xs">
                <thead>
                  <tr className="border-b border-[#2b2b2b]">
                    <th
                      className="relative w-[10%] min-w-[70px] cursor-pointer px-2 text-left"
                      onClick={() => handleSort("type")}
                    >
                      Type
                      {sortConfig.field === "type" && (
                        <span className="ml-1">
                          {sortConfig.direction === "asc" ? "↑" : "↓"}
                        </span>
                      )}
                    </th>
                    <th
                      className="relative w-[40%] min-w-[180px] cursor-pointer overflow-hidden border-r border-gray-200 p-2 text-left text-ellipsis whitespace-nowrap"
                      onClick={() => handleSort("address")}
                    >
                      Address
                      {sortConfig.field === "address" && (
                        <span className="ml-1">
                          {sortConfig.direction === "asc" ? "↑" : "↓"}
                        </span>
                      )}
                    </th>
                    {callTypes.map((type) => (
                      <th
                        key={type}
                        className="relative min-w-[100px] cursor-pointer overflow-hidden p-2 text-center text-ellipsis whitespace-nowrap"
                        style={{
                          width: `${50 / callTypes.length}%`,
                        }}
                        onClick={() => handleSort(type)}
                      >
                        {type}
                        {sortConfig.field === type && (
                          <span className="ml-1">
                            {sortConfig.direction === "asc" ? "↑" : "↓"}
                          </span>
                        )}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {processedEdges.map((edge, index) => (
                    <tr
                      key={`${edge.source}-${edge.target}-${index}`}
                      className="cursor-pointer border-b border-gray-200"
                      style={{
                        backgroundColor:
                          highlightAddress &&
                          (edge.source.toLowerCase() ===
                            highlightAddress.toLowerCase() ||
                            edge.target.toLowerCase() ===
                              highlightAddress.toLowerCase())
                            ? "#e8f4fd"
                            : "white",
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
                      <td className="px-2 py-2">
                        <div
                          className="inline-block rounded-sm px-2 py-1 align-middle text-xs"
                          style={{
                            backgroundColor:
                              edge.interactionType === "Direct"
                                ? "#e3e1f0"
                                : "#f0f0f0",
                            color:
                              edge.interactionType === "Direct"
                                ? "#7469B6"
                                : "#666",
                          }}
                        >
                          {edge.interactionType}
                        </div>
                      </td>
                      <td
                        className="overflow-hidden border-r border-gray-200 px-2 py-2 font-mono text-xs text-ellipsis whitespace-nowrap"
                        style={{ width: "40%", minWidth: "180px" }}
                      >
                        <>
                          <div
                            className="text-left"
                            style={{
                              fontWeight:
                                !displayOptions.showOriginalAddresses &&
                                edge.sourceName !== undefined
                                  ? "500"
                                  : "normal",
                            }}
                          >
                            {!displayOptions.showOriginalAddresses &&
                            edge.sourceName
                              ? edge.sourceName
                              : edge.source}
                          </div>

                          <div className="text-left text-gray-400">↓</div>

                          <div
                            className="text-left"
                            style={{
                              fontWeight:
                                !displayOptions.showOriginalAddresses &&
                                edge.targetName !== undefined
                                  ? "500"
                                  : "normal",
                            }}
                          >
                            {!displayOptions.showOriginalAddresses &&
                            edge.targetName
                              ? edge.targetName
                              : edge.target}
                          </div>
                        </>
                      </td>
                      {callTypes.map((type) => (
                        <td
                          key={type}
                          className="overflow-hidden px-2 py-2 text-center align-middle text-ellipsis"
                          style={{
                            color: edge.types[type] ? "#333" : "#ccc",
                            minWidth: "120px",
                            width: "120px",
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
