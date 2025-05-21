import React, { useState } from "react";
import { handleDefaultAnalyze, getDefaultBlockRange } from "@/utils/defaultAnalyze";
import type { CustomSubmitEvent } from "@/utils/defaultAnalyze";
import { filterOptions } from "@/utils/popularContracts";
import '../../App.css';
import { Link, useNavigate } from "react-router";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useLocalAlert } from "@/components/ui/local-alert";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Label } from "@/components/ui/label";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select"
import {
    Popover,
    PopoverContent,
    PopoverTrigger,
} from "@/components/ui/popover"
import { AddressInput } from "@/components/common/AddressInput";

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

    // Remove the filterOptions useState and use the imported constant directly
    const [selectedFilter, setSelectedFilter] = useState<string>("");

    // Add state for radio selection
    const [blockRangeType, setBlockRangeType] = useState<string>("deep");

    // Replace the local state with the hook
    const { showLocalAlert } = useLocalAlert();

    // Add navigate function from React Router
    const navigate = useNavigate();

    // Function to handle preset block range selection
    const handleBlockRangeSelect = async (blocks: number): Promise<void> => {
        try {
            // Check if the same range is clicked again (toggle behavior)
            if (lastSelectedRange === blocks) {
                // Clear the block range inputs
                setFromBlock("");
                setToBlock("");
                setLastSelectedRange(null);
                return;
            }

            // TODO: Get the block range from the API
            const response = await fetch(
                `http://localhost:8000/info/block-latest`,
            );
            const data = await response.json();
            const { from_block, to_block } = data;

            setFromBlock(from_block.toString());
            setToBlock(to_block.toString());
            setLastSelectedRange(blocks);

            // Show the custom block range when a preset is selected
            setShowCustomBlockRange(true);

            // Automatically submit when any day button is clicked and there's an address
            if (inputAddress) {
                // Update URL with the new block range
                updateUrlWithParams(inputAddress, from_block.toString(), to_block.toString());

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

    // Update validateAndSubmit to also update URL
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

        // If validation passes, call the original handleSubmit and update URL
        if (isValid) {
            // Create a new event with block range data
            const newEvent = { ...e } as CustomSubmitEvent;
            newEvent.blockRange = {
                fromBlock: fromBlock ? parseInt(fromBlock) : null,
                toBlock: toBlock ? parseInt(toBlock) : null,
            };

            // Update URL with query parameters
            updateUrlWithParams(inputAddress, fromBlock, toBlock);

            // Call the original handleSubmit
            handleSubmit(newEvent);
        } else {
            showLocalAlert(errorMessage);
        }
    };

    // Function to update URL with address and block parameters
    const updateUrlWithParams = (address: string, from?: string, to?: string): void => {
        let url = `/graph/?address=${address}`;

        // Add query parameters if block range is specified
        if (from && to) {
            url += `&from_block=${from}&to_block=${to}`;
        }

        // Update URL without reloading the page
        navigate(url, { replace: true });
    };

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


    // Function to handle block range type selection
    const handleBlockRangeTypeChange = async (e: React.ChangeEvent<HTMLInputElement>): Promise<void> => {
        const newType = e.target.value;
        setBlockRangeType(newType);

        // If selecting a preset option, automatically fetch the block range
        if (newType === "deep") {
            // Use the existing function for consistency
            await handleBlockRangeSelect(1);
        } else if (newType === "ultimate") {
            await handleBlockRangeSelect(7);
        } else {
            // For custom, just clear the fields if they contain preset values
            if (lastSelectedRange !== null) {
                setFromBlock("");
                setToBlock("");
                setLastSelectedRange(null);
            }
        }
    };

    // Update analyzeWithCurrentSettings to also update URL
    const analyzeWithCurrentSettings = (e: React.MouseEvent | React.FormEvent): void => {
        // Check if address is empty and show alert if needed
        if (!inputAddress) {
            showLocalAlert("Please enter a contract address.");
            return;
        }

        // Update URL with query parameters
        updateUrlWithParams(inputAddress, fromBlock, toBlock);

        // Create a synthetic event with preventDefault
        const syntheticEvent = {
            ...e,
            preventDefault: () => { },
        };

        // Create a custom event with block range
        const customEvent = syntheticEvent as CustomSubmitEvent;
        customEvent.blockRange = {
            fromBlock: fromBlock ? parseInt(fromBlock) : null,
            toBlock: toBlock ? parseInt(toBlock) : null,
        };

        // Call handleSubmit directly with our custom event
        handleSubmit(customEvent);
    };

    // handleDefaultAnalyzeClick is used to handle the default analyze button click and update the URL with the default block range
    const handleDefaultAnalyzeClick = async (): Promise<void> => {
        if (!inputAddress) {
            showLocalAlert("Please enter a contract address.");
            return;
        }

        // Get default block range before updating URL
        const blockRange = await getDefaultBlockRange();
        if (blockRange) {
            // Update URL with the default block range
            updateUrlWithParams(inputAddress, blockRange.fromBlock.toString(), blockRange.toBlock.toString());
        }

        await handleDefaultAnalyze(
            inputAddress,
            setFromBlock,
            setToBlock,
            handleSubmit,
            showLocalAlert
        );
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
                <Link to="/">
                    <div
                        style={{
                            // fontWeight: "bold",
                            fontSize: "24px",
                            color: "#2b2b2b",
                            display: "flex",
                            alignItems: "center",
                            fontFamily: "Jersey 20, 'Funnel Sans'"
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
                </Link>

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
                                backgroundColor: "white",
                            }}
                        >
                            <SelectValue placeholder="Select" style={{ color: selectedFilter ? '#2b2b2b' : 'inherit' }} />
                        </SelectTrigger>
                        <SelectContent
                            className="border border-black rounded-none p-0 overflow-hidden"
                            style={{
                                backgroundColor: "white",
                                zIndex: 1000,
                                border: "1.5px solid #0a0a0a",
                                // boxShadow: "inset -1px -1px #0a0a0a, inset 1px 1px #0a0a0a, inset -2px -2px #dfdfdf, inset 2px 2px grey"
                            }}
                        >
                            {filterOptions.map((option) => (
                                <SelectItem
                                    key={option.value}
                                    value={option.value}
                                    className="text-sm hover:bg-[#7469B6] hover:text-white focus:bg-[#7469B6] focus:text-white rounded-none "
                                    style={{ padding: "4px 8px" }}
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
                            // Reset dropdown selection if user is typing manually
                            if (selectedFilter && value !== filterOptions.find(opt => opt.value === selectedFilter)?.value) {
                                setSelectedFilter("");
                            }
                        }}
                        style={{ width: "28rem" }}
                    />

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
                                handleDefaultAnalyzeClick();
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
                                                        Put your own block numbers
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

                                    {/* Submit button*/}
                                    <Button
                                        type="button"
                                        onClick={(e) => analyzeWithCurrentSettings(e)}
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
        </div >
    );
}
