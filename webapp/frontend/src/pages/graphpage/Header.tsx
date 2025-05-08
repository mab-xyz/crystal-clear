import React, { useState, useRef } from "react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from "@/components/ui/select";
import {
    Tooltip,
    TooltipContent,
    TooltipTrigger,
} from "@/components/ui/tooltip";
import { TooltipProvider } from "@/components/ui/tooltip";

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

interface PopularContract {
    name: string;
    address: string;
}

interface BlockRangeOption {
    label: string;
    days: number;
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
    // Add state for custom alert
    const [alertMessage, setAlertMessage] = useState<string>("");
    const [showAlert, setShowAlert] = useState<boolean>(false);
    const [lastSelectedRange, setLastSelectedRange] = useState<number | null>(
        null,
    );
    const [showCustomBlockRange, setShowCustomBlockRange] =
        useState<boolean>(false);
    const [showBlockRangeDropdown, setShowBlockRangeDropdown] =
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
        { label: "e.g. something", value: "something else" },
    ]);

    const [selectedFilter, setSelectedFilter] = useState<string>("");

    // Function to show alert
    const showCustomAlert = (message: string): void => {
        setAlertMessage(message);
        setShowAlert(true);

        // Auto-hide after 3 seconds
        setTimeout(() => {
            setShowAlert(false);
        }, 3000);
    };

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

            // Example API call (replace with your actual API endpoint)
            const response = await fetch(
                `http://localhost:8000/v1/analysis/block-range?days=${days}`,
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

    // Function to handle quick address selection
    const handleAddressSelect = (address: string, name: string): void => {
        // If the address is already selected, clear it (unselect)
        if (inputAddress === address) {
            setInputAddress("");
        } else {
            setInputAddress(address);
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

    // Wrap the original handleSubmit to add validation
    const validateAndSubmit = (e: React.FormEvent): void => {
        e.preventDefault();

        // Check if inputs are valid
        let isValid = true;
        let errorMessage = "";

        // Validate address (basic check)
        if (!inputAddress) {
            isValid = false;
            errorMessage = "Please enter a contract address";
        }

        // Validate block numbers (if provided)
        if (fromBlock && !/^\d+$/.test(fromBlock)) {
            isValid = false;
            errorMessage = "From Block must contain only numbers";
        }

        if (toBlock && !/^\d+$/.test(toBlock)) {
            isValid = false;
            errorMessage = "To Block must contain only numbers";
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
            showCustomAlert(errorMessage);
        }
    };

    // Popular contract addresses with labels
    const popularContracts: PopularContract[] = [
        {
            name: "Uniswap V3 Router",
            address: "0xE592427A0AEce92De3Edee1F18E0157C05861564",
        },
        { name: "USDC", address: "0xA0b86991c6218b36c1d19D4a2e9Eb0cE3606eB48" },
        { name: "USDT", address: "0xdAC17F958D2ee523a2206206994597C13D831ec7" },
        {
            name: "Seaport 1.6",
            address: "0x0000000000000068F116a894984e2DB1123eB395",
        },
    ];


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

    // Block range options
    // const blockRangeOptions: BlockRangeOption[] = [
    //     { label: "Fast", days: 1 },
    //     { label: "Deep", days: 3 },
    //     { label: "Ultimate", days: 7 }
    // ];

    // Function to handle default analyze (20 blocks)
    const handleDefaultAnalyze = async (): Promise<void> => {
        try {
            if (!inputAddress) {
                showCustomAlert("Please enter a contract address");
                return;
            }

            // Get current block and calculate from block (current - 20)
            const response = await fetch(
                "http://localhost:8000/v1/analysis/block-range?days=1",
            );
            const data = await response.json();
            const currentBlock = data.to_block;
            const fromBlockNum = currentBlock - 20;

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

    // Toggle block range dropdown
    const toggleBlockRangeDropdown = (): void => {
        setShowBlockRangeDropdown(!showBlockRangeDropdown);
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
                    height: "60px",
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
                        width="65"
                        height="65"
                        viewBox="0 0 1357 679"
                        fill="none"
                        xmlns="http://www.w3.org/2000/svg"
                        style={{ marginRight: "8px" }}
                    >
                        <path
                            d="M29.8823 458.387C25.0234 300.861 15.5044 289.583 24.6411 288.467L64.9279 264.714L94.1015 302.332M94.1015 302.332L110.062 381.878M94.1015 302.332L92.4058 247.359L148.531 218.114L179.364 244.676M179.364 244.676L203.524 362.988M179.364 244.676L237.988 215.355L295.809 241.085M295.809 241.085L314.768 320.538M295.809 241.085L307.075 71.1565L355.911 32.6325L399.961 49.7826L414.019 505.566L632.548 519.335L652.812 576.237L636.648 652.272L418.752 658.993"
                            stroke="black"
                            strokeWidth="40"
                        />
                        <path
                            d="M1333.52 437.513C1332.92 279.914 1342.04 268.312 1332.87 267.514L1291.78 245.171L1263.93 283.779M1263.93 283.779L1250.74 363.83M1263.93 283.779L1263.72 228.779L1206.61 201.498L1176.72 229.113M1176.72 229.113L1156.68 348.191M1176.72 229.113L1117.11 201.841L1060.22 229.56M1060.22 229.56L1044.03 309.623M1060.22 229.56L1043.07 60.1246L992.928 23.3168L949.5 41.9837L951.25 497.98L733.33 519.317L715.051 576.887L733.841 652.316L951.839 651.479"
                            stroke="black"
                            strokeWidth="40"
                        />
                        <rect
                            x="26.2239"
                            y="-0.336626"
                            width="225.617"
                            height="225.525"
                            transform="matrix(0.645906 -0.763417 0.665289 0.746586 519.839 276.693)"
                            stroke="black"
                            strokeWidth="40"
                        />
                        <path
                            d="M536.883 256.901L831.982 253.476"
                            stroke="black"
                            strokeWidth="25"
                        />
                        <path d="M684 98L684 416" stroke="black" strokeWidth="25" />
                    </svg>
                    Crystal Clear
                </div>

                {/* Space for future hamburger menu */}
                <div style={{ marginLeft: "auto" }}>
                    {/* Hamburger menu will go here in the future */}
                </div>
            </div>

            {/* Search Bar Section */}
            <div
                style={{
                    display: "flex",
                    flexDirection: "column",
                    padding: "15px 20px",
                    backgroundColor: "#ffffff",
                    boxShadow: "0 2px 4px rgba(0,0,0,0.1)",
                    position: "relative", // For alert positioning
                }}
            >
                {/* Custom Alert */}
                {showAlert && (
                    <div
                        style={{
                            position: "absolute",
                            top: "70px",
                            left: "50%",
                            transform: "translateX(-50%)",
                            backgroundColor: "#f8d7da",
                            color: "#721c24",
                            padding: "10px 15px",
                            borderRadius: "4px",
                            boxShadow: "0 2px 5px rgba(0,0,0,0.2)",
                            zIndex: 1000,
                            display: "flex",
                            alignItems: "center",
                            maxWidth: "80%",
                        }}
                    >
                        <svg
                            width="20"
                            height="20"
                            viewBox="0 0 24 24"
                            fill="none"
                            xmlns="http://www.w3.org/2000/svg"
                            style={{ marginRight: "10px" }}
                        >
                            <path
                                d="M12 22C17.5228 22 22 17.5228 22 12C22 6.47715 17.5228 2 12 2C6.47715 2 2 6.47715 2 12C2 17.5228 6.47715 22 12 22Z"
                                stroke="#721c24"
                                strokeWidth="2"
                            />
                            <path
                                d="M12 8V12"
                                stroke="#721c24"
                                strokeWidth="2"
                                strokeLinecap="round"
                            />
                            <circle cx="12" cy="16" r="1" fill="#721c24" />
                        </svg>
                        {alertMessage}
                    </div>
                )}

                {/* Search Form and Quick Selections Container */}
                <div
                    style={{
                        display: "flex",
                        flexDirection: "column",
                        flex: 1,
                        gap: "10px",
                        justifyContent: "center",
                    }}
                >
                    {/* Search Form */}
                    <form
                        onSubmit={validateAndSubmit}
                        style={{
                            display: "flex",
                            width: "100%",
                            alignItems: "flex-start",
                            gap: "10px",
                        }}
                    >
                        {/* Address input and block range container */}
                        <div
                            style={{
                                display: "flex",
                                flexDirection: "column",
                                flex: 2,
                                gap: "10px",
                            }}
                        >
                            {/* Address input row */}
                            <div
                                style={{
                                    display: "flex",
                                    alignItems: "center",
                                    gap: "10px",
                                }}
                            >
                                {/* Filter Dropdown */}
                                <Select
                                    onValueChange={handleFilterChange}
                                    value={selectedFilter}
                                >
                                    <SelectTrigger
                                        className="w-[180px]"
                                        style={{ height: "32px", fontSize: "13px" }}
                                    >
                                        <SelectValue placeholder="Popular contract" />
                                    </SelectTrigger>
                                    <SelectContent>
                                        {filterOptions.map((option) => (
                                            <SelectItem key={option.value} value={option.value}>
                                                {option.label}
                                            </SelectItem>
                                        ))}
                                    </SelectContent>
                                </Select>

                                <div
                                    style={{
                                        position: "relative",
                                        flex: 1,
                                        display: "flex",
                                        alignItems: "center",
                                    }}
                                >
                                    <Input
                                        type="text"
                                        value={inputAddress}
                                        onChange={(e) => setInputAddress(e.target.value)}
                                        placeholder="Enter contract address"
                                        style={{
                                            height: "32px",
                                            fontSize: "13px",
                                            width: "100%",
                                            paddingRight: "30px", // Make room for the clear button
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
                                                backgroundColor: "white",
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

                                {/* Single Analyze Button + Dropdown */}
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
                                        variant="outline"
                                        onClick={handleDefaultAnalyze}
                                        disabled={!inputAddress}
                                        style={{
                                            backgroundColor: inputAddress ? "#5c5cb7" : "#cccccc",
                                            color: "white",
                                            fontSize: "14px",
                                            boxShadow: inputAddress
                                                ? "0 2px 4px rgba(116, 105, 182, 0.4)"
                                                : "none",
                                            transition: "all 0.2s ease",
                                            cursor: "pointer",
                                        }}
                                    >
                                        Analyze
                                    </Button>

                                    <Button
                                        type="button"
                                        onClick={toggleBlockRangeDropdown}
                                        variant="outline"
                                        style={{
                                            padding: "0 8px",
                                            backgroundColor: "#72a5da",
                                            boxShadow: inputAddress
                                                ? "0 2px 4px rgba(116, 105, 182, 0.4)"
                                                : "none",
                                            transition: "all 0.2s ease",
                                            cursor: "pointer",
                                        }}
                                    >
                                        <svg
                                            width="16"
                                            height="16"
                                            viewBox="0 0 24 24"
                                            fill="none"
                                            xmlns="http://www.w3.org/2000/svg"
                                        >
                                            <path
                                                d="M12 15C13.6569 15 15 13.6569 15 12C15 10.3431 13.6569 9 12 9C10.3431 9 9 10.3431 9 12C9 13.6569 10.3431 15 12 15Z"
                                                stroke="white"
                                                strokeWidth="2"
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                            />
                                            <path
                                                d="M19.4 15C19.2669 15.3016 19.2272 15.6362 19.286 15.9606C19.3448 16.285 19.4995 16.5843 19.73 16.82L19.79 16.88C19.976 17.0657 20.1235 17.2863 20.2241 17.5291C20.3248 17.7719 20.3766 18.0322 20.3766 18.295C20.3766 18.5578 20.3248 18.8181 20.2241 19.0609C20.1235 19.3037 19.976 19.5243 19.79 19.71C19.6043 19.896 19.3837 20.0435 19.1409 20.1441C18.8981 20.2448 18.6378 20.2966 18.375 20.2966C18.1122 20.2966 17.8519 20.2448 17.6091 20.1441C17.3663 20.0435 17.1457 19.896 16.96 19.71L16.9 19.65C16.6643 19.4195 16.365 19.2648 16.0406 19.206C15.7162 19.1472 15.3816 19.1869 15.08 19.32C14.7842 19.4468 14.532 19.6572 14.3543 19.9255C14.1766 20.1938 14.0813 20.5082 14.08 20.83V21C14.08 21.5304 13.8693 22.0391 13.4942 22.4142C13.1191 22.7893 12.6104 23 12.08 23C11.5496 23 11.0409 22.7893 10.6658 22.4142C10.2907 22.0391 10.08 21.5304 10.08 21V20.91C10.0723 20.579 9.96512 20.258 9.77251 19.9887C9.5799 19.7194 9.31074 19.5143 9 19.4C8.69838 19.2669 8.36381 19.2272 8.03941 19.286C7.71502 19.3448 7.41568 19.4995 7.18 19.73L7.12 19.79C6.93425 19.976 6.71368 20.1235 6.47088 20.2241C6.22808 20.3248 5.96783 20.3766 5.705 20.3766C5.44217 20.3766 5.18192 20.3248 4.93912 20.2241C4.69632 20.1235 4.47575 19.976 4.29 19.79C4.10405 19.6043 3.95653 19.3837 3.85588 19.1409C3.75523 18.8981 3.70343 18.6378 3.70343 18.375C3.70343 18.1122 3.75523 17.8519 3.85588 17.6091C3.95653 17.3663 4.10405 17.1457 4.29 16.96L4.35 16.9C4.58054 16.6643 4.73519 16.365 4.794 16.0406C4.85282 15.7162 4.81312 15.3816 4.68 15.08C4.55324 14.7842 4.34276 14.532 4.07447 14.3543C3.80618 14.1766 3.49179 14.0813 3.17 14.08H3C2.46957 14.08 1.96086 13.8693 1.58579 13.4942C1.21071 13.1191 1 12.6104 1 12.08C1 11.5496 1.21071 11.0409 1.58579 10.6658C1.96086 10.2907 2.46957 10.08 3 10.08H3.09C3.42099 10.0723 3.742 9.96512 4.0113 9.77251C4.28059 9.5799 4.48572 9.31074 4.6 9C4.73312 8.69838 4.77282 8.36381 4.714 8.03941C4.65519 7.71502 4.50054 7.41568 4.27 7.18L4.21 7.12C4.02405 6.93425 3.87653 6.71368 3.77588 6.47088C3.67523 6.22808 3.62343 5.96783 3.62343 5.705C3.62343 5.44217 3.67523 5.18192 3.77588 4.93912C3.87653 4.69632 4.02405 4.47575 4.21 4.29C4.39575 4.10405 4.61632 3.95653 4.85912 3.85588C5.10192 3.75523 5.36217 3.70343 5.625 3.70343C5.88783 3.70343 6.14808 3.75523 6.39088 3.85588C6.63368 3.95653 6.85425 4.10405 7.04 4.29L7.1 4.35C7.33568 4.58054 7.63502 4.73519 7.95941 4.794C8.28381 4.85282 8.61838 4.81312 8.92 4.68H9C9.29577 4.55324 9.54802 4.34276 9.72569 4.07447C9.90337 3.80618 9.99872 3.49179 10 3.17V3C10 2.46957 10.2107 1.96086 10.5858 1.58579C10.9609 1.21071 11.4696 1 12 1C12.5304 1 13.0391 1.21071 13.4142 1.58579C13.7893 1.96086 14 2.46957 14 3V3.09C14.0013 3.41179 14.0966 3.72618 14.2743 3.99447C14.452 4.26276 14.7042 4.47324 15 4.6C15.3016 4.73312 15.6362 4.77282 15.9606 4.714C16.285 4.65519 16.5843 4.50054 16.82 4.27L16.88 4.21C17.0657 4.02405 17.2863 3.87653 17.5291 3.77588C17.7719 3.67523 18.0322 3.62343 18.295 3.62343C18.5578 3.62343 18.8181 3.67523 19.0609 3.77588C19.3037 3.87653 19.5243 4.02405 19.71 4.21C19.896 4.39575 20.0435 4.61632 20.1441 4.85912C20.2448 5.10192 20.2966 5.36217 20.2966 5.625C20.2966 5.88783 20.2448 6.14808 20.1441 6.39088C20.0435 6.63368 19.896 6.85425 19.71 7.04L19.65 7.1C19.4195 7.33568 19.2648 7.63502 19.206 7.95941C19.1472 8.28381 19.1869 8.61838 19.32 8.92V9C19.4468 9.29577 19.6572 9.54802 19.9255 9.72569C20.1938 9.90337 20.5082 9.99872 20.83 10H21C21.5304 10 22.0391 10.2107 22.4142 10.5858C22.7893 10.9609 23 11.4696 23 12C23 12.5304 22.7893 13.0391 22.4142 13.4142C22.0391 13.7893 21.5304 14 21 14H20.91C20.5882 14.0013 20.2738 14.0966 20.0055 14.2743C19.7372 14.452 19.5268 14.7042 19.4 15Z"
                                                stroke="white"
                                                strokeWidth="2"
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                            />
                                        </svg>
                                    </Button>

                                    {/* Block Range Dropdown */}
                                    {showBlockRangeDropdown && (
                                        <div
                                            style={{
                                                position: "absolute",
                                                top: "calc(100% + 8px)",
                                                right: "0",
                                                width: "260px",
                                                backgroundColor: "white",
                                                padding: "10px",
                                                borderRadius: "6px",
                                                border: "1px solid #e9cbf5",
                                                boxShadow: "0 4px 8px rgba(0,0,0,0.1)",
                                                zIndex: 1000,
                                                display: "flex",
                                                flexDirection: "column",
                                                gap: "8px",
                                                maxHeight: "calc(100vh - 200px)",
                                                overflowY: "auto",
                                            }}
                                        >
                                            {/* Triangle pointer */}
                                            <div
                                                style={{
                                                    position: "absolute",
                                                    top: "-8px",
                                                    right: "10px",
                                                    width: "0",
                                                    height: "0",
                                                    borderLeft: "8px solid transparent",
                                                    borderRight: "8px solid transparent",
                                                    borderBottom: "8px solid white",
                                                    zIndex: 1001,
                                                }}
                                            ></div>
                                            <div
                                                style={{
                                                    position: "absolute",
                                                    top: "-9px",
                                                    right: "9px",
                                                    width: "0",
                                                    height: "0",
                                                    borderLeft: "9px solid transparent",
                                                    borderRight: "9px solid transparent",
                                                    borderBottom: "9px solid #e9cbf5",
                                                    zIndex: 1000,
                                                }}
                                            ></div>

                                            <div
                                                style={{
                                                    fontSize: "12px",
                                                    fontWeight: "500",
                                                    color: "#333",
                                                    marginBottom: "2px",
                                                }}
                                            >
                                                Analysis Mode
                                            </div>

                                            {/* Deep and Ultimate buttons */}
                                            <div style={{ display: "flex", gap: "8px" }}>
                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <Button
                                                                type="button"
                                                                onClick={() => handleBlockRangeSelect(1)}
                                                                variant="outline"
                                                                style={{
                                                                    flex: 1,
                                                                    fontSize: "12px", // Smaller font size
                                                                }}
                                                            >
                                                                Deep
                                                            </Button>
                                                        </TooltipTrigger>
                                                        <TooltipContent
                                                            side="bottom"
                                                            sideOffset={5}
                                                            style={{
                                                                zIndex: 2000,
                                                                backgroundColor: "#434978",
                                                            }}
                                                        >
                                                            (WIP)Analyze the last 1 day of transactions
                                                        </TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>

                                                <TooltipProvider>
                                                    <Tooltip>
                                                        <TooltipTrigger asChild>
                                                            <Button
                                                                type="button"
                                                                onClick={() => handleBlockRangeSelect(7)}
                                                                variant="outline"
                                                                style={{
                                                                    flex: 1,
                                                                    fontSize: "12px", // Smaller font size
                                                                }}
                                                            >
                                                                Ultimate
                                                            </Button>
                                                        </TooltipTrigger>
                                                        <TooltipContent
                                                            side="bottom"
                                                            sideOffset={5}
                                                            style={{
                                                                zIndex: 2000,
                                                                backgroundColor: "#434978",
                                                            }}
                                                        >
                                                            (WIP)Analyze the transactions since the contract
                                                            was deployed
                                                        </TooltipContent>
                                                    </Tooltip>
                                                </TooltipProvider>
                                            </div>

                                            <div
                                                style={{
                                                    fontSize: "12px",
                                                    fontWeight: "500",
                                                    color: "#333",
                                                    marginTop: "4px",
                                                    marginBottom: "2px",
                                                }}
                                            >
                                                Custom Block Range:
                                            </div>

                                            {/* Custom block range inputs */}
                                            <div style={{ display: "flex", gap: "8px" }}>
                                                <Input
                                                    type="text"
                                                    value={fromBlock}
                                                    onChange={handleFromBlockChange}
                                                    placeholder="From Block"
                                                    style={{
                                                        height: "28px",
                                                        fontSize: "12px",
                                                        flex: 1,
                                                    }}
                                                />
                                                <Input
                                                    type="text"
                                                    value={toBlock}
                                                    onChange={handleToBlockChange}
                                                    placeholder="To Block"
                                                    style={{
                                                        height: "28px",
                                                        fontSize: "12px",
                                                        flex: 1,
                                                    }}
                                                />
                                            </div>

                                            {/* Submit button */}
                                            <Button
                                                type="button"
                                                onClick={(e) => {
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
                                                disabled={!inputAddress}
                                                style={{
                                                    marginTop: "8px",
                                                    backgroundColor: inputAddress ? "#7469B6" : "#cccccc",
                                                    color: "white",
                                                    fontSize: "14px",
                                                }}
                                            >
                                                Submit
                                            </Button>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Quick Address Selection - Kept below */}
                            <div
                                style={{
                                    display: "flex",
                                    gap: "8px",
                                    alignItems: "center",
                                }}
                            >
                                <span
                                    style={{
                                        fontSize: "12px",
                                        color: "#666",
                                        marginRight: "4px",
                                    }}
                                >
                                    Popular:
                                </span>
                                {popularContracts.map((contract, index) => (
                                    <Button
                                        key={index}
                                        type="button"
                                        onClick={() =>
                                            handleAddressSelect(contract.address, contract.name)
                                        }
                                        variant="outline"
                                        style={{
                                            padding: "4px 8px",
                                            fontSize: "12px",
                                            whiteSpace: "nowrap",
                                            border:
                                                inputAddress === contract.address
                                                    ? "1px solid rgb(116,85,150)"
                                                    : "",
                                            backgroundColor:
                                                inputAddress === contract.address
                                                    ? "rgba(237,128,246,0.1)"
                                                    : "",
                                        }}
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
    );
}
