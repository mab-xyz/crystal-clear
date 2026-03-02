import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Sidebar from "@/app/components/Sidebar";
import { MemoryRouter } from "react-router";
import { vi, describe, it, beforeEach, expect } from "vitest";

vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(() => ({ data: 72 })),
}));
vi.mock("@/shared/components/ui", () => ({
  useLocalAlert: () => ({
    showLocalAlert: vi.fn(),
    hideLocalAlert: vi.fn(),
    localAlert: { visible: false, message: "" },
  }),
  TooltipProvider: ({ children }: any) => children,
  Tooltip: ({ children }: any) => children,
  TooltipTrigger: ({ children }: any) => children,
  TooltipContent: ({ children }: any) => <span>{children}</span>,
}));
vi.mock("@/domains/graph", () => ({
  Interactions: () => <div>Interactions</div>,
}));

const clipboardWrite = vi.fn();
Object.assign(navigator, {
  clipboard: { writeText: clipboardWrite },
});

describe("Sidebar", () => {
  beforeEach(() => {
    clipboardWrite.mockReset();
  });

  const baseProps: React.ComponentProps<typeof Sidebar> = {
    activeTab: "Risk Details",
    setActiveTab: vi.fn(),
    loading: false,
    jsonData: { address: "0xabc", nodes: [], edges: [] },
    deploymentInfo: {
      address: "0xabc",
      deployer: "0xdef",
      deployer_eoa: "0x123",
      tx_hash: "0x456",
      block_number: 100,
    },
    inputAddress: "0xabc",
    fromBlock: 10,
    toBlock: 20,
    selectedNode: null,
    setSelectedNode: vi.fn(),
    highlightAddress: null,
    setHighlightAddress: vi.fn(),
  };

  const renderWithRouter = (
    ui: React.ReactNode,
    initialEntry = "/graph?address=0xabc",
  ) =>
    render(<MemoryRouter initialEntries={[initialEntry]}>{ui}</MemoryRouter>);

  it("renders contract details and risk score badges", async () => {
    renderWithRouter(<Sidebar {...baseProps} />);

    expect(screen.getByText(/Contract Information/)).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getAllByText(/Medium Risk/i).length).toBeGreaterThan(0),
    );
  });

  it("copies contract address to clipboard", async () => {
    renderWithRouter(<Sidebar {...baseProps} />);
    const copyButtons = screen.getAllByRole("button");
    await userEvent.click(copyButtons[0]);
    expect(clipboardWrite).toHaveBeenCalledWith("0xabc");
  });

  it("shows placeholder when no jsonData", () => {
    renderWithRouter(
      <Sidebar {...baseProps} jsonData={null} inputAddress="" />,
      "/graph",
    );
    expect(screen.getAllByText(/Waiting for an address/)).toHaveLength(2);
  });
});
