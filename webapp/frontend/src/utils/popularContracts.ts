// Popular Ethereum contracts for quick access
export const popularContracts = [
    {
        name: "Uniswap V3 Router",
        address: "0xE592427A0AEce92De3Edee1F18E0157C05861564",
    },
    { name: "Ether.fi Liquidity Pool", address: "0x308861A430be4cce5502d0A12724771Fc6DaF216" },
    { name: "Aave", address: "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2" },
    {
        name: "Seaport 1.6",
        address: "0x0000000000000068F116a894984e2DB1123eB395",
    },
];

// Define the FilterOption interface
export interface FilterOption {
    label: string;
    value: string;
}

// Export the filter options array
export const filterOptions: FilterOption[] = [
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
];