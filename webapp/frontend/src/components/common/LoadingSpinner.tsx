import { useEffect, useState } from "react";
import { NewtonsCradle } from "ldrs/react";
import "ldrs/react/NewtonsCradle.css";
import catSpinningGif from "../../assets/cat-spinning.gif";
import { useSearchParams } from "react-router";

export default function LoadingSpinner() {
  const [loaderType, setLoaderType] = useState<"newtonsCradle" | "gif">("newtonsCradle");

  const searchParams = new URLSearchParams(location.search);

  const address = searchParams.get("address") || "";
  const fromBlock = searchParams.get("from_block") || "";
  const toBlock = searchParams.get("to_block") || "";

  useEffect(() => {
    const random = Math.random() < 0.7 ? "newtonsCradle" : "gif";
    setLoaderType(random);
  }, []);

  const formatAddress = (addr: string): string => {
    if (!addr) return "the contract";
    return addr.length > 14
      ? `${addr.slice(0, 8)}...${addr.slice(-6)}`
      : addr;

  };

  return (
    <div
      className="loading-container"
      style={{
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "40px",
      }}
    >
      <div style={{ marginBottom: "15px" }}>
        {loaderType === "newtonsCradle" ? (
          <NewtonsCradle size={78} speed={1.4} color="#2b2b2b" />
        ) : (
          <img
            src={catSpinningGif}
            alt="Loading"
            width={80}
            height={80}
            style={{ display: "block" }}
          />
        )}
      </div>

      <div style={{ fontSize: "16px", fontWeight: 500, color: "#444", marginBottom: "8px" }}>
        Analyzing Contract Dependencies
      </div>

      <div style={{ fontSize: "14px", color: "#666", textAlign: "center", maxWidth: "400px", lineHeight: 1.5 }}>
        Fetching data for{" "}



        <strong>{formatAddress(address)}</strong>
        <br />

        {fromBlock && toBlock && (
          <> from block {fromBlock} to block {toBlock}</>
        )}
        <br />
        <span style={{ fontSize: "13px", opacity: 0.8 }}>
          This may take a few seconds depending on contract complexity.
        </span>
      </div>
    </div>
  );
}
