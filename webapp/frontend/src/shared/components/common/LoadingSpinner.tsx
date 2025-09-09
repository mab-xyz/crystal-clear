import { useEffect, useState } from "react";
import { NewtonsCradle } from "ldrs/react";
import "ldrs/react/NewtonsCradle.css";
import catSpinningGif from "@/assets/cat-spinning.gif";

export default function LoadingSpinner() {
  const [loaderType, setLoaderType] = useState<"newtonsCradle" | "gif">(
    "newtonsCradle",
  );

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
    return addr.length > 14 ? `${addr.slice(0, 8)}...${addr.slice(-6)}` : addr;
  };

  return (
    <div className="flex flex-col items-center justify-center px-10 py-16">
      <div className="mb-4">
        {loaderType === "newtonsCradle" ? (
          <NewtonsCradle size={78} speed={1.4} color="#2b2b2b" />
        ) : (
          <img
            src={catSpinningGif}
            alt="Loading"
            width={80}
            height={80}
            className="block"
          />
        )}
      </div>

      <div className="mb-2 text-base font-medium text-gray-700">
        Analyzing Contract Dependencies
      </div>

      <div className="max-w-sm text-center text-sm leading-6 text-gray-600">
        Fetching data for <strong>{formatAddress(address)}</strong>
        <br />
        {fromBlock && toBlock && (
          <>
            {" "}
            from block {fromBlock} to block {toBlock}
          </>
        )}
        <br />
        <span className="text-xs opacity-80">
          This may take a few seconds depending on contract complexity.
        </span>
      </div>
    </div>
  );
}
