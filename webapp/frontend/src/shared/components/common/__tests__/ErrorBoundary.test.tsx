import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, it, expect, vi } from "vitest";
import { ErrorBoundary } from "@/shared/components/common/ErrorBoundary";

const ProblemChild = () => {
  throw new Error("Boom!");
};

describe("ErrorBoundary", () => {
  it("renders fallback when child throws", () => {
    render(
      <ErrorBoundary>
        <ProblemChild />
      </ErrorBoundary>,
    );

    expect(screen.getByText(/Something went wrong/)).toBeInTheDocument();
    expect(screen.getByText(/Boom!/)).toBeInTheDocument();
  });

  it("invokes onError callback", () => {
    const onError = vi.fn();
    render(
      <ErrorBoundary onError={onError}>
        <ProblemChild />
      </ErrorBoundary>,
    );
    expect(onError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({ componentStack: expect.any(String) }),
    );
  });

  it("recovers when reset button clicked", async () => {
    const { rerender } = render(
      <ErrorBoundary>
        <ProblemChild />
      </ErrorBoundary>,
    );

    rerender(
      <ErrorBoundary>
        <div>OK</div>
      </ErrorBoundary>,
    );

    await userEvent.click(screen.getByRole("button", { name: /Try Again/i }));

    expect(screen.getByText("OK")).toBeInTheDocument();
  });
});
