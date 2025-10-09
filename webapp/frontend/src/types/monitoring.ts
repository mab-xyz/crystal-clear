export type MonitoringAction = "subscribe" | "unsubscribe";

export type NotificationMethod = "email";

export interface MonitoringRequest {
  method: NotificationMethod;
  target: string;
  contractAddress: string;
}

export interface MonitoringResponse {
  message: string;
}

export interface MonitoringError {
  status: number;
  message: string;
}

export interface MonitoringResult {
  ok: boolean;
  status: number;
  message?: string;
  error?: string;
}
