import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Header from "@/app/components/Header";
import { vi, describe, it, beforeEach, expect } from "vitest";
import { MemoryRouter } from "react-router";

vi.mock("ethers", () => ({ isAddress: vi.fn(() => true) }));
vi.mock("@/utils/blockRange", () => ({
  validateBlockRange: vi.fn(() => ({ valid: true })),
  handleBlockRangeTypeChange: vi.fn(),
}));
vi.mock("@/utils/defaultAnalyze", () => ({
  handleDefaultAnalyze: vi.fn(),
  getDefaultBlockRange: vi.fn(),
}));
vi.mock("@/utils/queries", () => ({
  getDeploymentInfo: vi.fn().mockResolvedValue(null),
  getLatestBlock: vi.fn().mockResolvedValue(123),
  getApiAvailability: vi.fn().mockResolvedValue(true),
}));
vi.mock("@/shared/utils/errorManager", () => ({
  errorManager: () => ({ setError: vi.fn(), errors: {} }),
}));
vi.mock("@/utils/popularContracts", () => ({
  filterOptions: [],
}));

const navigateMock = vi.fn();
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>(
    "react-router",
  );
  return {
    ...actual,
    useNavigate: () => navigateMock,
    Link: ({ children }: any) => <div>{children}</div>,
  };
});

describe("Header", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const setup = async (
    props?: Partial<React.ComponentProps<typeof Header>>,
  ) => {
    const handleSubmit = vi.fn();

    const defaultAnalyze = await import("@/utils/defaultAnalyze");
    vi.mocked(defaultAnalyze.getDefaultBlockRange).mockResolvedValue({
      fromBlock: 90,
      toBlock: 100,
      success: true,
    });
    vi.mocked(defaultAnalyze.handleDefaultAnalyze).mockImplementation(
      async (_address, setFrom, setTo, submitCb) => {
        setFrom("90");
        setTo("100");
        submitCb({} as any);
      },
    );

    render(
      <MemoryRouter>
        <Header
          inputAddress="0xabc"
          setInputAddress={vi.fn()}
          fromBlock="10"
          setFromBlock={vi.fn()}
          toBlock="20"
          setToBlock={vi.fn()}
          handleSubmit={handleSubmit}
          {...props}
        />
      </MemoryRouter>,
    );
    return { handleSubmit };
  };

  it("prevents submission when validation fails", async () => {
    const validateBlockRange = await import("@/utils/blockRange");
    vi.mocked(validateBlockRange.validateBlockRange).mockReturnValueOnce({
      valid: false,
      reason: "Invalid block range.",
    });

    const { handleSubmit } = await setup();
    await userEvent.click(screen.getAllByRole("button", { name: /analyze/i })[0]);
    expect(handleSubmit).not.toHaveBeenCalled();
  });

  it("runs default analyze and updates range", async () => {
    const setFromBlock = vi.fn();
    const setToBlock = vi.fn();
    await setup({ setFromBlock, setToBlock });
    await userEvent.click(screen.getAllByRole("button", { name: /analyze/i })[0]);

    await waitFor(() => {
      expect(setFromBlock).toHaveBeenCalledWith("90");
      expect(setToBlock).toHaveBeenCalledWith("100");
    });
  });
});
