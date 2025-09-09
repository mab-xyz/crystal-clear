import React, { useState, useEffect } from "react";
import { isAddress } from "ethers";
import { Link, useNavigate } from "react-router";

import { Input } from "@/shared/components/ui/input";
import { Button } from "@/shared/components/ui/button";
import { RadioGroup, RadioGroupItem } from "@/shared/components/ui/radio-group";
import { Label } from "@/shared/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/shared/components/ui/select";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/shared/components/ui/popover";

import { AddressInput } from "@/shared/components/common/AddressInput";
import { filterOptions } from "@/utils/popularContracts";
import {
  validateBlockRange,
  handleBlockRangeTypeChange,
  type BlockRangeType,
} from "@/utils/blockRange";
import {
  handleDefaultAnalyze,
  getDefaultBlockRange,
} from "@/utils/defaultAnalyze";
import { errorManager } from "@/shared/utils/errorManager";
import {
  getDeploymentInfo,
  getLatestBlock,
  getApiAvailability,
} from "@/utils/queries";
import type { CustomSubmitEvent } from "@/utils/defaultAnalyze";

interface HeaderProps {
  inputAddress: string;
  setInputAddress: (address: string, isValid?: boolean) => void;
  fromBlock: string;
  setFromBlock: (block: string) => void;
  toBlock: string;
  setToBlock: (block: string) => void;
  handleSubmit: (e: React.FormEvent | CustomSubmitEvent) => void;
}

