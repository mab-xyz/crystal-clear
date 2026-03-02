import { render, screen, act, fireEvent } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import {
  LocalAlertProvider,
  useLocalAlert,
} from "@/shared/components/ui/local-alert";

const Harness = () => {
  const { showLocalAlert, hideLocalAlert, localAlert } = useLocalAlert();
  return (
    <div>
      <span data-testid="visible">{String(localAlert.visible)}</span>
      <button onClick={() => showLocalAlert("Hello", 1000)}>show</button>
      <button onClick={() => hideLocalAlert()}>hide</button>
    </div>
  );
};

describe("LocalAlertProvider", () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it("shows and auto hides alert after duration", () => {
    render(
      <LocalAlertProvider>
        <Harness />
      </LocalAlertProvider>,
    );

    fireEvent.click(screen.getByText("show"));

    expect(screen.getByText("Hello")).toBeInTheDocument();
    act(() => {
      vi.advanceTimersByTime(1000);
    });
    expect(screen.queryByText("Hello")).not.toBeInTheDocument();
  });

  it("hides alert immediately via hideLocalAlert", () => {
    render(
      <LocalAlertProvider>
        <Harness />
      </LocalAlertProvider>,
    );

    fireEvent.click(screen.getByText("show"));
    expect(screen.getByText("Hello")).toBeInTheDocument();

    fireEvent.click(screen.getByText("hide"));
    expect(screen.queryByText("Hello")).not.toBeInTheDocument();
  });

  it("throws when hook used outside provider", () => {
    const renderWithoutProvider = () =>
      render(
        // @ts-expect-error intentionally misuse for test
        <Harness />,
      );
    expect(renderWithoutProvider).toThrow(
      "useLocalAlert must be used within a LocalAlertProvider",
    );
  });
});
