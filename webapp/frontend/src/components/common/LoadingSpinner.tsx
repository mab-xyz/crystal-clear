import { useEffect, useState } from "react";
import { NewtonsCradle } from "ldrs/react";
import "ldrs/react/NewtonsCradle.css";
import catSpinningGif from "../../assets/cat-spinning.gif";

// Default values shown
<NewtonsCradle size="78" speed="1.4" color="#2b2b2b" />;

interface LoadingSpinnerProps {
  inputAddress: string;
  fromBlock: number | null;
  toBlock: number | null;
}

export default function LoadingSpinner({
  inputAddress,
  fromBlock,
  toBlock,
}: LoadingSpinnerProps) {
  const [loaderType, setLoaderType] = useState<"newtonsCradle" | "gif">(
    "newtonsCradle",
  );

  useEffect(() => {
    // Randomly choose a loader when component mounts
    const randomLoader = Math.random() < 0.7 ? "newtonsCradle" : "gif";
    setLoaderType(randomLoader);
  }, []);

  return (
    <div
      className="loading-container"
      style={{
        display: "flex",
        justifyContent: "center",
        alignItems: "center",
        padding: "40px",
        flexDirection: "column",
      }}
    >
      <div
        className="loading-spinner"
        style={{
          marginBottom: "15px",
        }}
      >
        {loaderType === "newtonsCradle" ? (
          <NewtonsCradle size={78} speed={1.4} color="#2b2b2b" />
        ) : (
          <img
            src={catSpinningGif}
            alt="Loading"
            width="80"
            height="80"
            style={{ display: "block" }}
          />
        )}
      </div>
      <div
        style={{
          color: "#444",
          fontSize: "16px",
          fontWeight: "500",
          marginBottom: "8px",
        }}
      >
        Analyzing Contract Dependencies
      </div>
      <div
        style={{
          color: "#666",
          fontSize: "14px",
          textAlign: "center",
          maxWidth: "400px",
          lineHeight: "1.5",
        }}
      >
        Fetching data for{" "}
        <span style={{ fontWeight: "bold" }}>
          {inputAddress.substring(0, 8)}...
          {inputAddress.substring(inputAddress.length - 6)}
        </span>
        {fromBlock && toBlock && (
          <>
            <br />
            Blocks: {fromBlock} to {toBlock}
          </>
        )}
        {fromBlock && !toBlock && (
          <>
            <br />
            From block: {fromBlock}
          </>
        )}
        {!fromBlock && toBlock && (
          <>
            <br />
            To block: {toBlock}
          </>
        )}
        <br />
        <span style={{ fontSize: "13px", opacity: "0.8" }}>
          This may take a moment depending on contract complexity
        </span>
      </div>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }

      `}</style>
    </div>
  );
}
