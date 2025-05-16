import React, { useState, useEffect } from "react";
import type { JsonData } from "../../types";
// import { useLocalAlert } from "../ui/local-alert";

interface RiskDetailsProps {
    jsonData: JsonData | null;
}

interface RiskMetric {
    name: string;
    value: string;
    level: "high" | "medium" | "low";
}

export default function RiskDetails({ jsonData }: RiskDetailsProps) {
    // const { showLocalAlert } = useLocalAlert();
    const [riskMetrics, setRiskMetrics] = useState<RiskMetric[]>([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        // For now, we'll just use placeholders instead of fetching real data
        setRiskMetrics([]);
    }, [jsonData]);

    // Comment out the actual fetch function for now
    /*
    const fetchRiskData = async (address: string) => {
        try {
            setLoading(true);

            // Fetch risk data from the API
            const response = await fetch(`http://localhost:8000/v1/analysis/${address}/risk`);

            if (!response.ok) {
                throw new Error(`Failed to fetch risk data: ${response.statusText}`);
            }

            const data = await response.json();

            // Transform the risk factors into our format
            if (data.risk_factors) {
                const metrics: RiskMetric[] = Object.entries(data.risk_factors).map(([key, value]: [string, any]) => {
                    // Determine risk level based on the value
                    let level: "high" | "medium" | "low" = "medium";
                    if (typeof value === "number") {
                        level = value > 70 ? "high" : value > 30 ? "medium" : "low";
                    } else if (typeof value === "string") {
                        level = value.toLowerCase().includes("high") ? "high" :
                            value.toLowerCase().includes("medium") ? "medium" : "low";
                    }

                    return {
                        name: key.replace(/_/g, " ").replace(/\b\w/g, l => l.toUpperCase()),
                        value: typeof value === "string" ? value : String(value),
                        level
                    };
                });

                setRiskMetrics(metrics);
            }
        } catch (error) {
            console.error("Error fetching risk data:", error);
            showLocalAlert("Failed to fetch risk details");

            // Set default metrics if API call fails
            setRiskMetrics([
                { name: "Immutability", value: "Placeholder_high", level: "high" },
                { name: "Admin Privileges", value: "Placeholder_Medium", level: "medium" },
                { name: "Auditing Information", value: "Placeholder_Low", level: "low" },
                { name: "GitHub Quality", value: "Placeholder_Medium", level: "medium" },
            ]);
        } finally {
            setLoading(false);
        }
    };
    */

    // If no data yet, show placeholders
    if (riskMetrics.length === 0) {
        return (
            <div style={{
                backgroundColor: "white",
                padding: "15px",
                borderRadius: "8px",
                height: "100%",
                width: "100%"
            }}>
                <div style={{ fontWeight: "bold", marginBottom: 10 }}>
                    Risk Metrics
                </div>
                {[
                    "Immutability",
                    "Admin Privileges",
                    "Auditing Information",
                    "GitHub Quality",
                ].map((item, index) => (
                    <div
                        key={index}
                        style={{
                            display: "flex",
                            justifyContent: "space-between",
                            padding: "8px 10px",
                            marginBottom: 5,
                            backgroundColor: "white",
                            borderRadius: "4px",
                            border: "1px solid #eee",
                        }}
                    >
                        <span>{item}</span>
                        <span
                            style={{
                                fontWeight: "500",
                                color:
                                    index % 3 === 0
                                        ? "#e74c3c"
                                        : index % 3 === 1
                                            ? "#f39c12"
                                            : "#27ae60",
                            }}
                        >
                            {index % 3 === 0
                                ? "Placeholder_high"
                                : index % 3 === 1
                                    ? "Placeholder_Medium"
                                    : "Placeholder_Low"}
                        </span>
                    </div>
                ))}

                <div
                    style={{
                        marginTop: 30,
                        fontSize: 13,
                        color: "#666",
                        lineHeight: "1.5",
                        textAlign: "left"
                    }}
                >
                    Risk assessment is based on risk metrics. The tools are
                    selected from the state-of-the-art research.
                </div>
            </div>
        );
    }

    // Show actual risk metrics
    return (
        <div style={{
            backgroundColor: "white",
            padding: "15px",
            borderRadius: "8px",
            height: "100%",
            width: "100%"
        }}>
            <div style={{ fontWeight: "bold", marginBottom: 10 }}>
                Risk Metrics
            </div>

            {loading ? (
                <div style={{ textAlign: "center", padding: "20px" }}>
                    Loading risk data...
                </div>
            ) : (
                <>
                    {riskMetrics.map((metric, index) => (
                        <div
                            key={index}
                            style={{
                                display: "flex",
                                justifyContent: "space-between",
                                padding: "8px 10px",
                                marginBottom: 5,
                                backgroundColor: "white",
                                borderRadius: "4px",
                                border: "1px solid #eee",
                            }}
                        >
                            <span>{metric.name}</span>
                            <span
                                style={{
                                    fontWeight: "500",
                                    color:
                                        metric.level === "high"
                                            ? "#e74c3c"
                                            : metric.level === "medium"
                                                ? "#f39c12"
                                                : "#27ae60",
                                }}
                            >
                                {metric.value}
                            </span>
                        </div>
                    ))}


                </>
            )}
        </div>
    );
}