import API_BASE_URL from "@/shared/utils/api";
import type {
  MonitoringRequest,
  MonitoringResponse,
  MonitoringResult,
} from "@/types";

const parseJsonSafe = async (response: Response): Promise<Record<string, unknown> | null> => {
  const contentType = response.headers.get("content-type") ?? "";
  if (!contentType.toLowerCase().includes("application/json")) {
    const fallbackText = await response.text();
    return fallbackText ? { message: fallbackText } : null;
  }

  try {
    return (await response.json()) as Record<string, unknown> | null;
  } catch (error) {
    console.error("Failed to parse monitoring response", error);
    return null;
  }
};

const extractMessage = (
  body: Record<string, unknown> | null,
  fallback: string,
): string => {
  const detail = body?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail.trim();
  }

  const message = body?.message;
  if (typeof message === "string" && message.trim()) {
    return message.trim();
  }

  return fallback;
};

const sendMonitoringRequest = async (
  path: string,
  payload: MonitoringRequest,
  fallbackSuccess: string,
  fallbackError: string,
): Promise<MonitoringResult> => {
  try {
    const response = await fetch(`${API_BASE_URL}${path}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Accept: "application/json",
      },
      body: JSON.stringify(payload satisfies MonitoringRequest),
    });

    const body = await parseJsonSafe(response);

    if (!response.ok) {
      return {
        ok: false,
        status: response.status,
        error: extractMessage(body, fallbackError),
      } satisfies MonitoringResult;
    }

    return {
      ok: true,
      status: response.status,
      message: extractMessage(body, fallbackSuccess),
    } satisfies MonitoringResult;
  } catch (error) {
    const message =
      error instanceof Error ? error.message : "Failed to reach monitoring service.";
    return {
      ok: false,
      status: 0,
      error: message,
    } satisfies MonitoringResult;
  }
};

export const subscribeToContract = async (
  payload: MonitoringRequest,
): Promise<MonitoringResult> => {
  const fallbackSuccess = "Subscribed successfully." satisfies MonitoringResponse["message"];
  const fallbackError = "Failed to subscribe.";
  return sendMonitoringRequest(
    "/monitor/subscribe",
    payload,
    fallbackSuccess,
    fallbackError,
  );
};

export const unsubscribeFromContract = async (
  payload: MonitoringRequest,
): Promise<MonitoringResult> => {
  const fallbackSuccess = "Unsubscribed successfully." satisfies MonitoringResponse["message"];
  const fallbackError = "Failed to unsubscribe.";
  return sendMonitoringRequest(
    "/monitor/unsubscribe",
    payload,
    fallbackSuccess,
    fallbackError,
  );
};

export type { MonitoringResult };
