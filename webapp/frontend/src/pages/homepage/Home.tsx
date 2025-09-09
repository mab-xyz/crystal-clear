import React, { useState, useEffect, useCallback } from "react";
import { useLocation, useNavigate } from "react-router";
import { isAddress } from "ethers";
import { GraphLayout } from "@/domains/graph";
import type { GraphData } from "@/types/graph";
import { Button } from "@/shared/components/ui";
import { AddressInput, SimpleLoader } from "@/shared/components/common";
import { getDefaultBlockRange } from "@/utils/defaultAnalyze";
import { popularContracts } from "@/domains/contracts";
import { getLatestBlock, getApiAvailability } from "@/domains/contracts";
import { validateBlockRange } from "@/utils/blockRange";
import { useAppContext } from "@/app/contexts/AppContext";
import { useLocalAlert } from "@/shared/components/ui";
import { TEXT } from "@/constants";
import styles from "./Home.module.css";
// load sample graph data from json file
import SAMPLE_GRAPH_DATA from "./home_graph_eg.json";

export default function HomePage() {
  const [inputAddress, setInputAddress] = useState<string>("");
  const [highlightAddress, setHighlightAddress] = useState<string | null>(null);
  const [apiAvailability, setApiAvailability] = useState<boolean | undefined>(
    undefined,
  );
  const [loading, setLoading] = useState<boolean>(false);

  const { setGlobalError, clearGlobalError } = useAppContext();
  const { showLocalAlert } = useLocalAlert();

  const location = useLocation();
  const navigate = useNavigate();

  const latestBlockNumber = getLatestBlock(apiAvailability);

  // --- Effect: Load API health and query params ---
  useEffect(() => {
    (async () => {
      const available = await getApiAvailability();
      setApiAvailability(available);
      console.log("apiAvailability in homepage", available);
    })();

    const addressParam = new URLSearchParams(location.search).get("address");
    if (addressParam) setInputAddress(addressParam);
  }, [location]);

  // --- Handle form submission ---
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    clearGlobalError();

    if (loading) return;
    setLoading(true);

    try {
      if (!inputAddress.trim()) {
        showLocalAlert("Please enter a contract address.");
        return;
      }

      if (!isAddress(inputAddress)) {
        showLocalAlert("Invalid Ethereum address.");
        return;
      }

      if (!apiAvailability) {
        const errorMsg = "API is not available. Please refresh the page.";
        setGlobalError(errorMsg);
        showLocalAlert(errorMsg);
        return;
      }

      try {
        const resolvedLatestBlock = await latestBlockNumber;
        if (!resolvedLatestBlock) {
          const errorMsg = "Latest block number is not available.";
          setGlobalError(errorMsg);
          showLocalAlert(errorMsg);
          return;
        }

        const { fromBlock, toBlock } = await getDefaultBlockRange(
          (_type, message) => {
            setGlobalError(message);
            showLocalAlert(message);
          },
          resolvedLatestBlock,
          apiAvailability,
        );
        const { valid, reason } = validateBlockRange(fromBlock, toBlock);
        if (!valid) {
          const errorMsg = reason || "Invalid block range.";
          setGlobalError(errorMsg);
          showLocalAlert(errorMsg);
          return;
        }

        navigate(
          `/graph?address=${inputAddress}&from_block=${fromBlock}&to_block=${toBlock}`,
        );
      } catch (error) {
        const errorMsg = "Failed to fetch latest block number.";
        setGlobalError(errorMsg);
        showLocalAlert(errorMsg);
      }
    } finally {
      setLoading(false);
    }
  };

  // --- Handle popular address selection ---
  const handleAddressSelect = (address: string) => {
    setInputAddress((prev) => (prev === address ? "" : address));
  };

  // --- Handle node click in demo graph ---
  const handleNodeClick = useCallback(() => {
    setHighlightAddress(null);
  }, []);

  return (
    <div className={styles["container"]}>
      {/* Header Section */}
      <header className={styles["header"]}>
        {/* TODO: Future navigation elements will go here */}
      </header>

      <div className={styles["mainContent"]}>
        {/* Left side: Interactive network graph visualization */}
        <div className={styles["graphSection"]}>
          {/* Interactive sample graph */}
          <GraphLayout
            jsonData={SAMPLE_GRAPH_DATA as GraphData}
            highlightAddress={highlightAddress}
            inputAddress={"0xSampleMainContract"}
            onNodeClick={handleNodeClick}
            isHomepage={true}
          />
        </div>

        {/* Right side: Name and search bar */}
        <div className={styles["contentSection"]}>
          <div className={styles["contentCard"]}>
            <h2 className={styles["title"]}>{TEXT.APP_NAME}</h2>
            <p className={styles["subtitle"]}>{TEXT.TAGLINE}</p>

            <div className={styles["searchSection"]}>
              {/* Search form */}
              <form onSubmit={handleSubmit} className={styles["searchForm"]}>
                <div className={styles["inputGroup"]}>
                  <div className={styles["inputContainer"]}>
                    <AddressInput
                      value={inputAddress}
                      onChange={(value) => {
                        setInputAddress(value);
                        console.log("inputAddress in homepage", inputAddress);
                      }}
                      placeholder={TEXT.PLACEHOLDER_ADDRESS}
                      className="flex-1"
                    />
                    <Button
                      variant="default"
                      size="default"
                      type="submit"
                      disabled={loading}
                      className="flex items-center gap-2 !px-6"
                    >
                      {loading && <SimpleLoader size="sm" color="white" />}
                      {loading ? TEXT.LOADING_TEXT : TEXT.ANALYZE_BUTTON}
                    </Button>
                  </div>
                </div>

                {/* Popular Protocols Section */}
                <div className={styles["protocolsSection"]}>
                  <span className={styles["protocolsLabel"]}>
                    {TEXT.TRY_PROTOCOLS}
                  </span>
                  <div className={styles["protocolsGrid"]}>
                    {popularContracts.map((contract, index) => (
                      <Button
                        key={index}
                        variant="secondary"
                        size="sm"
                        type="button"
                        onClick={() => handleAddressSelect(contract.address)}
                        className={`${styles["protocolButton"]} px-4 py-2`}
                      >
                        {contract.name}
                      </Button>
                    ))}
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