export default function Header({
  inputAddress,
  setInputAddress,
  fromBlock,
  setFromBlock,
  toBlock,
  setToBlock,
  handleSubmit,
}: HeaderProps) {
  const [selectedFilter, setSelectedFilter] = useState<string>("");
  const [blockRangeType, setBlockRangeType] = useState<BlockRangeType>("deep");

  const [lastSelectedRange, setLastSelectedRange] = useState<number | null>(
    null,
  );
  const [apiAvailability, setApiAvailability] = useState<boolean>(true);
  const navigate = useNavigate();
  const { setError } = errorManager();

  const [latestBlockNumber, setLatestBlockNumber] = useState<number | null>(
    null,
  );

  // Check if the API is available
  useEffect(() => {
    (async () => {
      const available = await getApiAvailability();
      setApiAvailability(available);
      console.log("apiAvailability in homepage", apiAvailability);

      const latestBlock = await getLatestBlock(apiAvailability);
      setLatestBlockNumber(latestBlock);
      console.log("latestBlockNumber", latestBlock);
    })();
  }, []);

  // Function to update URL with address and block parameters
  const updateUrlWithParams = (
    address: string,
    from?: string,
    to?: string,
  ): void => {
    let url = `/graph/?address=${address}`;

    // Add query parameters if block range is specified
    if (from && to) {
      url += `&from_block=${from}&to_block=${to}`;
    }

    // Update URL without reloading the page
    navigate(url, { replace: true });
  };

  const validateForm = (
    fromBlock: string,
    toBlock: string,
  ): { valid: boolean; error?: string } => {
    if (!inputAddress || inputAddress.trim() === "")
      return { valid: false, error: "Please enter a contract address." };
    if (!isAddress(inputAddress))
      return { valid: false, error: "Invalid Ethereum address." };

    if (fromBlock && !/^\d+$/.test(fromBlock))
      return { valid: false, error: "From Block must contain only numbers." };
    if (toBlock && !/^\d+$/.test(toBlock))
      return { valid: false, error: "To Block must contain only numbers." };

    console.log("inputAddress", inputAddress, typeof inputAddress);
    console.log("fromBlockinisFormValid", fromBlock, typeof fromBlock);
    console.log("toBlockinisFormValid", toBlock, typeof toBlock);

    const { valid: rangeValid, reason } = validateBlockRange(
      fromBlock,
      toBlock,
    );
    if (!rangeValid)
      return { valid: false, error: reason || "Invalid block range." };

    return { valid: true };
  };

  // Function to handle from block input changes with validation
  const handleBlockInputChange = (
    e: React.ChangeEvent<HTMLInputElement>,
    setter: (block: string) => void,
  ): void => {
    const cleanedValue = e.target.value.replace(/[^0-9]/g, "");
    setter(cleanedValue);
  };

  const fetchDeploymentInfo = async (): Promise<boolean> => {
    try {
      await getDeploymentInfo(inputAddress, apiAvailability ?? false, () => {});
      return true;
    } catch (err) {
      // Silently fail - let Sidebar handle showing deployment info errors in UI
      console.log("Failed to fetch deployment information:", err);
      return false;
    }
  };

  const submitWithBlockRange = async (
    e: React.FormEvent | CustomSubmitEvent,
  ) => {
    e.preventDefault();

    const { valid, error } = validateForm(fromBlock, toBlock);
    console.log("valid", valid, "error", error);
    if (!valid) {
      setError("form", error || "Invalid input.");
      return;
    }

    // Try to fetch deployment info but don't block analysis if it fails
    await fetchDeploymentInfo();

    const customEvent = { ...e, preventDefault: () => {} } as CustomSubmitEvent;
    customEvent.blockRange = {
      fromBlock: fromBlock ? parseInt(fromBlock) : null,
      toBlock: toBlock ? parseInt(toBlock) : null,
    };
    updateUrlWithParams(inputAddress, fromBlock, toBlock);
    handleSubmit(customEvent);
  };

  const handleDefaultAnalyzeClick = async (): Promise<void> => {
    if (!latestBlockNumber) return;

    console.log("latestBlockNumber", latestBlockNumber);
    console.log("fromBlock", fromBlock);
    console.log("toBlock", toBlock);

    const { valid, error } = validateForm(fromBlock, toBlock);
    if (!valid) {
      setError("form", error || "Invalid input.");
      return;
    }

    const blockRange = await getDefaultBlockRange(
      setError,
      latestBlockNumber,
      apiAvailability,
    );
    if (!blockRange) return;

    setFromBlock(blockRange.fromBlock.toString());
    setToBlock(blockRange.toBlock.toString());
    updateUrlWithParams(
      inputAddress,
      blockRange.fromBlock.toString(),
      blockRange.toBlock.toString(),
    );

    // Try to fetch deployment info but don't block analysis if it fails
    await fetchDeploymentInfo();

    await handleDefaultAnalyze(
      inputAddress,
      setFromBlock,
      setToBlock,
      handleSubmit,
      (msg) => setError("api", msg),
      latestBlockNumber,
      apiAvailability,
    );
  };

  const handleFilterChange = (value: string): void => {
    const selectedOption = filterOptions.find((opt) => opt.value === value);
    if (!selectedOption) return;
    setSelectedFilter(value);
    setInputAddress(value);
  };

  return (
    <div>
      {/* Pinned Header */}
      <div className="sticky top-0 z-[1000] border-b-1 bg-white px-4 py-2">
        <div className="mx-2 flex h-auto min-h-[54px] flex-wrap items-center justify-between gap-2.5 py-1.5">
          {/* Logo */}
          <Link to="/">
            <div className="flex items-center text-2xl text-[#2b2b2b]">
              <svg
                width="80"
                height="50"
                viewBox="0 0 2300 700"
                fill="none"
                xmlns="http://www.w3.org/2000/svg"
                className="mr-2"
              >
                <path
                  d="M29.8823 458.387C25.0234 300.861 15.5044 289.583 24.6411 288.467L64.9279 264.714L94.1015 302.332M94.1015 302.332L110.062 381.878M94.1015 302.332L92.4058 247.359L148.531 218.114L179.364 244.676M179.364 244.676L203.524 362.988M179.364 244.676L237.988 215.355L295.809 241.085M295.809 241.085L314.768 320.538M295.809 241.085L307.075 71.1565L355.911 32.6325L399.961 49.7826L414.019 505.566L632.548 519.335L652.812 576.237L636.648 652.272L418.752 658.993"
                  stroke="#2b2b2b"
                  stroke-width="40"
                />
                <path
                  d="M1333.52 437.513C1332.92 279.914 1342.04 268.312 1332.87 267.514L1291.78 245.171L1263.93 283.779M1263.93 283.779L1250.74 363.83M1263.93 283.779L1263.72 228.779L1206.61 201.498L1176.72 229.113M1176.72 229.113L1156.68 348.191M1176.72 229.113L1117.11 201.841L1060.22 229.56M1060.22 229.56L1044.03 309.623M1060.22 229.56L1043.07 60.1246L992.928 23.3168L949.5 41.9837L951.25 497.98L733.33 519.317L715.051 576.887L733.841 652.316L951.839 651.479"
                  stroke="#2b2b2b"
                  stroke-width="40"
                />
                <rect
                  x="26.2239"
                  y="-0.336626"
                  width="225.617"
                  height="225.525"
                  transform="matrix(0.645906 -0.763417 0.665289 0.746586 519.839 276.693)"
                  stroke="#2b2b2b"
                  stroke-width="40"
                />
                <path
                  d="M536.883 256.901L831.982 253.476"
                  stroke="#2b2b2b"
                  stroke-width="25"
                />
                <path d="M684 98L684 416" stroke="#2b2b2b" stroke-width="25" />
                <path
                  d="M1018.8 671V452H1063.2L1084.5 521.6C1086.7 528.6 1088.5 535 1089.9 540.8C1091.3 546.6 1092.2 550.8 1092.6 553.4C1093 550.8 1093.9 546.6 1095.3 540.8C1096.7 535 1098.4 528.6 1100.4 521.6L1120.8 452H1165.2V671H1130.1V602.9C1130.1 592.9 1130.4 582 1131 570.2C1131.6 558.4 1132.3 546.6 1133.1 534.8C1133.9 523 1134.8 511.8 1135.8 501.2C1137 490.6 1138 481.3 1138.8 473.3L1109.4 576.8H1075.2L1044.9 473.3C1045.9 480.9 1046.9 489.9 1047.9 500.3C1048.9 510.5 1049.8 521.5 1050.6 533.3C1051.6 544.9 1052.4 556.7 1053 568.7C1053.6 580.7 1053.9 592.1 1053.9 602.9V671H1018.8ZM1192.38 671L1247.58 452H1295.88L1351.38 671H1312.98L1300.98 617.9H1242.78L1230.78 671H1192.38ZM1249.68 587.3H1294.08L1280.88 528.5C1278.68 518.7 1276.78 509.9 1275.18 502.1C1273.58 494.1 1272.48 488.3 1271.88 484.7C1271.28 488.3 1270.18 494.1 1268.58 502.1C1267.18 509.9 1265.28 518.6 1262.88 528.2L1249.68 587.3ZM1384.87 671V452H1452.07C1473.27 452 1490.07 457.1 1502.47 467.3C1514.87 477.3 1521.07 491 1521.07 508.4C1521.07 518.2 1518.87 526.7 1514.47 533.9C1510.07 541.1 1504.07 546.7 1496.47 550.7C1489.07 554.7 1480.47 556.7 1470.67 556.7V555.5C1481.27 555.3 1490.67 557.3 1498.87 561.5C1507.27 565.5 1513.87 571.5 1518.67 579.5C1523.67 587.5 1526.17 597.2 1526.17 608.6C1526.17 621.2 1523.27 632.2 1517.47 641.6C1511.67 651 1503.47 658.3 1492.87 663.5C1482.47 668.5 1469.97 671 1455.37 671H1384.87ZM1421.47 639.8H1452.97C1463.97 639.8 1472.57 636.9 1478.77 631.1C1485.17 625.1 1488.37 617 1488.37 606.8C1488.37 596.6 1485.17 588.4 1478.77 582.2C1472.57 575.8 1463.97 572.6 1452.97 572.6H1421.47V639.8ZM1421.47 542.3H1451.47C1461.47 542.3 1469.27 539.7 1474.87 534.5C1480.67 529.1 1483.57 521.8 1483.57 512.6C1483.57 503.4 1480.67 496.2 1474.87 491C1469.27 485.8 1461.47 483.2 1451.47 483.2H1421.47V542.3ZM1631.65 674C1623.05 674 1616.15 671.5 1610.95 666.5C1605.95 661.5 1603.45 654.7 1603.45 646.1C1603.45 637.5 1605.95 630.7 1610.95 625.7C1616.15 620.5 1623.05 617.9 1631.65 617.9C1640.25 617.9 1647.05 620.5 1652.05 625.7C1657.25 630.7 1659.85 637.5 1659.85 646.1C1659.85 654.7 1657.25 661.5 1652.05 666.5C1647.05 671.5 1640.25 674 1631.65 674ZM1729.93 671L1790.53 558.8L1733.53 452H1775.53L1803.13 506.9C1805.13 510.9 1806.93 514.8 1808.53 518.6C1810.13 522.2 1811.33 525 1812.13 527C1812.73 525 1813.83 522.2 1815.43 518.6C1817.03 514.8 1818.83 510.9 1820.83 506.9L1848.73 452H1889.53L1832.53 557.9L1893.13 671H1851.13L1820.23 610.4C1818.23 606.4 1816.33 602.5 1814.53 598.7C1812.93 594.9 1811.73 591.9 1810.93 589.7C1810.13 591.9 1808.93 594.9 1807.33 598.7C1805.73 602.5 1803.93 606.4 1801.93 610.4L1770.73 671H1729.93ZM1972.51 671V591.5L1908.31 452H1947.61L1981.81 527.9C1984.41 533.9 1986.61 539.8 1988.41 545.6C1990.21 551.4 1991.41 555.9 1992.01 559.1C1992.81 555.9 1994.01 551.4 1995.61 545.6C1997.41 539.8 1999.61 533.9 2002.21 527.9L2035.51 452H2074.51L2010.31 591.5V671H1972.51ZM2105 671V635.3L2192.9 486.8H2107.1V452H2234.3V487.7L2146.1 636.2H2237.6V671H2105Z"
                  fill="#212121"
                />
              </svg>
              Crystal Clear
            </div>
          </Link>

          {/* Search Form - RIGHT ALIGNED */}
          <form
            onSubmit={submitWithBlockRange}
            className="ml-auto flex w-auto min-w-[600px] items-center justify-end gap-2"
          >
            {/* Filter Dropdown */}
            <Select
              onValueChange={(value) => handleFilterChange(value)}
              value={selectedFilter}
            >
              <SelectTrigger className="h-9 w-32 rounded-sm border border-black bg-white px-4 !text-xs text-black">
                <SelectValue placeholder="Select" />
              </SelectTrigger>
              <SelectContent className="z-[1000] overflow-hidden rounded-sm border-[1.5px] border-[#0a0a0a] bg-white p-0">
                {filterOptions.map((option) => (
                  <SelectItem
                    key={option.value}
                    value={option.value}
                    className="rounded-none px-2 py-1 text-sm hover:bg-[#7469B6] hover:text-white focus:bg-[#7469B6] focus:text-white"
                  >
                    {option.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            {/* Address Input - Now using the abstracted component */}
            <AddressInput
              value={inputAddress}
              onChange={(value) => {
                setInputAddress(value);

                // Clear URL parameters when input is cleared
                if (value === "") {
                  navigate(window.location.pathname, { replace: true });
                }

                // Clear selected filter when input is cleared or doesn't match filter value
                if (
                  selectedFilter &&
                  (value === "" ||
                    value !==
                      filterOptions.find((opt) => opt.value === selectedFilter)
                        ?.value)
                ) {
                  setSelectedFilter("");
                }
              }}
              className="h-9"
            />

            {/* Analyze Button + Dropdown */}
            <div className="relative flex items-center gap-2">
              <Button
                type="button"
                variant="outline"
                onClick={() => {
                  if (!inputAddress || inputAddress.trim() === "") {
                    setError("form", "Please enter a contract address.");
                    return;
                  }
                  handleDefaultAnalyzeClick();
                }}
                className="bg-primary text-primary-foreground hover:bg-primary/90 h-9 rounded-sm border border-black px-4 text-xs"
              >
                <span>Analyze</span>
              </Button>

              <Popover>
                <PopoverTrigger asChild>
                  <Button
                    type="button"
                    size="icon"
                    className="h-9 w-9 rounded-sm border border-black bg-[#efefef] text-xs"
                  >
                    <svg
                      width="24"
                      height="24"
                      viewBox="0 0 24 24"
                      fill="none"
                      xmlns="http://www.w3.org/2000/svg"
                    >
                      <path
                        fillRule="evenodd"
                        clipRule="evenodd"
                        d="M4 4H10V7H22V9H10V12H4V9H2V7H4V4ZM6 6V10H8V6H6ZM14 12H20V15H22V17H20V20H14V17H2V15H14V12ZM16 14V18H18V14H16Z"
                        fill="black"
                      />
                    </svg>
                  </Button>
                </PopoverTrigger>
                <PopoverContent
                  className="z-[1000] w-[280px] overflow-visible rounded-sm border border-solid border-[#6985b6] bg-white p-4 shadow-lg"
                  align="end"
                  sideOffset={16}
                >
                  <div className="flex flex-col gap-4">
                    {/* Title with separator */}
                    <div className="mb-1 border-b border-gray-300 pb-3">
                      <div className="text-md mt-1 mb-1 flex items-center px-4 py-1 font-bold tracking-wide text-[#7469B6]">
                        {/* <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="mr-2 flex-shrink-0 !px-0.5">
                                                    <path fill-rule="evenodd" clip-rule="evenodd" d="M3 3H11V5H3V17H11V5H13V17H21V5H13V3H21H23V5V17V19H21H13V21H11V19H3H1V17V5V3H3ZM19 10H15V12H19V10ZM15 7H19V9H15V7ZM17 13H15V15H17V13Z" fill="#7469B6" />
                                                </svg> */}
                        Analysis Mode
                      </div>
                    </div>

                    {/* Radio options with better spacing */}
                    <div className="ml-2 flex flex-col items-start gap-1.5 px-4">
                      <RadioGroup
                        value={blockRangeType}
                        onValueChange={(value: BlockRangeType) => {
                          console.log("Block range type selected:", value);
                          setBlockRangeType(value); // Set state immediately for UI responsiveness
                          handleBlockRangeTypeChange(
                            value,
                            setBlockRangeType,
                            setFromBlock,
                            setToBlock,
                            setLastSelectedRange,
                            lastSelectedRange,
                            inputAddress,
                            updateUrlWithParams,
                            handleSubmit,
                            (msg: string) => setError("api", msg),
                            apiAvailability,
                          );
                          console.log("handleBlockRangeTypeChange called");
                        }}
                        className="space-y-3"
                      >
                        <div className="group relative flex w-full items-center space-x-2 rounded-sm p-1.5 hover:bg-[#c9e0be]">
                          <div className="flex items-center gap-2 space-x-3">
                            <RadioGroupItem value="deep" id="deep" />
                            <Label htmlFor="deep" className="cursor-pointer">
                              Deep
                            </Label>
                          </div>
                          <div className="absolute -top-10 left-1/2 z-[1001] hidden w-auto -translate-x-1/2 rounded-sm border border-gray-600 bg-black px-2 py-1 text-xs whitespace-nowrap text-white shadow-lg group-hover:block">
                            (WIP) Fast Mode (50 blocks)
                          </div>
                        </div>

                        <div className="group relative flex w-full items-center space-x-2 rounded-sm p-1.5 hover:bg-[#c9e0be]">
                          <div className="flex items-center gap-2 space-x-3">
                            <RadioGroupItem value="ultimate" id="ultimate" />
                            <Label
                              htmlFor="ultimate"
                              className="cursor-pointer"
                            >
                              Ultimate
                            </Label>
                          </div>
                          <div className="absolute -top-10 left-1/2 z-[1001] hidden w-auto -translate-x-1/2 rounded-sm border border-gray-600 bg-black px-2 py-1 text-xs whitespace-nowrap text-white shadow-lg group-hover:block">
                            (WIP) Secure Mode (All lifetime blocks)
                          </div>
                        </div>

                        <div className="group relative flex w-full items-center space-x-2 rounded-sm p-1.5 hover:bg-[#c9e0be]">
                          <div className="flex items-center gap-2 space-x-3">
                            <RadioGroupItem value="custom" id="custom" />
                            <Label htmlFor="custom" className="cursor-pointer">
                              Custom Block Range
                            </Label>
                          </div>
                          <div className="absolute -top-10 left-1/2 z-[1001] hidden w-auto -translate-x-1/2 rounded-sm border border-gray-600 bg-black px-2 py-1 text-xs whitespace-nowrap text-white shadow-lg group-hover:block">
                            Put your own block numbers
                          </div>
                        </div>
                      </RadioGroup>
                    </div>

                    {/* Block range inputs with improved styling */}
                    <div className="mx-2 mt-1 flex gap-2.5 px-4 pt-2 text-xs">
                      <Input
                        type="text"
                        value={fromBlock}
                        onChange={(e) =>
                          handleBlockInputChange(e, setFromBlock)
                        }
                        placeholder="From Block"
                        className={`h-9 flex-1 rounded-sm border border-black px-2 text-xs ${blockRangeType === "custom" ? "bg-white" : "bg-[#a4a2bc]"}`}
                        disabled={blockRangeType !== "custom"}
                      />
                      <Input
                        type="text"
                        value={toBlock}
                        onChange={(e) => handleBlockInputChange(e, setToBlock)}
                        placeholder="To Block"
                        className={`h-9 flex-1 rounded-sm border border-black px-2 text-xs ${blockRangeType === "custom" ? "bg-white" : "bg-[#a4a2bc]"}`}
                        disabled={blockRangeType !== "custom"}
                      />
                    </div>

                    {/* Submit button*/}
                    <Button
                      type="button"
                      onClick={(e) => submitWithBlockRange(e)}
                      className="mx-2.5 mt-0.5 mb-2.5 rounded-none bg-[#AEEA94] px-2 text-xs"
                    >
                      <span className="font-bold text-[#000080]">Analyze</span>
                    </Button>
                  </div>
                </PopoverContent>
              </Popover>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
