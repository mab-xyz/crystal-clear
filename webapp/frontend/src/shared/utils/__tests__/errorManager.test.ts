import { describe, it, expect, beforeEach, vi } from "vitest";
import { renderHook, act } from "@testing-library/react";

const showLocalAlertMock = vi.fn();

vi.mock("@/shared/components/ui", () => ({
  useLocalAlert: () => ({
    showLocalAlert: showLocalAlertMock,
    hideLocalAlert: vi.fn(),
    localAlert: { visible: false, message: "" },
  }),
}));

import { errorManager } from "@/shared/utils/errorManager";

describe("errorManager", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("stores errors and triggers alert by default", () => {
    const { result } = renderHook(() => errorManager());

    act(() => {
      result.current.setError("form", "Message");
    });

    expect(result.current.errors.form).toEqual(["Message"]);
    expect(showLocalAlertMock).toHaveBeenCalledWith("Message");
  });

  it("can suppress immediate alert", () => {
    const { result } = renderHook(() => errorManager());

    act(() => {
      result.current.setError("api", "Silent", false);
    });

    expect(result.current.errors.api).toEqual(["Silent"]);
    expect(showLocalAlertMock).not.toHaveBeenCalled();
  });

  it("clears a single error type", () => {
    const { result } = renderHook(() => errorManager());

    act(() => {
      result.current.setError("api", "once");
      result.current.clearError("api");
    });

    expect(result.current.errors.api).toBeUndefined();
  });

  it("can clear all errors", () => {
    const { result } = renderHook(() => errorManager());

    act(() => {
      result.current.setError("api", "once");
      result.current.setError("form", "twice");
      result.current.clearError(undefined as unknown as any);
    });

    expect(result.current.errors).toEqual({});
  });
});
