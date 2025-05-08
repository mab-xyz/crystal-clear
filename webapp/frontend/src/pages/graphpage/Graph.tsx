import React, { useEffect, useRef, useState, useCallback } from "react";
import * as d3 from "d3";
import Header from "./Header";
import Sidebar from "./Sidebar";

// Define TypeScript interfaces for data structures
interface Node {
    id: string;
    group: string;
    x?: number;
    y?: number;
    fx?: number | null;
    fy?: number | null;
}

interface Edge {
    source: string;
    target: string;
    types: Record<string, number>;
}

interface Link {
    source: string | { id: string; x?: number; y?: number };
    target: string | { id: string; x?: number; y?: number };
    type: string;
    count: number;
}

interface GraphData {
    address: string;
    edges: Edge[];
    nodes?: Record<string, string>;
    // Add other properties as needed based on your API response
}

export default function ContractGraph() {
    const svgRef = useRef<SVGSVGElement | null>(null);
    const [jsonData, setJsonData] = useState<GraphData | null>(null);
    const [activeTab, setActiveTab] = useState<string>("Risk Score");
    const [inputAddress, setInputAddress] = useState<string>("");
    // const [inputAddress, setInputAddress] = useState<string>("0xE592427A0AEce92De3Edee1F18E0157C05861564")
    const [loading, setLoading] = useState<boolean>(false);
    const [fromBlock, setFromBlock] = useState<string>("");
    const [toBlock, setToBlock] = useState<string>("");
    const [selectedNode, setSelectedNode] = useState<Node | null>(null);
    const [highlightAddress, setHighlightAddress] = useState<string | null>(null);

    const fetchData = useCallback(
        async (address: string) => {
            // Don't fetch if no address is provided
            if (!address) return;

            try {
                setLoading(true);

                // Build the URL with optional query parameters
                let url = `http://localhost:8000/v1/analysis/${address}/dependencies`;
                const params = new URLSearchParams();

                if (fromBlock) params.append("from_block", fromBlock);
                if (toBlock) params.append("to_block", toBlock);

                // Add the query parameters to the URL if any exist
                if (params.toString()) {
                    url += `?${params.toString()}`;
                }

                console.log("Fetching data from:", url);
                const response = await fetch(url);
                const data = await response.json();
                setJsonData(data);
                drawGraph(data);
            } catch (err) {
                console.error("Failed to fetch data:", err);
            } finally {
                setLoading(false);
            }
        },
        [fromBlock, toBlock],
    );

    // const fetchData = useCallback(async (address: string) => {
    //     const data = require("../test.json");
    //     setJsonData(data);
    //     drawGraph(data);
    // }, []);

    // Handle form submission
    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (inputAddress) {
            fetchData(inputAddress);
        }
    };

    const drawGraph = (data: GraphData) => {
        const width = window.innerWidth * 0.618;
        const height = window.innerHeight;

        if (!svgRef.current) return;

        d3.select(svgRef.current).selectAll("*").remove();
        const svg = d3
            .select(svgRef.current)
            .attr("viewBox", [0, 0, width, height]);

        // Add a group for the graph that will be transformed by zoom
        const g = svg.append("g");

        // Add zoom behavior
        const zoom = d3
            .zoom<SVGSVGElement, unknown>()
            .scaleExtent([0.1, 4]) // Set min/max zoom scale
            .on("zoom", (event) => {
                g.attr("transform", event.transform);
            });

        // Apply zoom to the SVG
        svg.call(zoom);

        // Add zoom controls
        const zoomControls = svg
            .append("g")
            .attr("transform", `translate(${width - 100}, 20)`);

        // Zoom in button
        zoomControls
            .append("rect")
            .attr("x", 0)
            .attr("y", 0)
            .attr("width", 30)
            .attr("height", 30)
            .attr("fill", "#f0f0f0")
            .attr("stroke", "#ccc")
            .attr("rx", 5)
            .style("cursor", "pointer")
            .on("click", () => {
                svg.transition().duration(300).call(zoom.scaleBy, 1.3);
            });

        zoomControls
            .append("text")
            .attr("x", 15)
            .attr("y", 20)
            .attr("text-anchor", "middle")
            .attr("font-size", "20px")
            .text("+")
            .style("cursor", "pointer")
            .style("user-select", "none")
            .on("click", () => {
                svg.transition().duration(300).call(zoom.scaleBy, 1.3);
            });

        // Zoom out button
        zoomControls
            .append("rect")
            .attr("x", 40)
            .attr("y", 0)
            .attr("width", 30)
            .attr("height", 30)
            .attr("fill", "#f0f0f0")
            .attr("stroke", "#ccc")
            .attr("rx", 5)
            .style("cursor", "pointer")
            .on("click", () => {
                svg.transition().duration(300).call(zoom.scaleBy, 0.7);
            });

        zoomControls
            .append("text")
            .attr("x", 55)
            .attr("y", 20)
            .attr("text-anchor", "middle")
            .attr("font-size", "20px")
            .text("-")
            .style("cursor", "pointer")
            .style("user-select", "none")
            .on("click", () => {
                svg.transition().duration(300).call(zoom.scaleBy, 0.7);
            });

        const links: Link[] = data.edges.flatMap((edge) => {
            return Object.entries(edge.types).map(([type, count]) => ({
                source: edge.source,
                target: edge.target,
                type,
                count,
            }));
        });

        const nodeSet = new Set<string>();
        links.forEach((l) => {
            nodeSet.add(typeof l.source === "string" ? l.source : l.source.id);
            nodeSet.add(typeof l.target === "string" ? l.target : l.target.id);
        });

        const nodes: Node[] = Array.from(nodeSet).map((id) => ({
            id,
            group: id.toLowerCase() === data.address.toLowerCase() ? "main" : "other",
        }));

        const color = d3
            .scaleOrdinal<string>()
            .domain(["main", "other"])
            .range(["#C5BAFF", "#91b8ff"]);

        const simulation = d3
            .forceSimulation<Node>(nodes)
            .force(
                "link",
                d3
                    .forceLink<Node, Link>(links)
                    .id((d) => d.id)
                    .distance(120),
            )
            .force("charge", d3.forceManyBody().strength(-400))
            .force("center", d3.forceCenter(width / 2, height / 2));

        // Create links
        const link = g
            .append("g")
            .attr("fill", "none")
            .attr("stroke", "#999")
            .attr("stroke-opacity", 0.6)
            .selectAll("line")
            .data(links)
            .join("line")
            .attr("stroke-width", (d) => Math.sqrt(d.count))
            .attr("class", (d) => {
                const sourceId =
                    typeof d.source === "object" && d.source.id
                        ? d.source.id.toLowerCase()
                        : typeof d.source === "string"
                            ? d.source.toLowerCase()
                            : "";

                const targetId =
                    typeof d.target === "object" && d.target.id
                        ? d.target.id.toLowerCase()
                        : typeof d.target === "string"
                            ? d.target.toLowerCase()
                            : "";

                return `link-${sourceId} link-${targetId}`;
            });

        // Add animated dots along the links
        const flowDots = g
            .append("g")
            .selectAll(".flow-dot")
            .data(links)
            .join("circle")
            .attr("class", "flow-dot")
            .attr("r", 2)
            .attr("fill", "#fff")
            .style("opacity", 0.7);

        // Animation function for the flow dots
        function animateFlowDots() {
            flowDots.each(function (d) {
                const dot = d3.select(this);

                // Reset the animation
                dot
                    .attr("opacity", 0.7)
                    .transition()
                    .duration(2000)
                    .ease(d3.easeLinear)
                    .attrTween("transform", function () {
                        return function (t: number) {
                            // Get current positions of source and target
                            const sourceX =
                                typeof d.source === "object" ? d.source.x || 0 : 0;
                            const sourceY =
                                typeof d.source === "object" ? d.source.y || 0 : 0;
                            const targetX =
                                typeof d.target === "object" ? d.target.x || 0 : 0;
                            const targetY =
                                typeof d.target === "object" ? d.target.y || 0 : 0;

                            // Calculate position along the path based on time
                            const x = sourceX + (targetX - sourceX) * t;
                            const y = sourceY + (targetY - sourceY) * t;

                            return `translate(${x}, ${y})`;
                        };
                    })
                    .on("end", function () {
                        // Fade out at the end of the path
                        dot
                            .transition()
                            .duration(200)
                            .attr("opacity", 0)
                            .on("end", function () {
                                // Restart the animation after a delay
                                setTimeout(() => {
                                    if (d3.select(this.parentNode).node()) {
                                        animateDot(dot, d);
                                    }
                                }, Math.random() * 1000); // Random delay for natural effect
                            });
                    });
            });
        }

        function animateDot(
            dot: d3.Selection<d3.BaseType, unknown, null, undefined>,
            d: Link,
        ) {
            dot
                .attr("opacity", 0.7)
                .transition()
                .duration(2000)
                .ease(d3.easeLinear)
                .attrTween("transform", function () {
                    return function (t: number) {
                        const sourceX = typeof d.source === "object" ? d.source.x || 0 : 0;
                        const sourceY = typeof d.source === "object" ? d.source.y || 0 : 0;
                        const targetX = typeof d.target === "object" ? d.target.x || 0 : 0;
                        const targetY = typeof d.target === "object" ? d.target.y || 0 : 0;

                        const x = sourceX + (targetX - sourceX) * t;
                        const y = sourceY + (targetY - sourceY) * t;

                        return `translate(${x}, ${y})`;
                    };
                })
                .on("end", function () {
                    dot
                        .transition()
                        .duration(200)
                        .attr("opacity", 0)
                        .on("end", function () {
                            setTimeout(() => {
                                if (d3.select(this.parentNode).node()) {
                                    animateDot(dot, d);
                                }
                            }, Math.random() * 1000);
                        });
                });
        }

        // Start the animation
        animateFlowDots();

        // Create nodes
        const node = g
            .append("g")
            .attr("stroke", "#fff")
            .attr("stroke-width", 1.5)
            .selectAll<SVGCircleElement, Node>("circle")
            .data(nodes)
            .join("circle")
            .attr("r", (d) => (d.group === "main" ? 10 : 5))
            .attr("fill", (d) => color(d.group))
            .attr("class", (d) => `node-${d.id.toLowerCase()}`)
            .style("cursor", "pointer")
            .on("click", (event: MouseEvent, d: Node) => {
                setSelectedNode(d);
                setActiveTab("Dependency");
            })
            .call(drag(simulation) as any);

        const label = g
            .append("g")
            .selectAll("text")
            .data(nodes)
            .join("text")
            .text((d) => {
                // Try multiple case variations to find a name
                const addressLower = d.id.toLowerCase();

                // Try both case variations
                const name = data.nodes?.[addressLower] || data.nodes?.[d.id];

                // Use name if available, otherwise use shortened address
                if (name) {
                    console.log(`  - Found name: ${name}`);
                    return name;
                }

                return `${d.id.slice(0, 6)}...${d.id.slice(-4)}`;
            })
            .attr("font-size", 10)
            .attr("dx", 8)
            .attr("dy", "0.35em");

        simulation.on("tick", () => {
            link
                .attr("x1", (d) =>
                    typeof d.source === "object" && d.source.x ? d.source.x : 0,
                )
                .attr("y1", (d) =>
                    typeof d.source === "object" && d.source.y ? d.source.y : 0,
                )
                .attr("x2", (d) =>
                    typeof d.target === "object" && d.target.x ? d.target.x : 0,
                )
                .attr("y2", (d) =>
                    typeof d.target === "object" && d.target.y ? d.target.y : 0,
                );

            // Update flow dots positions during simulation
            flowDots.each(function () {
                // The position is handled by the animation, so we don't need to update it here
                // This prevents the dots from jumping during simulation ticks
            });

            node.attr("cx", (d) => d.x || 0).attr("cy", (d) => d.y || 0);

            label.attr("x", (d) => d.x || 0).attr("y", (d) => d.y || 0);
        });

        function drag(simulation: d3.Simulation<Node, undefined>) {
            return d3
                .drag<SVGCircleElement, Node>()
                .on(
                    "start",
                    (event: d3.D3DragEvent<SVGCircleElement, Node, Node>, d: Node) => {
                        if (!event.active) simulation.alphaTarget(0.3).restart();
                        d.fx = d.x;
                        d.fy = d.y;
                    },
                )
                .on(
                    "drag",
                    (event: d3.D3DragEvent<SVGCircleElement, Node, Node>, d: Node) => {
                        d.fx = event.x;
                        d.fy = event.y;
                    },
                )
                .on(
                    "end",
                    (event: d3.D3DragEvent<SVGCircleElement, Node, Node>, d: Node) => {
                        if (!event.active) simulation.alphaTarget(0);
                        d.fx = null;
                        d.fy = null;
                    },
                );
        }

        // Add a reset zoom button and flow dots toggle button
        zoomControls
            .append("rect")
            .attr("x", 0)
            .attr("y", 40)
            .attr("width", 70)
            .attr("height", 30)
            .attr("fill", "#f0f0f0")
            .attr("stroke", "#ccc")
            .attr("rx", 5)
            .style("cursor", "pointer")
            .on("click", () => {
                svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
            });

        zoomControls
            .append("text")
            .attr("x", 35)
            .attr("y", 60)
            .attr("text-anchor", "middle")
            .attr("font-size", "12px")
            .text("Reset")
            .style("cursor", "pointer")
            .style("user-select", "none")
            .on("click", () => {
                svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
            });

        // Add flow dots toggle button
        const flowDotsButton = zoomControls
            .append("rect")
            .attr("x", 0)
            .attr("y", 80) // Position below the reset button
            .attr("width", 70)
            .attr("height", 30)
            .attr("fill", "#f0f0f0")
            .attr("stroke", "#ccc")
            .attr("rx", 5)
            .style("cursor", "pointer");

        const flowDotsText = zoomControls
            .append("text")
            .attr("x", 35)
            .attr("y", 100) // Position to match the button
            .attr("text-anchor", "middle")
            .attr("font-size", "12px")
            .attr("class", "flow-dots-text")
            .text("Hide Dots") // Initial state shows dots
            .style("cursor", "pointer")
            .style("user-select", "none");

        // Add click handlers for both the button and text
        flowDotsButton.on("click", toggleFlowDots);
        flowDotsText.on("click", toggleFlowDots);

        function toggleFlowDots() {
            // Toggle flow dots visibility
            const dotsVisible = g.selectAll(".flow-dot").style("display") !== "none";
            g.selectAll(".flow-dot").style("display", dotsVisible ? "none" : "block");

            // Update button appearance
            flowDotsButton.attr("fill", dotsVisible ? "#f0f0f0" : "#e6f2ff");

            // Update the button text
            flowDotsText.text(dotsVisible ? "Show Dots" : "Hide Dots");
        }
    };

    // Move the highlighting effect outside of drawGraph
    useEffect(() => {
        if (!svgRef.current || !jsonData) return;

        // Reset all nodes and links to default opacity
        d3.select(svgRef.current)
            .selectAll("circle")
            .attr("opacity", 1)
            .attr("stroke-width", 1.5);

        d3.select(svgRef.current)
            .selectAll("line")
            .attr("stroke-opacity", 0.6)
            .attr("stroke", "#999");

        if (highlightAddress) {
            // Dim all nodes and links
            d3.select(svgRef.current).selectAll("circle").attr("opacity", 0.2);

            d3.select(svgRef.current).selectAll("line").attr("stroke-opacity", 0.1);

            // Highlight the selected node
            d3.select(svgRef.current)
                .selectAll(`.node-${highlightAddress}`)
                .attr("opacity", 1)
                .attr("stroke-width", 3);

            // Find if the highlighted address is the input address
            const isInputAddress = highlightAddress === inputAddress.toLowerCase();

            // Highlight connected links with different colors based on whether they're direct or transitive
            d3.select(svgRef.current)
                .selectAll(`line.link-${highlightAddress}`)
                .attr("stroke-opacity", 1)
                .attr("stroke", (d: any) => {
                    // Check if this is a direct edge from input address or a transitive edge
                    const sourceId =
                        typeof d.source === "object" && d.source.id
                            ? d.source.id.toLowerCase()
                            : typeof d.source === "string"
                                ? d.source.toLowerCase()
                                : "";

                    const targetId =
                        typeof d.target === "object" && d.target.id
                            ? d.target.id.toLowerCase()
                            : typeof d.target === "string"
                                ? d.target.toLowerCase()
                                : "";

                    // If either end is the input address, it's a direct edge (red)
                    // Otherwise it's a transitive edge (orange)
                    if (
                        sourceId === inputAddress.toLowerCase() ||
                        targetId === inputAddress.toLowerCase()
                    ) {
                        return "#ff6666"; // Red for direct edges
                    } else {
                        return "#ff9933"; // Orange for transitive edges
                    }
                });
        }
    }, [highlightAddress, jsonData, inputAddress]);

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
                    <svg ref={svgRef} style={{ width: "100%", height: "100%" }}></svg>
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
