// Interactive D3.js force-directed graph component for visualizing smart contract dependencies
// Handles node positioning, link rendering, zoom/pan interactions, and node selection
import { useEffect, useRef, useCallback, useState, memo } from "react";
// Tree-shake D3 imports to reduce bundle size - only import what we need
import { select, type Selection, type BaseType } from "d3-selection";
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  type Simulation,
} from "d3-force";
import { zoom, type ZoomBehavior } from "d3-zoom";
import { drag, type D3DragEvent } from "d3-drag";
import { scaleOrdinal } from "d3-scale";
import { easeLinear } from "d3-ease";
import GraphControlPanel from "./GraphLayoutPanel";
import NodeHoverCard from "./NodeHoverCard";
import type { Node, Link, GraphData, NodeHoverInfo } from "@/types/graph";

interface GraphLayoutProps {
  jsonData: GraphData | null;
  highlightAddress: string | null;
  inputAddress: string;
  onNodeClick: (node: Node) => void;
  isHomepage?: boolean;
}

const GraphLayout = memo(function GraphLayout({
  jsonData,
  highlightAddress,
  inputAddress,
  onNodeClick,
  isHomepage = false,
}: GraphLayoutProps) {
  const draggingRef = useRef(false);
  const onNodeClickRef = useRef(onNodeClick);

  useEffect(() => {
    onNodeClickRef.current = onNodeClick;
  }, [onNodeClick]);

  const svgRef = useRef<SVGSVGElement | null>(null);
  const graphDrawnRef = useRef<boolean>(false);
  // Add refs to store D3 selections for use in the control panel
  const svgSelection = useRef<Selection<
    SVGSVGElement,
    unknown,
    null,
    undefined
  > | null>(null);
  const gSelection = useRef<Selection<
    SVGGElement,
    unknown,
    null,
    undefined
  > | null>(null);
  const zoomBehavior = useRef<ZoomBehavior<SVGSVGElement, unknown> | null>(
    null,
  );
  // Store simulation reference for cleanup
  const simulationRef = useRef<Simulation<Node, undefined> | null>(null);
  const [dimensions, setDimensions] = useState<{
    width: number;
    height: number;
  } | null>(null);

  const [hoveredNodeId, setHoveredNodeId] = useState<string | null>(null);
  const [hoveredNodeInfo, setHoveredNodeInfo] = useState<NodeHoverInfo | null>(
    null,
  );

  const drawGraph = useCallback((data: GraphData) => {
    console.log("[drawGraph] invoked", new Date().toISOString());
    // Only draw the graph if it hasn't been drawn yet or if we're forcing a redraw
    if (graphDrawnRef.current) return;

    const width = window.innerWidth * 0.618;
    const height = window.innerHeight;

    // Store dimensions for the control panel
    setDimensions({ width, height });

    // if there is no svg element, return
    if (!svgRef.current) return;

    select(svgRef.current).selectAll("*").remove();
    const svg = select(svgRef.current).attr("viewBox", [0, 0, width, height]);

    // Store the svg selection for use in the control panel
    svgSelection.current = svg;

    // Add a purple background to the SVG
    svg
      .append("rect")
      .attr("width", width)
      .attr("height", height)
      // .attr("fill", "#f5f0ff")  // Light purple background
      .attr("fill", "white")
      .attr("rx", 8) // Rounded corners
      .attr("ry", 8);

    // Add a group for the graph that will be transformed by zoom
    const g = svg.append("g");

    // Store the g selection for use in the control panel
    gSelection.current = g;

    // Add zoom behavior
    const zoomHandler = zoom<SVGSVGElement, unknown>()
      .scaleExtent([0.1, 4]) // Set min/max zoom scale
      .on("zoom", (event) => {
        g.attr("transform", event.transform);
      });

    // Store the zoom behavior for use in the control panel
    zoomBehavior.current = zoomHandler;

    // Apply zoom to the SVG
    svg.call(zoomHandler);

    // graph layout

    const links: Link[] = (data.edges || []).flatMap((edge) => {
      return Object.entries(edge.types || {}).map(([type, count]) => ({
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

    const color = scaleOrdinal<string>()
      .domain(["main", "other"])
      .range(["#C5BAFF", "#91b8ff"]);

    const simulation = forceSimulation<Node>(nodes)
      .force(
        "link",
        forceLink<Node, Link>(links)
          .id((d) => d.id)
          .distance(200),
      )
      .force("charge", forceManyBody().strength(-350))
      .force("center", forceCenter(width / 2, height / 2));

    // Store simulation reference for cleanup
    simulationRef.current = simulation;

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
      .attr("class", "flow-dots-layer")
      .selectAll(".flow-dot")
      .data(links)
      .join("circle")
      .attr("class", "flow-dot")
      .attr("r", 2)
      .attr("fill", "#EFB6C8")
      .style("opacity", 0.7)
      .attr("filter", "url(#dotGlow)");

    // Animation function for the flow dots
    function animateFlowDots() {
      flowDots.each(function (d) {
        const dot = select(this);

        // Reset the animation
        dot
          .attr("opacity", 0.7)
          .transition()
          .duration(2000)
          .ease(easeLinear)
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
            dot
              .transition()
              .duration(200)
              .attr("opacity", 0)
              .on("end", function () {
                const parent = (this as Element).parentNode as Element | null;
                if (parent && select(parent).node()) {
                  setTimeout(() => {
                    animateDot(dot, d);
                  }, Math.random() * 1000);
                }
              });
          });
      });
    }

    function animateDot(
      dot: Selection<BaseType, unknown, null, undefined>,
      d: Link,
    ) {
      dot
        .attr("opacity", 0.7)
        .transition()
        .duration(2000)
        .ease(easeLinear)
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
              const parent = (this as Element).parentNode as Element | null;
              if (parent && select(parent).node()) {
                setTimeout(() => {
                  animateDot(dot, d);
                }, Math.random() * 1000);
              }
            });
        });
    }

    // Start the animation
    animateFlowDots();

    // Create nodes (highest layer)
    const node = g
      .append("g")
      .attr("stroke", "#fff")
      .attr("stroke-width", 0.2)
      .selectAll<SVGCircleElement, Node>("circle")
      .data(nodes)
      .join("circle")
      .attr("r", (d) => (d.group === "main" ? 10 : 5))
      .attr("fill", (d) => color(d.group))
      .attr("class", (d) => `node-${d.id.toLowerCase()}`)
      .style("cursor", "pointer")
      .on("click", (_event: MouseEvent, d: Node) => {
        onNodeClickRef.current(d);
      })
      .call(dragHandler(simulation))
      .on("mouseover", (_event, d) => {
        if (draggingRef.current) return;
        setHoveredNodeId(d.id);
        setHoveredNodeInfo({});

        fetch(`/api/balance?id=${d.id}`)
          .then((res) => res.json())
          .then((data) => {
            setHoveredNodeInfo((prev) => ({ ...prev, balance: data.balance }));
          })
          .catch(() => {
            setHoveredNodeInfo((prev) => ({
              ...prev,
              balance: null,
              error: true,
            }));
          });

        fetch(`/api/company?id=${d.id}`)
          .then((res) => res.json())
          .then((data) => {
            setHoveredNodeInfo((prev) => ({ ...prev, company: data.company }));
          })
          .catch(() => {
            setHoveredNodeInfo((prev) => ({
              ...prev,
              company: null,
              error: true,
            }));
          });
      })
      .on("mouseout", () => {
        setHoveredNodeId(null);
        setHoveredNodeInfo(null);
      });

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

      console.log("Simulation tick");
      // console.log(simulation.alpha());

      if (simulation.alpha() < 0.01) {
        simulation.stop();
        console.log("Simulation stopped");
      }

      // Update flow dots positions during simulation
      flowDots.each(function () {
        // The position is handled by the animation, so we don't need to update it here
        // This prevents the dots from jumping during simulation ticks
      });

      node.attr("cx", (d) => d.x || 0).attr("cy", (d) => d.y || 0);

      label.attr("x", (d) => d.x || 0).attr("y", (d) => d.y || 0);
    });

    function dragHandler(simulation: Simulation<Node, undefined>) {
      return drag<SVGCircleElement, Node>()
        .on(
          "start",
          (event: D3DragEvent<SVGCircleElement, Node, Node>, d: Node) => {
            draggingRef.current = true;
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x ?? null;
            d.fy = d.y ?? null;
          },
        )
        .on(
          "drag",
          (event: D3DragEvent<SVGCircleElement, Node, Node>, d: Node) => {
            d.fx = event.x;
            d.fy = event.y;
          },
        )
        .on(
          "end",
          (event: D3DragEvent<SVGCircleElement, Node, Node>, d: Node) => {
            draggingRef.current = false;
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          },
        );
    }

    // Mark the graph as drawn
    graphDrawnRef.current = true;
  }, []);

  // Draw the graph only when data changes or component mounts
  useEffect(() => {
    if (jsonData) {
      // Reset the drawn flag when jsonData changes
      graphDrawnRef.current = false;
      drawGraph(jsonData);
    }
  }, [jsonData]);

  // Handle highlighting effect without redrawing the graph
  useEffect(() => {
    if (!svgRef.current || !jsonData) return;

    // Reset all nodes and links to default opacity
    select(svgRef.current)
      .selectAll("circle")
      .attr("opacity", 1)
      .attr("stroke-width", 1.5);

    select(svgRef.current)
      .selectAll("line")
      .attr("stroke-opacity", 0.6)
      .attr("stroke", "#999");

    if (highlightAddress) {
      // Dim all nodes and links
      select(svgRef.current).selectAll("circle").attr("opacity", 0.2);

      select(svgRef.current).selectAll("line").attr("stroke-opacity", 0.1);

      // Highlight the selected node
      select(svgRef.current)
        .selectAll(`.node-${highlightAddress}`)
        .attr("opacity", 1)
        .attr("stroke-width", 3);

      // Highlight connected links with different colors based on whether they're direct or transitive
      select(svgRef.current)
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
            sourceId === jsonData.address.toLowerCase() ||
            targetId === jsonData.address.toLowerCase()
          ) {
            return "#ff6666"; // Red for direct edges
          } else {
            return "#ff9933"; // Orange for transitive edges
          }
        });
    }
  }, [highlightAddress, jsonData, inputAddress]);

  // Memory cleanup: Stop simulation and clear SVG on unmount
  useEffect(() => {
    return () => {
      // Stop the force simulation to free memory
      if (simulationRef.current) {
        simulationRef.current.stop();
        simulationRef.current = null;
      }

      // Clear SVG elements and event listeners
      if (svgRef.current) {
        select(svgRef.current).selectAll("*").remove();
        select(svgRef.current).on(".zoom", null); // Remove zoom event listeners
      }

      // Clear refs
      svgSelection.current = null;
      gSelection.current = null;
      zoomBehavior.current = null;
    };
  }, []); // Empty dependency array = only runs on unmount

  return (
    <div className="relative h-full w-full">
      <svg ref={svgRef} className="h-full w-full"></svg>

      {/* 🟡 Empty result message */}
      {jsonData && jsonData.edges && jsonData.edges.length === 0 && (
        <div className="absolute top-0 left-0 flex h-full w-full items-center justify-center bg-white text-center text-base text-gray-800">
          <div className="rounded-lg border border-pink-500 bg-white px-2 py-4 shadow-md">
            No dependencies found for this contract in the selected block range.
          </div>
        </div>
      )}

      {hoveredNodeId && hoveredNodeInfo && (
        <NodeHoverCard nodeId={hoveredNodeId} nodeInfo={hoveredNodeInfo} />
      )}

      {/* Only render GraphControlPanel when not on homepage and all dependencies are available */}
      {!isHomepage &&
        svgSelection.current &&
        gSelection.current &&
        zoomBehavior.current &&
        dimensions && (
          <GraphControlPanel
            svg={svgSelection.current}
            g={gSelection.current}
            zoom={zoomBehavior.current}
            width={dimensions.width}
            height={dimensions.height}
          />
        )}
    </div>
  );
});

export default GraphLayout;
