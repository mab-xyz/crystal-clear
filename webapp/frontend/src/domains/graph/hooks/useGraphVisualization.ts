// Custom hook for D3 graph visualization logic
import { useRef, useCallback, useState } from "react";
import { select, type Selection } from "d3-selection";
import {
  forceSimulation,
  forceLink,
  forceManyBody,
  forceCenter,
  type Simulation,
} from "d3-force";
import { zoom, type ZoomBehavior } from "d3-zoom";
import { drag, type D3DragEvent } from "d3-drag";
import type { Node, Link, GraphData, GraphDimensions } from "@/types/graph";

interface UseGraphVisualizationReturn {
  svgRef: React.RefObject<SVGSVGElement | null>;
  dimensions: GraphDimensions | null;
  drawGraph: (data: GraphData) => void;
  cleanup: () => void;
  svgSelection: React.RefObject<Selection<
    SVGSVGElement,
    unknown,
    null,
    undefined
  > | null>;
  gSelection: React.RefObject<Selection<
    SVGGElement,
    unknown,
    null,
    undefined
  > | null>;
  zoomBehavior: React.RefObject<ZoomBehavior<SVGSVGElement, unknown> | null>;
}

export function useGraphVisualization(
  onNodeClick: (node: Node) => void,
): UseGraphVisualizationReturn {
  const svgRef = useRef<SVGSVGElement | null>(null);
  const graphDrawnRef = useRef<boolean>(false);
  const simulationRef = useRef<Simulation<Node, undefined> | null>(null);
  const [dimensions, setDimensions] = useState<GraphDimensions | null>(null);

  // D3 selections for external access
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

  const drawGraph = useCallback(
    (data: GraphData) => {
      if (graphDrawnRef.current || !svgRef.current) return;

      const width = window.innerWidth * 0.618;
      const height = window.innerHeight;
      setDimensions({ width, height });

      // Clear previous graph
      select(svgRef.current).selectAll("*").remove();
      const svg = select(svgRef.current).attr("viewBox", [0, 0, width, height]);
      svgSelection.current = svg;

      // Add background
      svg
        .append("rect")
        .attr("width", width)
        .attr("height", height)
        .attr("fill", "white")
        .attr("rx", 8)
        .attr("ry", 8);

      // Add main group with zoom
      const g = svg.append("g");
      gSelection.current = g;

      const zoomHandler = zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
          g.attr("transform", event.transform);
        });

      zoomBehavior.current = zoomHandler;
      svg.call(zoomHandler);

      // Transform data for D3
      const links: Link[] = (data.edges || []).flatMap((edge) =>
        Object.entries(edge.types || {}).map(([type, count]) => ({
          source: edge.source,
          target: edge.target,
          type,
          count,
        })),
      );

      const nodeSet = new Set<string>();
      links.forEach((l) => {
        nodeSet.add(typeof l.source === "string" ? l.source : l.source.id);
        nodeSet.add(typeof l.target === "string" ? l.target : l.target.id);
      });

      const nodes: Node[] = Array.from(nodeSet).map((id) => ({
        id,
        group:
          id.toLowerCase() === data.address.toLowerCase() ? "main" : "other",
      }));

      // Create force simulation
      const simulation = forceSimulation<Node>(nodes)
        .force(
          "link",
          forceLink<Node, Link>(links)
            .id((d) => d.id)
            .distance(200),
        )
        .force("charge", forceManyBody().strength(-350))
        .force("center", forceCenter(width / 2, height / 2));

      simulationRef.current = simulation;
      graphDrawnRef.current = true;

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

      // Create nodes
      const node = g
        .append("g")
        .attr("stroke", "#fff")
        .attr("stroke-width", 0.2)
        .selectAll<SVGCircleElement, Node>("circle")
        .data(nodes)
        .join("circle")
        .attr("r", (d) => (d.group === "main" ? 10 : 5))
        .attr("fill", (d) => (d.group === "main" ? "#C5BAFF" : "#91b8ff"))
        .attr("class", (d) => `node-${d.id.toLowerCase()}`)
        .style("cursor", "pointer")
        .on("click", (_event: MouseEvent, d: Node) => {
          onNodeClick(d);
        })
        .call(dragHandler(simulation));

      // Add labels
      const label = g
        .append("g")
        .selectAll("text")
        .data(nodes)
        .join("text")
        .text((d) => {
          // Use name if available, otherwise use shortened address
          const name = data.nodes?.[d.id.toLowerCase()] || data.nodes?.[d.id];
          if (name) {
            return name;
          }
          return `${d.id.slice(0, 6)}...${d.id.slice(-4)}`;
        })
        .attr("font-size", 10)
        .attr("dx", 8)
        .attr("dy", "0.35em");

      // Update positions on simulation tick
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

        node.attr("cx", (d) => d.x || 0).attr("cy", (d) => d.y || 0);
        label.attr("x", (d) => d.x || 0).attr("y", (d) => d.y || 0);
      });

      function dragHandler(simulation: Simulation<Node, undefined>) {
        return drag<SVGCircleElement, Node>()
          .on(
            "start",
            (event: D3DragEvent<SVGCircleElement, Node, Node>, d: Node) => {
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
              if (!event.active) simulation.alphaTarget(0);
              d.fx = null;
              d.fy = null;
            },
          );
      }
    },
    [onNodeClick],
  );

  const cleanup = useCallback(() => {
    if (simulationRef.current) {
      simulationRef.current.stop();
      simulationRef.current = null;
    }
    if (svgRef.current) {
      select(svgRef.current).selectAll("*").remove();
      select(svgRef.current).on(".zoom", null);
    }
    svgSelection.current = null;
    gSelection.current = null;
    zoomBehavior.current = null;
    graphDrawnRef.current = false;
  }, []);

  return {
    svgRef,
    dimensions,
    drawGraph,
    cleanup,
    svgSelection,
    gSelection,
    zoomBehavior,
  };
}
