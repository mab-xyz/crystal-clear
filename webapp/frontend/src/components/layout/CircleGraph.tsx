import React, { useEffect, useRef } from 'react';
import * as d3 from 'd3';

interface Node {
    id: string;
    x?: number;
    y?: number;
}

interface Link {
    source: string;
    target: string;
}

const CircleGraph: React.FC = () => {
    const svgRef = useRef<SVGSVGElement>(null);

    useEffect(() => {
        if (!svgRef.current) return;

        const width = 600;
        const height = 600;
        const radius = 250;

        const nodes: Node[] = [
            { id: "A" }, { id: "B" }, { id: "C" },
            { id: "D" }, { id: "E" }, { id: "F" }
        ];

        const links: Link[] = [
            { source: "A", target: "B" },
            { source: "A", target: "C" },
            { source: "B", target: "D" },
            { source: "C", target: "E" },
            { source: "E", target: "F" }
        ];

        // Compute circular positions
        nodes.forEach((node, i) => {
            const angle = (i / nodes.length) * 2 * Math.PI;
            node.x = width / 2 + radius * Math.cos(angle);
            node.y = height / 2 + radius * Math.sin(angle);
        });

        // Draw
        const svg = d3.select(svgRef.current);

        // Clear any existing elements
        svg.selectAll("*").remove();

        // Links
        svg.selectAll("line")
            .data(links)
            .enter()
            .append("line")
            .attr("x1", d => nodes.find(n => n.id === d.source)?.x || 0)
            .attr("y1", d => nodes.find(n => n.id === d.source)?.y || 0)
            .attr("x2", d => nodes.find(n => n.id === d.target)?.x || 0)
            .attr("y2", d => nodes.find(n => n.id === d.target)?.y || 0)
            .attr("stroke", "#aaa");

        // Nodes
        svg.selectAll("circle")
            .data(nodes)
            .enter()
            .append("circle")
            .attr("cx", d => d.x || 0)
            .attr("cy", d => d.y || 0)
            .attr("r", 8)
            .attr("fill", "steelblue");

        // Labels
        svg.selectAll("text")
            .data(nodes)
            .enter()
            .append("text")
            .attr("x", d => d.x || 0)
            .attr("y", d => (d.y || 0) - 12)
            .attr("text-anchor", "middle")
            .text(d => d.id);
    }, []);

    return (
        <svg ref={svgRef} width="600" height="600"></svg>
    );
};

export default CircleGraph;
