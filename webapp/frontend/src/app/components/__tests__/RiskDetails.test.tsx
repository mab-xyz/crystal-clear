import { render, screen } from "@testing-library/react";
import RiskDetails from "@/app/components/RiskDetails";
import { useQuery } from "@tanstack/react-query";
import { vi, describe, it, beforeEach, expect } from "vitest";

vi.mock("@tanstack/react-query", () => ({
  useQuery: vi.fn(),
}));

const useQueryMock = vi.mocked(useQuery);

const makeQueryResult = (overrides = {}) => ({
  data: null,
  error: null,
  isLoading: false,
  refetch: vi.fn(),
  ...overrides,
});

describe("RiskDetails", () => {
  beforeEach(() => {
    useQueryMock.mockReset();

    const defaultResult = makeQueryResult();
    const resultsByKey: Record<string, ReturnType<typeof makeQueryResult>> = {
      proxyInfo: makeQueryResult({
        data: { type: "not a proxy", message: "N/A" },
      }),
      permissionInfo: makeQueryResult({ data: null }),
      verificationInfo: makeQueryResult({ data: null }),
      auditInfo: makeQueryResult({ data: [] }),
    };

    useQueryMock.mockImplementation((options: any) => {
      const key = options?.queryKey?.[0];
      return resultsByKey[key] ?? defaultResult;
    });
  });

  it("shows loading state while any query is pending", () => {
    const defaultResult = makeQueryResult();
    const resultsByKey: Record<string, ReturnType<typeof makeQueryResult>> = {
      proxyInfo: makeQueryResult({ isLoading: true }),
    };

    useQueryMock.mockImplementation((options: any) => {
      const key = options?.queryKey?.[0];
      return resultsByKey[key] ?? defaultResult;
    });

    render(<RiskDetails address="0xabc" />);
    expect(
      screen.getByText("🔍 Fetching Risk Details...", { exact: false }),
    ).toBeInTheDocument();
  });

  it("renders risk cards with fetched data", () => {
    const defaultResult = makeQueryResult();
    const resultsByKey: Record<string, ReturnType<typeof makeQueryResult>> = {
      proxyInfo: makeQueryResult({
        data: { type: "proxy", message: "Proxy message" },
      }),
      permissionInfo: makeQueryResult({
        data: { function: ["transfer"] },
      }),
      verificationInfo: makeQueryResult({
        data: { verification: "verified", verifiedAt: "now" },
      }),
      auditInfo: makeQueryResult({
        data: [{ company: "Trail of Bits", protocol: "A", version: "1.0" }],
      }),
    };

    useQueryMock.mockImplementation((options: any) => {
      const key = options?.queryKey?.[0];
      return resultsByKey[key] ?? defaultResult;
    });

    render(<RiskDetails address="0xabc" />);

    expect(screen.getByText("Immutability")).toBeInTheDocument();
    expect(screen.getByText("Proxy")).toBeInTheDocument();
    expect(screen.getByText("Admin Privileges")).toBeInTheDocument();
    expect(screen.getByText(/1 functions/)).toBeInTheDocument();
    expect(screen.getByText("Verification")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(screen.getByText("Audit")).toBeInTheDocument();
    expect(screen.getByText("Audited")).toBeInTheDocument();
  });

  it("falls back to error details when a fetch fails", () => {
    const defaultResult = makeQueryResult();
    const resultsByKey: Record<string, ReturnType<typeof makeQueryResult>> = {
      proxyInfo: makeQueryResult({ error: new Error("proxy fail") }),
    };

    useQueryMock.mockImplementation((options: any) => {
      const key = options?.queryKey?.[0];
      return resultsByKey[key] ?? defaultResult;
    });

    render(<RiskDetails address="0xabc" />);

    expect(
      screen.getByText(/Failed to fetch proxy information/i),
    ).toBeInTheDocument();
    expect(screen.getAllByText(/Error/i).length).toBeGreaterThan(0);
  });
});
