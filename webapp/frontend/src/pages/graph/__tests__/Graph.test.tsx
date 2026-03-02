import { render, act } from "@testing-library/react";
import ContractGraph from "@/pages/graph/Graph";
import { vi, describe, it, beforeEach, expect } from "vitest";
import { MemoryRouter } from "react-router";

const refetchMock = vi.fn();
const setGlobalErrorMock = vi.fn();
const showLocalAlertMock = vi.fn();

vi.mock("@/shared/hooks/useGraphAnalysis", () => ({
  useGraphAnalysis: vi.fn(() => ({
    jsonData: { address: "0xabc" },
    apiAvailability: true,
    loading: false,
    error: null,
    selectedNode: null,
    setSelectedNode: vi.fn(),
    highlightAddress: null,
    setHighlightAddress: vi.fn(),
    refetchData: refetchMock,
    prefetchData: vi.fn(),
    hasData: true,
    hasError: false,
  })),
}));
vi.mock("@/app/contexts/AppContext", () => ({
  useAppContext: () => ({
    state: { currentTab: "Risk Details" },
    setCurrentTab: vi.fn(),
    setGlobalError: setGlobalErrorMock,
  }),
}));
vi.mock("@/shared/components/ui", () => ({
  useLocalAlert: () => ({
    showLocalAlert: showLocalAlertMock,
    hideLocalAlert: vi.fn(),
  }),
}));
vi.mock("@/domains/contracts", () => ({
  getDeploymentInfo: vi.fn().mockResolvedValue(null),
}));
vi.mock("@/app/index", () => ({
  Header: (props: any) => <div data-testid="header" {...props} />,
  Sidebar: (props: any) => <div data-testid="sidebar" {...props} />,
  RiskDetails: () => <div>RiskDetails</div>,
}));
vi.mock("@/domains/graph", () => ({
  GraphLayout: () => <div>GraphLayout</div>,
}));

describe("ContractGraph", () => {
  beforeEach(() => {
    refetchMock.mockClear();
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const renderGraph = (entry: string) =>
    render(
      <MemoryRouter initialEntries={[entry]}>
        <ContractGraph />
      </MemoryRouter>,
    );

  it("refetches when URL contains analysis params", () => {
    renderGraph("/graph?address=0xabc&from_block=1&to_block=2");

    act(() => {
      vi.runAllTimers();
    });

    expect(refetchMock).toHaveBeenCalled();
  });
});
