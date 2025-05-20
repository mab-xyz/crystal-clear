import { useEffect } from "react";
import * as d3 from "d3";

interface GraphControlPanelProps {
    svg: d3.Selection<SVGSVGElement, unknown, null, undefined>;
    g: d3.Selection<SVGGElement, unknown, null, undefined>;
    zoom: d3.ZoomBehavior<SVGSVGElement, unknown>;
    width: number;
    height: number;
}

export default function GraphControlPanel({
    svg,
    g,
    zoom,
    width,
    height
}: GraphControlPanelProps) {
    // Move all the D3 code into a useEffect hook
    useEffect(() => {
        // Add zoom controls with a panel-like appearance - positioned in right corner
        const controlPanel = svg
            .append("g")
            .attr("class", "control-panel")
            .attr("transform", `translate(${width - width * 0.15}, ${height * 0.05})`);

        // Zoom in button with improved styling
        controlPanel
            .append("rect")
            .attr("x", 10)
            .attr("y", 30)
            .attr("width", 25)
            .attr("height", 25)
            .attr("fill", "#ffffff")
            .attr("stroke", "#c9e0be")
            .attr("rx", 5)
            .style("cursor", "pointer")
            .style("filter", "drop-shadow(0px 1px 2px rgba(0, 0, 0, 0.1))")
            .on("click", () => {
                svg.transition().duration(300).call(zoom.scaleBy, 1.3);
            });

        controlPanel
            .append("text")
            .attr("x", 22.5)
            .attr("y", 47)
            .attr("text-anchor", "middle")
            .attr("font-size", "18px")
            .attr("fill", "#555")
            .text("+")
            .style("cursor", "pointer")
            .style("user-select", "none")
            .on("click", () => {
                svg.transition().duration(300).call(zoom.scaleBy, 1.3);
            });

        // Zoom out button with improved styling
        controlPanel
            .append("rect")
            .attr("x", 42.5)
            .attr("y", 30)
            .attr("width", 25)
            .attr("height", 25)
            .attr("fill", "#ffffff")
            .attr("stroke", "#c9e0be")
            .attr("rx", 4)
            .style("cursor", "pointer")
            .style("filter", "drop-shadow(0px 1px 2px rgba(0, 0, 0, 0.1))")
            .on("click", () => {
                svg.transition().duration(300).call(zoom.scaleBy, 0.7);
            });

        controlPanel
            .append("text")
            .attr("x", 55)
            .attr("y", 47)
            .attr("text-anchor", "middle")
            .attr("font-size", "18px")
            .attr("fill", "#555")
            .text("-")
            .style("cursor", "pointer")
            .style("user-select", "none")
            .on("click", () => {
                svg.transition().duration(300).call(zoom.scaleBy, 0.7);
            });

        // Reset zoom button  
        controlPanel
            .append("rect")
            .attr("x", 75)
            .attr("y", 30)
            .attr("width", 25)
            .attr("height", 25)
            .attr("fill", "#ffffff")
            .attr("stroke", "#c9e0be")
            .attr("rx", 4)
            .style("cursor", "pointer")
            .style("filter", "drop-shadow(0px 1px 2px rgba(0, 0, 0, 0.1))")
            .on("click", () => {
                svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
            });

        controlPanel
            .append("text")
            .attr("x", 87.5)
            .attr("y", 47)
            .attr("text-anchor", "middle")
            .attr("font-size", "14px")
            .attr("fill", "#555")
            .text("R")
            .style("cursor", "pointer")
            .style("user-select", "none")
            .on("click", () => {
                svg.transition().duration(300).call(zoom.transform, d3.zoomIdentity);
            });

        // Flow dots toggle button with improved styling
        const flowDotsButton = controlPanel
            .append("rect")
            .attr("x", 10)
            .attr("y", 65)
            .attr("width", 90)
            .attr("height", 25)
            .attr("fill", "#ffffff")
            .attr("stroke", "#c9e0be")
            .attr("rx", 4)
            .style("cursor", "pointer")
            .style("filter", "drop-shadow(0px 1px 2px rgba(0, 0, 0, 0.1))");

        const flowDotsText = controlPanel
            .append("text")
            .attr("x", 55)
            .attr("y", 80)
            .attr("text-anchor", "middle")
            .attr("font-size", "10px")
            .attr("fill", "#555")
            .attr("class", "flow-dots-text")
            .text("Hide Direction")
            .style("cursor", "pointer")
            .style("user-select", "none");

        // Define toggleFlowDots as a regular function, not useCallback
        const toggleFlowDots = () => {
            // Toggle flow dots visibility
            const dotsVisible = g.selectAll(".flow-dot").style("display") !== "none";
            g.selectAll(".flow-dot").style("display", dotsVisible ? "none" : "block");

            // Update button appearance
            flowDotsButton.attr("fill", dotsVisible ? "#ffffff" : "#f0f7ff");

            // Update the button text
            flowDotsText.text(dotsVisible ? "Show Direction" : "Hide Direction");
        };

        flowDotsButton.on("click", toggleFlowDots);
        flowDotsText.on("click", toggleFlowDots);

        // Add resize listener
        const updateControlPanelPosition = () => {
            const currentWidth = Number(svg.attr("width")) || width;
            controlPanel.attr("transform", `translate(${currentWidth - 160}, 20)`);
        };

        window.addEventListener("resize", updateControlPanelPosition);

        // Return cleanup function
        return () => {
            window.removeEventListener("resize", updateControlPanelPosition);
            controlPanel.remove(); // Remove the control panel when component unmounts
        };
    }, [svg, g, zoom, width, height]); // Dependencies

    // Return null since the actual UI is created with D3
    return null;
}