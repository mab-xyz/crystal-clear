import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import HomePage from "@/pages/homepage/Home";
import { vi, describe, it, beforeEach, expect } from "vitest";
import { MemoryRouter } from "react-router";

const { useLocalAlertMock, navigateMock } = vi.hoisted(() => ({
  useLocalAlertMock: vi.fn(() => ({
    showLocalAlert: vi.fn(),
    hideLocalAlert: vi.fn(),
  })),
  navigateMock: vi.fn(),
}));

vi.mock("@/domains/graph", () => ({
  GraphLayout: () => <div>Graph Layout</div>,
}));
vi.mock("@/app/contexts/AppContext", () => ({
  useAppContext: () => ({ setGlobalError: vi.fn(), clearGlobalError: vi.fn() }),
}));
vi.mock("@/shared/components/ui", () => ({
  Button: ({ children, ...props }: any) => <button {...props}>{children}</button>,
  useLocalAlert: useLocalAlertMock,
}));
vi.mock("@/utils/defaultAnalyze", () => ({
  getDefaultBlockRange: vi.fn().mockResolvedValue({ fromBlock: 10, toBlock: 20 }),
}));
vi.mock("@/utils/blockRange", () => ({
  validateBlockRange: vi.fn(() => ({ valid: true })),
}));
vi.mock("@/domains/contracts", () => ({
  popularContracts: [],
  getLatestBlock: vi.fn().mockResolvedValue(100),
  getApiAvailability: vi.fn().mockResolvedValue(true),
}));
vi.mock("react-router", async () => {
  const actual = await vi.importActual<typeof import("react-router")>(
    "react-router",
  );
  return {
    ...actual,
    useNavigate: () => navigateMock,
  };
});

describe("HomePage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useLocalAlertMock.mockReset();
    navigateMock.mockReset();
    useLocalAlertMock.mockReturnValue({
      showLocalAlert: vi.fn(),
      hideLocalAlert: vi.fn(),
    });
  });

  const renderHome = () =>
    render(
      <MemoryRouter initialEntries={["/"]}>
        <HomePage />
      </MemoryRouter>,
    );

  it("alerts when submit with empty address", async () => {
    const showLocalAlert = vi.fn();
    useLocalAlertMock.mockReturnValue({
      showLocalAlert,
      hideLocalAlert: vi.fn(),
    });

    renderHome();
    await userEvent.click(screen.getByRole("button", { name: /analyze/i }));
    expect(showLocalAlert).toHaveBeenCalledWith(
      "Please enter a contract address.",
    );
  });

  it("navigates to graph on success", async () => {
    renderHome();
    const input = screen.getByPlaceholderText(/Enter contract address/i);
    await userEvent.type(
      input,
      "0x1234567890abcdef1234567890abcdef12345678",
    );

    await userEvent.click(screen.getByRole("button", { name: /analyze/i }));

    expect(navigateMock).toHaveBeenCalledWith(
      "/graph?address=0x1234567890abcdef1234567890abcdef12345678&from_block=10&to_block=20",
    );
  });
});
