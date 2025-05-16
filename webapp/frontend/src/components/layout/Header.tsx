import React, { useState } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"
import { useLocalAlert } from "@/components/ui/local-alert";
import { checkApiAvailability } from "@/utils/api";

// Define TypeScript interfaces for props and other data structures
interface HeaderProps {
    inputAddress: string;
    setInputAddress: (address: string) => void;
    fromBlock: string;
    setFromBlock: (block: string) => void;
    toBlock: string;
    setToBlock: (block: string) => void;
    handleSubmit: (e: React.FormEvent | CustomSubmitEvent) => void;
}

// Define custom event type that includes blockRange
interface CustomSubmitEvent extends React.FormEvent {
    blockRange?: {
        fromBlock: number | null;
        toBlock: number | null;
    };
}

interface FilterOption {
    label: string;
    value: string;
}

// interface PopularContract {
//     name: string;
//     address: string;
// }

// interface BlockRangeOption {
//     label: string;
//     days: number;
// }

export default function Header({
    inputAddress,
    setInputAddress,
    fromBlock,
    setFromBlock,
    toBlock,
    setToBlock,
    handleSubmit,
}: HeaderProps) {

    const [lastSelectedRange, setLastSelectedRange] = useState<number | null>(
        null,
    );
    const [showCustomBlockRange, setShowCustomBlockRange] =
        useState<boolean>(false);

    // Add state for filter dropdown
    const [filterOptions] = useState<FilterOption[]>([
        {
            label: "Uniswap: V3 Router",
            value: "0xE592427A0AEce92De3Edee1F18E0157C05861564",
        },
        {
            label: "MetaMask: Swap Router",
            value: "0x881D40237659C251811CEC9c364ef91dC08D300C",
        },
        {
            label: "LI.FI: LiFi Diamond",
            value: "0x1231DEB6f5749EF6cE6943a275A1D3E7486F4EaE",
        },
        { label: "e.g. something", value: "something else A" },
        { label: "e.g. something looooo00oong", value: "something else B" },
    ]);

    const [selectedFilter, setSelectedFilter] = useState<string>("");

    // Add state for radio selection
    const [blockRangeType, setBlockRangeType] = useState<string>("deep");

    // Replace the local state with the hook
    const { showLocalAlert } = useLocalAlert();

    // Function to handle preset block range selection
    const handleBlockRangeSelect = async (days: number): Promise<void> => {
        try {
            // Check if the same range is clicked again (toggle behavior)
            if (lastSelectedRange === days) {
                // Clear the block range inputs
                setFromBlock("");
                setToBlock("");
                setLastSelectedRange(null);
                return;
            }

            // Check API availability first
            const isAvailable = await checkApiAvailability();

            if (!isAvailable) {
                console.error("API is not available at port 8000");
                showLocalAlert("API unavailable. Check port 8000.");
                return;
            }

            const response = await fetch(
                `http://localhost:8000/info/block-latest`,
            );
            const data = await response.json();
            const { from_block, to_block } = data;

            setFromBlock(from_block.toString());
            setToBlock(to_block.toString());
            setLastSelectedRange(days);

            // Show the custom block range when a preset is selected
            setShowCustomBlockRange(true);

            // Automatically submit when any day button is clicked and there's an address
            if (inputAddress) {
                // Create a new event and pass the block range data
                const event = new CustomEvent("submit") as unknown as CustomSubmitEvent;
                // Add block range data to the event
                event.blockRange = {
                    fromBlock: from_block,
                    toBlock: to_block,
                };
                handleSubmit(event);
            }
        } catch (error) {
            console.error("Error setting block range:", error);
        }
    };

    // Function to handle quick address selection - removed for now
    // const handleAddressSelect = (address: string, name: string): void => {
    //     // If the address is already selected, clear it (unselect)
    //     if (inputAddress === address) {
    //         setInputAddress("");
    //     } else {
    //         setInputAddress(address);
    //     }
    // };

    // Function to handle from block input changes with validation
    const handleFromBlockChange = (
        e: React.ChangeEvent<HTMLInputElement>,
    ): void => {
        const value = e.target.value;

        // Remove commas and other non-numeric characters
        const cleanedValue = value.replace(/[^0-9]/g, "");

        setFromBlock(cleanedValue);
    };

    // Function to handle to block input changes with validation
    const handleToBlockChange = (
        e: React.ChangeEvent<HTMLInputElement>,
    ): void => {
        const value = e.target.value;

        // Remove commas and other non-numeric characters
        const cleanedValue = value.replace(/[^0-9]/g, "");

        setToBlock(cleanedValue);
    };

    // Wrap the original handleSubmit to add validation
    const validateAndSubmit = (e: React.FormEvent): void => {
        e.preventDefault();

        // Check if inputs are valid
        let isValid = true;
        let errorMessage = "";

        // Validate address (basic check)
        if (!inputAddress) {
            isValid = false;
            errorMessage = "Please enter a contract address.";
        }

        // Validate block numbers (if provided)
        if (fromBlock && !/^\d+$/.test(fromBlock)) {
            isValid = false;
            errorMessage = "From Block must contain only numbers.";
        }

        if (toBlock && !/^\d+$/.test(toBlock)) {
            isValid = false;
            errorMessage = "To Block must contain only numbers.";
        }

        // If validation passes, call the original handleSubmit
        if (isValid) {
            // Create a new event with block range data
            const newEvent = { ...e } as CustomSubmitEvent;
            newEvent.blockRange = {
                fromBlock: fromBlock ? parseInt(fromBlock) : null,
                toBlock: toBlock ? parseInt(toBlock) : null,
            };
            handleSubmit(newEvent);
        } else {
            showLocalAlert(errorMessage);
        }
    };

    // Popular contract addresses with labels, removed for now
    // const popularContracts: PopularContract[] = [
    //     {
    //         name: "Uniswap V3 Router",
    //         address: "0xE592427A0AEce92De3Edee1F18E0157C05861564",
    //     },
    //     { name: "USDC", address: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48" },
    //     { name: "USDT", address: "0xdAC17F958D2ee523a2206206994597C13D831ec7" },
    //     {
    //         name: "Seaport 1.6",
    //         address: "0x0000000000000068F116a894984e2DB1123eB395",
    //     },
    // ];


    // Function to handle filter selection - updated to fill search bar
    const handleFilterChange = (value: string): void => {
        // Find the selected filter option to get its label
        const selectedOption = filterOptions.find(
            (option) => option.value === value,
        );
        if (selectedOption) {
            setSelectedFilter(value);

            // If a value is provided, fill it into the contract address search bar
            if (value) {
                setInputAddress(value);
            }
        }
    };

    // Block range options - removed for now
    // const blockRangeOptions: BlockRangeOption[] = [
    //     { label: "Fast", days: 1 },
    //     { label: "Deep", days: 3 },
    //     { label: "Ultimate", days: 7 }
    // ];

    // Function to handle default analyze (20 blocks)
    const handleDefaultAnalyze = async (): Promise<void> => {
        try {
            if (!inputAddress || inputAddress.trim() === "") {
                showLocalAlert("Please enter a contract address.");
                return;
            }

            // Check API availability first
            const isAvailable = await checkApiAvailability();

            if (!isAvailable) {
                console.error("API is not available at port 8000");
                showLocalAlert("API unavailable. Check port 8000.");
                return;
            }

            // Get current block and calculate from block (current - 20)
            const response = await fetch(
                "http://localhost:8000/info/block-latest",
            );
            const data = await response.json();
            const currentBlock = data.block_number;
            const fromBlockNum = currentBlock - 20;

            console.log(currentBlock, fromBlockNum);
            console.log(typeof currentBlock, typeof fromBlockNum);


            setFromBlock(fromBlockNum.toString());
            setToBlock(currentBlock.toString());

            // Create a new event with block range data
            const event = new CustomEvent("submit") as unknown as CustomSubmitEvent;
            event.blockRange = {
                fromBlock: fromBlockNum,
                toBlock: currentBlock,
            };
            handleSubmit(event);
        } catch (error) {
            console.error("Error setting default block range:", error);
        }
    };

    // Function to handle block range type selection
    const handleBlockRangeTypeChange = (e: React.ChangeEvent<HTMLInputElement>): void => {
        setBlockRangeType(e.target.value);

        // If selecting a preset option, automatically fetch the block range
        if (e.target.value === "deep") {
            // TODO: remove this once we have the API endpoint
            handleBlockRangeSelect(1);
        } else if (e.target.value === "ultimate") {
            // TODO: remove this once we have the API endpoint
            handleBlockRangeSelect(7);
        } else {
            // For custom, just clear the fields if they contain preset values
            if (lastSelectedRange !== null) {
                setFromBlock("");
                setToBlock("");
                setLastSelectedRange(null);
            }
        }
    };

    return (
        <div>
            {/* Pinned Header */}
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "6px 16px",
                    backgroundColor: "#fdfafb",
                    color: "white",
                    boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
                    position: "sticky",
                    top: 0,
                    zIndex: 1000,
                    minHeight: "50px",
                    height: "auto",
                    flexWrap: "wrap",
                    gap: "10px",
                    justifyContent: "space-between",
                }}
            >
                {/* Logo */}
                <div
                    style={{
                        fontWeight: "bold",
                        fontSize: "24px",
                        color: "#7469B6",
                        display: "flex",
                        alignItems: "center",
                    }}
                >
                    <svg
                        width="80"
                        height="50"
                        viewBox="0 0 2300 700"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                        style={{ marginRight: "8px" }}
                    >
                        <path d="M29.8823 458.387C25.0234 300.861 15.5044 289.583 24.6411 288.467L64.9279 264.714L94.1015 302.332M94.1015 302.332L110.062 381.878M94.1015 302.332L92.4058 247.359L148.531 218.114L179.364 244.676M179.364 244.676L203.524 362.988M179.364 244.676L237.988 215.355L295.809 241.085M295.809 241.085L314.768 320.538M295.809 241.085L307.075 71.1565L355.911 32.6325L399.961 49.7826L414.019 505.566L632.548 519.335L652.812 576.237L636.648 652.272L418.752 658.993" stroke="#2b2b2b" stroke-width="40" />
                        <path d="M1333.52 437.513C1332.92 279.914 1342.04 268.312 1332.87 267.514L1291.78 245.171L1263.93 283.779M1263.93 283.779L1250.74 363.83M1263.93 283.779L1263.72 228.779L1206.61 201.498L1176.72 229.113M1176.72 229.113L1156.68 348.191M1176.72 229.113L1117.11 201.841L1060.22 229.56M1060.22 229.56L1044.03 309.623M1060.22 229.56L1043.07 60.1246L992.928 23.3168L949.5 41.9837L951.25 497.98L733.33 519.317L715.051 576.887L733.841 652.316L951.839 651.479" stroke="#2b2b2b" stroke-width="40" />
                        <rect x="26.2239" y="-0.336626" width="225.617" height="225.525" transform="matrix(0.645906 -0.763417 0.665289 0.746586 519.839 276.693)" stroke="#2b2b2b" stroke-width="40" />
                        <path d="M536.883 256.901L831.982 253.476" stroke="#2b2b2b" stroke-width="25" />
                        <path d="M684 98L684 416" stroke="#2b2b2b" stroke-width="25" />
                        <path d="M1018.8 671V452H1063.2L1084.5 521.6C1086.7 528.6 1088.5 535 1089.9 540.8C1091.3 546.6 1092.2 550.8 1092.6 553.4C1093 550.8 1093.9 546.6 1095.3 540.8C1096.7 535 1098.4 528.6 1100.4 521.6L1120.8 452H1165.2V671H1130.1V602.9C1130.1 592.9 1130.4 582 1131 570.2C1131.6 558.4 1132.3 546.6 1133.1 534.8C1133.9 523 1134.8 511.8 1135.8 501.2C1137 490.6 1138 481.3 1138.8 473.3L1109.4 576.8H1075.2L1044.9 473.3C1045.9 480.9 1046.9 489.9 1047.9 500.3C1048.9 510.5 1049.8 521.5 1050.6 533.3C1051.6 544.9 1052.4 556.7 1053 568.7C1053.6 580.7 1053.9 592.1 1053.9 602.9V671H1018.8ZM1192.38 671L1247.58 452H1295.88L1351.38 671H1312.98L1300.98 617.9H1242.78L1230.78 671H1192.38ZM1249.68 587.3H1294.08L1280.88 528.5C1278.68 518.7 1276.78 509.9 1275.18 502.1C1273.58 494.1 1272.48 488.3 1271.88 484.7C1271.28 488.3 1270.18 494.1 1268.58 502.1C1267.18 509.9 1265.28 518.6 1262.88 528.2L1249.68 587.3ZM1384.87 671V452H1452.07C1473.27 452 1490.07 457.1 1502.47 467.3C1514.87 477.3 1521.07 491 1521.07 508.4C1521.07 518.2 1518.87 526.7 1514.47 533.9C1510.07 541.1 1504.07 546.7 1496.47 550.7C1489.07 554.7 1480.47 556.7 1470.67 556.7V555.5C1481.27 555.3 1490.67 557.3 1498.87 561.5C1507.27 565.5 1513.87 571.5 1518.67 579.5C1523.67 587.5 1526.17 597.2 1526.17 608.6C1526.17 621.2 1523.27 632.2 1517.47 641.6C1511.67 651 1503.47 658.3 1492.87 663.5C1482.47 668.5 1469.97 671 1455.37 671H1384.87ZM1421.47 639.8H1452.97C1463.97 639.8 1472.57 636.9 1478.77 631.1C1485.17 625.1 1488.37 617 1488.37 606.8C1488.37 596.6 1485.17 588.4 1478.77 582.2C1472.57 575.8 1463.97 572.6 1452.97 572.6H1421.47V639.8ZM1421.47 542.3H1451.47C1461.47 542.3 1469.27 539.7 1474.87 534.5C1480.67 529.1 1483.57 521.8 1483.57 512.6C1483.57 503.4 1480.67 496.2 1474.87 491C1469.27 485.8 1461.47 483.2 1451.47 483.2H1421.47V542.3ZM1631.65 674C1623.05 674 1616.15 671.5 1610.95 666.5C1605.95 661.5 1603.45 654.7 1603.45 646.1C1603.45 637.5 1605.95 630.7 1610.95 625.7C1616.15 620.5 1623.05 617.9 1631.65 617.9C1640.25 617.9 1647.05 620.5 1652.05 625.7C1657.25 630.7 1659.85 637.5 1659.85 646.1C1659.85 654.7 1657.25 661.5 1652.05 666.5C1647.05 671.5 1640.25 674 1631.65 674ZM1729.93 671L1790.53 558.8L1733.53 452H1775.53L1803.13 506.9C1805.13 510.9 1806.93 514.8 1808.53 518.6C1810.13 522.2 1811.33 525 1812.13 527C1812.73 525 1813.83 522.2 1815.43 518.6C1817.03 514.8 1818.83 510.9 1820.83 506.9L1848.73 452H1889.53L1832.53 557.9L1893.13 671H1851.13L1820.23 610.4C1818.23 606.4 1816.33 602.5 1814.53 598.7C1812.93 594.9 1811.73 591.9 1810.93 589.7C1810.13 591.9 1808.93 594.9 1807.33 598.7C1805.73 602.5 1803.93 606.4 1801.93 610.4L1770.73 671H1729.93ZM1972.51 671V591.5L1908.31 452H1947.61L1981.81 527.9C1984.41 533.9 1986.61 539.8 1988.41 545.6C1990.21 551.4 1991.41 555.9 1992.01 559.1C1992.81 555.9 1994.01 551.4 1995.61 545.6C1997.41 539.8 1999.61 533.9 2002.21 527.9L2035.51 452H2074.51L2010.31 591.5V671H1972.51ZM2105 671V635.3L2192.9 486.8H2107.1V452H2234.3V487.7L2146.1 636.2H2237.6V671H2105Z" fill="#212121" />
                    </svg>

                    Crystal Clear
                </div>

                {/* Search Form - RIGHT ALIGNED */}
                <form
                    onSubmit={validateAndSubmit}
                    style={{
                        display: "flex",
                        alignItems: "center",
                        gap: "10px",
                        justifyContent: "flex-end",
                        marginLeft: "auto",
                    }}
                >
                    {/* Filter Dropdown */}
                    <Select
                        onValueChange={(value) => handleFilterChange(value)}
                        value={selectedFilter}
                    >
                        <SelectTrigger
                            className="border border-black rounded-none h-8 text-sm text-black"
                            style={{
                                height: "32px",
                                width: "8rem",
                                backgroundColor: "#e3e1f0",
                            }}
                        >
                            <SelectValue placeholder="Select" style={{ color: selectedFilter ? '#2b2b2b' : 'inherit' }} />
                        </SelectTrigger>
                        <SelectContent
                            className="border border-black rounded-none p-0 overflow-hidden"
                            style={{
                                backgroundColor: "#e3e1f0",
                                zIndex: 1000,
                                boxShadow: "inset -1px -1px #0a0a0a, inset 1px 1px #0a0a0a, inset -2px -2px #dfdfdf, inset 2px 2px grey"
                            }}
                        >
                            {filterOptions.map((option) => (
                                <SelectItem
                                    key={option.value}
                                    value={option.value}
                                    className="text-sm hover:bg-[#7469B6] hover:text-white focus:bg-[#7469B6] focus:text-white "
                                    style={{ padding: "4px 8px" }}
                                >
                                    {option.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>

                    {/* Address Input */}
                    <div
                        style={{
                            position: "relative",
                            display: "flex",
                            alignItems: "center",
                            width: "28rem",
                        }}
                    >
                        <Input
                            type="text"
                            value={inputAddress}
                            onChange={(e) => {
                                setInputAddress(e.target.value);
                                // Reset dropdown selection if user is typing manually
                                if (selectedFilter && e.target.value !== filterOptions.find(opt => opt.value === selectedFilter)?.value) {
                                    setSelectedFilter("");
                                }
                            }}
                            placeholder="Enter contract address"
                            style={{
                                display: "flex",
                                color: "#2b2b2b",
                                height: "32px",
                                border: "1px solid #2b2b2b",
                                borderRightColor: "grey",
                                borderBottomColor: "grey",
                                borderRadius: "0px",
                                fontSize: "13px",
                                width: "100%",
                                paddingRight: "30px",
                                textAlign: "left",
                                boxShadow: "inset -1px -1px #fff, inset 1px 1px grey, inset 2px 2px #fff, inset 2px 2px #fff"
                            }}
                        />

                        {/* Clear button */}
                        {inputAddress && (
                            <div
                                style={{
                                    position: "absolute",
                                    right: "10px",
                                    top: "50%",
                                    transform: "translateY(-50%)",
                                    display: "flex",
                                    alignItems: "center",
                                    justifyContent: "center",
                                    cursor: "pointer",
                                    color: "#999",
                                    zIndex: 10,
                                    backgroundColor: "inherit",
                                    borderRadius: "50%",
                                    width: "16px",
                                    height: "16px",
                                }}
                                onClick={() => setInputAddress("")}
                            >
                                <svg
                                    width="14"
                                    height="14"
                                    viewBox="0 0 24 24"
                                    fill="none"
                                    stroke="currentColor"
                                    strokeWidth="2"
                                    strokeLinecap="round"
                                    strokeLinejoin="round"
                                >
                                    <line x1="18" y1="6" x2="6" y2="18"></line>
                                    <line x1="6" y1="6" x2="18" y2="18"></line>
                                </svg>
                            </div>
                        )}
                    </div>

                    {/* Analyze Button + Dropdown */}
                    <div
                        style={{
                            display: "flex",
                            gap: "8px",
                            alignItems: "center",
                            position: "relative",
                        }}
                    >
                        <Button
                            type="button"
                            onClick={() => {
                                if (!inputAddress || inputAddress.trim() === "") {
                                    showLocalAlert("Please enter a contract address.");
                                    return;
                                }
                                handleDefaultAnalyze();
                            }}
                            className="border border-black rounded-none h-8 text-sm"
                            style={{
                                height: "32px",
                                backgroundColor: "#efefef",
                                boxShadow: "inset -1px -1px #0a0a0a, inset 1px 1px #fff, inset -2px -2px grey, inset 2px 2px #dfdfdf"
                            }}
                        >
                            <span style={{ fontFamily: "ms_sans_serif", color: "#000080", fontWeight: "bold" }}>Analyze</span>
                        </Button>

                        <Popover>
                            <PopoverTrigger asChild>
                                <Button
                                    type="button"
                                    className="border border-black rounded-none h-8 text-sm"
                                    style={{
                                        height: "32px",
                                        width: "32px",
                                        backgroundColor: "#efefef",
                                        boxShadow: "inset -1px -1px #0a0a0a, inset 1px 1px #fff, inset -2px -2px grey, inset 2px 2px #dfdfdf"
                                    }}
                                >
                                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <path fillRule="evenodd" clipRule="evenodd" d="M4 4H10V7H22V9H10V12H4V9H2V7H4V4ZM6 6V10H8V6H6ZM14 12H20V15H22V17H20V20H14V17H2V15H14V12ZM16 14V18H18V14H16Z" fill="black" />
                                    </svg>
                                </Button>
                            </PopoverTrigger>
                            <PopoverContent
                                className="w-[280px] border-2 border-solid rounded-none overflow-visible bg-white mt-[6px] p-1"
                                align="end"
                                sideOffset={12}
                                style={{
                                    borderColor: "#6985b6",
                                    borderWidth: "1px",
                                    borderStyle: "solid",
                                    zIndex: 1000
                                }}
                            >
                                <div className="p-5 flex flex-col gap-2">
                                    {/* Title with separator */}
                                    <div className="pb-3 mb-1 border-b border-gray-300">
                                        <div
                                            style={{
                                                fontSize: "18px",
                                                fontWeight: "700",
                                                color: "#7469B6",
                                                marginBottom: "0.2rem",
                                                marginLeft: "0.5rem",
                                                marginTop: "0.5rem",
                                                display: "flex",
                                                alignItems: "center",
                                                letterSpacing: "0.5px"
                                            }}
                                        >
                                            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" style={{ marginRight: "0.5rem", flexShrink: 0 }}>
                                                <path fill-rule="evenodd" clip-rule="evenodd" d="M3 3H11V5H3V17H11V5H13V17H21V5H13V3H21H23V5V17V19H21H13V21H11V19H3H1V17V5V3H3ZM19 10H15V12H19V10ZM15 7H19V9H15V7ZM17 13H15V15H17V13Z" fill="#7469B6" />
                                            </svg>

                                            Analysis Mode
                                        </div>
                                    </div>

                                    {/* Radio options with better spacing */}
                                    <div style={{ display: "flex", flexDirection: "column", gap: "6px", alignItems: "flex-start", marginLeft: "10px" }}>
                                        <RadioGroup
                                            value={blockRangeType}
                                            onValueChange={(value) => {
                                                const event = { target: { value } } as React.ChangeEvent<HTMLInputElement>;
                                                handleBlockRangeTypeChange(event);
                                            }}
                                            className="space-y-3"
                                        >
                                            <div className="flex items-center space-x-2 tooltip-container hover:bg-[#c9e0be] p-1.5 rounded-sm cursor-pointer w-full">
                                                <div className="relative group">
                                                    <div className="flex items-center space-x-3">
                                                        <RadioGroupItem value="deep" id="deep" />
                                                        <Label htmlFor="deep" className="cursor-pointer">Deep</Label>
                                                    </div>
                                                    <div className="absolute left-0 -top-8 hidden group-hover:block bg-black text-white rounded px-6 py-3 z-50 w-auto whitespace-nowrap shadow-lg backdrop-blur-sm border border-white/10" style={{ fontSize: '12px', paddingLeft: '0.5rem', paddingRight: '0.5rem', paddingTop: '0.2rem', paddingBottom: '0.2rem' }}>
                                                        (WIP) 1 day of transactions
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="flex items-center space-x-2 tooltip-container hover:bg-[#c9e0be] p-1.5 rounded-sm cursor-pointer w-full">
                                                <div className="relative group">
                                                    <div className="flex items-center space-x-3">
                                                        <RadioGroupItem value="ultimate" id="ultimate" />
                                                        <Label htmlFor="ultimate" className="cursor-pointer">Ultimate</Label>
                                                    </div>
                                                    <div className="absolute left-0 -top-8 hidden group-hover:block bg-black text-white rounded px-6 py-3 z-50 w-auto whitespace-nowrap shadow-lg backdrop-blur-sm border border-white/10" style={{ fontSize: '12px', paddingLeft: '0.5rem', paddingRight: '0.5rem', paddingTop: '0.2rem', paddingBottom: '0.2rem' }}>
                                                        (WIP) 7 days of transactions
                                                    </div>
                                                </div>
                                            </div>

                                            <div className="flex items-center space-x-2 tooltip-container hover:bg-[#c9e0be] p-1.5 rounded-sm cursor-pointer w-full">
                                                <div className="relative group">
                                                    <div className="flex items-center space-x-3">
                                                        <RadioGroupItem value="custom" id="custom" />
                                                        <Label htmlFor="custom" className="cursor-pointer">Custom Block Range</Label>
                                                    </div>
                                                    <div className="absolute left-0 -top-8 hidden group-hover:block bg-black text-white rounded px-6 py-3 z-50 w-auto whitespace-nowrap shadow-lg backdrop-blur-sm border border-white/10" style={{ fontSize: '12px', paddingLeft: '0.5rem', paddingRight: '0.5rem', paddingTop: '0.2rem', paddingBottom: '0.2rem' }}>
                                                        (WIP)Put your own block numbers
                                                    </div>
                                                </div>
                                            </div>
                                        </RadioGroup>
                                    </div>

                                    {/* Block range inputs with improved styling */}
                                    <div style={{ display: "flex", gap: "10px", marginTop: "4px", marginLeft: "10px", marginRight: "10px" }} className="pt-2">
                                        <Input
                                            type="text"
                                            value={fromBlock}
                                            onChange={handleFromBlockChange}
                                            placeholder="From Block"
                                            className="h-8 text-xs flex-1 border border-black rounded-none"
                                            style={{
                                                backgroundColor: blockRangeType === "custom" ? "white" : "#a4a2bc",
                                                // boxShadow: "inset -1px -1px #fff, inset 1px 1px grey, inset -2px -2px #fff, inset 2px 2px #dfdfdf"
                                            }}
                                            disabled={blockRangeType !== "custom"}
                                        />
                                        <Input
                                            type="text"
                                            value={toBlock}
                                            onChange={handleToBlockChange}
                                            placeholder="To Block"
                                            className="h-8 text-xs flex-1 border border-black rounded-none"
                                            style={{
                                                backgroundColor: blockRangeType === "custom" ? "white" : "#a4a2bc",
                                                // boxShadow: "inset -1px -1px #fff, inset 1px 1px grey, inset -2px -2px #fff, inset 2px 2px #dfdfdf"
                                            }}
                                            disabled={blockRangeType !== "custom"}
                                        />
                                    </div>

                                    {/* Submit button with improved styling */}
                                    <Button
                                        type="button"
                                        onClick={(e) => {
                                            // Check if address is empty and show alert if needed
                                            if (!inputAddress) {
                                                showLocalAlert("Please enter a contract address.");
                                                return;
                                            }

                                            // Create a synthetic event with preventDefault
                                            const syntheticEvent = {
                                                ...e,
                                                preventDefault: () => { },
                                            };

                                            // Create a custom event with block range
                                            const customEvent =
                                                syntheticEvent as CustomSubmitEvent;
                                            customEvent.blockRange = {
                                                fromBlock: fromBlock ? parseInt(fromBlock) : null,
                                                toBlock: toBlock ? parseInt(toBlock) : null,
                                            };

                                            // Call handleSubmit directly with our custom event
                                            handleSubmit(customEvent);
                                        }}
                                        style={{
                                            backgroundColor: "#efefef",
                                            marginTop: "2px",
                                            marginLeft: "10px",
                                            marginRight: "10px",
                                            marginBottom: "10px",
                                            borderRadius: "1px",
                                            boxShadow: "inset -1px -1px #0a0a0a, inset 1px 1px #fff, inset -2px -2px grey, inset 2px 2px #dfdfdf"
                                        }}
                                    >
                                        <span style={{ fontFamily: "ms_sans_serif", color: "#000080", fontWeight: "bold" }}>Analyze</span>
                                    </Button>
                                </div>
                            </PopoverContent>
                        </Popover>
                    </div>
                </form>
            </div>

            {/* Popular Protocols Section, removed for now */}
            {/* <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    padding: "8px 16px",
                    backgroundColor: "white",
                    boxShadow: "0 1px 2px rgba(0,0,0,0.1)",
                    gap: "8px",
                }}
            > */}
            {/* <span
                    style={{
                        fontSize: "14px",
                        color: "#666",
                        whiteSpace: "nowrap",
                    }}
                >
                    Popular Protocols:
                </span> */}
            {/* <div style={{ display: "flex", gap: "8px", overflow: "auto", paddingBottom: "4px" }}>
                    {popularContracts.map((contract, index) => (
                        <Button
                            key={index}
                            variant="outline"
                            type="button"
                            onClick={() =>
                                handleAddressSelect(contract.address, contract.name)
                            }
                            style={{
                                padding: "4px 8px",
                                height: "28px",
                                fontSize: "12px",
                                whiteSpace: "nowrap",
                                borderRadius: "4px",
                            }}
                        >
                            {contract.name}
                        </Button>
                    ))}
                </div> */}
        </div >
    );
}
